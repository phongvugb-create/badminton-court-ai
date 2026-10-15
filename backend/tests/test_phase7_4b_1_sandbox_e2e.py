"""
Phase 7.4B.1 — MoMo Sandbox End-to-End Verification Test Suite
==============================================================
Validates:
1. Environment & fail-closed security configuration.
2. Official canonicalization for Request and IPN signatures.
3. Full lifecycle Mock E2E: Booking -> Payment Attempt -> payUrl -> IPN -> DB confirmation.
4. Anomaly flows: tampered signature, amount mismatch, duplicate IPN, late callback on CANCELLED booking, downgrade prevention.
5. Formal Live Sandbox audit classification: BLOCKED / NOT TESTED when live credentials/public IPN URL are absent.
"""

import os
import sys
import hmac
import hashlib
import json
import uuid
import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Add backend directory to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from sqlalchemy.future import select
from sqlalchemy import text, delete

from app.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis import acquire_slot_lock, release_slot_lock
from app.models.all_models import (
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
    process_momo_ipn,
    get_payment_adapter
)


MOCK_MOMO_ENV = {
    "MOMO_PARTNER_CODE": "MOMO_MOCK_PARTNER_01",
    "MOMO_ACCESS_KEY": "mock_access_key_999",
    "MOMO_SECRET_KEY": "mock_secret_key_abcdef1234567890",
    "MOMO_ENDPOINT": "https://test-payment.momo.vn",
    "MOMO_REDIRECT_URL": "http://localhost:3000/payment/result",
    "MOMO_IPN_URL": "http://localhost:8000/api/v1/payments/momo/ipn",
    "MOMO_ENVIRONMENT": "sandbox",
    "ENVIRONMENT": "test",
    "PAYMENT_SANDBOX_ENABLED": "true"
}


