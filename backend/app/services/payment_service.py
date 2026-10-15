"""
BADMINTON.AI - PHASE 7.4A PAYMENT ARCHITECTURE, SANDBOX & RECONCILIATION FOUNDATION
Authoritative, shared payment processing service and sandbox engine.
Features:
1. Distinct lifecycle concepts: Booking created, Payment pending, Confirmed, Failed, Expired, Reconciliation required.
2. Provider-agnostic adapter interface (Sandbox, VNPay, MoMo, ZaloPay ready).
3. Strict environment guard: Sandbox strictly disabled when ENVIRONMENT/NODE_ENV is 'production'.
4. Zero external network calls in Sandbox adapter.
5. Idempotent webhook handling with anti-tampering (amount, currency, booking_id, signature).
6. Out-of-order downgrade protection: never downgrade a SUCCESS/DEPOSITED booking on delayed failed callback.
7. Anti-IDOR protection: users can only access and initiate payments for their own bookings.
8. Zero storage or leakage of sensitive card data or gateway secrets.
"""

import os
import hmac
import hashlib
import json
import uuid
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_

from app.config import settings
from app.models.all_models import Booking, User, Payment, PaymentStatus, TransactionStatus

from decimal import Decimal, InvalidOperation

logger = logging.getLogger("payment_service")

# Internal Sandbox Secret for HMAC test verification (isolated to non-production)
SANDBOX_SECRET = os.getenv("PAYMENT_SANDBOX_SECRET", "sandbox_internal_hmac_secret_phase7_4a")


def normalize_vnd_amount(val: Any) -> Optional[Decimal]:
    """
    Normalizes monetary values to exact integer VND using Decimal.
    - Accepts: int, str, float, Decimal representing positive integer VND amounts.
    - Rejects: None, bool, NaN, Infinity, negative/zero, non-numeric strings,
               and non-zero fractional decimals (e.g. 40000.5 or '40000.5' is rejected without rounding).
    - Returns Decimal integer (e.g. Decimal("40000")) or None if invalid.
    """
    if val is None or isinstance(val, bool):
        return None
    try:
        if isinstance(val, float):
            import math
            if math.isnan(val) or math.isinf(val):
                return None
            val_str = str(val)
        elif isinstance(val, Decimal):
            if val.is_nan() or val.is_infinite():
                return None
            val_str = str(val)
        else:
            val_str = str(val).strip()

        dec = Decimal(val_str)
        if dec.is_nan() or dec.is_infinite():
            return None
        if dec <= 0:
            return None

        # Disallow non-zero fractional amounts (VND is integer-only)
        # Prevents auto-rounding that could disguise invalid amounts
        if dec % 1 != 0:
            return None

        return dec.quantize(Decimal("1"))
    except (InvalidOperation, ValueError, TypeError):
        return None


class BasePaymentAdapter:
    """Base interface for payment gateway adapters."""
    @property
    def provider_name(self) -> str:
        raise NotImplementedError

    def generate_signature(self, payload: Dict[str, Any]) -> str:
        raise NotImplementedError

    def verify_signature(self, payload: Dict[str, Any], signature: str) -> bool:
        raise NotImplementedError


class SandboxPaymentAdapter(BasePaymentAdapter):
    """
    Internal Sandbox Adapter for development and testing.
    Never calls external networks. Strictly disabled in production and staging.
    """
    @property
    def provider_name(self) -> str:
        return "SANDBOX"

    def is_enabled(self) -> bool:
        """
        Fail-closed environment safeguard:
        Sandbox is ONLY allowed when:
        1. PAYMENT_SANDBOX_ENABLED is explicitly True.
        2. AND ENVIRONMENT is strictly in ('development', 'dev', 'test', 'testing').
        3. AND ENVIRONMENT is NOT in ('production', 'prod', 'staging', 'uat').
        4. If ENVIRONMENT is missing or empty, DENY!
        """
        sb_env = os.getenv("PAYMENT_SANDBOX_ENABLED")
        if sb_env is not None:
            sandbox_flag = sb_env.strip().lower() in ("true", "1", "yes")
        else:
            sandbox_flag = getattr(settings, "PAYMENT_SANDBOX_ENABLED", False)

        if not sandbox_flag:
            return False

        raw_env = os.getenv("ENVIRONMENT") or getattr(settings, "ENVIRONMENT", "")
        if not raw_env or not str(raw_env).strip():
            return False

        env_clean = str(raw_env).strip().lower()
        disallowed_envs = {"production", "prod", "staging", "uat"}
        if env_clean in disallowed_envs:
            return False

        allowed_envs = {"development", "dev", "test", "testing"}
        if env_clean not in allowed_envs:
            return False

        raw_node_env = os.getenv("NODE_ENV") or getattr(settings, "NODE_ENV", "")
        if raw_node_env:
            node_clean = str(raw_node_env).strip().lower()
            if node_clean in disallowed_envs:
                return False

        return True

    def generate_signature(self, payload: Dict[str, Any]) -> str:
        """Deterministic HMAC-SHA256 signature for sandbox payload."""
        sorted_keys = sorted(payload.keys())
        sign_str = "&".join(f"{k}={payload[k]}" for k in sorted_keys if payload[k] is not None and k != "signature")
        return hmac.new(SANDBOX_SECRET.encode("utf-8"), sign_str.encode("utf-8"), hashlib.sha256).hexdigest()

    def verify_signature(self, payload: Dict[str, Any], signature: str) -> bool:
        """Verifies signature using constant-time comparison to prevent timing attacks."""
        if not signature or not isinstance(signature, str):
            return False
        expected = self.generate_signature(payload)
        return hmac.compare_digest(expected, signature)


