"""Real local HTTP requests with independent authenticated users and an isolated store."""
import copy
from concurrent.futures import ThreadPoolExecutor
import http.server
import json
import threading
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error
import server


class Store:
    def __init__(self):
        self.data = {'users': [{'id': i, 'name': f'Player {i}', 'skill_tier_id': 5} for i in range(1, 6)],
                     'matchmaking_rooms': [], 'notifications': []}

    def load_data(self):
        return copy.deepcopy(self.data)

    def save_data(self, data):
        self.data = copy.deepcopy(data)


class RoomNotificationTests(unittest.TestCase):
    def setUp(self):
        self.store = Store()
        self.patch = patch.object(server, 'db_manager', self.store)
        self.patch.start()
        class QuietHandler(server.BadmintonServerHandler):
            def log_message(self, *args):
                pass
        self.httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        self.httpd.daemon_threads = True
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.httpd.server_port}'
        self.create_room()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
        self.patch.stop()

    def create_room(self, rid=100, capacity=4, **extra):
        room = {'id': rid, 'host_id': 1, 'host_name': 'Player 1', 'room_name': 'Test room',
                'players': [{'id': 1, 'name': 'Player 1', 'role': 'Host'}], 'current_players': 1,
                'max_players': capacity, 'status': 'OPEN', 'required_tier_id': 5, 'chat_messages': [], **extra}
        server._save_central_database_update({'matchmaking_rooms': [room]})

    def request(self, path, user=None, body=None, cookie_user=None):
        headers = {'Content-Type': 'application/json'}
        if user:
            headers['Authorization'] = 'Bearer ' + server.create_access_token(user, 'CUSTOMER')
        if cookie_user:
            headers['Cookie'] = 'auth_token=' + server.create_access_token(cookie_user, 'CUSTOMER')
            headers['Origin'] = self.base
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=3) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            raw = error.read()
            return error.code, json.loads(raw) if raw else {}

    def join(self, user, rid=100):
        return self.request(f'/api/matchmaking/rooms/{rid}/join', user, {})

    def test_room_number_stable_across_stale_save(self):
        first = self.store.data['matchmaking_rooms'][0]['room_number']
        self.assertEqual(first, 1)
        server._save_central_database_update({'matchmaking_rooms': [{'id': 100, 'room_number': 999}]})
        self.assertEqual(self.store.data['matchmaking_rooms'][0]['room_number'], first)
        self.create_room(101)
        self.assertEqual(self.store.data['matchmaking_rooms'][1]['room_number'], 2)

    def test_join_notifies_host_and_other_members_not_joiner(self):
        self.assertEqual(self.join(2)[0], 200)
        self.assertEqual(self.join(3)[0], 200)
        notices = [n for n in self.store.data['notifications'] if n['sender_id'] == 3]
        self.assertEqual({n['recipient_id'] for n in notices}, {1, 2})
        self.assertTrue(all(n['type'] == 'ROOM_MEMBER_JOINED' for n in notices))
        self.assertTrue(all('Player 3' in n['content'] and '#1' in n['content'] for n in notices))

    def test_join_retry_is_idempotent_even_after_room_fills(self):
        self.create_room(101, capacity=2)
        self.join(2, 101)
        count = len(self.store.data['notifications'])
        status, result = self.join(2, 101)
        self.assertEqual(status, 200)
        self.assertFalse(result['joined'])
        self.assertEqual(len(self.store.data['notifications']), count)

    def test_last_slot_race(self):
        self.create_room(101, capacity=2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda uid: self.join(uid, 101)[0], [2, 3]))
        self.assertEqual(sorted(results), [200, 409])
        room = next(r for r in self.store.data['matchmaking_rooms'] if r['id'] == 101)
        self.assertEqual(len(room['players']), 2)

    def test_guest_and_private_room_rejected(self):
        self.assertEqual(self.join(None)[0], 401)
        self.create_room(101, visibility='INVITE_ONLY', invited_player_ids=[2])
        self.assertEqual(self.join(3, 101)[0], 403)
        self.assertEqual(self.join(2, 101)[0], 200)

    def test_chat_notifications_all_other_members_and_retry(self):
        self.join(2)
        self.join(3)
        body = {'id': 'msg1', 'text': 'Hẹn lúc 18h nhé', 'sender': 'Impersonated host'}
        status, result = self.request('/api/chat/rooms/100/messages', 2, body)
        self.assertEqual(status, 200)
        self.assertEqual(result['message']['sender'], 'Player 2')
        self.assertEqual(result['message']['sender_id'], 2)
        notices = [n for n in self.store.data['notifications'] if n['type'] == 'ROOM_CHAT_MESSAGE']
        self.assertEqual({n['recipient_id'] for n in notices}, {1, 3})
        self.assertTrue(all('18h' in n['content'] for n in notices))
        self.request('/api/chat/rooms/100/messages', 2, body)
        self.assertEqual(len([n for n in self.store.data['notifications'] if n['type'] == 'ROOM_CHAT_MESSAGE']), 2)

    def test_nonmember_cannot_send_or_subscribe(self):
        self.assertEqual(self.request('/api/chat/rooms/100/messages', 5, {'text': 'intrude'})[0], 403)
        self.assertEqual(self.request('/api/chat/rooms/100/events', 5)[0], 403)
        self.assertFalse(self.store.data['notifications'])

    def test_read_state_survives_stale_snapshot(self):
        self.join(2)
        notification = copy.deepcopy(self.store.data['notifications'][0])
        server._save_central_database_update({'notifications': [{**notification, 'is_read': True}]})
        server._save_central_database_update({'notifications': [notification]})
        self.assertTrue(self.store.data['notifications'][0]['is_read'])

    def test_legacy_roster_sync_also_generates_notification(self):
        server._save_central_database_update({'matchmaking_rooms': [{'id': 100, 'players': [{'id': 2, 'name': 'Player 2'}]}]})
        self.assertEqual(len(self.store.data['notifications']), 1)
        self.assertEqual(self.store.data['notifications'][0]['recipient_id'], 1)

    def test_same_name_different_id_is_not_a_member(self):
        self.store.data['users'][4]['name'] = 'Player 1'
        self.assertEqual(self.request('/api/chat/rooms/100/messages', 5, {'text': 'intrude'})[0], 403)

    def test_shared_cookie_cannot_join_as_the_wrong_account(self):
        status, result = self.request('/api/matchmaking/rooms/100/join', user=2, body={'expected_user_id': 2}, cookie_user=1)
        self.assertEqual(status, 409)
        self.assertIn('Phiên đăng nhập', result['detail'])
        self.assertEqual(self.store.data['matchmaking_rooms'][0]['current_players'], 1)
        status, result = self.request('/api/matchmaking/rooms/100/join', body={'expected_user_id': 2}, cookie_user=2)
        self.assertEqual(status, 200)
        self.assertEqual(result['actor_user_id'], '2')
        self.assertEqual({p['id'] for p in result['room']['players']}, {1, 2})
        self.assertEqual(self.store.data['notifications'][0]['recipient_id'], 1)

    def test_legacy_name_only_member_repaired_without_duplicate(self):
        room = self.store.data['matchmaking_rooms'][0]
        room['players'].append({'name': 'Player 2'})
        room['current_players'] = 2
        status, result = self.join(2)
        self.assertEqual(status, 200)
        self.assertEqual(len(result['room']['players']), 2)
        self.assertEqual({p['id'] for p in result['room']['players']}, {1, 2})
        self.assertEqual(self.request('/api/chat/rooms/100/messages',2,{'text':'Now I can chat','expected_user_id':2})[0],200)

    def test_roster_version_increases_only_when_members_change(self):
        before = self.store.data['matchmaking_rooms'][0]['_membership_version']
        _, result = self.join(2)
        after = result['room']['_membership_version']
        self.assertGreater(after,before)
        _, retry = self.join(2)
        self.assertEqual(retry['room']['_membership_version'],after)

    def test_message_rejects_session_identity_mismatch(self):
        self.join(2)
        status,_ = self.request('/api/chat/rooms/100/messages',body={'text':'Wrong actor','expected_user_id':2},cookie_user=1)
        self.assertEqual(status,409)
        self.assertFalse([n for n in self.store.data['notifications'] if n['type']=='ROOM_CHAT_MESSAGE'])

    def test_conflicting_host_metadata_does_not_create_phantom_membership(self):
        # Exact symptom: a nonmember is reported already joined because a stale
        # host_id identifies them even though only the real host is in players.
        self.store.data['matchmaking_rooms'][0]['host_id'] = 2
        status, result = self.request('/api/matchmaking/rooms/100/join',2,{'expected_user_id':2})
        self.assertEqual(status,200)
        self.assertTrue(result['joined'])
        self.assertEqual(len(result['room']['players']),2)
        self.assertEqual(self.store.data['notifications'][0]['recipient_id'],1)


if __name__ == '__main__':
    unittest.main()
