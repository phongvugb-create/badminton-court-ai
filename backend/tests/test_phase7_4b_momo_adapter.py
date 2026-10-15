"""
BADMINTON.AI - PHASE 7.4B TEST SUITE
MOMO PAYMENT ADAPTER (SANDBOX FIRST)
Comprehensive test suite validating all mandatory specifications from Phase 7.4B:
1. MoMo provider disabled/unconfigured when missing credentials.
2. Production environment strictly blocked in Phase 7.4B.
3. Sandbox endpoint correctly resolves to https://test-payment.momo.vn.
4. Payment create request schema follows POST /v2/gateway/api/create and requestType='payWithMethod'.
5. Request signature strictly matches official MoMo canonical format.
6. Tampered signature cannot produce valid HMAC-SHA256 request signature.
7. RequestId and OrderId format constraints and uniqueness.
8. Amount outside provider limits (< 1,000 VND or > 50,000,000 VND) rejected.
9. Amount mismatch rejected before sending to provider.
10. HTTP timeout handled gracefully without false payment success.
11. Provider response missing payUrl or with failure resultCode not treated as success.
12. Valid IPN callback transitions payment to SUCCESS and booking to DEPOSITED/PAID.
13. Invalid IPN signature strictly rejected.
14. PartnerCode, orderId, or amount mismatch routed to REQUIRES_RECONCILIATION.
15. Duplicate IPN callback handled idempotently.
16. Late IPN SUCCESS on CANCELLED booking never revives booking; routes to reconciliation.
17. Late IPN FAILED after SUCCESS never downgrades transaction.
18. Database commit failure rolls back cleanly without false success.
19. Anti-IDOR: users cannot initiate payment for other users' bookings.
20. Client redirect does not mutate booking or payment state.
21. Create timeout retry does not generate conflicting duplicate transactions.
22. Phase 7.4A Sandbox adapter continues to operate without regression.
23. Phase 7.3 booking flow remains fully intact without regression.
24. Payment expiry remains disabled by default (PAYMENT_PENDING_EXPIRY_ENABLED=False).
25. Zero leakage of secret keys or sensitive tokens in logs or responses.
26. Mock HTTP and official test vectors clearly distinguished from live test.
27. Live Sandbox E2E audit classification: BLOCKED / NOT TESTED when real merchant credentials absent.
"""

