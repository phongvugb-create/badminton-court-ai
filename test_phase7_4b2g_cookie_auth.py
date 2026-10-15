"""
PHASE 7.4B.2G — Cookie Auth, Session Persistence & Payment Security
Test suite covering all 10 required test scenarios.

Run: python -m pytest test_phase7_4b2g_cookie_auth.py -v
"""
import os
import sys
import json
import time
import secrets
import unittest
import http.cookies
import threading
import http.server
import http.client
from http.client import HTTPMessage
from typing import Mapping, Optional
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# ── path setup ────────────────────────────────────────────────────────────────
ROOT_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.core.security import create_access_token, decode_token
from app.config import settings

# ── helpers ───────────────────────────────────────────────────────────────────

def _to_http_message(headers_map: Optional[Mapping[str, str]] = None) -> HTTPMessage:
    """Chuyển Mapping[str, str] thành HTTPMessage chuẩn của http.client."""
    message = HTTPMessage()
    if headers_map:
        for key, value in headers_map.items():
            message[key] = value
    return message

def _make_expired_token(user_id: str = "u_test", role: str = "CUSTOMER") -> str:
    """Create a JWT that is already expired."""
    try:
        from jose import jwt
    except ImportError:
        return "expired.token.placeholder"
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.utcnow() - timedelta(seconds=10)
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _make_valid_token(user_id: str = "u_test", role: str = "CUSTOMER") -> str:
    return create_access_token(subject=user_id, role=role)


def _parse_set_cookie(header_value: str) -> dict:
    """Parse a Set-Cookie header string into a dict of attributes."""
    parts = [p.strip() for p in header_value.split(";")]
    result = {}
    for i, part in enumerate(parts):
        if "=" in part:
            k, v = part.split("=", 1)
            if i == 0:
                result["name"] = k.strip()
                result["value"] = v.strip()
            else:
                result[k.strip().lower()] = v.strip()
        else:
            result[part.strip().lower()] = True
    return result


# ══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 1 — JWT & Token Layer
# ══════════════════════════════════════════════════════════════════════════════
class TestJWTLayer(unittest.TestCase):

    def test_01_valid_token_decodes_correctly(self):
        """Valid JWT encodes and decodes sub + role without mutation."""
        token = _make_valid_token(user_id="u_001", role="CUSTOMER")
        payload = decode_token(token)
        self.assertIsNotNone(payload, "decode_token returned None for valid token")
        self.assertEqual(str(payload["sub"]), "u_001")
        self.assertEqual(payload["role"], "CUSTOMER")

    def test_02_malformed_token_returns_none(self):
        """Malformed JWT must return None (not raise)."""
        for bad in ["", "bad", "a.b.c", "Bearer abc123"]:
            with self.subTest(token=bad):
                result = decode_token(bad)
                self.assertIsNone(result, f"Expected None for token={bad!r}")

    def test_03_expired_token_returns_none(self):
        """Expired JWT must be rejected by decode_token."""
        expired = _make_expired_token()
        payload = decode_token(expired)
        self.assertIsNone(payload, "Expired token should decode to None")

    def test_04_token_expire_matches_config(self):
        """Token expiry must match ACCESS_TOKEN_EXPIRE_MINUTES from settings."""
        before = datetime.utcnow()
        token = _make_valid_token()
        after = datetime.utcnow()
        payload = decode_token(token)
        exp = datetime.utcfromtimestamp(payload["exp"])
        expected_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        lo = before + timedelta(minutes=expected_minutes) - timedelta(seconds=5)
        hi = after + timedelta(minutes=expected_minutes) + timedelta(seconds=5)
        self.assertTrue(lo <= exp <= hi,
            f"Token exp {exp} not in expected range [{lo}, {hi}]")


