"""Persistent room event notifications. All functions operate on a locked snapshot."""
import hashlib
import time
import copy


def members(room, users):
    by_id = {str(u['id']): u for u in users if u.get('id') is not None}
    result = {}
    entries = list(room.get('players') or []) + [{'id': room.get('host_id') or room.get('host_user_id') or room.get('owner_id'), 'name': room.get('host_name')}]
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        uid = entry.get('id')
        user = by_id.get(str(uid))
        if uid is None:  # legacy names only; never send to an ambiguous account
            matches = [u for u in users if entry.get('name') and u.get('name') == entry['name']]
            user = matches[0] if len(matches) == 1 else None
        if user:
            result[str(user['id'])] = user
    return result


def assign_room_numbers(previous, rooms):
    old = {str(r['id']): r for r in previous}
    used = {int(r['room_number']) for r in previous if str(r.get('room_number', '')).isdigit()}
    counter = max(used or {0})
    for room in rooms:
        number = old.get(str(room['id']), {}).get('room_number')
        if number is None:
            counter += 1
            number = counter
        room['room_number'] = number  # cannot be overwritten by a stale browser


def build_room_notifications(previous, rooms, users):
    old = {str(r['id']): r for r in previous}
    result = []
    for room in rooms:
        before = old.get(str(room['id']))
        if before is None:
            continue  # creation does not announce pre-existing welcome messages
        roster = members(room, users)
        earlier = members(before, users)
        label = f"#{room.get('room_number', room['id'])} · {room.get('room_name', 'Phòng ghép')}"
        events = []
        for uid in roster.keys() - earlier.keys():
            user = roster[uid]
            events.append((f"join:{uid}", 'ROOM_MEMBER_JOINED', uid, user.get('name', 'Thành viên'),
                           f"{user.get('name', 'Thành viên')} đã tham gia phòng {label}.", 'Thành viên mới vào phòng'))
        seen_messages = {str(m.get('id')) for m in before.get('chat_messages', []) if isinstance(m, dict) and m.get('id')}
        for message in room.get('chat_messages') or []:
            if not isinstance(message, dict) or not message.get('id') or str(message['id']) in seen_messages or message.get('isAI'):
                continue
            sender = str(message.get('sender_id') or '')
            if sender not in roster:
                candidates = [uid for uid, user in roster.items() if user.get('name') == message.get('sender')]
                if len(candidates) != 1:
                    continue
                sender = candidates[0]
            name = roster[sender].get('name', 'Thành viên')
            events.append((f"message:{message['id']}", 'ROOM_CHAT_MESSAGE', sender, name,
                           f"{name}: {str(message.get('text', ''))[:180]}", f"Tin nhắn mới · Phòng #{room.get('room_number', room['id'])}"))
        for key, kind, sender, name, content, title in events:
            for uid, user in roster.items():
                if uid == sender:
                    continue
                identity = f"{room['id']}:{key}:{uid}"
                result.append({
                    'id': 'room_n_' + hashlib.sha256(identity.encode()).hexdigest()[:32],
                    'type': kind, 'recipient_id': user['id'], 'recipient_name': user.get('name'),
                    'sender_id': roster[sender]['id'], 'sender_name': name,
                    'room_id': room['id'], 'room_number': room.get('room_number'),
                    'title': title, 'content': content, 'is_read': False,
                    'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    'timestamp': int(time.time() * 1000),
                })
    return result


class RoomError(ValueError):
    def __init__(self, status, message):
        self.status = status
        super().__init__(message)


def tier_group(profile):
    raw = profile.get('skill_tier_id') or profile.get('required_tier_id') or profile.get('host_tier_id')
    if raw is None:
        raw = {'Yếu': 1, 'Trung bình': 3, 'Khá': 5}.get(profile.get('skill_tier') or profile.get('required_tier'))
    if raw is None:
        elo = float(profile.get('elo_rating') or 1650)
        raw = next((i + 1 for i, maximum in enumerate([950, 1150, 1350, 1550, 1750, 1950]) if elo <= maximum), 7)
    return 1 if int(raw) <= 2 else 3 if int(raw) <= 4 else 5


def join_room(data, user_id, room_id):
    """Validate using the latest server roster. Caller holds CENTRAL_DATABASE_LOCK."""
    user = next((u for u in data.get('users', []) if str(u.get('id')) == str(user_id)), None)
    if not user:
        raise RoomError(401, 'Vui lòng đăng nhập lại.')
    original = next((r for r in data.get('matchmaking_rooms', []) if str(r.get('id')) == str(room_id)), None)
    if not original:
        raise RoomError(404, 'Không tìm thấy phòng.')
    room = copy.deepcopy(original)
    roster = members(room, data.get('users', []))
    if str(user_id) in roster:
        return room, False
    if room.get('visibility') == 'INVITE_ONLY':
        invited = {str(x) for x in room.get('invited_player_ids', [])}
        if str(user_id) not in invited:
            raise RoomError(403, 'Phòng riêng chỉ dành cho người được mời.')
    capacity = int(room.get('max_players') or 4)
    count = max(len(room.get('players') or []), int(room.get('current_players') or 0))
    if room.get('status', 'OPEN') != 'OPEN' or count >= capacity:
        raise RoomError(409, 'Phòng đã đủ người hoặc đã đóng.')
    allowed = {'same': 0, 'adjacent': 2, 'all': 10}.get(room.get('match_tolerance', 'same'), 0)
    if abs(tier_group(user) - tier_group(room)) > allowed:
        raise RoomError(403, 'Cấp bậc của bạn chưa phù hợp điều kiện phòng.')
    players = room.setdefault('players', [])
    if not players and roster:
        players.extend({'id': u['id'], 'name': u.get('name'), 'role': 'Host'} for u in roster.values())
    # Preserve occupied legacy slots without inventing a real recipient for them.
    while len(players) < count:
        players.append({'id': f"legacy-member-{room_id}-{len(players)}", 'name': 'Thành viên cũ'})
    players.append({'id': user['id'], 'name': user.get('name'), 'photo': user.get('photo'),
                    'tier_id': user.get('skill_tier_id') or tier_group(user),
                    'tier': user.get('skill_tier'), 'role': 'Member'})
    room['current_players'] = len(players)
    if len(players) >= capacity:
        room['status'] = 'MATCHED'
    room.setdefault('chat_messages', []).append({
        'id': f"join_{room_id}_{user_id}", 'sender': '🤖 AI Match Referee',
        'text': f"{user.get('name', 'Thành viên')} đã tham gia phòng.", 'isAI': True,
        'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    })
    return room, True