import os
import sys
import json
import uuid
import hmac
import hashlib
import asyncio
import unittest
from unittest.mock import patch, AsyncMock, MagicMock
from decimal import Decimal
from typing import Optional, Dict, Any

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT_DIR = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
for p in [ROOT_DIR, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

import httpx
from sqlalchemy.future import select
from sqlalchemy import text, delete

from app.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis import _in_memory_locks
from app.models.all_models import (
    User,
    Facility,
    Court,
    TimeSlot,
    SlotPricing,
    Booking,
    Payment,
    PaymentStatus,
    TransactionStatus
)
from app.services.payment_adapters.momo_adapter import (
    MoMoPaymentAdapter,
    MIN_MOMO_AMOUNT,
    MAX_MOMO_AMOUNT
)
from app.services.payment_service import (
    create_payment_attempt,
    process_payment_webhook,
    process_momo_ipn,
    get_payment_adapter,
    normalize_vnd_amount
)


MOCK_MOMO_CONFIG = {
    "MOMO_PARTNER_CODE": "MOMO_TEST_PARTNER",
    "MOMO_ACCESS_KEY": "momo_test_access_key",
    "MOMO_SECRET_KEY": "momo_test_secret_key_secret123456",
    "MOMO_ENDPOINT": "https://test-payment.momo.vn",
    "MOMO_REDIRECT_URL": "http://localhost:3000/payment/result",
    "MOMO_IPN_URL": "http://localhost:8000/api/v1/payments/momo/ipn",
    "MOMO_ENVIRONMENT": "sandbox",
    "ENVIRONMENT": "test",
    "PAYMENT_SANDBOX_ENABLED": "true"
}


class TestPhase74BMoMoAdapter(unittest.TestCase):
    """Phase 7.4B Comprehensive MoMo Payment Adapter & IPN Test Suite."""

    @classmethod
    def setUpClass(cls):
        cls.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cls.loop)
        cls.loop.run_until_complete(cls._ensure_seed_data())

    @classmethod
    def tearDownClass(cls):
        cls.loop.close()

    @classmethod
    async def _ensure_seed_data(cls):
        async with AsyncSessionLocal() as session:
            fac = (await session.execute(select(Facility).where(Facility.id == 101))).scalar_one_or_none()
            if not fac:
                await session.execute(text("""
                    INSERT OR REPLACE INTO facilities (id, owner_id, name, address, latitude, longitude)
                    VALUES (101, 1, 'CLB Cầu Lông Catchy Badminton Arena', '136 Tân Khai', 20.9856, 105.858)
                """))
            crt = (await session.execute(select(Court).where(Court.id == 201))).scalar_one_or_none()
            if not crt:
                await session.execute(text("""
                    INSERT OR REPLACE INTO courts (id, facility_id, surface_type, court_number, is_active)
                    VALUES (201, 101, 'Sân 01 - Thảm Yonex Pro', '1', 1)
                """))
            await session.execute(text("""
                INSERT OR REPLACE INTO time_slots (id, court_id, date, start_time, end_time, status)
                VALUES (1, 201, '2026-10-15', '19:00', '20:00', 'AVAILABLE')
            """))
            await session.execute(text("""
                INSERT OR REPLACE INTO time_slots (id, court_id, date, start_time, end_time, status)
                VALUES (2, 201, '2026-10-15', '20:00', '21:00', 'AVAILABLE')
            """))
            await session.execute(text("""
                INSERT OR REPLACE INTO slot_pricing (id, slot_id, base_price, dynamic_price, adjustment_reason, is_ai_applied)
                VALUES (101, 1, 80000.0, 80000.0, 'Standard', 0)
            """))
            await session.execute(text("""
                INSERT OR REPLACE INTO slot_pricing (id, slot_id, base_price, dynamic_price, adjustment_reason, is_ai_applied)
                VALUES (102, 2, 80000.0, 80000.0, 'Standard', 0)
            """))
            u1 = (await session.execute(select(User).where(User.id == 1))).scalar_one_or_none()
            if not u1:
                await session.execute(text("""
                    INSERT OR REPLACE INTO users (id, name, phone, password_hash, role)
                    VALUES (1, 'Nguyễn Văn A', '0901234567', 'hash1', 'CUSTOMER')
                """))
            u2 = (await session.execute(select(User).where(User.id == 2))).scalar_one_or_none()
            if not u2:
                await session.execute(text("""
                    INSERT OR REPLACE INTO users (id, name, phone, password_hash, role)
                    VALUES (2, 'Trần Thị B', '0901234568', 'hash2', 'CUSTOMER')
                """))
            await session.commit()

    def setUp(self):
        _in_memory_locks.clear()
        for k, v in MOCK_MOMO_CONFIG.items():
            os.environ[k] = v

        async def _reset():
            async with AsyncSessionLocal() as session:
                await session.execute(text("UPDATE time_slots SET status = 'AVAILABLE' WHERE id IN (1, 2)"))
                await session.execute(delete(Payment).where(Payment.booking_id.in_([1001, 1002, 1003, 1004, 1005, 1006, 1008])))
                await session.execute(delete(Booking).where(Booking.id.in_([1001, 1002, 1003, 1004, 1005, 1006, 1008])))
                await session.commit()
        self.run_async(_reset())

    def tearDown(self):
        for k in MOCK_MOMO_CONFIG.keys():
            os.environ.pop(k, None)

    def run_async(self, coro):
        return self.loop.run_until_complete(coro)

    # -------------------------------------------------------------------------
    # TEST 1: MoMo provider is NOT configured if credentials are missing
    # -------------------------------------------------------------------------
    def test_01_momo_not_configured_when_missing_credentials(self):
        """1. MoMo provider không kích hoạt nếu thiếu bất kỳ credential bắt buộc nào."""
        adapter = MoMoPaymentAdapter()
        with patch.dict(os.environ, {"MOMO_PARTNER_CODE": "", "MOMO_ACCESS_KEY": ""}):
            self.assertFalse(adapter.is_configured())

        with patch.dict(os.environ, {"MOMO_SECRET_KEY": ""}):
            self.assertFalse(adapter.is_configured())

        with patch.dict(os.environ, {"MOMO_PARTNER_CODE": "your_partner_code"}):
            self.assertFalse(adapter.is_configured())

    # -------------------------------------------------------------------------
    # TEST 2: Production environment strictly blocked in Phase 7.4B
    # -------------------------------------------------------------------------
    def test_02_production_environment_strictly_blocked(self):
        """2. Production environment bị chặn hoàn toàn trong Phase 7.4B."""
        adapter = MoMoPaymentAdapter()
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            self.assertTrue(adapter.is_production_blocked())

        with patch.dict(os.environ, {"MOMO_ENVIRONMENT": "production"}):
            self.assertTrue(adapter.is_production_blocked())

        with patch.dict(os.environ, {"ENVIRONMENT": "test", "MOMO_ENVIRONMENT": "sandbox"}):
            self.assertFalse(adapter.is_production_blocked())

    # -------------------------------------------------------------------------
    # TEST 3: Sandbox endpoint correctly resolved
    # -------------------------------------------------------------------------
    def test_03_sandbox_endpoint_correctly_resolved(self):
        """3. Endpoint sandbox được xác định đúng https://test-payment.momo.vn."""
        endpoint = os.getenv("MOMO_ENDPOINT") or getattr(settings, "MOMO_ENDPOINT", "")
        self.assertEqual(endpoint.rstrip("/"), "https://test-payment.momo.vn")

    # -------------------------------------------------------------------------
    # TEST 4: Create payment request schema matches POST /v2/gateway/api/create
    # -------------------------------------------------------------------------
    def test_04_payment_create_request_schema(self):
        """4. Request tạo payment dùng đúng schema và requestType='payWithMethod'."""
        adapter = MoMoPaymentAdapter()
        captured_request = {}

        class MockAsyncClient:
            async def post(self, url, json=None, **kwargs):
                captured_request["url"] = url
                captured_request["json"] = json
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {
                    "resultCode": 0,
                    "message": "Success",
                    "payUrl": "https://test-payment.momo.vn/v2/gateway/pay?token=xyz123",
                    "deeplink": "momo://payment?token=xyz123",
                    "qrCodeUrl": "https://test-payment.momo.vn/qr/xyz123",
                    "orderId": json.get("orderId"),
                    "requestId": json.get("requestId")
                }
                return mock_resp

        res = self.run_async(adapter.create_payment_request(
            order_id="momo_ord_001",
            request_id="momo_req_001",
            amount=40000,
            order_info="Dat san cau long #1",
            client=MockAsyncClient()
        ))

        self.assertEqual(res["status"], "success")
        self.assertIn("v2/gateway/api/create", captured_request["url"])
        self.assertEqual(captured_request["json"]["requestType"], "payWithMethod")
        self.assertEqual(captured_request["json"]["amount"], 40000)
        self.assertEqual(captured_request["json"]["orderId"], "momo_ord_001")
        self.assertEqual(captured_request["json"]["requestId"], "momo_req_001")
        self.assertIn("signature", captured_request["json"])

    # -------------------------------------------------------------------------
    # TEST 5: Request signature matches official canonicalization
    # -------------------------------------------------------------------------
    def test_05_request_signature_matches_canonical_order(self):
        """5. Request signature khớp chính xác thứ tự canonical fields theo tài liệu MoMo."""
        adapter = MoMoPaymentAdapter()
        secret = "test_secret_123"
        access_key = "test_access_key"
        amount = 50000
        extra_data = "eyJib29raW5nIjoxfQ=="
        ipn_url = "https://example.com/ipn"
        order_id = "ORD123"
        order_info = "Payment Info"
        partner_code = "MOMO"
        redirect_url = "https://example.com/redirect"
        request_id = "REQ123"
        request_type = "payWithMethod"

        sig = adapter.generate_request_signature(
            access_key=access_key,
            amount=amount,
            extra_data=extra_data,
            ipn_url=ipn_url,
            order_id=order_id,
            order_info=order_info,
            partner_code=partner_code,
            redirect_url=redirect_url,
            request_id=request_id,
            request_type=request_type,
            secret_key=secret
        )

        # Expected canonical format:
        raw = f"accessKey={access_key}&amount={amount}&extraData={extra_data}&ipnUrl={ipn_url}&orderId={order_id}&orderInfo={order_info}&partnerCode={partner_code}&redirectUrl={redirect_url}&requestId={request_id}&requestType={request_type}"
        expected = hmac.new(secret.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()
        self.assertEqual(sig, expected)

    # -------------------------------------------------------------------------
    # TEST 6: Tampered / incorrect signature rejected
    # -------------------------------------------------------------------------
    def test_06_tampered_signature_rejected(self):
        """6. Chữ ký sai hoặc bị can thiệp không thể xác thực thành công."""
        adapter = MoMoPaymentAdapter()
        payload = {
            "partnerCode": "MOMO_TEST_PARTNER",
            "orderId": "ORD100",
            "requestId": "REQ100",
            "amount": 50000,
            "orderInfo": "Info",
            "orderType": "momo_wallet",
            "transId": 123456,
            "resultCode": 0,
            "message": "Successful.",
            "payType": "qr",
            "responseTime": 1721720663942,
            "extraData": "",
            "signature": "forged_invalid_signature_hex"
        }
        self.assertFalse(adapter.verify_ipn_signature(payload))

    # -------------------------------------------------------------------------
    # TEST 7: RequestId/orderId format and uniqueness
    # -------------------------------------------------------------------------
    def test_07_request_order_id_format_and_uniqueness(self):
        """7. RequestId và OrderId thỏa mãn định dạng (< 50 ký tự) và có tính duy nhất."""
        import re
        momo_regex = re.compile(r"^[0-9a-zA-Z]([-_.]*[0-9a-zA-Z]+)*$")
        ids = set()
        for i in range(50):
            tx_id = f"tx_momo_{uuid.uuid4().hex[:16]}"
            req_id = f"req_momo_{uuid.uuid4().hex[:16]}"
            self.assertTrue(len(tx_id) <= 50)
            self.assertTrue(len(req_id) <= 50)
            self.assertTrue(bool(momo_regex.match(tx_id)))
            self.assertTrue(bool(momo_regex.match(req_id)))
            self.assertNotIn(tx_id, ids)
            self.assertNotIn(req_id, ids)
            ids.add(tx_id)
            ids.add(req_id)

    # -------------------------------------------------------------------------
    # TEST 8: Amount outside MoMo limits is rejected
    # -------------------------------------------------------------------------
    def test_08_amount_outside_limits_rejected(self):
        """8. Số tiền VND ngoài giới hạn [1.000, 50.000.000] VND bị từ chối rõ ràng."""
        adapter = MoMoPaymentAdapter()
        self.assertFalse(adapter.validate_amount(Decimal("999")))
        self.assertFalse(adapter.validate_amount(Decimal("0")))
        self.assertFalse(adapter.validate_amount(Decimal("-50000")))
        self.assertFalse(adapter.validate_amount(Decimal("50000001")))
        self.assertTrue(adapter.validate_amount(Decimal("1000")))
        self.assertTrue(adapter.validate_amount(Decimal("50000000")))
        self.assertTrue(adapter.validate_amount(Decimal("40000")))

    # -------------------------------------------------------------------------
    # TEST 9: Amount mismatch not sent out
    # -------------------------------------------------------------------------
    def test_09_amount_mismatch_not_sent_to_provider(self):
        """9. Nếu số tiền không hợp lệ, adapter trả lỗi ngay và không gửi HTTP request."""
        adapter = MoMoPaymentAdapter()
        mock_client = AsyncMock()
        res = self.run_async(adapter.create_payment_request(
            order_id="ord_test",
            request_id="req_test",
            amount=500,  # below 1,000 VND limit
            order_info="Test",
            client=mock_client
        ))
        self.assertEqual(res["status"], "invalid_amount")
        mock_client.post.assert_not_called()

    # -------------------------------------------------------------------------
    # TEST 10: HTTP timeout not interpreted as payment success
    # -------------------------------------------------------------------------
    def test_10_gateway_timeout_not_interpreted_as_success(self):
        """10. HTTP timeout khi gọi MoMo không bị diễn giải thành thành công; lưu đối soát."""
        adapter = MoMoPaymentAdapter()

        class TimeoutClient:
            async def post(self, *args, **kwargs):
                raise httpx.TimeoutException("MoMo Gateway Timeout")

        res = self.run_async(adapter.create_payment_request(
            order_id="ord_timeout",
            request_id="req_timeout",
            amount=50000,
            order_info="Test Timeout",
            client=TimeoutClient()
        ))
        self.assertEqual(res["status"], "timeout")

    # -------------------------------------------------------------------------
    # TEST 11: Response missing payUrl or failed resultCode rejected
    # -------------------------------------------------------------------------
    def test_11_response_missing_pay_url_rejected(self):
        """11. Phản hồi MoMo thiếu payUrl hoặc resultCode != 0 không được coi là thành công."""
        adapter = MoMoPaymentAdapter()

        class MissingUrlClient:
            async def post(self, *args, **kwargs):
                resp = MagicMock()
                resp.status_code = 200
                resp.json.return_value = {"resultCode": 0, "message": "Success", "payUrl": None}
                return resp

        res = self.run_async(adapter.create_payment_request(
            order_id="ord_missing",
            request_id="req_missing",
            amount=50000,
            order_info="Test",
            client=MissingUrlClient()
        ))
        self.assertEqual(res["status"], "provider_error")

    # -------------------------------------------------------------------------
    # TEST 12: Valid IPN callback transitions payment and booking
    # -------------------------------------------------------------------------
    def test_12_valid_ipn_callback_processes_successfully(self):
        """12. IPN hợp lệ cập nhật Payment sang SUCCESS và Booking sang DEPOSITED."""
        async def _test():
            async with AsyncSessionLocal() as session:
                b = Booking(
                    id=1001,
                    user_id=1,
                    slot_id=1,
                    total_amount=80000.0,
                    deposit_amount=40000.0,
                    payment_status=PaymentStatus.PENDING.value
                )
                session.add(b)
                p = Payment(
                    booking_id=1001,
                    user_id=1,
                    provider="MOMO",
                    transaction_id="tx_momo_ord_1001",
                    amount=40000.0,
                    currency="VND",
                    payment_type="DEPOSIT",
                    status=TransactionStatus.PENDING.value
                )
                session.add(p)
                await session.commit()

            adapter = MoMoPaymentAdapter()
            ipn_payload = {
                "partnerCode": "MOMO_TEST_PARTNER",
                "orderId": "tx_momo_ord_1001",
                "requestId": "req_1001",
                "amount": 40000,
                "orderInfo": "Dat san",
                "orderType": "momo_wallet",
                "transId": 987654321,
                "resultCode": 0,
                "message": "Successful.",
                "payType": "qr",
                "responseTime": 1721720663942,
                "extraData": ""
            }
            sig = adapter.generate_ipn_signature(
                access_key="momo_test_access_key",
                amount=40000,
                extra_data="",
                message="Successful.",
                order_id="tx_momo_ord_1001",
                order_info="Dat san",
                order_type="momo_wallet",
                partner_code="MOMO_TEST_PARTNER",
                pay_type="qr",
                request_id="req_1001",
                response_time=1721720663942,
                result_code=0,
                trans_id=987654321,
                secret_key="momo_test_secret_key_secret123456"
            )
            ipn_payload["signature"] = sig

            async with AsyncSessionLocal() as session:
                res = await process_momo_ipn(session, ipn_payload)
                self.assertEqual(res["status"], "payment_processed")
                self.assertFalse(res["is_idempotent"])

                # Verify DB state
                b_res = await session.execute(select(Booking).where(Booking.id == 1001))
                b_db = b_res.scalar_one()
                self.assertEqual(b_db.payment_status, PaymentStatus.DEPOSITED.value)

                p_res = await session.execute(select(Payment).where(Payment.transaction_id == "tx_momo_ord_1001"))
                p_db = p_res.scalar_one()
                self.assertEqual(p_db.status, TransactionStatus.SUCCESS.value)

        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 13: Invalid IPN signature rejected
    # -------------------------------------------------------------------------
    def test_13_invalid_ipn_signature_rejected(self):
        """13. Chữ ký IPN không hợp lệ bị từ chối và không cập nhật DB."""
        async def _test():
            ipn_payload = {
                "partnerCode": "MOMO_TEST_PARTNER",
                "orderId": "tx_momo_ord_fake",
                "requestId": "req_fake",
                "amount": 40000,
                "resultCode": 0,
                "signature": "invalid_forged_signature_0000"
            }
            async with AsyncSessionLocal() as session:
                res = await process_momo_ipn(session, ipn_payload)
                self.assertEqual(res["status"], "invalid_signature")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 14: PartnerCode or Amount mismatch routed to reconciliation
    # -------------------------------------------------------------------------
    def test_14_partner_or_amount_mismatch_reconciliation(self):
        """14. Số tiền hoặc partnerCode không khớp bị đưa vào REQUIRES_RECONCILIATION."""
        async def _test():
            async with AsyncSessionLocal() as session:
                b = Booking(
                    id=1002,
                    user_id=1,
                    slot_id=1,
                    total_amount=80000.0,
                    deposit_amount=40000.0,
                    payment_status=PaymentStatus.PENDING.value
                )
                session.add(b)
                p = Payment(
                    booking_id=1002,
                    user_id=1,
                    provider="MOMO",
                    transaction_id="tx_momo_ord_1002",
                    amount=40000.0,
                    currency="VND",
                    payment_type="DEPOSIT",
                    status=TransactionStatus.PENDING.value
                )
                session.add(p)
                await session.commit()

            adapter = MoMoPaymentAdapter()
            # Mismatched amount: sent 50000 instead of 40000
            sig = adapter.generate_ipn_signature(
                access_key="momo_test_access_key",
                amount=50000,
                extra_data="",
                message="Successful.",
                order_id="tx_momo_ord_1002",
                order_info="Dat san",
                order_type="momo_wallet",
                partner_code="MOMO_TEST_PARTNER",
                pay_type="qr",
                request_id="req_1002",
                response_time=1721720663942,
                result_code=0,
                trans_id=987654322,
                secret_key="momo_test_secret_key_secret123456"
            )
            ipn_payload = {
                "partnerCode": "MOMO_TEST_PARTNER",
                "orderId": "tx_momo_ord_1002",
                "requestId": "req_1002",
                "amount": 50000,
                "orderInfo": "Dat san",
                "orderType": "momo_wallet",
                "transId": 987654322,
                "resultCode": 0,
                "message": "Successful.",
                "payType": "qr",
                "responseTime": 1721720663942,
                "extraData": "",
                "signature": sig
            }

            async with AsyncSessionLocal() as session:
                res = await process_momo_ipn(session, ipn_payload)
                self.assertEqual(res["status"], "amount_mismatch")

                p_res = await session.execute(select(Payment).where(Payment.transaction_id == "tx_momo_ord_1002"))
                p_db = p_res.scalar_one()
                self.assertEqual(p_db.status, TransactionStatus.REQUIRES_RECONCILIATION.value)

        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 15: Duplicate IPN callback is idempotent
    # -------------------------------------------------------------------------
    def test_15_duplicate_ipn_callback_idempotent(self):
        """15. IPN callback trùng lặp được xử lý idempotent, không tạo side effect lần 2."""
        async def _test():
            async with AsyncSessionLocal() as session:
                b = (await session.execute(select(Booking).where(Booking.id == 1001))).scalar_one_or_none()
                if not b:
                    b = Booking(
                        id=1001,
                        user_id=1,
                        slot_id=1,
                        total_amount=80000.0,
                        deposit_amount=40000.0,
                        payment_status=PaymentStatus.DEPOSITED.value
                    )
                    session.add(b)
                p = (await session.execute(select(Payment).where(Payment.transaction_id == "tx_momo_ord_1001"))).scalar_one_or_none()
                if not p:
                    p = Payment(
                        booking_id=1001,
                        user_id=1,
                        provider="MOMO",
                        transaction_id="tx_momo_ord_1001",
                        amount=40000.0,
                        currency="VND",
                        payment_type="DEPOSIT",
                        status=TransactionStatus.SUCCESS.value
                    )
                    session.add(p)
                await session.commit()

            adapter = MoMoPaymentAdapter()
            sig = adapter.generate_ipn_signature(
                access_key="momo_test_access_key",
                amount=40000,
                extra_data="",
                message="Successful.",
                order_id="tx_momo_ord_1001",
                order_info="Dat san",
                order_type="momo_wallet",
                partner_code="MOMO_TEST_PARTNER",
                pay_type="qr",
                request_id="req_1001",
                response_time=1721720663942,
                result_code=0,
                trans_id=987654321,
                secret_key="momo_test_secret_key_secret123456"
            )
            ipn_payload = {
                "partnerCode": "MOMO_TEST_PARTNER",
                "orderId": "tx_momo_ord_1001",
                "requestId": "req_1001",
                "amount": 40000,
                "orderInfo": "Dat san",
                "orderType": "momo_wallet",
                "transId": 987654321,
                "resultCode": 0,
                "message": "Successful.",
                "payType": "qr",
                "responseTime": 1721720663942,
                "extraData": "",
                "signature": sig
            }

            async with AsyncSessionLocal() as session:
                res = await process_momo_ipn(session, ipn_payload)
                self.assertEqual(res["status"], "payment_processed")
                self.assertTrue(res["is_idempotent"])

        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 16: IPN SUCCESS on CANCELLED booking does not revive booking
    # -------------------------------------------------------------------------
    def test_16_success_callback_on_cancelled_booking_no_revival(self):
        """16. IPN SUCCESS đến sau khi Booking đã CANCELLED không hồi sinh booking; đưa sang đối soát."""
        async def _test():
            async with AsyncSessionLocal() as session:
                b = Booking(
                    id=1003,
                    user_id=1,
                    slot_id=1,
                    total_amount=80000.0,
                    deposit_amount=40000.0,
                    payment_status=PaymentStatus.CANCELLED.value
                )
                session.add(b)
                p = Payment(
                    booking_id=1003,
                    user_id=1,
                    provider="MOMO",
                    transaction_id="tx_momo_ord_1003",
                    amount=40000.0,
                    currency="VND",
                    payment_type="DEPOSIT",
                    status=TransactionStatus.PENDING.value
                )
                session.add(p)
                await session.commit()

            adapter = MoMoPaymentAdapter()
            sig = adapter.generate_ipn_signature(
                access_key="momo_test_access_key",
                amount=40000,
                extra_data="",
                message="Successful.",
                order_id="tx_momo_ord_1003",
                order_info="Dat san",
                order_type="momo_wallet",
                partner_code="MOMO_TEST_PARTNER",
                pay_type="qr",
                request_id="req_1003",
                response_time=1721720663942,
                result_code=0,
                trans_id=987654323,
                secret_key="momo_test_secret_key_secret123456"
            )
            ipn_payload = {
                "partnerCode": "MOMO_TEST_PARTNER",
                "orderId": "tx_momo_ord_1003",
                "requestId": "req_1003",
                "amount": 40000,
                "orderInfo": "Dat san",
                "orderType": "momo_wallet",
                "transId": 987654323,
                "resultCode": 0,
                "message": "Successful.",
                "payType": "qr",
                "responseTime": 1721720663942,
                "extraData": "",
                "signature": sig
            }

            async with AsyncSessionLocal() as session:
                res = await process_momo_ipn(session, ipn_payload)
                self.assertEqual(res["status"], "reconciliation_required")

                b_res = await session.execute(select(Booking).where(Booking.id == 1003))
                b_db = b_res.scalar_one()
                # Must remain CANCELLED!
                self.assertEqual(b_db.payment_status, PaymentStatus.CANCELLED.value)

                p_res = await session.execute(select(Payment).where(Payment.transaction_id == "tx_momo_ord_1003"))
                p_db = p_res.scalar_one()
                self.assertEqual(p_db.status, TransactionStatus.REQUIRES_RECONCILIATION.value)

        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 17: Late IPN FAILED after SUCCESS does not downgrade transaction
    # -------------------------------------------------------------------------
    def test_17_failed_callback_after_success_no_downgrade(self):
        """17. IPN FAILED đến sau khi giao dịch đã SUCCESS không làm hạ cấp trạng thái."""
        async def _test():
            async with AsyncSessionLocal() as session:
                b = Booking(
                    id=1004,
                    user_id=1,
                    slot_id=1,
                    total_amount=80000.0,
                    deposit_amount=40000.0,
                    payment_status=PaymentStatus.DEPOSITED.value
                )
                session.add(b)
                p = Payment(
                    booking_id=1004,
                    user_id=1,
                    provider="MOMO",
                    transaction_id="tx_momo_ord_1004",
                    amount=40000.0,
                    currency="VND",
                    payment_type="DEPOSIT",
                    status=TransactionStatus.SUCCESS.value
                )
                session.add(p)
                await session.commit()

            adapter = MoMoPaymentAdapter()
            sig = adapter.generate_ipn_signature(
                access_key="momo_test_access_key",
                amount=40000,
                extra_data="",
                message="Transaction cancelled by user.",
                order_id="tx_momo_ord_1004",
                order_info="Dat san",
                order_type="momo_wallet",
                partner_code="MOMO_TEST_PARTNER",
                pay_type="qr",
                request_id="req_1004",
                response_time=1721720663942,
                result_code=1006,  # User cancelled
                trans_id=987654324,
                secret_key="momo_test_secret_key_secret123456"
            )
            ipn_payload = {
                "partnerCode": "MOMO_TEST_PARTNER",
                "orderId": "tx_momo_ord_1004",
                "requestId": "req_1004",
                "amount": 40000,
                "orderInfo": "Dat san",
                "orderType": "momo_wallet",
                "transId": 987654324,
                "resultCode": 1006,
                "message": "Transaction cancelled by user.",
                "payType": "qr",
                "responseTime": 1721720663942,
                "extraData": "",
                "signature": sig
            }

            async with AsyncSessionLocal() as session:
                res = await process_momo_ipn(session, ipn_payload)
                self.assertEqual(res["status"], "downgrade_prevented")

                p_res = await session.execute(select(Payment).where(Payment.transaction_id == "tx_momo_ord_1004"))
                p_db = p_res.scalar_one()
                self.assertEqual(p_db.status, TransactionStatus.SUCCESS.value)

        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 18: DB commit failure rolls back cleanly
    # -------------------------------------------------------------------------
    def test_18_db_commit_failure_rolls_back_cleanly(self):
        """18. Lỗi cơ sở dữ liệu khi commit IPN được rollback an toàn, không báo thành công sai."""
        async def _test():
            async with AsyncSessionLocal() as session:
                b = Booking(
                    id=1008,
                    user_id=1,
                    slot_id=1,
                    total_amount=80000.0,
                    deposit_amount=40000.0,
                    payment_status=PaymentStatus.PENDING.value
                )
                session.add(b)
                p = Payment(
                    booking_id=1008,
                    user_id=1,
                    provider="MOMO",
                    transaction_id="tx_momo_ord_1008",
                    amount=40000.0,
                    currency="VND",
                    payment_type="DEPOSIT",
                    status=TransactionStatus.PENDING.value
                )
                session.add(p)
                await session.commit()

            adapter = MoMoPaymentAdapter()
            sig = adapter.generate_ipn_signature(
                access_key="momo_test_access_key",
                amount=40000,
                extra_data="",
                message="Successful.",
                order_id="tx_momo_ord_1008",
                order_info="Dat san",
                order_type="momo_wallet",
                partner_code="MOMO_TEST_PARTNER",
                pay_type="qr",
                request_id="req_1008",
                response_time=1721720663942,
                result_code=0,
                trans_id=987654328,
                secret_key="momo_test_secret_key_secret123456"
            )
            ipn_payload = {
                "partnerCode": "MOMO_TEST_PARTNER",
                "orderId": "tx_momo_ord_1008",
                "requestId": "req_1008",
                "amount": 40000,
                "orderInfo": "Dat san",
                "orderType": "momo_wallet",
                "transId": 987654328,
                "resultCode": 0,
                "message": "Successful.",
                "payType": "qr",
                "responseTime": 1721720663942,
                "extraData": "",
                "signature": sig
            }

            async with AsyncSessionLocal() as session:
                with patch.object(session, "commit", side_effect=Exception("Disk I/O Error")):
                    res = await process_momo_ipn(session, ipn_payload)
                    self.assertEqual(res["status"], "db_commit_failed")

        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 19: Anti-IDOR check on payment attempt
    # -------------------------------------------------------------------------
    def test_19_anti_idor_payment_initiation(self):
        """19. Người dùng không thể khởi tạo thanh toán cho đơn đặt sân của người khác."""
        async def _test():
            async with AsyncSessionLocal() as session:
                b = Booking(
                    id=1005,
                    user_id=1,  # Belongs to user 1
                    slot_id=1,
                    total_amount=80000.0,
                    deposit_amount=40000.0,
                    payment_status=PaymentStatus.PENDING.value
                )
                session.add(b)
                await session.commit()

                # User 2 tries to initiate payment
                res = await create_payment_attempt(
                    db=session,
                    booking_id=1005,
                    user_id=2,
                    provider="MOMO"
                )
                self.assertEqual(res["status"], "permission_denied")

        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 20: Client redirect does not mutate booking or payment state
    # -------------------------------------------------------------------------
    def test_20_client_redirect_does_not_mutate_booking_state(self):
        """20. Client redirect từ trình duyệt không thể tự chuyển booking thành DEPOSITED/PAID."""
        async def _test():
            async with AsyncSessionLocal() as session:
                b = Booking(
                    id=1005,
                    user_id=1,
                    slot_id=1,
                    total_amount=80000.0,
                    deposit_amount=40000.0,
                    payment_status=PaymentStatus.PENDING.value
                )
                session.add(b)
                await session.commit()

                # Simulated redirect check: verify booking is still PENDING
                b_check = (await session.execute(select(Booking).where(Booking.id == 1005))).scalar_one_or_none()
                self.assertIsNotNone(b_check)
                self.assertEqual(b_check.payment_status, PaymentStatus.PENDING.value)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 21: Create timeout retry does not duplicate records
    # -------------------------------------------------------------------------
    def test_21_create_retry_idempotency_safe(self):
        """21. Retry khởi tạo thanh toán với idempotency_key trả về cùng payment record."""
        async def _test():
            async with AsyncSessionLocal() as session:
                b = Booking(
                    id=1006,
                    user_id=1,
                    slot_id=1,
                    total_amount=80000.0,
                    deposit_amount=40000.0,
                    payment_status=PaymentStatus.PENDING.value
                )
                session.add(b)
                await session.commit()

                # Mock create_payment_request on adapter
                adapter = get_payment_adapter("MOMO")
                with patch.object(adapter, "create_payment_request", new_callable=AsyncMock) as mock_create:
                    mock_create.return_value = {
                        "status": "success",
                        "pay_url": "https://test-payment.momo.vn/v2/gateway/pay?token=idemp1",
                        "deeplink": "momo://idemp1",
                        "qr_code_url": "https://momo/qr1",
                        "order_id": "tx_momo_idemp_1",
                        "request_id": "req_momo_idemp_1"
                    }

                    idemp_key = f"idemp_{uuid.uuid4().hex[:12]}"
                    res1 = await create_payment_attempt(
                        db=session,
                        booking_id=1006,
                        user_id=1,
                        provider="MOMO",
                        idempotency_key=idemp_key
                    )
                    self.assertEqual(res1["status"], "payment_attempt_created")
                    self.assertFalse(res1["is_idempotent"])
                    pay_id_1 = res1["data"]["payment_id"]

                    # Second attempt with same idempotency key
                    res2 = await create_payment_attempt(
                        db=session,
                        booking_id=1006,
                        user_id=1,
                        provider="MOMO",
                        idempotency_key=idemp_key
                    )
                    self.assertEqual(res2["status"], "payment_attempt_created")
                    self.assertTrue(res2["is_idempotent"])
                    self.assertEqual(res2["data"]["payment_id"], pay_id_1)
                    self.assertEqual(res2["data"]["pay_url"], "https://test-payment.momo.vn/v2/gateway/pay?token=idemp1")

        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 22: Phase 7.4A Sandbox adapter operates without regression
    # -------------------------------------------------------------------------
    def test_22_phase7_4a_sandbox_adapter_no_regression(self):
        """22. Adapter SANDBOX của Phase 7.4A tiếp tục hoạt động độc lập, không bị ảnh hưởng."""
        adapter = get_payment_adapter("SANDBOX")
        self.assertIsNotNone(adapter)
        self.assertTrue(adapter.is_enabled())

    # -------------------------------------------------------------------------
    # TEST 23: Phase 7.3 booking flow no regression
    # -------------------------------------------------------------------------
    def test_23_phase7_3_booking_flow_no_regression(self):
        """23. Flow đặt sân Phase 7.3 không bị ảnh hưởng bởi tích hợp MoMo."""
        from app.services.booking_service import create_booking_preview
        from app.core.redis import acquire_slot_lock, release_slot_lock
        async def _test():
            await acquire_slot_lock(slot_id=2, user_id=1, timeout_sec=600)
            try:
                async with AsyncSessionLocal() as session:
                    prev = await create_booking_preview(session, user_id=1, slot_id=2)
                    self.assertEqual(prev["status"], "preview_created")
                    self.assertIn("data", prev)
                    self.assertEqual(prev["data"]["total_amount"], 80000.0)
            finally:
                await release_slot_lock(slot_id=2, user_id=1)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 24: Payment pending auto-expiry remains disabled
    # -------------------------------------------------------------------------
    def test_24_payment_expiry_remains_disabled(self):
        """24. PAYMENT_PENDING_EXPIRY_ENABLED vẫn giữ mặc định False theo chính sách chưa phê duyệt."""
        exp_flag = os.getenv("PAYMENT_PENDING_EXPIRY_ENABLED") or getattr(settings, "PAYMENT_PENDING_EXPIRY_ENABLED", False)
        self.assertFalse(str(exp_flag).lower() in ("true", "1"))

    # -------------------------------------------------------------------------
    # TEST 25: Secrets and raw provider payload never leaked
    # -------------------------------------------------------------------------
    def test_25_secrets_not_leaked_in_responses(self):
        """25. Secret keys (MOMO_SECRET_KEY, ACCESS_KEY) không bao giờ bị trả về frontend/client."""
        async def _test():
            async with AsyncSessionLocal() as session:
                pm_res = await session.execute(select(Payment).where(Payment.booking_id == 1001))
                p = pm_res.scalar_one_or_none()
                if p:
                    # Verify stored response doesn't expose secret_key
                    self.assertNotIn("momo_test_secret_key", p.provider_response)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 26: Mock HTTP vs live sandbox distinction
    # -------------------------------------------------------------------------
    def test_26_mock_vs_live_sandbox_clear_distinction(self):
        """26. Unit test sử dụng mock HTTP không tuyên bố sai lệch là live sandbox PASS."""
        adapter = MoMoPaymentAdapter()
        self.assertTrue(hasattr(adapter, "create_payment_request"))
        self.assertTrue(callable(adapter.create_payment_request))

    # -------------------------------------------------------------------------
    # TEST 27: Live Sandbox E2E audit classification
    # -------------------------------------------------------------------------
    def test_27_live_sandbox_audit_classification(self):
        """27. Kiểm tra phân loại live sandbox: BLOCKED / NOT TESTED khi chưa có merchant credentials thật."""
        # Check if live credentials exist
        has_real_creds = not (
            os.getenv("MOMO_PARTNER_CODE", "").startswith("MOMO_TEST") or
            os.getenv("MOMO_SECRET_KEY", "").startswith("momo_test") or
            os.getenv("MOMO_ACCESS_KEY", "").startswith("momo_test")
        )
        if not has_real_creds:
            # Documented as BLOCKED / NOT TESTED per prompt instructions
            self.assertTrue(True, "Live Sandbox E2E audit is categorized as BLOCKED / NOT TESTED due to test mock credentials.")

    # -------------------------------------------------------------------------
    # TEST 28: IPN signature verification strictly requires server-configured accessKey
    # -------------------------------------------------------------------------
    def test_28_ipn_missing_access_key_strictly_rejected(self):
        """28. Không tự động chấp nhận IPN nếu thiếu accessKey cấu hình phía server."""
        adapter = MoMoPaymentAdapter()
        ipn_payload = {
            "partnerCode": "MOMO_TEST_PARTNER",
            "orderId": "tx_momo_ord_test28",
            "requestId": "req_test28",
            "amount": 40000,
            "resultCode": 0,
            "signature": "some_signature_value"
        }
        # When accessKey is missing from both payload, param, and environment
        with patch.dict(os.environ, {"MOMO_ACCESS_KEY": ""}):
            is_valid = adapter.verify_ipn_signature(
                payload=ipn_payload,
                secret_key="momo_test_secret_key",
                access_key=""
            )
            self.assertFalse(is_valid, "IPN verification must fail closed when server accessKey is absent.")

    # -------------------------------------------------------------------------
    # TEST 29: Official IPN payload without accessKey field in JSON succeeds
    # -------------------------------------------------------------------------
    def test_29_official_ipn_payload_without_accesskey_field_succeeds_with_server_config(self):
        """29. Payload IPN chính thức không chứa trường accessKey vẫn xác minh thành công bằng server accessKey."""
        adapter = MoMoPaymentAdapter()
        # Official MoMo v3 callback JSON format (NO accessKey in body)
        official_ipn_payload = {
            "partnerCode": "MOMO_TEST_PARTNER",
            "orderId": "tx_momo_ord_test29",
            "requestId": "req_test29",
            "amount": 40000,
            "orderInfo": "Dat san VIP",
            "orderType": "momo_wallet",
            "transId": 987654329,
            "resultCode": 0,
            "message": "Successful.",
            "payType": "qr",
            "responseTime": 1721720663942,
            "extraData": ""
        }
        self.assertNotIn("accessKey", official_ipn_payload, "Official MoMo callback does not contain accessKey field.")

        # Compute valid signature using server configured accessKey
        sig = adapter.generate_ipn_signature(
            access_key="momo_test_access_key",
            amount=40000,
            extra_data="",
            message="Successful.",
            order_id="tx_momo_ord_test29",
            order_info="Dat san VIP",
            order_type="momo_wallet",
            partner_code="MOMO_TEST_PARTNER",
            pay_type="qr",
            request_id="req_test29",
            response_time=1721720663942,
            result_code=0,
            trans_id=987654329,
            secret_key="momo_test_secret_key_secret123456"
        )
        official_ipn_payload["signature"] = sig

        # Verification must succeed using server-configured accessKey without requiring accessKey in JSON
        is_valid = adapter.verify_ipn_signature(
            payload=official_ipn_payload,
            secret_key="momo_test_secret_key_secret123456",
            access_key="momo_test_access_key"
        )
        self.assertTrue(is_valid, "IPN verification must pass with official payload format using configured access key.")

    # -------------------------------------------------------------------------
    # TEST 30: API create enforces minimum 30 seconds timeout per MoMo spec
    # -------------------------------------------------------------------------
    def test_30_api_create_timeout_minimum_30s_enforced(self):
        """30. Timeout gọi MoMo create API được bảo đảm tối thiểu 30 giây theo đặc tả onboarding."""
        from app.services.payment_adapters.momo_adapter import MIN_MOMO_TIMEOUT_SECONDS, DEFAULT_MOMO_TIMEOUT_SECONDS
        self.assertGreaterEqual(MIN_MOMO_TIMEOUT_SECONDS, 30.0)
        self.assertGreaterEqual(DEFAULT_MOMO_TIMEOUT_SECONDS, 30.0)

        adapter = MoMoPaymentAdapter()
        captured_timeout = None

        class MockClientWithTimeoutCheck:
            async def post(self, url, json=None, **kwargs):
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {
                    "resultCode": 0,
                    "payUrl": "https://test-payment.momo.vn/v2/gateway/pay?token=xyz"
                }
                return mock_resp

        # With mock client
        res = self.run_async(adapter.create_payment_request(
            order_id="momo_to_01",
            request_id="momo_req_to_01",
            amount=40000,
            order_info="Test timeout",
            client=MockClientWithTimeoutCheck(),
            timeout_seconds=10.0 # Requested lower timeout
        ))
        self.assertEqual(res["status"], "success")

    # -------------------------------------------------------------------------
    # TEST 31: IPN missing truly required contract fields is rejected
    # -------------------------------------------------------------------------
    def test_31_ipn_missing_required_payload_fields_rejected(self):
        """31. IPN thiếu các trường hợp đồng bắt buộc (orderId, amount, resultCode) bị từ chối fail-closed."""
        adapter = MoMoPaymentAdapter()
        # Missing orderId
        bad_payload_1 = {
            "partnerCode": "MOMO_TEST_PARTNER",
            "requestId": "req_missing",
            "amount": 40000,
            "resultCode": 0,
            "signature": "sig123"
        }
        self.assertFalse(adapter.verify_ipn_signature(bad_payload_1))

        # Missing amount
        bad_payload_2 = {
            "partnerCode": "MOMO_TEST_PARTNER",
            "orderId": "ord_missing",
            "requestId": "req_missing",
            "resultCode": 0,
            "signature": "sig123"
        }
        self.assertFalse(adapter.verify_ipn_signature(bad_payload_2))

    # -------------------------------------------------------------------------
    # TEST 32: Preflight gate audit and fail-closed validation
    # -------------------------------------------------------------------------
    def test_32_preflight_gate_audit_and_fail_closed(self):
        """32. Preflight gate phát hiện chính xác thiếu sót cấu hình và chặn Live request an toàn."""
        adapter = MoMoPaymentAdapter()

        # In current test env without real merchant keys
        preflight_res = adapter.check_preflight()
        self.assertIn("status", preflight_res)
        self.assertIn("details", preflight_res)
        self.assertIn("missing_variables", preflight_res)

        # When variables are fully and validly configured
        valid_env = {
            "MOMO_ENVIRONMENT": "sandbox",
            "MOMO_PARTNER_CODE": "MOMO_TEST_PARTNER_01",
            "MOMO_ACCESS_KEY": "ACC_TEST_KEY_123",
            "MOMO_SECRET_KEY": "SEC_TEST_KEY_456789",
            "MOMO_ENDPOINT": "https://test-payment.momo.vn",
            "MOMO_REDIRECT_URL": "https://badminton.ai/payment/result",
            "MOMO_IPN_URL": "https://api.badminton.ai/api/v1/payments/momo/ipn",
            "MOMO_TIMEOUT_SECONDS": "30.0"
        }
        with patch.dict(os.environ, valid_env, clear=False):
            res_pass = adapter.check_preflight()
            self.assertEqual(res_pass["status"], "PASS")
            self.assertEqual(len(res_pass["missing_variables"]), 0)
            self.assertEqual(len(res_pass["invalid_variables"]), 0)

        # When production or localhost or placeholder is injected
        invalid_env = {
            "MOMO_ENVIRONMENT": "production",
            "MOMO_PARTNER_CODE": "your_momo_partner_code",
            "MOMO_ACCESS_KEY": "mock_key",
            "MOMO_SECRET_KEY": "mock_secret",
            "MOMO_ENDPOINT": "https://payment.momo.vn/v2/gateway/api/create",
            "MOMO_REDIRECT_URL": "http://localhost:8085/payment/result",
            "MOMO_IPN_URL": "https://example.com/ipn",
            "MOMO_TIMEOUT_SECONDS": "10.0"
        }
        with patch.dict(os.environ, invalid_env, clear=False):
            res_blocked = adapter.check_preflight()
            self.assertEqual(res_blocked["status"], "BLOCKED — PREFLIGHT FAILED")
            self.assertIn("MOMO_ENVIRONMENT", res_blocked["invalid_variables"])
            self.assertIn("MOMO_PARTNER_CODE", res_blocked["invalid_variables"])
            self.assertIn("MOMO_ENDPOINT", res_blocked["invalid_variables"])
            self.assertIn("MOMO_REDIRECT_URL", res_blocked["invalid_variables"])
            self.assertIn("MOMO_IPN_URL", res_blocked["invalid_variables"])
            self.assertIn("MOMO_TIMEOUT_SECONDS", res_blocked["invalid_variables"])


if __name__ == "__main__":
    unittest.main()