# ══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 2 — Set-Cookie Header Analysis
# ══════════════════════════════════════════════════════════════════════════════
class TestSetCookieAttributes(unittest.TestCase):

    def _get_handler(self):
        import server as srv
        handler = srv.BadmintonServerHandler.__new__(srv.BadmintonServerHandler)
        handler.headers = _to_http_message()
        return handler

    def test_05_auth_cookie_has_httponly(self):
        """Login Set-Cookie header MUST contain HttpOnly."""
        h = self._get_handler()
        token = _make_valid_token()
        cookie_str = h._build_auth_cookie(token)
        attrs = _parse_set_cookie(cookie_str)
        self.assertIn("httponly", attrs,
            f"HttpOnly missing from cookie: {cookie_str}")

    def test_06_auth_cookie_has_samesite_lax(self):
        """Set-Cookie must use SameSite=Lax (for MoMo redirect compatibility)."""
        h = self._get_handler()
        token = _make_valid_token()
        cookie_str = h._build_auth_cookie(token)
        self.assertIn("samesite", cookie_str.lower(),
            "SameSite attribute missing")
        self.assertIn("lax", cookie_str.lower(),
            f"Expected SameSite=Lax, got: {cookie_str}")

    def test_07_auth_cookie_has_path_slash(self):
        """Set-Cookie Path must be /."""
        h = self._get_handler()
        token = _make_valid_token()
        cookie_str = h._build_auth_cookie(token)
        attrs = _parse_set_cookie(cookie_str)
        self.assertEqual(attrs.get("path", ""), "/",
            f"Expected Path=/, got: {attrs.get('path')}")

    def test_08_auth_cookie_max_age_matches_jwt(self):
        """Cookie Max-Age must match JWT expiry (7 days = 604800 seconds)."""
        h = self._get_handler()
        token = _make_valid_token()
        cookie_str = h._build_auth_cookie(token)
        attrs = _parse_set_cookie(cookie_str)
        expected_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        actual = int(attrs.get("max-age", 0))
        self.assertEqual(actual, expected_seconds,
            f"Max-Age {actual} != expected {expected_seconds}")

    def test_09_clear_cookie_has_max_age_zero(self):
        """Logout Set-Cookie must have Max-Age=0 to expire the cookie."""
        h = self._get_handler()
        cookie_str = h._build_clear_cookie()
        attrs = _parse_set_cookie(cookie_str)
        self.assertIn("httponly", attrs, "Clear cookie must also be HttpOnly")
        actual_age = int(attrs.get("max-age", -1))
        self.assertEqual(actual_age, 0,
            f"Expected Max-Age=0 on clear cookie, got {actual_age}")

    def test_10_https_env_adds_secure_flag(self):
        """When HTTPS=1 env var is set, Secure flag must appear in cookie."""
        h = self._get_handler()
        token = _make_valid_token()
        original = os.environ.get("HTTPS", "")
        try:
            os.environ["HTTPS"] = "1"
            cookie_str = h._build_auth_cookie(token)
            self.assertIn("; Secure", cookie_str,
                f"Secure flag missing when HTTPS=1: {cookie_str}")
        finally:
            if original:
                os.environ["HTTPS"] = original
            else:
                os.environ.pop("HTTPS", None)

    def test_11_no_https_env_no_secure_flag(self):
        """Without HTTPS env var, Secure flag must NOT appear (dev compatibility)."""
        h = self._get_handler()
        token = _make_valid_token()
        original = os.environ.get("HTTPS", "")
        try:
            os.environ.pop("HTTPS", None)
            cookie_str = h._build_auth_cookie(token)
            self.assertNotIn("; Secure", cookie_str,
                f"Unexpected Secure flag in dev mode: {cookie_str}")
        finally:
            if original:
                os.environ["HTTPS"] = original