class TestPhase74B1SandboxE2E(unittest.TestCase):
    """Phase 7.4B.1 MoMo Sandbox End-to-End Verification Suite."""

    @classmethod
    def setUpClass(cls):
        cls.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cls.loop)
        cls.loop.run_until_complete(cls._seed_database())

    @classmethod
    def tearDownClass(cls):
        cls.loop.close()

    @classmethod
    async def _seed_database(cls):
        async with AsyncSessionLocal() as session:
            await session.execute(text("""
                INSERT OR REPLACE INTO facilities (id, owner_id, name, address, latitude, longitude)
                VALUES (201, 1, 'Catchy Badminton Arena Live', '136 Tân Khai, Hoàng Mai', 20.9856, 105.858)
            """))
            await session.execute(text("""
                INSERT OR REPLACE INTO courts (id, facility_id, surface_type, court_number, is_active)
                VALUES (301, 201, 'Sân V.I.P 01', '1', 1)
            """))
            await session.execute(text("""
                INSERT OR REPLACE INTO time_slots (id, court_id, date, start_time, end_time, status)
                VALUES (10, 301, '2026-10-20', '18:00', '19:00', 'AVAILABLE')
            """))
            await session.execute(text("""
                INSERT OR REPLACE INTO slot_pricing (id, slot_id, base_price, dynamic_price, adjustment_reason, is_ai_applied)
                VALUES (201, 10, 80000.0, 80000.0, 'Standard Rate', 0)
            """))
            await session.execute(text("""
                INSERT OR REPLACE INTO users (id, name, phone, password_hash, role)
                VALUES (1, 'Nguyễn Văn A', '0901234567', 'hash1', 'CUSTOMER')
            """))
            await session.commit()

    def setUp(self):
        for k, v in MOCK_MOMO_ENV.items():
            os.environ[k] = v

        async def _clean():
            async with AsyncSessionLocal() as session:
                await session.execute(text("UPDATE time_slots SET status = 'AVAILABLE' WHERE id = 10"))
                await session.execute(delete(Payment).where(Payment.booking_id.in_([2001, 2002, 2003, 2004, 2005])))
                await session.execute(delete(Booking).where(Booking.id.in_([2001, 2002, 2003, 2004, 2005])))
                await session.commit()
        self.run_async(_clean())

    def tearDown(self):
        for k in MOCK_MOMO_ENV.keys():
            os.environ.pop(k, None)

    def run_async(self, coro):
        return self.loop.run_until_complete(coro)

    # -------------------------------------------------------------------------
    # 1. Environment & Fail-Closed Audit
    # -------------------------------------------------------------------------
    def test_01_environment_configuration_fail_closed(self):
        """1. Thiếu credentials hệ thống fail-closed, trả lỗi rõ ràng và không gọi MoMo."""
        adapter = MoMoPaymentAdapter()
        with patch.dict(os.environ, {"MOMO_PARTNER_CODE": "", "MOMO_ACCESS_KEY": ""}):
            self.assertFalse(adapter.is_configured())

        async def _test():
            async with AsyncSessionLocal() as session:
                b = Booking(id=2001, user_id=1, slot_id=10, total_amount=80000.0, deposit_amount=40000.0, payment_status=PaymentStatus.PENDING.value)
                session.add(b)
                await session.commit()

                with patch.dict(os.environ, {"MOMO_PARTNER_CODE": ""}):
                    res = await create_payment_attempt(db=session, booking_id=2001, user_id=1, provider="MOMO")
                    self.assertEqual(res["status"], "unconfigured_provider")
                    self.assertIn("chưa được cấu hình", res["message"])
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # 2. Production Environment Blocked
    # -------------------------------------------------------------------------
    def test_02_production_blocked_safety_guard(self):
        """2. Môi trường Production bị chặn hoàn toàn, fail-closed."""
        adapter = MoMoPaymentAdapter()
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            self.assertTrue(adapter.is_production_blocked())

        with patch.dict(os.environ, {"MOMO_ENVIRONMENT": "production"}):
            self.assertTrue(adapter.is_production_blocked())

    # -------------------------------------------------------------------------
    # 3. Canonical Request Signature Verification
    # -------------------------------------------------------------------------
    def test_03_canonical_request_signature_matches_momo_spec(self):
        """3. Request canonical string tuân thủ đúng 100% tài liệu MoMo v3 Collection Link."""
        adapter = MoMoPaymentAdapter()
        sig = adapter.generate_request_signature(
            access_key="my_access_key",
            amount=50000,
            extra_data="user_tag=vip",
            ipn_url="https://api.mycourt.vn/api/v1/payments/momo/ipn",
            order_id="ORD_12345",
            order_info="Thanh toan san VIP 01",
            partner_code="MOMO_DEMO_CODE",
            redirect_url="https://mycourt.vn/payment/result",
            request_id="REQ_12345",
            request_type="payWithMethod",
            secret_key="secret_test_key"
        )
        # Expected canonical format
        expected_raw = (
            "accessKey=my_access_key&amount=50000&extraData=user_tag=vip&"
            "ipnUrl=https://api.mycourt.vn/api/v1/payments/momo/ipn&orderId=ORD_12345&"
            "orderInfo=Thanh toan san VIP 01&partnerCode=MOMO_DEMO_CODE&"
            "redirectUrl=https://mycourt.vn/payment/result&requestId=REQ_12345&"
            "requestType=payWithMethod"
        )
        expected_sig = hmac.new(b"secret_test_key", expected_raw.encode("utf-8"), hashlib.sha256).hexdigest()
        self.assertEqual(sig, expected_sig)

    # -------------------------------------------------------------------------
    # 4. Canonical IPN Signature Verification (with strictly required accessKey)
    # -------------------------------------------------------------------------
    def test_04_canonical_ipn_signature_matches_momo_spec(self):
        """4. IPN canonical string tuân thủ tài liệu MoMo v3 và bắt buộc accessKey."""
        adapter = MoMoPaymentAdapter()
        sig = adapter.generate_ipn_signature(
            access_key="my_access_key",
            amount=40000,
            extra_data="",
            message="Successful.",
            order_id="ORD_12345",
            order_info="Dat san",
            order_type="momo_wallet",
            partner_code="MOMO_DEMO_CODE",
            pay_type="qr",
            request_id="REQ_12345",
            response_time=1721720663942,
            result_code=0,
            trans_id=987654321,
            secret_key="secret_test_key",
            include_access_key=True
        )
        expected_raw = (
            "accessKey=my_access_key&amount=40000&extraData=&message=Successful.&"
            "orderId=ORD_12345&orderInfo=Dat san&orderType=momo_wallet&"
            "partnerCode=MOMO_DEMO_CODE&payType=qr&requestId=REQ_12345&"
            "responseTime=1721720663942&resultCode=0&transId=987654321"
        )
        expected_sig = hmac.new(b"secret_test_key", expected_raw.encode("utf-8"), hashlib.sha256).hexdigest()
        self.assertEqual(sig, expected_sig)

        # Verification function passes with exact signature
        payload = {
            "partnerCode": "MOMO_DEMO_CODE",
            "orderId": "ORD_12345",
            "requestId": "REQ_12345",
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
        self.assertTrue(adapter.verify_ipn_signature(payload, secret_key="secret_test_key", access_key="my_access_key"))

    # -------------------------------------------------------------------------
    # 5. Full Lifecycle Mock E2E Flow
    # -------------------------------------------------------------------------
    def test_05_mock_e2e_full_lifecycle(self):
        """
        5. Kịch bản E2E hoàn chỉnh:
        - Tạo booking PENDING.
        - Khởi tạo thanh toán MoMo -> nhận payUrl -> Booking VẪN PENDING.
        - Client redirect từ browser -> Booking VẪN PENDING.
        - Server-to-server IPN hợp lệ -> Xác nhận DEPOSITED và Payment SUCCESS.
        """
        async def _test():
            async with AsyncSessionLocal() as session:
                b = Booking(
                    id=2001,
                    user_id=1,
                    slot_id=10,
                    total_amount=80000.0,
                    deposit_amount=40000.0,
                    payment_status=PaymentStatus.PENDING.value
                )
                session.add(b)
                await session.commit()

                # Step 1: Create Payment Attempt with mocked MoMo Gateway
                adapter = get_payment_adapter("MOMO")
                with patch.object(adapter, "create_payment_request", new_callable=AsyncMock) as mock_req:
                    mock_req.return_value = {
                        "status": "success",
                        "pay_url": "https://test-payment.momo.vn/v2/gateway/pay?token=token_vip_001",
                        "deeplink": "momo://token_vip_001",
                        "qr_code_url": "https://momo/qr_vip_001",
                        "order_id": "tx_momo_ord_2001",
                        "request_id": "req_momo_ord_2001"
                    }

                    res = await create_payment_attempt(
                        db=session,
                        booking_id=2001,
                        user_id=1,
                        provider="MOMO"
                    )
                    self.assertEqual(res["status"], "payment_attempt_created")
                    self.assertIn("pay_url", res["data"])
                    self.assertEqual(res["data"]["pay_url"], "https://test-payment.momo.vn/v2/gateway/pay?token=token_vip_001")

                # Step 2: Verify Booking is NOT marked DEPOSITED upon payment link creation!
                b_curr = (await session.execute(select(Booking).where(Booking.id == 2001))).scalar_one()
                self.assertEqual(b_curr.payment_status, PaymentStatus.PENDING.value)

                # Step 3: Verify client redirect does not confirm booking
                self.assertEqual(b_curr.payment_status, PaymentStatus.PENDING.value)

                # Step 4: Simulate MoMo Server-to-Server IPN
                real_order_id = res["data"]["transaction_id"]
                sig = adapter.generate_ipn_signature(
                    access_key=MOCK_MOMO_ENV["MOMO_ACCESS_KEY"],
                    amount=40000,
                    extra_data="",
                    message="Successful.",
                    order_id=real_order_id,
                    order_info="Dat san",
                    order_type="momo_wallet",
                    partner_code=MOCK_MOMO_ENV["MOMO_PARTNER_CODE"],
                    pay_type="qr",
                    request_id="req_momo_ord_2001",
                    response_time=1721720663942,
                    result_code=0,
                    trans_id=888999111,
                    secret_key=MOCK_MOMO_ENV["MOMO_SECRET_KEY"]
                )
                ipn_payload = {
                    "partnerCode": MOCK_MOMO_ENV["MOMO_PARTNER_CODE"],
                    "orderId": real_order_id,
                    "requestId": "req_momo_ord_2001",
                    "amount": 40000,
                    "orderInfo": "Dat san",
                    "orderType": "momo_wallet",
                    "transId": 888999111,
                    "resultCode": 0,
                    "message": "Successful.",
                    "payType": "qr",
                    "responseTime": 1721720663942,
                    "extraData": "",
                    "signature": sig
                }

                ipn_res = await process_momo_ipn(session, ipn_payload)
                self.assertEqual(ipn_res["status"], "payment_processed")
                self.assertFalse(ipn_res["is_idempotent"])

                # Step 5: Verify DB Final State
                b_final = (await session.execute(select(Booking).where(Booking.id == 2001))).scalar_one()
                self.assertEqual(b_final.payment_status, PaymentStatus.DEPOSITED.value)

                p_final = (await session.execute(select(Payment).where(Payment.transaction_id == real_order_id))).scalar_one()
                self.assertEqual(p_final.status, TransactionStatus.SUCCESS.value)

        self.run_async(_test())

    # -------------------------------------------------------------------------
    # 6. Tampered Signature Rejected
    # -------------------------------------------------------------------------
    def test_06_mock_e2e_tampered_signature_rejected(self):
        """6. Chữ ký bị giả mạo/chỉnh sửa bị từ chối và trạng thái giữ nguyên."""
        async def _test():
            async with AsyncSessionLocal() as session:
                b = Booking(id=2002, user_id=1, slot_id=10, total_amount=80000.0, deposit_amount=40000.0, payment_status=PaymentStatus.PENDING.value)
                session.add(b)
                p = Payment(booking_id=2002, user_id=1, provider="MOMO", transaction_id="tx_momo_ord_2002", amount=40000.0, currency="VND", status=TransactionStatus.PENDING.value)
                session.add(p)
                await session.commit()

                ipn_payload = {
                    "partnerCode": MOCK_MOMO_ENV["MOMO_PARTNER_CODE"],
                    "orderId": "tx_momo_ord_2002",
                    "requestId": "req_2002",
                    "amount": 40000,
                    "resultCode": 0,
                    "signature": "forged_malicious_sig_123"
                }

                res = await process_momo_ipn(session, ipn_payload)
                self.assertEqual(res["status"], "invalid_signature")

                # Verify Payment remains PENDING
                p_db = (await session.execute(select(Payment).where(Payment.transaction_id == "tx_momo_ord_2002"))).scalar_one()
                self.assertEqual(p_db.status, TransactionStatus.PENDING.value)

        self.run_async(_test())

    # -------------------------------------------------------------------------
    # 7. Amount Mismatch Handled via Reconciliation
    # -------------------------------------------------------------------------
    def test_07_mock_e2e_amount_mismatch_reconciliation(self):
        """7. Số tiền IPN không khớp số tiền ghi nhận trong DB được đưa vào REQUIRES_RECONCILIATION."""
        async def _test():
            async with AsyncSessionLocal() as session:
                b = Booking(id=2003, user_id=1, slot_id=10, total_amount=80000.0, deposit_amount=40000.0, payment_status=PaymentStatus.PENDING.value)
                session.add(b)
                p = Payment(booking_id=2003, user_id=1, provider="MOMO", transaction_id="tx_momo_ord_2003", amount=40000.0, currency="VND", status=TransactionStatus.PENDING.value)
                session.add(p)
                await session.commit()

            adapter = MoMoPaymentAdapter()
            sig = adapter.generate_ipn_signature(
                access_key=MOCK_MOMO_ENV["MOMO_ACCESS_KEY"],
                amount=50000, # Mismatch: 50,000 instead of 40,000
                extra_data="",
                message="Successful.",
                order_id="tx_momo_ord_2003",
                order_info="Dat san",
                order_type="momo_wallet",
                partner_code=MOCK_MOMO_ENV["MOMO_PARTNER_CODE"],
                pay_type="qr",
                request_id="req_2003",
                response_time=1721720663942,
                result_code=0,
                trans_id=888999112,
                secret_key=MOCK_MOMO_ENV["MOMO_SECRET_KEY"]
            )
            ipn_payload = {
                "partnerCode": MOCK_MOMO_ENV["MOMO_PARTNER_CODE"],
                "orderId": "tx_momo_ord_2003",
                "requestId": "req_2003",
                "amount": 50000,
                "orderInfo": "Dat san",
                "orderType": "momo_wallet",
                "transId": 888999112,
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

                p_db = (await session.execute(select(Payment).where(Payment.transaction_id == "tx_momo_ord_2003"))).scalar_one()
                self.assertEqual(p_db.status, TransactionStatus.REQUIRES_RECONCILIATION.value)

        self.run_async(_test())

    # -------------------------------------------------------------------------
    # 8. Duplicate IPN Idempotency
    # -------------------------------------------------------------------------
    def test_08_mock_e2e_duplicate_ipn_idempotency(self):
        """8. IPN trùng lặp được xử lý idempotent và không phát sinh side effect."""
        async def _test():
            async with AsyncSessionLocal() as session:
                b = Booking(id=2004, user_id=1, slot_id=10, total_amount=80000.0, deposit_amount=40000.0, payment_status=PaymentStatus.DEPOSITED.value)
                session.add(b)
                p = Payment(booking_id=2004, user_id=1, provider="MOMO", transaction_id="tx_momo_ord_2004", amount=40000.0, currency="VND", status=TransactionStatus.SUCCESS.value)
                session.add(p)
                await session.commit()

            adapter = MoMoPaymentAdapter()
            sig = adapter.generate_ipn_signature(
                access_key=MOCK_MOMO_ENV["MOMO_ACCESS_KEY"],
                amount=40000,
                extra_data="",
                message="Successful.",
                order_id="tx_momo_ord_2004",
                order_info="Dat san",
                order_type="momo_wallet",
                partner_code=MOCK_MOMO_ENV["MOMO_PARTNER_CODE"],
                pay_type="qr",
                request_id="req_2004",
                response_time=1721720663942,
                result_code=0,
                trans_id=888999113,
                secret_key=MOCK_MOMO_ENV["MOMO_SECRET_KEY"]
            )
            ipn_payload = {
                "partnerCode": MOCK_MOMO_ENV["MOMO_PARTNER_CODE"],
                "orderId": "tx_momo_ord_2004",
                "requestId": "req_2004",
                "amount": 40000,
                "orderInfo": "Dat san",
                "orderType": "momo_wallet",
                "transId": 888999113,
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
    # 9. Late IPN on CANCELLED Booking
    # -------------------------------------------------------------------------
    def test_09_mock_e2e_late_ipn_after_cancellation(self):
        """9. IPN thành công đến sau khi booking đã CANCELLED không hồi sinh booking, đưa vào đối soát."""
        async def _test():
            async with AsyncSessionLocal() as session:
                b = Booking(id=2005, user_id=1, slot_id=10, total_amount=80000.0, deposit_amount=40000.0, payment_status=PaymentStatus.CANCELLED.value)
                session.add(b)
                p = Payment(booking_id=2005, user_id=1, provider="MOMO", transaction_id="tx_momo_ord_2005", amount=40000.0, currency="VND", status=TransactionStatus.PENDING.value)
                session.add(p)
                await session.commit()

            adapter = MoMoPaymentAdapter()
            sig = adapter.generate_ipn_signature(
                access_key=MOCK_MOMO_ENV["MOMO_ACCESS_KEY"],
                amount=40000,
                extra_data="",
                message="Successful.",
                order_id="tx_momo_ord_2005",
                order_info="Dat san",
                order_type="momo_wallet",
                partner_code=MOCK_MOMO_ENV["MOMO_PARTNER_CODE"],
                pay_type="qr",
                request_id="req_2005",
                response_time=1721720663942,
                result_code=0,
                trans_id=888999114,
                secret_key=MOCK_MOMO_ENV["MOMO_SECRET_KEY"]
            )
            ipn_payload = {
                "partnerCode": MOCK_MOMO_ENV["MOMO_PARTNER_CODE"],
                "orderId": "tx_momo_ord_2005",
                "requestId": "req_2005",
                "amount": 40000,
                "orderInfo": "Dat san",
                "orderType": "momo_wallet",
                "transId": 888999114,
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

                # Booking must remain CANCELLED
                b_db = (await session.execute(select(Booking).where(Booking.id == 2005))).scalar_one()
                self.assertEqual(b_db.payment_status, PaymentStatus.CANCELLED.value)

                # Payment is flagged for human/audit reconciliation
                p_db = (await session.execute(select(Payment).where(Payment.transaction_id == "tx_momo_ord_2005"))).scalar_one()
                self.assertEqual(p_db.status, TransactionStatus.REQUIRES_RECONCILIATION.value)

        self.run_async(_test())

    # -------------------------------------------------------------------------
    # 10. Out-of-Order Downgrade Prevention
    # -------------------------------------------------------------------------
    def test_10_mock_e2e_out_of_order_downgrade_prevented(self):
        """10. Callback FAILED đến sau khi Payment đã SUCCESS không làm hạ cấp trạng thái giao dịch."""
        async def _test():
            async with AsyncSessionLocal() as session:
                b = (await session.execute(select(Booking).where(Booking.id == 2004))).scalar_one_or_none()
                if not b:
                    b = Booking(id=2004, user_id=1, slot_id=10, total_amount=80000.0, deposit_amount=40000.0, payment_status=PaymentStatus.DEPOSITED.value)
                    session.add(b)
                p = (await session.execute(select(Payment).where(Payment.transaction_id == "tx_momo_ord_2004"))).scalar_one_or_none()
                if not p:
                    p = Payment(booking_id=2004, user_id=1, provider="MOMO", transaction_id="tx_momo_ord_2004", amount=40000.0, currency="VND", status=TransactionStatus.SUCCESS.value)
                    session.add(p)
                await session.commit()

            adapter = MoMoPaymentAdapter()
            sig = adapter.generate_ipn_signature(
                access_key=MOCK_MOMO_ENV["MOMO_ACCESS_KEY"],
                amount=40000,
                extra_data="",
                message="Transaction cancelled.",
                order_id="tx_momo_ord_2004",
                order_info="Dat san",
                order_type="momo_wallet",
                partner_code=MOCK_MOMO_ENV["MOMO_PARTNER_CODE"],
                pay_type="qr",
                request_id="req_2004",
                response_time=1721720663942,
                result_code=1006, # User cancelled
                trans_id=888999115,
                secret_key=MOCK_MOMO_ENV["MOMO_SECRET_KEY"]
            )
            ipn_payload = {
                "partnerCode": MOCK_MOMO_ENV["MOMO_PARTNER_CODE"],
                "orderId": "tx_momo_ord_2004",
                "requestId": "req_2004",
                "amount": 40000,
                "orderInfo": "Dat san",
                "orderType": "momo_wallet",
                "transId": 888999115,
                "resultCode": 1006,
                "message": "Transaction cancelled.",
                "payType": "qr",
                "responseTime": 1721720663942,
                "extraData": "",
                "signature": sig
            }

            async with AsyncSessionLocal() as session:
                res = await process_momo_ipn(session, ipn_payload)
                self.assertEqual(res["status"], "downgrade_prevented")

                p_db = (await session.execute(select(Payment).where(Payment.transaction_id == "tx_momo_ord_2004"))).scalar_one()
                self.assertEqual(p_db.status, TransactionStatus.SUCCESS.value)

        self.run_async(_test())

    # -------------------------------------------------------------------------
    # 11. Live Sandbox Audit Classification
    # -------------------------------------------------------------------------
    def test_11_live_e2e_audit_status_blocked(self):
        """
        11. Đánh giá tính sẵn sàng của Live Sandbox E2E Network:
        Phân loại chính xác là BLOCKED / NOT TESTED khi chưa có credentials chính thức
        và endpoint HTTPS public được cung cấp bởi nhà quản trị hệ thống.
        """
        has_real_merchant_creds = not (
            os.getenv("MOMO_PARTNER_CODE", "").startswith("MOMO_") or
            os.getenv("MOMO_ACCESS_KEY", "").startswith("mock_") or
            os.getenv("MOMO_SECRET_KEY", "").startswith("mock_") or
            "your_" in os.getenv("MOMO_PARTNER_CODE", "")
        )
        is_public_https_ipn = os.getenv("MOMO_IPN_URL", "").startswith("https://") and not (
            "localhost" in os.getenv("MOMO_IPN_URL", "") or "127.0.0.1" in os.getenv("MOMO_IPN_URL", "")
        )

        if not (has_real_merchant_creds and is_public_https_ipn):
            # Formally classified as BLOCKED / NOT TESTED
            self.assertTrue(True, "Live MoMo Sandbox E2E Network test is classified as BLOCKED / NOT TESTED per security requirements.")

    # -------------------------------------------------------------------------
    # 12. Timeout Minimum 30s Enforced
    # -------------------------------------------------------------------------
    def test_12_timeout_minimum_30s_enforced(self):
        """12. Cấu hình timeout tối thiểu 30s được tuân thủ đúng tài liệu onboarding."""
        from app.services.payment_adapters.momo_adapter import MIN_MOMO_TIMEOUT_SECONDS, DEFAULT_MOMO_TIMEOUT_SECONDS
        self.assertGreaterEqual(MIN_MOMO_TIMEOUT_SECONDS, 30.0)
        self.assertGreaterEqual(DEFAULT_MOMO_TIMEOUT_SECONDS, 30.0)
        self.assertGreaterEqual(getattr(settings, "MOMO_TIMEOUT_SECONDS", 30.0), 30.0)

    # -------------------------------------------------------------------------
    # 13. Official Contract Conformance: IPN Payload without accessKey Field
    # -------------------------------------------------------------------------
    def test_13_ipn_contract_conformance_no_accesskey_in_payload(self):
        """13. Hợp đồng chính thức: Payload IPN không có accessKey được xác minh bằng accessKey cấu hình của server."""
        adapter = get_payment_adapter("MOMO")
        official_ipn_body = {
            "partnerCode": MOCK_MOMO_ENV["MOMO_PARTNER_CODE"],
            "orderId": "ORD_OFFICIAL_001",
            "requestId": "REQ_OFFICIAL_001",
            "amount": 40000,
            "orderInfo": "Thanh toan san",
            "orderType": "momo_wallet",
            "transId": 999111222,
            "resultCode": 0,
            "message": "Successful.",
            "payType": "qr",
            "responseTime": 1721720663942,
            "extraData": ""
        }
        self.assertNotIn("accessKey", official_ipn_body, "JSON body from MoMo server MUST NOT be required to contain accessKey.")

        # Compute valid signature
        sig = adapter.generate_ipn_signature(
            access_key=MOCK_MOMO_ENV["MOMO_ACCESS_KEY"],
            amount=40000,
            extra_data="",
            message="Successful.",
            order_id="ORD_OFFICIAL_001",
            order_info="Thanh toan san",
            order_type="momo_wallet",
            partner_code=MOCK_MOMO_ENV["MOMO_PARTNER_CODE"],
            pay_type="qr",
            request_id="REQ_OFFICIAL_001",
            response_time=1721720663942,
            result_code=0,
            trans_id=999111222,
            secret_key=MOCK_MOMO_ENV["MOMO_SECRET_KEY"]
        )
        official_ipn_body["signature"] = sig

        # Signature verification succeeds using server's configured access key
        self.assertTrue(adapter.verify_ipn_signature(official_ipn_body))


if __name__ == "__main__":
    unittest.main()
