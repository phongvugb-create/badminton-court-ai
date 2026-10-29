"""Natural-language interval availability: clarify ambiguity, then verify one court
is free throughout the requested interval. Never consult static SRS for live slots.
"""
import re
import unicodedata
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict


def fold(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower().replace('đ', 'd')) if not unicodedata.combining(c))


TIME_RANGE = re.compile(
    r'(?<![\d/-])(\d{1,2})(?::([0-5]\d)|\s*(?:gio|h)(?:\s*([0-5]\d))?)?\s*(sang|toi|chieu|trua)?\s*'
    r'(?:den|toi|[-–])\s*(\d{1,2})(?::([0-5]\d)|\s*(?:gio|h)(?:\s*([0-5]\d))?)?\s*(sang|toi|chieu|trua)?(?![\d/])'
)


def is_availability(text):
    q = fold(text)
    return bool(re.search(r'\b(?:san|slot)\b', q) and re.search(r'\b(?:trong|con cho|dat duoc)\b', q)) and not re.search(r'\b(?:quy dinh|chinh sach|huong dan|cach|huy|hoan coc)\b', q)


def is_booking(text):
    q = fold(text)
    return bool(re.search(r'\b(?:dat|thue)\s+(?:(?:\d+|mot|vai)\s+)?san\b', q)) and not re.search(
        r'\b(?:quy dinh|chinh sach|huong dan|quy trinh|cach|huy|hoan|xac nhan|dong y|nhu the nao|la gi|bao lau)\b', q)


def range_question(message, history=None):
    if (is_availability(message) or is_booking(message)) and TIME_RANGE.search(fold(message)):
        return message
    # A short answer to our missing date/period question continues only the
    # immediately preceding user's availability question, never bot/page context.
    q = fold(message)
    if len(q.split()) <= 12 and re.search(r'\b(?:sang|toi|chieu|hom nay|ngay mai)\b', q) and not TIME_RANGE.search(q):
        recent = (history or [])[-8:]
        for index in range(len(recent) - 1, -1, -1):
            item = recent[index]
            if item.get('role', item.get('sender')) not in ('user', 'customer'):
                continue
            previous = str(item.get('content') or item.get('text') or '')
            if fold(previous) == q:
                continue
            if TIME_RANGE.search(fold(previous)):
                resolved = range_question(previous, recent[:index])
                if resolved:
                    return resolved + ' ' + message
            break
    # Scheduling replies may omit "sân" entirely and include the browser's
    # current message in history. Only continue the recent user topic.
    if len(q.split()) <= 24 and TIME_RANGE.search(q) and not re.search(
        r'\b(?:quy dinh|chinh sach|huong dan|cach|huy|hoan)\b', q
    ):
        for item in reversed((history or [])[-8:]):
            if item.get('role', item.get('sender')) not in ('user', 'customer'):
                continue
            previous = str(item.get('content') or item.get('text') or '')
            if fold(previous) == q:
                continue
            if is_booking(previous) or is_availability(previous):
                return message + ', ' + previous
            break
    if len(q.split()) <= 12 and re.search(r'\b(?:hom nay|mai|ngay kia|sang|toi|chieu|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})\b', q):
        answers = []
        for item in reversed((history or [])[-8:]):
            if item.get('role', item.get('sender')) not in ('user', 'customer'):
                continue
            previous = str(item.get('content') or item.get('text') or '')
            if fold(previous) == q:
                continue
            if (is_availability(previous) or is_booking(previous)) and TIME_RANGE.search(fold(previous)):
                return ' '.join([previous, *reversed(answers), message])
            if len(previous.split()) <= 8 and re.search(r'\b(?:hom nay|mai|ngay kia|sang|toi|chieu|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})\b', fold(previous)):
                answers.append(previous)
                continue
            break
    return None


def parse_range(text):
    q = fold(text)
    match = TIME_RANGE.search(q)
    if not match:
        return None
    sh, sm1, sm2, sp, eh, em1, em2, ep = match.groups()
    sh, eh = int(sh), int(eh)
    sm, em = int(sm1 or sm2 or 0), int(em1 or em2 or 0)
    global_period = re.search(r'\b(?:buoi\s+)?(sang|chieu|toi|trua)\s*(?:nay|mai)?\b', q[match.end():])
    period = global_period.group(1) if global_period else None
    if not period:
        before = re.search(r'\b(sang|chieu|toi|trua)\s+(?:nay\s+|mai\s+)?(?:tu\s+)?$', q[:match.start()])
        period = before.group(1) if before else None
    sp, ep = sp or period or ep, ep or period or sp
    if sh > 23 or eh > 24 or (eh == 24 and em):
        return {'error': 'Giờ không hợp lệ. Bạn nhập khoảng giờ trong cùng ngày, ví dụ 19:00–21:00 nhé.'}
    ambiguous = (1 <= sh <= 12 and not sp) or (1 <= eh <= 12 and not ep)
    # Colon notation is an explicit 24-hour clock (07:00 vs 19:00).
    if sm1 is not None and em1 is not None:
        ambiguous = False
    if sp in ('toi', 'chieu') and 1 <= sh < 12:
        sh += 12
    if ep in ('toi', 'chieu') and 1 <= eh < 12:
        eh += 12
    start, end = sh * 60 + sm, eh * 60 + em
    if not ambiguous and end <= start:
        return {'error': 'Bạn cho biết lại khoảng giờ kết thúc sau giờ bắt đầu nhé. Hiện tôi tra lịch trong cùng một ngày.'}
    day = None
    raw = re.search(r'\b\d{4}-\d{2}-\d{2}\b', q)
    local = re.search(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b', q)
    try:
        if raw:
            day = date.fromisoformat(raw.group()).isoformat()
        elif local:
            d, m, y = map(int, local.groups())
            day = date(y, m, d).isoformat()
        else:
            today = datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).date()
            if re.search(r'\bngay kia\b', q):
                day = (today + timedelta(days=2)).isoformat()
            elif re.search(r'\b(?:ngay mai|toi mai|sang mai|chieu mai)\b', q):
                day = (today + timedelta(days=1)).isoformat()
            elif re.search(r'\b(?:hom nay|toi nay|sang nay|chieu nay)\b', q):
                day = today.isoformat()
    except ValueError:
        return {'error': 'Ngày không hợp lệ. Bạn nhập ngày theo dạng DD/MM/YYYY nhé.'}
    location = re.search(r'\b(?:o|tai|khu vuc)\s+(.+?)(?=\s+(?:co|con|trong|tu|luc|hom|ngay|buoi|sang|chieu|toi)\b|[?!,]|$)', q)
    return {'start': start, 'end': end, 'date': day, 'ambiguous': ambiguous,
            'location': location.group(1).strip() if location else None}