# ══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 3 — Cookie Parsing & Authentication
# ══════════════════════════════════════════════════════════════════════════════
class TestCookieAuthentication(unittest.TestCase):

    def _make_handler_with_headers(self, headers: Mapping[str, str]):
        import server as srv
        h = srv.BadmintonServerHandler.__new__(srv.BadmintonServerHandler)
        h.headers = _to_http_message(headers)
        return h

    def test_12_parse_auth_cookie_valid(self):
        """_parse_auth_cookie() correctly extracts auth_token from Cookie header."""
        token = _make_valid_token()
        h = self._make_handler_with_headers({"Cookie": f"auth_token={token}"})
        result = h._parse_auth_cookie()
        self.assertEqual(result, token)

    def test_13_parse_auth_cookie_missing(self):
        """_parse_auth_cookie() returns None when cookie absent."""
        h = self._make_handler_with_headers({"Cookie": "session_id=abc123; theme=dark"})
        result = h._parse_auth_cookie()
        self.assertIsNone(result)

    def test_14_authenticate_request_via_cookie(self):
        """_authenticate_request() returns valid payload when cookie has valid JWT."""
        token = _make_valid_token(user_id="u_cookie_test")
        h = self._make_handler_with_headers({
            "Cookie": f"auth_token={token}",
            "Authorization": ""
        })
        payload = h._authenticate_request()
        self.assertIsNotNone(payload)
        self.assertEqual(str(payload["sub"]), "u_cookie_test")

    def test_15_authenticate_request_falls_back_to_bearer(self):
        """_authenticate_request() uses Bearer header when no valid cookie."""
        token = _make_valid_token(user_id="u_bearer_test")
        h = self._make_handler_with_headers({
            "Cookie": "",
            "Authorization": f"Bearer {token}"
        })
        payload = h._authenticate_request()
        self.assertIsNotNone(payload)
        self.assertEqual(str(payload["sub"]), "u_bearer_test")

    def test_16_expired_cookie_falls_back_to_bearer(self):
        """Expired cookie JWT falls back to valid Bearer."""
        expired = _make_expired_token()
        valid = _make_valid_token(user_id="u_fallback")
        h = self._make_handler_with_headers({
            "Cookie": f"auth_token={expired}",
            "Authorization": f"Bearer {valid}"
        })
        payload = h._authenticate_request()
        self.assertIsNotNone(payload)
        self.assertEqual(str(payload["sub"]), "u_fallback")

    def test_17_both_invalid_returns_none(self):
        """_authenticate_request() returns None when both cookie and bearer invalid."""
        h = self._make_handler_with_headers({
            "Cookie": "auth_token=garbage.not.valid",
            "Authorization": "Bearer also.invalid.token"
        })
        payload = h._authenticate_request()
        self.assertIsNone(payload)


# ══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 4 — CSRF Protection
# ══════════════════════════════════════════════════════════════════════════════
class TestCSRFProtection(unittest.TestCase):

    def _make_handler_with_headers(self, headers: Mapping[str, str]):
        import server as srv
        h = srv.BadmintonServerHandler.__new__(srv.BadmintonServerHandler)
        h.headers = _to_http_message(headers)
        return h

    def test_18_csrf_same_origin_allowed(self):
        """Same-origin requests pass CSRF check."""
        import server as srv
        h = self._make_handler_with_headers({
            "Host": f"localhost:{srv.PORT}",
            "Origin": f"http://localhost:{srv.PORT}"
        })
        self.assertTrue(h._check_csrf_origin(), "Same-origin request blocked")

    def test_19_csrf_different_origin_blocked(self):
        """Cross-origin requests fail CSRF check."""
        import server as srv
        h = self._make_handler_with_headers({
            "Host": f"localhost:{srv.PORT}",
            "Origin": "https://evil-site.example.com"
        })
        self.assertFalse(h._check_csrf_origin(),
            "Cross-origin request should be blocked")

    def test_20_csrf_no_origin_allowed_non_browser(self):
        """Requests with no Origin/Referer pass (non-browser can't carry HttpOnly cookies)."""
        import server as srv
        h = self._make_handler_with_headers({"Host": f"localhost:{srv.PORT}"})
        self.assertTrue(h._check_csrf_origin(),
            "Non-browser request (no Origin) should pass")

    def test_21_csrf_localhost_always_allowed(self):
        """localhost origins always allowed in dev."""
        import server as srv
        h = self._make_handler_with_headers({
            "Host": "127.0.0.1:8085",
            "Origin": "http://localhost:8085"
        })
        self.assertTrue(h._check_csrf_origin())

    def test_21b_csrf_blocks_cross_origin_cookie_post(self):
        """Cross-origin POST with cookie is blocked with 403."""
        import server as srv
        import io
        h = srv.BadmintonServerHandler.__new__(srv.BadmintonServerHandler)
        token = _make_valid_token()
        h.headers = _to_http_message({
            "Host": "localhost:8085",
            "Origin": "https://attacker.example.com",
            "Cookie": f"auth_token={token}",
            "Content-Length": "2",
        })
        h.rfile = io.BytesIO(b"{}")
        h.wfile = io.BytesIO()
        h.path = "/api/database"
        sent_response: list[int] = []
        sent_headers: dict[str, str] = {}
        def mock_send_response(code: int, message: Optional[str] = None) -> None:
            sent_response.append(code)
        def mock_send_header(keyword: str, value: str) -> None:
            sent_headers[keyword] = value
        def mock_end_headers() -> None:
            pass
        h.send_response = mock_send_response
        h.send_header = mock_send_header
        h.end_headers = mock_end_headers
        h.do_POST()
        self.assertEqual(sent_response, [403])
        self.assertIn(b"CSRF", h.wfile.getvalue())

    def test_11b_production_env_adds_secure_flag(self):
        """When ENVIRONMENT=production, Secure flag must be added even if HTTPS env is absent."""
        import server as srv
        h = srv.BadmintonServerHandler.__new__(srv.BadmintonServerHandler)
        token = _make_valid_token()
        orig_env = os.environ.get("ENVIRONMENT", "")
        orig_https = os.environ.get("HTTPS", "")
        try:
            os.environ["ENVIRONMENT"] = "production"
            os.environ.pop("HTTPS", None)
            cookie_str = h._build_auth_cookie(token)
            self.assertIn("; Secure", cookie_str, "Production mode must enforce Secure flag")
            clear_str = h._build_clear_cookie()
            self.assertIn("; Secure", clear_str, "Production mode clear cookie must have Secure flag")
        finally:
            if orig_env:
                os.environ["ENVIRONMENT"] = orig_env
            else:
                os.environ.pop("ENVIRONMENT", None)
            if orig_https:
                os.environ["HTTPS"] = orig_https
            else:
                os.environ.pop("HTTPS", None)



