"""Two tabs sharing one browser cookie jar, real HTTP, isolated fake users/store."""
import http.cookiejar
import json
import unittest
import urllib.request
import urllib.error
from unittest.mock import patch, AsyncMock
import server
from test_room_notifications import RoomNotificationTests as Fixture


class TabSessionTests(unittest.TestCase):
    create_room = Fixture.create_room

    def setUp(self):
        Fixture.setUp(self)
        for user in self.store.data['users']:
            user.update(phone=f"090000000{user['id']}", password='test-only-password', role='CUSTOMER')
        for method in ['remaining_lock_seconds', 'clear_failed_logins']:
            guard = patch.object(server, method, new=AsyncMock(return_value=0))
            guard.start()
            self.addCleanup(guard.stop)
        self.cookies = http.cookiejar.CookieJar()
        self.browser = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))
        self.a = self.login(1)
        self.b = self.login(2)

    def tearDown(self):
        Fixture.tearDown(self)

    def request(self, path, session=None, body=None):
        headers = {'Content-Type': 'application/json', 'Origin': self.base}
        if session is not None:
            headers['X-Tab-Session'] = session
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
        try:
            with self.browser.open(req, timeout=5) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            raw = e.read()
            return e.code, json.loads(raw) if raw else {}

    def login(self, uid):
        code, result = self.request('/api/login', body={'phone':f'090000000{uid}', 'password':'test-only-password'})
        self.assertEqual(code, 200)
        self.assertNotIn('access_token', result)
        self.assertNotIn('password', result['user'])
        return result['tab_session_id']

    def test_shared_cookie_accounts_stay_independent(self):
        self.assertNotEqual(self.a, self.b)
        self.assertEqual(self.request('/api/auth/me', self.a)[1]['user']['id'], 1)
        self.assertEqual(self.request('/api/auth/me', self.b)[1]['user']['id'], 2)
        # Legacy cookie is deliberately user 2; tab A still resolves user 1.
        self.assertEqual(self.request('/api/auth/me')[1]['user']['id'], 2)
        tab_cookies = [c for c in self.cookies if c.name.startswith('auth_tab_')]
        self.assertEqual(len(tab_cookies), 2)
        self.assertTrue(all(c.has_nonstandard_attr('HttpOnly') for c in tab_cookies))

    def test_join_and_send_as_both_users_in_same_browser(self):
        status, result = self.request('/api/matchmaking/rooms/100/join', self.b, {'expected_user_id':2})
        self.assertEqual(status,200)
        self.assertEqual(result['room']['current_players'],2)
        self.assertEqual(self.store.data['notifications'][0]['recipient_id'],1)
        for uid, session in [(1,self.a),(2,self.b)]:
            status, result = self.request('/api/chat/rooms/100/messages', session, {'id':f'm{uid}', 'text':f'Hello from {uid}', 'expected_user_id':uid})
            self.assertEqual(status,200)
            self.assertEqual(result['message']['sender_id'],uid)
        notices = [n for n in self.store.data['notifications'] if n['type']=='ROOM_CHAT_MESSAGE']
        self.assertEqual({(n['sender_id'],n['recipient_id']) for n in notices},{(1,2),(2,1)})

    def test_logout_one_tab_does_not_logout_other(self):
        self.assertEqual(self.request('/api/logout', self.a, {})[0],200)
        self.assertEqual(self.request('/api/auth/me', self.a)[0],401)
        self.assertEqual(self.request('/api/auth/me', self.b)[1]['user']['id'],2)

    def test_invalid_locator_never_falls_back_to_another_user(self):
        for locator in ['missing_session_12345678', 'bad']:
            self.assertEqual(self.request('/api/auth/me', locator)[0],401)

    def test_sse_uses_tab_locator_without_token_in_url(self):
        self.request('/api/matchmaking/rooms/100/join',self.b,{'expected_user_id':2})
        # Native EventSource cannot set headers, so it carries only a public locator.
        req = urllib.request.Request(self.base + '/api/chat/rooms/100/events?tab_session=' + self.a)
        with self.browser.open(req,timeout=5) as stream:
            self.assertIn('text/event-stream',stream.headers['Content-Type'])
            self.assertEqual(stream.readline().strip(),b': connected')
            self.request('/api/chat/rooms/100/messages',self.b,{'id':'sse-test','text':'Realtime hello','expected_user_id':2})
            line = stream.readline()
            while not line.startswith(b'data:'):
                line=stream.readline()
            event=json.loads(line[5:])
            self.assertEqual(event['sender_id'],2)
            self.assertEqual(event['text'],'Realtime hello')


if __name__=='__main__':
    unittest.main()