# Registered Adapters
from app.services.payment_adapters.momo_adapter import MoMoPaymentAdapter

_adapters: Dict[str, Any] = {
    "SANDBOX": SandboxPaymentAdapter(),
    "MOMO": MoMoPaymentAdapter()
}


def get_payment_adapter(provider: str = "SANDBOX") -> Optional[Any]:
    return _adapters.get(provider.upper())


def register_payment_adapter(provider: str, adapter: Any) -> None:
    """Dynamically register or override an adapter (e.g. for testing)."""
    _adapters[provider.upper()] = adapter


# ==============================================================================
# CORE PAYMENT SERVICE METHODS
# ==============================================================================

async def create_payment_attempt(
    db: AsyncSession,
    booking_id: int,
    user_id: int,
    provider: str = "SANDBOX",
    payment_type: str = "DEPOSIT",
    idempotency_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates a new payment attempt record linked to an existing booking.
    Enforces user ownership, prevents paying already confirmed bookings,
    and returns idempotent response if idempotency_key was already processed.
    """
    if not user_id:
        return {
            "status": "authentication_required",
            "message": "Yêu cầu đăng nhập để thực hiện thanh toán.",
            "data": None
        }

    provider_clean = provider.upper()
    adapter = get_payment_adapter(provider_clean)
    if not adapter:
        return {
            "status": "unsupported_provider",
            "message": f"Cổng thanh toán '{provider}' không được hỗ trợ trong phiên bản hiện tại.",
            "data": None
        }

    # Environment safeguard for Sandbox
    if provider_clean == "SANDBOX":
        sandbox: SandboxPaymentAdapter = adapter
        if not sandbox.is_enabled():
            return {
                "status": "sandbox_disabled_in_production",
                "message": "Chế độ thanh toán Sandbox bị vô hiệu hóa trong môi trường production.",
                "data": None
            }

    # Environment safeguard for MoMo
    if provider_clean == "MOMO":
        momo_ad: MoMoPaymentAdapter = adapter
        if momo_ad.is_production_blocked():
            return {
                "status": "production_blocked",
                "message": "Cổng MoMo chưa được kích hoạt trên môi trường production trong Phase 7.4B.",
                "data": None
            }
        if not momo_ad.is_configured():
            return {
                "status": "unconfigured_provider",
                "message": "Cổng MoMo chưa được cấu hình đầy đủ credentials hoặc callback URLs.",
                "data": None
            }

    # 1. Fetch Booking and verify ownership (Anti-IDOR)
    stmt = select(Booking).where(Booking.id == booking_id)
    res = await db.execute(stmt)
    booking = res.scalar_one_or_none()
    if not booking:
        return {
            "status": "booking_not_found",
            "message": f"Không tìm thấy đơn đặt sân #{booking_id}.",
            "data": None
        }

    if booking.user_id != user_id:
        logger.warning(f"[create_payment_attempt] Anti-IDOR: user {user_id} tried to pay booking {booking_id} belonging to user {booking.user_id}")
        return {
            "status": "permission_denied",
            "message": "Bạn không có quyền thực hiện thanh toán cho đơn đặt sân của khách hàng khác.",
            "data": None
        }

    # 2. Idempotency Check: if idempotency_key exists, return existing attempt
    if idempotency_key:
        idemp_stmt = select(Payment).where(Payment.idempotency_key == idempotency_key)
        idemp_res = await db.execute(idemp_stmt)
        existing_pm = idemp_res.scalar_one_or_none()
        if existing_pm:
            resp_data = {
                "payment_id": existing_pm.id,
                "booking_id": existing_pm.booking_id,
                "transaction_id": existing_pm.transaction_id,
                "amount": existing_pm.amount,
                "currency": existing_pm.currency,
                "status": existing_pm.status,
                "provider": existing_pm.provider
            }
            if existing_pm.provider == "MOMO" and existing_pm.provider_response:
                try:
                    pr = json.loads(existing_pm.provider_response)
                    if "pay_url" in pr:
                        resp_data["pay_url"] = pr["pay_url"]
                    if "deeplink" in pr:
                        resp_data["deeplink"] = pr.get("deeplink")
                    if "qr_code_url" in pr:
                        resp_data["qr_code_url"] = pr.get("qr_code_url")
                except Exception:
                    pass
            return {
                "status": "payment_attempt_created",
                "is_idempotent": True,
                "message": "Yêu cầu thanh toán đã được khởi tạo trước đó.",
                "data": resp_data
            }

    # 3. Check if booking is already paid
    if booking.payment_status in (PaymentStatus.DEPOSITED.value, PaymentStatus.PAID.value):
        return {
            "status": "already_paid",
            "is_idempotent": True,
            "message": f"Đơn đặt sân này đã được thanh toán (Trạng thái: {booking.payment_status}).",
            "data": {
                "booking_id": booking.id,
                "payment_status": booking.payment_status
            }
        }

    if booking.payment_status == PaymentStatus.CANCELLED.value:
        return {
            "status": "booking_cancelled",
            "message": "Đơn đặt sân này đã bị hủy, không thể tiến hành thanh toán.",
            "data": None
        }

    # 4. Determine and normalize expected amount
    raw_amount = booking.deposit_amount if payment_type.upper() == "DEPOSIT" else booking.total_amount
    norm_amount = normalize_vnd_amount(raw_amount)
    if norm_amount is None:
        return {
            "status": "invalid_amount",
            "message": f"Số tiền đơn đặt sân #{booking_id} không hợp lệ.",
            "data": None
        }

    # Provider-specific amount validation
    if provider_clean == "MOMO":
        momo_ad: MoMoPaymentAdapter = adapter
        if not momo_ad.validate_amount(norm_amount):
            return {
                "status": "invalid_amount",
                "message": f"Số tiền thanh toán MoMo ({norm_amount} VND) không hợp lệ. Cho phép từ 1.000 đến 50.000.000 VND.",
                "data": None
            }

    amount = float(norm_amount)

    # 5. Generate unique transaction ID
    tx_id = f"tx_{provider_clean.lower()}_{uuid.uuid4().hex[:16]}"
    effective_idemp_key = idempotency_key or f"idemp_pay_{uuid.uuid4().hex[:16]}"

    payment = Payment(
        booking_id=booking.id,
        user_id=user_id,
        provider=provider_clean,
        transaction_id=tx_id,
        amount=amount,
        currency="VND",
        payment_type=payment_type.upper(),
        status=TransactionStatus.PENDING.value,
        idempotency_key=effective_idemp_key,
        provider_response=json.dumps({"initiated_at": datetime.utcnow().isoformat()})
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    # 6. Provider-specific gateway integration
    if provider_clean == "MOMO":
        momo_ad: MoMoPaymentAdapter = adapter
        req_id = f"req_momo_{uuid.uuid4().hex[:16]}"
        momo_res = await momo_ad.create_payment_request(
            order_id=tx_id,
            request_id=req_id,
            amount=int(norm_amount),
            order_info=f"Thanh toan dat san #{booking.id}"
        )

        if momo_res.get("status") == "success":
            payment.provider_response = json.dumps(momo_res)
            await db.commit()
            await db.refresh(payment)
            return {
                "status": "payment_attempt_created",
                "is_idempotent": False,
                "message": "Khởi tạo phiên thanh toán MoMo thành công.",
                "data": {
                    "payment_id": payment.id,
                    "booking_id": payment.booking_id,
                    "transaction_id": payment.transaction_id,
                    "amount": payment.amount,
                    "currency": payment.currency,
                    "status": payment.status,
                    "provider": payment.provider,
                    "pay_url": momo_res.get("pay_url"),
                    "deeplink": momo_res.get("deeplink"),
                    "qr_code_url": momo_res.get("qr_code_url")
                }
            }
        elif momo_res.get("status") == "timeout":
            payment.status = TransactionStatus.REQUIRES_RECONCILIATION.value
            payment.provider_response = json.dumps(momo_res)
            await db.commit()
            return {
                "status": "gateway_timeout",
                "message": "Kết nối tới MoMo bị quá hạn (timeout). Giao dịch được lưu để đối soát.",
                "data": {
                    "payment_id": payment.id,
                    "booking_id": payment.booking_id,
                    "transaction_id": payment.transaction_id,
                    "status": payment.status,
                    "provider": payment.provider
                }
            }
        else:
            payment.status = TransactionStatus.FAILED.value
            payment.provider_response = json.dumps(momo_res)
            await db.commit()
            return {
                "status": "provider_error",
                "message": momo_res.get("message", "Lỗi tạo yêu cầu thanh toán từ cổng MoMo."),
                "data": {
                    "payment_id": payment.id,
                    "booking_id": payment.booking_id,
                    "transaction_id": payment.transaction_id,
                    "status": payment.status,
                    "provider": payment.provider
                }
            }

    return {
        "status": "payment_attempt_created",
        "is_idempotent": False,
        "message": "Khởi tạo phiên thanh toán thành công.",
        "data": {
            "payment_id": payment.id,
            "booking_id": payment.booking_id,
            "transaction_id": payment.transaction_id,
            "amount": payment.amount,
            "currency": payment.currency,
            "status": payment.status,
            "provider": payment.provider
        }
    }


async def process_payment_webhook(
    db: AsyncSession,
    provider: str,
    transaction_id: str,
    booking_id: int,
    amount: float,
    currency: str,
    status: str,
    signature: str,
    raw_payload: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Authoritative webhook / callback reconciliation handler.
    Guarantees:
    - Signature cryptographic verification.
    - Anti-tampering verification (booking_id, amount, currency).
    - Idempotency on repeated callbacks.
    - Out-of-order downgrade protection (never changes DEPOSITED/PAID back to FAILED).
    """
    provider_clean = provider.upper()
    adapter = get_payment_adapter(provider_clean)
    if not adapter:
        return {
            "status": "unsupported_provider",
            "message": f"Provider '{provider}' không hợp lệ."
        }

    # 1. Cryptographic Signature Verification
    payload_to_verify = raw_payload or {
        "provider": provider_clean,
        "transaction_id": transaction_id,
        "booking_id": booking_id,
        "amount": amount,
        "currency": currency,
        "status": status
    }

    if not adapter.verify_signature(payload_to_verify, signature):
        logger.warning(f"[process_payment_webhook] Invalid signature from provider {provider_clean} for tx {transaction_id}")
        return {
            "status": "invalid_signature",
            "message": "Chữ ký webhook không hợp lệ. Từ chối cập nhật trạng thái giao dịch."
        }

    # 2. Amount Validity Check
    norm_incoming_amount = normalize_vnd_amount(amount)
    if norm_incoming_amount is None:
        return {
            "status": "invalid_amount",
            "message": f"Số tiền webhook không hợp lệ ({amount}). Yêu cầu số nguyên VND dương."
        }

    # 3. Standardized Lock Acquisition Order: Booking -> Payment -> TimeSlot
    # Consistent with payment_expiry_service to eliminate deadlock risk on PostgreSQL.
    is_postgres = False
    try:
        if db.bind and hasattr(db.bind, "dialect") and db.bind.dialect.name == "postgresql":
            is_postgres = True
    except Exception:
        pass

    # Step 3a: Non-locking lookup to determine target booking_id
    lookup_stmt = select(Payment.booking_id).where(Payment.transaction_id == transaction_id)
    lookup_res = await db.execute(lookup_stmt)
    target_booking_id = lookup_res.scalar_one_or_none() or booking_id

    # Step 3b: Lock Order Position 1 — Row-level lock on Booking FIRST
    bk_query = select(Booking).where(Booking.id == target_booking_id)
    if is_postgres:
        bk_query = bk_query.with_for_update()
    b_res = await db.execute(bk_query)
    booking = b_res.scalar_one_or_none()
    if not booking:
        return {
            "status": "booking_not_found",
            "message": f"Không tìm thấy đơn đặt sân gắn với giao dịch #{target_booking_id}."
        }

    # Step 3c: Lock Order Position 2 — Row-level lock on Payment SECOND
    stmt = select(Payment).where(Payment.transaction_id == transaction_id)
    if is_postgres:
        stmt = stmt.with_for_update()
    res = await db.execute(stmt)
    payment = res.scalar_one_or_none()

    if not payment:
        # Fallback: check if exists by booking_id
        bk_stmt = select(Payment).where(
            and_(
                Payment.booking_id == target_booking_id,
                Payment.provider == provider_clean
            )
        ).order_by(Payment.id.desc())
        if is_postgres:
            bk_stmt = bk_stmt.with_for_update()
        bk_res = await db.execute(bk_stmt)
        payment = bk_res.scalars().first()

    if not payment:
        return {
            "status": "transaction_not_found",
            "message": f"Không tìm thấy bản ghi thanh toán cho mã giao dịch {transaction_id}."
        }

    # 5. Anti-Tampering Reconciliations
    # A. Booking ID Match
    if payment.booking_id != booking_id:
        payment.status = TransactionStatus.REQUIRES_RECONCILIATION.value
        await db.commit()
        return {
            "status": "booking_mismatch",
            "message": f"Mã booking không khớp giữa dữ liệu callback ({booking_id}) và hệ thống ({payment.booking_id})."
        }

    # B. Currency Match
    if not currency or str(currency).strip().upper() != "VND":
        payment.status = TransactionStatus.REQUIRES_RECONCILIATION.value
        await db.commit()
        return {
            "status": "currency_mismatch",
            "message": f"Loại tiền tệ '{currency}' không hợp lệ (yêu cầu VND)."
        }

    # C. Monetary Integrity: Integer VND Amount Match (No Float Drift)
    norm_expected_amount = normalize_vnd_amount(payment.amount)
    if norm_expected_amount is None or norm_incoming_amount != norm_expected_amount:
        payment.status = TransactionStatus.REQUIRES_RECONCILIATION.value
        await db.commit()
        return {
            "status": "amount_mismatch",
            "message": f"Số tiền thanh toán ({norm_incoming_amount} VND) không khớp với số tiền yêu cầu ({norm_expected_amount} VND)."
        }

    # 6. Out-of-order Downgrade Protection & Idempotency
    # If payment is already SUCCESS or booking is already DEPOSITED/PAID:
    is_already_confirmed = (
        payment.status == TransactionStatus.SUCCESS.value or
        booking.payment_status in (PaymentStatus.DEPOSITED.value, PaymentStatus.PAID.value)
    )

    if is_already_confirmed:
        if status.upper() in ("FAILED", "CANCELLED", "TIMEOUT"):
            logger.warning(
                f"[process_payment_webhook] Downgrade attempt blocked: tx {transaction_id} is already confirmed, "
                f"ignoring delayed callback with status {status}"
            )
            return {
                "status": "downgrade_prevented",
                "is_idempotent": True,
                "message": "Giao dịch đã được ghi nhận thành công trước đó. Bỏ qua callback trễ.",
                "data": {
                    "payment_id": payment.id,
                    "booking_id": booking.id,
                    "payment_status": booking.payment_status
                }
            }
        else:
            # Repeated SUCCESS callback -> idempotent return
            return {
                "status": "payment_processed",
                "is_idempotent": True,
                "message": "Giao dịch đã được xử lý thành công trước đó (Idempotent).",
                "data": {
                    "payment_id": payment.id,
                    "booking_id": booking.id,
                    "payment_status": booking.payment_status
                }
            }

    # 7. Process State Transitions wrapped in transactional safety
    clean_status = status.upper()
    try:
        if clean_status == "SUCCESS":
            # Late webhook on CANCELLED/EXPIRED booking safeguard:
            # If booking was already cancelled or expired, DO NOT revive or mark booking as DEPOSITED/PAID!
            # Instead, route transaction to REQUIRES_RECONCILIATION so admin/staff can review/refund manually.
            if booking.payment_status == PaymentStatus.CANCELLED.value:
                logger.warning(
                    f"[process_payment_webhook] Late SUCCESS callback for cancelled booking {booking.id}, tx {transaction_id}. "
                    f"Routing to REQUIRES_RECONCILIATION without altering cancelled booking status."
                )
                payment.status = TransactionStatus.REQUIRES_RECONCILIATION.value
                payment.updated_at = datetime.utcnow()
                payment.provider_response = json.dumps({
                    "status": "SUCCESS_ON_CANCELLED_BOOKING",
                    "reason": "late_callback_after_booking_cancelled_or_expired",
                    "verified_at": datetime.utcnow().isoformat(),
                    "transaction_id": transaction_id
                })
                await db.commit()
                await db.refresh(payment)
                return {
                    "status": "reconciliation_required",
                    "is_idempotent": False,
                    "message": "Đơn đặt sân đã bị hủy hoặc hết hạn trước khi nhận được callback thanh toán thành công. Giao dịch được chuyển sang đối soát (Reconciliation).",
                    "data": {
                        "payment_id": payment.id,
                        "booking_id": booking.id,
                        "payment_status": booking.payment_status,
                        "transaction_status": payment.status,
                        "transaction_id": payment.transaction_id
                    }
                }

            payment.status = TransactionStatus.SUCCESS.value
            # If deposit payment, mark DEPOSITED; if full payment, mark PAID
            if payment.payment_type == "FULL":
                booking.payment_status = PaymentStatus.PAID.value
            else:
                booking.payment_status = PaymentStatus.DEPOSITED.value

            payment.updated_at = datetime.utcnow()
            payment.provider_response = json.dumps({
                "status": "SUCCESS",
                "verified_at": datetime.utcnow().isoformat(),
                "transaction_id": transaction_id
            })
            await db.commit()
            await db.refresh(booking)
            await db.refresh(payment)

            return {
                "status": "payment_processed",
                "is_idempotent": False,
                "message": "Xác nhận thanh toán thành công và đã cập nhật trạng thái đơn đặt sân.",
                "data": {
                    "payment_id": payment.id,
                    "booking_id": booking.id,
                    "payment_status": booking.payment_status,
                    "transaction_id": payment.transaction_id
                }
            }

        elif clean_status == "FAILED":
            payment.status = TransactionStatus.FAILED.value
            payment.updated_at = datetime.utcnow()
            # Booking remains PENDING (unpaid)
            await db.commit()
            return {
                "status": "payment_failed",
                "is_idempotent": False,
                "message": "Giao dịch thanh toán thất bại. Đơn đặt sân vẫn giữ trạng thái chờ thanh toán.",
                "data": {
                    "payment_id": payment.id,
                    "booking_id": booking.id,
                    "payment_status": booking.payment_status
                }
            }

        elif clean_status in ("TIMEOUT", "UNVERIFIED"):
            payment.status = TransactionStatus.REQUIRES_RECONCILIATION.value
            payment.updated_at = datetime.utcnow()
            await db.commit()
            return {
                "status": "reconciliation_required",
                "is_idempotent": False,
                "message": "Giao dịch chưa thể xác minh tự động, đã đưa vào danh sách đối soát.",
                "data": {
                    "payment_id": payment.id,
                    "booking_id": booking.id,
                    "payment_status": booking.payment_status
                }
            }

        else:
            payment.status = clean_status
            await db.commit()
            return {
                "status": f"payment_{clean_status.lower()}",
                "is_idempotent": False,
                "message": f"Trạng thái thanh toán được cập nhật thành {clean_status}.",
                "data": {
                    "payment_id": payment.id,
                    "booking_id": booking.id,
                    "payment_status": booking.payment_status
                }
            }
    except Exception as exc:
        await db.rollback()
        logger.error(f"[process_payment_webhook] DB commit failed: {exc}", exc_info=True)
        return {
            "status": "db_commit_failed",
            "message": "Không thể lưu trạng thái thanh toán do lỗi cơ sở dữ liệu. Đã rollback toàn bộ thay đổi."
        }


async def process_momo_ipn(
    db: AsyncSession,
    ipn_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Authoritative MoMo IPN Callback Processor (payWithMethod flow).
    Guarantees:
    1. Cryptographic HMAC-SHA256 signature verification according to MoMo v3 spec.
    2. Exact integer VND amount validation (1,000 to 50,000,000 VND).
    3. Row-level lock acquisition order: Booking -> Payment -> TimeSlot.
    4. Anti-tampering check: partnerCode, orderId, amount match database record.
    5. Out-of-order downgrade protection: never downgrade confirmed SUCCESS/DEPOSITED.
    6. Late callback protection on CANCELLED bookings: route to REQUIRES_RECONCILIATION without reviving cancelled booking.
    7. Idempotent repeated callbacks.
    8. Transactional atomicity: DB rollback on error.
    """
    adapter = get_payment_adapter("MOMO")
    if not adapter or not isinstance(adapter, MoMoPaymentAdapter):
        return {
            "status": "unsupported_provider",
            "message": "Cổng MoMo chưa được đăng ký hoặc cấu hình."
        }

    # 1. Cryptographic Signature Verification
    if not adapter.verify_ipn_signature(ipn_data):
        logger.warning(f"[process_momo_ipn] Invalid signature for orderId {ipn_data.get('orderId')}")
        return {
            "status": "invalid_signature",
            "message": "Chữ ký MoMo IPN không hợp lệ. Từ chối cập nhật trạng thái."
        }

    # 2. Extract and Validate MoMo Payload
    order_id = str(ipn_data.get("orderId", ""))
    request_id = str(ipn_data.get("requestId", ""))
    partner_code = str(ipn_data.get("partnerCode", ""))
    raw_amount = ipn_data.get("amount")
    result_code = int(ipn_data.get("resultCode", -1))
    trans_id = ipn_data.get("transId")

    norm_incoming_amount = normalize_vnd_amount(raw_amount)
    if norm_incoming_amount is None or not adapter.validate_amount(norm_incoming_amount):
        return {
            "status": "invalid_amount",
            "message": f"Số tiền thanh toán MoMo không hợp lệ ({raw_amount}). Yêu cầu số nguyên từ 1.000 đến 50.000.000 VND."
        }

    # 3. Check configured Partner Code
    configured_partner_code = os.getenv("MOMO_PARTNER_CODE") or getattr(settings, "MOMO_PARTNER_CODE", None)
    if configured_partner_code and partner_code != configured_partner_code:
        logger.warning(f"[process_momo_ipn] Partner code mismatch: incoming {partner_code} vs configured {configured_partner_code}")
        lookup_stmt = select(Payment).where(Payment.transaction_id == order_id)
        pm_res = await db.execute(lookup_stmt)
        pm = pm_res.scalar_one_or_none()
        if pm:
            pm.status = TransactionStatus.REQUIRES_RECONCILIATION.value
            await db.commit()
        return {
            "status": "partner_mismatch",
            "message": f"PartnerCode '{partner_code}' không khớp cấu hình hệ thống."
        }

    # 4. Standardized Row Lock Order: Booking FIRST, Payment SECOND, TimeSlot THIRD
    is_postgres = False
    try:
        if db.bind and hasattr(db.bind, "dialect") and db.bind.dialect.name == "postgresql":
            is_postgres = True
    except Exception:
        pass

    # Step 4a: Non-locking lookup to locate payment and booking
    lookup_stmt = select(Payment.id, Payment.booking_id).where(Payment.transaction_id == order_id)
    lookup_res = await db.execute(lookup_stmt)
    pm_info = lookup_res.first()
    if not pm_info:
        logger.warning(f"[process_momo_ipn] Transaction not found for orderId {order_id}")
        return {
            "status": "transaction_not_found",
            "message": f"Không tìm thấy giao dịch với orderId {order_id}."
        }

    target_payment_id, target_booking_id = pm_info[0], pm_info[1]

    # Step 4b: Lock Order Position 1 — Booking FIRST
    bk_query = select(Booking).where(Booking.id == target_booking_id)
    if is_postgres:
        bk_query = bk_query.with_for_update()
    bk_res = await db.execute(bk_query)
    booking = bk_res.scalar_one_or_none()
    if not booking:
        return {
            "status": "booking_not_found",
            "message": f"Không tìm thấy đơn đặt sân #{target_booking_id}."
        }

    # Step 4c: Lock Order Position 2 — Payment SECOND
    pm_query = select(Payment).where(Payment.id == target_payment_id)
    if is_postgres:
        pm_query = pm_query.with_for_update()
    pm_res = await db.execute(pm_query)
    payment = pm_res.scalar_one_or_none()
    if not payment:
        return {
            "status": "transaction_not_found",
            "message": f"Không tìm thấy bản ghi thanh toán #{target_payment_id}."
        }

    # 5. Anti-Tampering Reconciliations
    norm_expected_amount = normalize_vnd_amount(payment.amount)
    if norm_expected_amount is None or norm_incoming_amount != norm_expected_amount:
        logger.warning(f"[process_momo_ipn] Amount mismatch: incoming {norm_incoming_amount} vs expected {norm_expected_amount}")
        payment.status = TransactionStatus.REQUIRES_RECONCILIATION.value
        await db.commit()
        return {
            "status": "amount_mismatch",
            "message": f"Số tiền callback ({norm_incoming_amount} VND) không khớp với hệ thống ({norm_expected_amount} VND)."
        }

    # 6. Out-of-order Downgrade Protection & Idempotency
    is_already_confirmed = (
        payment.status == TransactionStatus.SUCCESS.value or
        booking.payment_status in (PaymentStatus.DEPOSITED.value, PaymentStatus.PAID.value)
    )

    if is_already_confirmed:
        if result_code != 0:
            logger.warning(f"[process_momo_ipn] Downgrade prevented: tx {order_id} is already confirmed, ignoring failure callback (resultCode={result_code}).")
            return {
                "status": "downgrade_prevented",
                "is_idempotent": True,
                "message": "Giao dịch đã được ghi nhận thành công trước đó. Bỏ qua callback thất bại trễ.",
                "data": {
                    "payment_id": payment.id,
                    "booking_id": booking.id,
                    "payment_status": booking.payment_status
                }
            }
        else:
            return {
                "status": "payment_processed",
                "is_idempotent": True,
                "message": "Giao dịch đã được xử lý thành công trước đó (Idempotent).",
                "data": {
                    "payment_id": payment.id,
                    "booking_id": booking.id,
                    "payment_status": booking.payment_status
                }
            }

    # 7. Late callback on CANCELLED/EXPIRED booking safeguard
    if booking.payment_status == PaymentStatus.CANCELLED.value:
        logger.warning(f"[process_momo_ipn] Late callback for CANCELLED booking {booking.id}, orderId {order_id}. Routing to REQUIRES_RECONCILIATION.")
        payment.status = TransactionStatus.REQUIRES_RECONCILIATION.value
        payment.updated_at = datetime.utcnow()
        payment.provider_response = json.dumps({
            "status": "SUCCESS_ON_CANCELLED_BOOKING" if result_code == 0 else "FAILED_ON_CANCELLED_BOOKING",
            "reason": "late_callback_after_booking_cancelled",
            "resultCode": result_code,
            "transId": trans_id,
            "verified_at": datetime.utcnow().isoformat()
        })
        await db.commit()
        return {
            "status": "reconciliation_required",
            "is_idempotent": False,
            "message": "Đơn đặt sân đã bị hủy trước khi nhận được callback thanh toán. Giao dịch được chuyển sang đối soát.",
            "data": {
                "payment_id": payment.id,
                "booking_id": booking.id,
                "payment_status": booking.payment_status,
                "transaction_status": payment.status
            }
        }

    # 8. State Transitions
    try:
        if result_code == 0:
            payment.status = TransactionStatus.SUCCESS.value
            if payment.payment_type == "FULL":
                booking.payment_status = PaymentStatus.PAID.value
            else:
                booking.payment_status = PaymentStatus.DEPOSITED.value

            payment.updated_at = datetime.utcnow()
            payment.provider_response = json.dumps({
                "status": "SUCCESS",
                "resultCode": result_code,
                "transId": trans_id,
                "verified_at": datetime.utcnow().isoformat()
            })
            await db.commit()
            await db.refresh(booking)
            await db.refresh(payment)
            return {
                "status": "payment_processed",
                "is_idempotent": False,
                "message": "Xác nhận thanh toán MoMo thành công và đã cập nhật đơn đặt sân.",
                "data": {
                    "payment_id": payment.id,
                    "booking_id": booking.id,
                    "payment_status": booking.payment_status,
                    "transaction_id": payment.transaction_id
                }
            }
        else:
            payment.status = TransactionStatus.FAILED.value
            payment.updated_at = datetime.utcnow()
            payment.provider_response = json.dumps({
                "status": "FAILED",
                "resultCode": result_code,
                "transId": trans_id,
                "message": ipn_data.get("message", "Thanh toán thất bại")
            })
            await db.commit()
            return {
                "status": "payment_failed",
                "is_idempotent": False,
                "message": "Giao dịch thanh toán MoMo thất bại.",
                "data": {
                    "payment_id": payment.id,
                    "booking_id": booking.id,
                    "payment_status": booking.payment_status
                }
            }
    except Exception as exc:
        await db.rollback()
        logger.error(f"[process_momo_ipn] DB error during IPN processing: {exc}")
        return {
            "status": "db_commit_failed",
            "message": "Lỗi lưu dữ liệu giao dịch. Đã rollback."
        }


async def simulate_sandbox_payment(
    db: AsyncSession,
    booking_id: int,
    user_id: int,
    outcome: str = "SUCCESS",
    custom_amount: Optional[float] = None,
    custom_currency: Optional[str] = None,
    idempotency_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    High-level Sandbox payment flow simulation for testing and development.
    Guarantees:
    - User authentication and ownership check.
    - Production environment lockout.
    - No external network access.
    - Simulates success, failure, timeout, and duplicate callback idempotency.
    """
    adapter = get_payment_adapter("SANDBOX")
    if not adapter or not adapter.is_enabled():
        return {
            "status": "sandbox_disabled_in_production",
            "message": "Chế độ thanh toán Sandbox bị vô hiệu hóa trong môi trường production.",
            "data": None
        }

    # 1. Create or retrieve payment attempt
    attempt_res = await create_payment_attempt(
        db=db,
        booking_id=booking_id,
        user_id=user_id,
        provider="SANDBOX",
        idempotency_key=idempotency_key
    )
    if attempt_res["status"] not in ("payment_attempt_created", "already_paid"):
        return attempt_res

    if attempt_res["status"] == "already_paid":
        return attempt_res

    payment_data = attempt_res["data"]
    tx_id = payment_data["transaction_id"]
    pay_amount = payment_data["amount"]
    pay_currency = payment_data["currency"]

    clean_outcome = outcome.upper()
    sim_status = "SUCCESS" if clean_outcome == "SUCCESS" else clean_outcome

    # Handle outcome shorthands
    if clean_outcome == "MISMATCH_AMOUNT_1VND":
        pay_amount = payment_data["amount"] + 1
        sim_status = "SUCCESS"
    elif clean_outcome == "NEGATIVE_AMOUNT":
        pay_amount = -50000.0
        sim_status = "SUCCESS"
    elif clean_outcome == "INVALID_CURRENCY":
        pay_currency = "USD"
        sim_status = "SUCCESS"

    if custom_amount is not None:
        pay_amount = custom_amount
    if custom_currency is not None:
        pay_currency = custom_currency

    # 2. Build Webhook Payload
    webhook_payload = {
        "provider": "SANDBOX",
        "transaction_id": tx_id,
        "booking_id": booking_id,
        "amount": pay_amount,
        "currency": pay_currency,
        "status": sim_status
    }

    # 3. Sign Payload
    if clean_outcome == "INVALID_SIGNATURE":
        signature = "tampered_invalid_signature_hex_0000"
    else:
        signature = adapter.generate_signature(webhook_payload)

    # 4. Process Webhook
    return await process_payment_webhook(
        db=db,
        provider="SANDBOX",
        transaction_id=tx_id,
        booking_id=booking_id,
        amount=pay_amount,
        currency=pay_currency,
        status=sim_status,
        signature=signature,
        raw_payload=webhook_payload
    )


async def get_booking_payments(
    db: AsyncSession,
    booking_id: int,
    user_id: int
) -> Dict[str, Any]:
    """
    Retrieves all payment attempts for a given booking.
    Strictly verifies user ownership (Anti-IDOR).
    """
    if not user_id:
        return {
            "status": "authentication_required",
            "message": "Yêu cầu đăng nhập để tra cứu lịch sử thanh toán.",
            "data": []
        }

    bk_stmt = select(Booking).where(Booking.id == booking_id)
    bk_res = await db.execute(bk_stmt)
    booking = bk_res.scalar_one_or_none()
    if not booking:
        return {
            "status": "booking_not_found",
            "message": f"Không tìm thấy đơn đặt sân #{booking_id}.",
            "data": []
        }

    if booking.user_id != user_id:
        logger.warning(f"[get_booking_payments] Anti-IDOR: user {user_id} tried to query payments of booking {booking_id}")
        return {
            "status": "permission_denied",
            "message": "Bạn không có quyền xem thông tin thanh toán của đơn đặt sân này.",
            "data": []
        }

    stmt = select(Payment).where(Payment.booking_id == booking_id).order_by(Payment.id.desc())
    res = await db.execute(stmt)
    payments = res.scalars().all()

    return {
        "status": "success",
        "message": f"Tìm thấy {len(payments)} lượt giao dịch thanh toán.",
        "data": [
            {
                "id": p.id,
                "booking_id": p.booking_id,
                "user_id": p.user_id,
                "provider": p.provider,
                "transaction_id": p.transaction_id,
                "amount": p.amount,
                "currency": p.currency,
                "payment_type": p.payment_type,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in payments
        ]
    }


# Re-export Payment Pending Expiry Service (Phase 7.4A.2)
from app.services.payment_expiry_service import expire_pending_bookings