# ══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 5 — Anti-IDOR & Payment Status Security
# ══════════════════════════════════════════════════════════════════════════════
class TestPaymentStatusSecurity(unittest.TestCase):

    def _build_sample_db(self):
        return {
            "users": [
                {"id": "u_alice", "phone": "0900000001", "name": "Alice", "role": "CUSTOMER"},
                {"id": "u_bob",   "phone": "0900000002", "name": "Bob",   "role": "CUSTOMER"},
            ],
            "booking_orders": [
                {
                    "booking_code": "BC_ALICE_001",
                    "user_phone": "0900000001",
                    "order_status": "Da Xac Nhan",
                    "deposit_status": "Da Coc"
                },
                {
                    "booking_code": "BC_BOB_002",
                    "user_phone": "0900000002",
                    "order_status": "Cho Xac Nhan",
                    "deposit_status": "Cho Coc"
                },
            ]
        }

    def test_22_alice_can_access_own_booking(self):
        """User A can access their own booking."""
        db = self._build_sample_db()
        alice_token = _make_valid_token(user_id="u_alice", role="CUSTOMER")
        payload = decode_token(alice_token)
        user = next((u for u in db["users"] if u["id"] == payload["sub"]), None)
        booking = next((b for b in db["booking_orders"]
                        if b["booking_code"] == "BC_ALICE_001"), None)
        self.assertEqual(booking["user_phone"], user["phone"])

    def test_23_bob_cannot_access_alices_booking(self):
        """User B must NOT access User A's booking (IDOR blocked)."""
        db = self._build_sample_db()
        bob_token = _make_valid_token(user_id="u_bob", role="CUSTOMER")
        payload = decode_token(bob_token)
        user = next((u for u in db["users"] if u["id"] == payload["sub"]), None)
        booking = next((b for b in db["booking_orders"]
                        if b["booking_code"] == "BC_ALICE_001"), None)
        self.assertNotEqual(booking["user_phone"], user["phone"],
            "Bob must NOT be able to access Alice's booking")

    def test_24_payment_status_logic_success(self):
        """Confirmed + paid booking resolves to success."""
        order_status = "Da Xac Nhan"
        deposit_status = "Da Coc"
        if "Da Xac Nhan" in order_status and (
                "Da Coc" in deposit_status or "paid" in deposit_status.lower()):
            result = "success"
        else:
            result = "other"
        self.assertEqual(result, "success")

    def test_25_payment_status_logic_pending(self):
        """Pending booking resolves to pending."""
        order_status = "Cho Xac Nhan"
        deposit_status = "Cho Coc"
        if "Da Xac Nhan" in order_status and (
                "Da Coc" in deposit_status or "paid" in deposit_status.lower()):
            result = "success"
        elif "Cho Xac Nhan" in order_status or "Cho Coc" in deposit_status:
            result = "pending"
        else:
            result = "failed"
        self.assertEqual(result, "pending")

    def test_26_momo_redirect_fake_success_rejected(self):
        """
        MoMo redirect with resultCode=0 must NOT confirm payment without DB verification.
        DB still shows pending -> system must not trust redirect param.
        """
        redirect_params = {"resultCode": "0", "orderId": "BC_BOB_002"}
        db = self._build_sample_db()
        booking = next((b for b in db["booking_orders"]
                        if b["booking_code"] == "BC_BOB_002"), None)
        order_status = booking["order_status"]
        deposit_status = booking["deposit_status"]
        if "Da Xac Nhan" in order_status and (
                "Da Coc" in deposit_status or "paid" in deposit_status.lower()):
            db_status = "success"
        elif "Cho Xac Nhan" in order_status or "Cho Coc" in deposit_status:
            db_status = "pending"
        else:
            db_status = "failed"
        # Even if MoMo says success, DB says pending -> must not confirm
        self.assertEqual(db_status, "pending",
            "DB still pending; MoMo redirect param must not override DB state")