def format_time(minutes):
    return f'{minutes // 60:02d}:{minutes % 60:02d}'


def continuously_available(slots, start, end):
    courts = defaultdict(list)
    for slot in slots:
        courts[slot['court_id']].append(slot)
    result = []
    for rows in courts.values():
        intervals = []
        blocked = False
        for row in rows:
            def minutes(value):
                h, m = str(value).split(':')[:2]
                return int(h) * 60 + int(m)
            a, b = minutes(row['start_time']), minutes(row['end_time'])
            if a < end and b > start:
                if row.get('effective_status') != 'AVAILABLE':
                    blocked = True
                intervals.append((a, b, row))
        if blocked:
            continue
        cursor = start
        for a, b, row in sorted(intervals, key=lambda item: (item[0], item[1])):
            if a > cursor:
                break
            cursor = max(cursor, b)
        if cursor >= end:
            result.append(rows[0])
    return result


async def answer_range(request, db, sync_inventory, availability_tool):
    from sqlalchemy import select
    from app.models.all_models import Facility
    def response(text, status='success', retrieval='supported'):
        return {'answer': text, 'reply': text, 'status': status, 'retrieval_status': retrieval, 'sources': [], 'provider': 'business_tools'}
    if request.get('error'):
        return response(request['error'], 'clarification_required', None)
    missing = []
    if not request['date']:
        missing.append('Bạn muốn tìm sân vào **ngày nào**?')
    if request['ambiguous']:
        missing.append('Khoảng **7–9 giờ** bạn muốn hỏi là buổi **sáng hay tối**?' if request['start'] == 420 and request['end'] == 540 else 'Bạn muốn khung giờ **sáng hay chiều/tối**? Bạn có thể nhập giờ dạng 24 giờ, ví dụ 19:00–21:00.')
    if missing:
        return response('Tôi có thể tra lịch sân trống cho bạn. ' + ' '.join(missing), 'clarification_required', None)
    if db is None:
        return response('Hiện tôi chưa kết nối được dữ liệu lịch sân. Bạn vui lòng thử lại sau.', 'error', 'data_unavailable')
    try:
        await sync_inventory(db, date=request['date'])
        rows = (await db.execute(select(Facility.id, Facility.name, Facility.address).where(Facility.is_approved == True))).all()
        location = request['location']
        if location:
            rows = [r for r in rows if location in fold(f'{r.name} {r.address}')]
        if not rows:
            return response('Chưa tìm thấy cơ sở phù hợp khu vực bạn hỏi. Bạn cho biết tên quận hoặc cụm sân cụ thể nhé.', 'clarification_required', 'no_results')
        matches = []
        for facility in rows:
            result = await availability_tool(db=db, facility_id=facility.id, date=request['date'], time=None, limit=500)
            if result.get('status') not in ('success', 'no_results') or result.get('reason') == 'availability_unverified' or len(result.get('data', [])) >= 500:
                return response('Tôi chưa thể xác minh đầy đủ lịch trống và trạng thái giữ chỗ lúc này. Bạn vui lòng thử lại sau hoặc xem ma trận lịch sân.', 'availability_unverified', 'data_unavailable')
            for court in continuously_available(result.get('data', []), request['start'], request['end']):
                matches.append(f"- **{facility.name} — Sân {court['court_number']}** · {facility.address}")
        label = f"{request['date']} · {format_time(request['start'])}–{format_time(request['end'])}"
        if not matches:
            return response(f'Tôi chưa tìm thấy sân trống liên tục suốt khoảng **{label}** trong các cơ sở phù hợp. Bạn thử đổi giờ hoặc khu vực nhé.', retrieval='no_results')
        text = f"**Sân còn trống liên tục {label}:**\n" + '\n'.join(matches[:30])
        text += '\n\nTrạng thái được kiểm tra tại thời điểm tra cứu; chỉ được giữ chỗ sau khi bạn xác nhận.'
        return response(text)
    except Exception:
        return response('Hiện tôi chưa đọc được lịch sân. Bạn vui lòng thử lại sau; tôi chưa thể xác nhận sân trống.', 'error', 'data_unavailable')