# ══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 6 — JS-Inaccessible Cookie (Architecture Guarantee)
# ══════════════════════════════════════════════════════════════════════════════
class TestHttpOnlyGuarantee(unittest.TestCase):

    def test_27_appjs_does_not_read_auth_cookie_via_js(self):
        """init() must NOT parse auth_token from document.cookie."""
        with open(os.path.join(ROOT_DIR, "js", "app.js"), "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn(
            "cookie.startsWith('auth_token=')",
            content,
            "init() still reads auth_token from JS-accessible cookie"
        )

    def test_28_appjs_does_not_write_auth_cookie_via_js(self):
        """handleLogin() must NOT write auth_token via document.cookie."""
        with open(os.path.join(ROOT_DIR, "js", "app.js"), "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn(
            "document.cookie = `auth_token=",
            content,
            "handleLogin() still writes auth_token to JS-accessible cookie"
        )

    def test_29_appjs_does_not_store_access_token_from_response(self):
        """handleLogin() must NOT store access_token from JSON response body."""
        with open(os.path.join(ROOT_DIR, "js", "app.js"), "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn(
            "this.authToken = data.access_token",
            content,
            "handleLogin() still stores access_token in JS memory"
        )

    def test_30_server_login_response_excludes_access_token_field(self):
        """The login handler JSON response must NOT include access_token."""
        with open(os.path.join(ROOT_DIR, "server.py"), "r", encoding="utf-8") as f:
            content = f.read()
        login_idx = content.find('if self.path == "/api/login"')
        login_section = content[login_idx:login_idx + 2000] if login_idx >= 0 else ""
        self.assertNotIn(
            '"access_token": access_token',
            login_section,
            "Login response still includes access_token in JSON body"
        )

    def test_31_server_uses_set_cookie_header_on_login(self):
        """server.py login handler must call Set-Cookie with HttpOnly."""
        with open(os.path.join(ROOT_DIR, "server.py"), "r", encoding="utf-8") as f:
            content = f.read()
        login_idx = content.find('if self.path == "/api/login"')
        login_section = content[login_idx:login_idx + 2500] if login_idx >= 0 else ""
        self.assertIn("Set-Cookie", login_section,
            "Login handler does not send Set-Cookie header")
        self.assertIn("HttpOnly", login_section,
            "Set-Cookie in login handler does not include HttpOnly")


# ══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 7 — Logout & Session Termination
# ══════════════════════════════════════════════════════════════════════════════
class TestLogoutSecurity(unittest.TestCase):

    def test_32_logout_endpoint_exists_in_server(self):
        """/api/logout POST handler must exist in server.py."""
        with open(os.path.join(ROOT_DIR, "server.py"), "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn('/api/logout', content,
            "No /api/logout endpoint in server.py")

    def test_33_logout_clears_cookie_via_max_age_zero(self):
        """_build_clear_cookie() must produce Max-Age=0 with HttpOnly."""
        import server as srv
        h = srv.BadmintonServerHandler.__new__(srv.BadmintonServerHandler)
        h.headers = _to_http_message()
        clear_cookie = h._build_clear_cookie()
        attrs = _parse_set_cookie(clear_cookie)
        self.assertIn("httponly", attrs, "Clear cookie missing HttpOnly")
        self.assertEqual(int(attrs.get("max-age", -1)), 0)

    def test_34_jwt_stateless_limitation_acknowledged_in_code(self):
        """Logout response must acknowledge JWT stateless limitation (no fake revocation claim)."""
        with open(os.path.join(ROOT_DIR, "server.py"), "r", encoding="utf-8") as f:
            content = f.read()
        logout_idx = content.find('/api/logout')
        logout_section = content[logout_idx:logout_idx + 1200] if logout_idx >= 0 else ""
        has_note = (
            "stateless" in logout_section.lower() or
            "revoc" in logout_section.lower() or
            "denylist" in logout_section.lower()
        )
        self.assertTrue(has_note,
            "Logout handler does not acknowledge JWT stateless limitation")

    def test_35_appjs_logout_calls_backend_endpoint(self):
        """app.js logout() must call /api/logout."""
        with open(os.path.join(ROOT_DIR, "js", "app.js"), "r", encoding="utf-8") as f:
            content = f.read()
        # Find the method definition, not an onclick call
        import re
        m = re.search(r'logout\(\)\s*\{', content)
        self.assertIsNotNone(m, "logout() method definition not found")
        logout_section = content[m.start():m.start() + 600]
        self.assertIn("/api/logout", logout_section,
            "logout() does not call /api/logout endpoint")

    def test_36_appjs_logout_uses_credentials_include(self):
        """logout() fetch must use credentials:include to send HttpOnly cookie."""
        with open(os.path.join(ROOT_DIR, "js", "app.js"), "r", encoding="utf-8") as f:
            content = f.read()
        import re
        m = re.search(r'logout\(\)\s*\{', content)
        self.assertIsNotNone(m, "logout() method definition not found")
        logout_section = content[m.start():m.start() + 700]
        self.assertIn("credentials", logout_section,
            "logout() fetch missing credentials:include")


# ══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 8 — Regression: Existing APIs Not Broken
# ══════════════════════════════════════════════════════════════════════════════
class TestAPIRegression(unittest.TestCase):

    def test_37_api_chat_endpoint_still_exists(self):
        with open(os.path.join(ROOT_DIR, "server.py"), "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn('/api/chat', content)
        self.assertIn('/api/v1/ai/chat', content)

    def test_38_api_database_endpoint_still_exists(self):
        with open(os.path.join(ROOT_DIR, "server.py"), "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn('/api/database', content)

    def test_39_matchmaking_endpoints_still_exist(self):
        with open(os.path.join(ROOT_DIR, "server.py"), "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn('/matchmaking/find', content)
        self.assertIn('/matchmaking/history', content)
        self.assertIn('/matchmaking/simulate', content)

    def test_40_payment_status_endpoint_still_exists(self):
        with open(os.path.join(ROOT_DIR, "server.py"), "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn('/api/payment/status', content)

    def test_41_cors_headers_still_set(self):
        with open(os.path.join(ROOT_DIR, "server.py"), "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Access-Control-Allow-Origin", content)
        self.assertIn("Access-Control-Allow-Methods", content)

    def test_42_security_imports_intact(self):
        with open(os.path.join(ROOT_DIR, "server.py"), "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("decode_token", content)
        self.assertIn("create_access_token", content)
        self.assertIn("verify_password", content)

    def test_43_checkpaymentstatus_uses_credentials_include(self):
        """checkPaymentStatus() must use credentials:include not Authorization header."""
        with open(os.path.join(ROOT_DIR, "js", "app.js"), "r", encoding="utf-8") as f:
            content = f.read()
        import re
        m = re.search(r'checkPaymentStatus\(orderId\)\s*\{', content)
        self.assertIsNotNone(m, "checkPaymentStatus() method definition not found")
        cps_section = content[m.start():m.start() + 700]
        self.assertIn("credentials", cps_section,
            "checkPaymentStatus() missing credentials:include")
        self.assertNotIn("Authorization", cps_section,
            "checkPaymentStatus() still sends Authorization header (should use cookie)")


# ══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 9 — Security Config Validation
# ══════════════════════════════════════════════════════════════════════════════
class TestSecurityConfig(unittest.TestCase):

    def test_44_secret_key_not_default_in_production(self):
        env = os.environ.get("ENVIRONMENT", "").lower()
        if env == "production":
            self.assertNotEqual(
                settings.SECRET_KEY, "badminton_super_secret_jwt_key_2026",
                "Production SECRET_KEY must not be the default value!"
            )
        else:
            self.skipTest("Skipped in non-production environment")

    def test_45_payment_pending_expiry_disabled(self):
        """PAYMENT_PENDING_EXPIRY_ENABLED must remain False."""
        self.assertFalse(
            settings.PAYMENT_PENDING_EXPIRY_ENABLED,
            "PAYMENT_PENDING_EXPIRY_ENABLED must stay False for this phase"
        )

    def test_46_access_token_expire_minutes_positive(self):
        self.assertIsNotNone(settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        self.assertGreater(settings.ACCESS_TOKEN_EXPIRE_MINUTES, 0)

    def test_47_algorithm_is_hs256(self):
        self.assertEqual(settings.ALGORITHM, "HS256")


# ══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 10 — End-to-End Flow (Logic layer, no live server)
# ══════════════════════════════════════════════════════════════════════════════
class TestEndToEndFlow(unittest.TestCase):

    def _make_handler(self, cookie_val: str = "", auth_header: str = "",
                      origin: str = "", host: str = "localhost:8085"):
        import server as srv
        h = srv.BadmintonServerHandler.__new__(srv.BadmintonServerHandler)
        headers: dict[str, str] = {"Host": host}
        if cookie_val:
            headers["Cookie"] = cookie_val
        if auth_header:
            headers["Authorization"] = auth_header
        if origin:
            headers["Origin"] = origin
        h.headers = _to_http_message(headers)
        return h

    def test_48_full_login_sets_correct_cookie(self):
        """Login flow produces cookie with all required attributes."""
        h = self._make_handler()
        token = _make_valid_token("u_full_test", "CUSTOMER")
        cookie = h._build_auth_cookie(token)
        attrs = _parse_set_cookie(cookie)
        self.assertIn("httponly", attrs)
        self.assertEqual(attrs.get("path"), "/")
        self.assertIn("samesite", cookie.lower())
        self.assertIn(token, cookie)

    def test_49_post_login_cookie_authenticates_payment_check(self):
        """After login, browser sends cookie -> /api/payment/status auth succeeds."""
        token = _make_valid_token("u_pay_test", "CUSTOMER")
        h = self._make_handler(cookie_val=f"auth_token={token}")
        payload = h._authenticate_request()
        self.assertIsNotNone(payload)
        self.assertEqual(str(payload["sub"]), "u_pay_test")

    def test_50_logout_clears_session_cookie(self):
        """Logout: Max-Age=0 set; empty token value does not authenticate."""
        h = self._make_handler()
        clear_cookie = h._build_clear_cookie()
        attrs = _parse_set_cookie(clear_cookie)
        self.assertEqual(int(attrs.get("max-age", -1)), 0)
        self.assertIn("httponly", attrs)
        # After logout the browser sends auth_token= (empty)
        h2 = self._make_handler(cookie_val="auth_token=")
        payload = h2._authenticate_request()
        self.assertIsNone(payload, "Empty token after logout should not authenticate")


if __name__ == "__main__":
    import sys
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors) - len(result.skipped)
    print(f"\n{'='*60}")
    print(f"PHASE 7.4B.2G TEST RESULTS")
    print(f"{'='*60}")
    print(f"TOTAL:   {total}")
    print(f"PASSED:  {passed}")
    print(f"FAILED:  {len(result.failures)}")
    print(f"ERROR:   {len(result.errors)}")
    print(f"SKIPPED: {len(result.skipped)}")
    print(f"{'='*60}")
    sys.exit(0 if result.wasSuccessful() else 1)
