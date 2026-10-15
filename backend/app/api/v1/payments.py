"""
BADMINTON.AI - PHASE 7.4A PAYMENT API ROUTER
Endpoints for initiating payment attempts, internal sandbox simulation,
webhook reconciliation, and payment history lookup.
Strictly enforces authentication, anti-IDOR, and production lockout for sandbox.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Header, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, List

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.all_models import User
from app.schemas.all_schemas import (
    PaymentInitiateRequest,
    PaymentResponse,
    PaymentSandboxSimulateRequest,
    PaymentSandboxSimulateResponse,
    PaymentWebhookPayload,
    MoMoIPNPayload
)
from app.services.payment_service import (
    create_payment_attempt,
    process_payment_webhook,
    process_momo_ipn,
    simulate_sandbox_payment,
    get_booking_payments
)

router = APIRouter(prefix="/payments", tags=["Payments & Reconciliation"])


@router.post("/initiate")
async def initiate_payment_endpoint(
    req: PaymentInitiateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Khởi tạo một lượt thanh toán mới (Payment Attempt) gắn với booking_id.
    Yêu cầu đăng nhập và kiểm tra quyền sở hữu đơn đặt sân (Anti-IDOR).
    Hỗ trợ cả SANDBOX và MOMO (payWithMethod trả về pay_url).
    """
    res = await create_payment_attempt(
        db=db,
        booking_id=req.booking_id,
        user_id=current_user.id,
        provider=req.provider or "SANDBOX",
        payment_type=req.payment_type or "DEPOSIT",
        idempotency_key=req.idempotency_key
    )
    if res["status"] in ("payment_attempt_created", "already_paid"):
        return res
    elif res["status"] == "booking_not_found":
        raise HTTPException(status_code=404, detail=res["message"])
    elif res["status"] == "permission_denied":
        raise HTTPException(status_code=403, detail=res["message"])
    elif res["status"] in ("sandbox_disabled_in_production", "production_blocked"):
        raise HTTPException(status_code=403, detail=res["message"])
    elif res["status"] in ("unconfigured_provider", "invalid_amount"):
        raise HTTPException(status_code=400, detail=res["message"])
    elif res["status"] in ("gateway_timeout", "provider_error"):
        raise HTTPException(status_code=502, detail=res["message"])
    else:
        raise HTTPException(status_code=400, detail=res["message"])


@router.post("/sandbox/simulate", response_model=PaymentSandboxSimulateResponse)
async def sandbox_simulate_endpoint(
    req: PaymentSandboxSimulateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mô phỏng kết quả thanh toán Sandbox (SUCCESS, FAILED, TIMEOUT, MISMATCH_AMOUNT).
    Chỉ khả dụng trong môi trường DEV / TEST, bị khóa hoàn toàn trên PRODUCTION.
    Yêu cầu đăng nhập và kiểm tra quyền sở hữu đơn đặt sân.
    """
    res = await simulate_sandbox_payment(
        db=db,
        booking_id=req.booking_id,
        user_id=current_user.id,
        outcome=req.outcome,
        custom_amount=req.custom_amount,
        custom_currency=req.custom_currency,
        idempotency_key=req.idempotency_key
    )
    if res["status"] in ("payment_processed", "payment_failed", "reconciliation_required", "already_paid", "downgrade_prevented"):
        return PaymentSandboxSimulateResponse(
            status=res["status"],
            is_idempotent=res.get("is_idempotent", False),
            message=res["message"],
            data=res.get("data")
        )
    elif res["status"] == "permission_denied":
        raise HTTPException(status_code=403, detail=res["message"])
    elif res["status"] == "sandbox_disabled_in_production":
        raise HTTPException(status_code=403, detail=res["message"])
    elif res["status"] == "booking_not_found":
        raise HTTPException(status_code=404, detail=res["message"])
    elif res["status"] in ("amount_mismatch", "currency_mismatch", "booking_mismatch", "invalid_signature", "invalid_amount"):
        raise HTTPException(status_code=400, detail=res["message"])
    else:
        raise HTTPException(status_code=400, detail=res["message"])


@router.post("/webhook")
async def payment_webhook_endpoint(
    payload: PaymentWebhookPayload,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint tiếp nhận webhook từ cổng thanh toán.
    Yêu cầu chữ ký số HMAC hợp lệ. Đối soát số tiền, loại tiền tệ và booking ID.
    Hoàn toàn idempotent với các callback lặp.
    """
    res = await process_payment_webhook(
        db=db,
        provider=payload.provider,
        transaction_id=payload.transaction_id,
        booking_id=payload.booking_id,
        amount=payload.amount,
        currency=payload.currency,
        status=payload.status,
        signature=payload.signature
    )
    if res["status"] in ("payment_processed", "payment_failed", "reconciliation_required", "downgrade_prevented"):
        return res
    elif res["status"] == "invalid_signature":
        raise HTTPException(status_code=401, detail=res["message"])
    elif res["status"] in ("amount_mismatch", "currency_mismatch", "booking_mismatch", "invalid_amount"):
        raise HTTPException(status_code=400, detail=res["message"])
    elif res["status"] == "transaction_not_found":
        raise HTTPException(status_code=404, detail=res["message"])
    else:
        raise HTTPException(status_code=400, detail=res["message"])


@router.post("/momo/ipn", status_code=204)
async def momo_ipn_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Official MoMo Instant Payment Notification (IPN) server-to-server callback.
    - Validates HMAC-SHA256 signature using official payWithMethod canonicalization.
    - Reconciles partnerCode, orderId, amount with database records.
    - Locks Booking -> Payment -> TimeSlot.
    - Returns HTTP 204 No Content within 15s time limit as required by MoMo contract.
    """
    try:
        raw_body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload in MoMo IPN.")

    if not raw_body or not isinstance(raw_body, dict):
        raise HTTPException(status_code=400, detail="Thiếu dữ liệu MoMo IPN callback.")

    res = await process_momo_ipn(db=db, ipn_data=raw_body)

    if res["status"] in ("payment_processed", "payment_failed", "reconciliation_required", "downgrade_prevented"):
        # MoMo specification strictly mandates HTTP 204 No Content for acknowledged IPN
        return Response(status_code=204)
    elif res["status"] == "invalid_signature":
        raise HTTPException(status_code=400, detail=res["message"])
    elif res["status"] in ("invalid_amount", "amount_mismatch", "partner_mismatch"):
        raise HTTPException(status_code=400, detail=res["message"])
    elif res["status"] == "transaction_not_found":
        raise HTTPException(status_code=404, detail=res["message"])
    else:
        raise HTTPException(status_code=400, detail=res["message"])


@router.get("/booking/{booking_id}")
async def get_booking_payments_endpoint(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Tra cứu lịch sử các lần thử thanh toán cho một đơn đặt sân.
    Bảo vệ Anti-IDOR: chỉ chủ sở hữu đơn mới có quyền truy cập.
    """
    res = await get_booking_payments(db=db, booking_id=booking_id, user_id=current_user.id)
    if res["status"] == "success":
        return res
    elif res["status"] == "booking_not_found":
        raise HTTPException(status_code=404, detail=res["message"])
    elif res["status"] == "permission_denied":
        raise HTTPException(status_code=403, detail=res["message"])
    else:
        raise HTTPException(status_code=400, detail=res["message"])


@router.post("/expiry/scan")
async def trigger_expiry_scan_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_scheduler_token: Optional[str] = Header(None, alias="X-Scheduler-Token"),
    batch_limit: Optional[int] = None
):
    """
    Endpoint kích hoạt quét và hủy các đơn đặt sân quá hạn thanh toán.
    
    Security & Authentication:
    1. Service-to-Service: Scheduler xác thực qua header 'X-Scheduler-Token',
       so khớp an toàn (hmac.compare_digest) với settings.SCHEDULER_API_SECRET.
    2. Administrative Users: Xác thực qua JWT Bearer token:
       - ADMIN: Quét toàn hệ thống (unrestricted scope).
       - OWNER: Giới hạn trong các cơ sở thuộc quyền sở hữu (facility-scoped).
       - STAFF: Giới hạn trong các cơ sở được phân công (facility-scoped).
       - CUSTOMER / Unauthenticated: Từ chối (401 / 403).
    3. Fail-Closed: Không bao giờ tự bật expiry policy từ request endpoint.
    4. Batch limit: Khống chế tối đa bookings xử lý trong 1 lượt quét (1..200).
    5. Không ghi secret ra log hay URL/query string.
    """
    import hmac
    from app.config import settings
    from app.core.security import oauth2_scheme, decode_token
    from app.models.all_models import Facility, User
    from app.services.payment_expiry_service import expire_pending_bookings
    from sqlalchemy.future import select as sa_select

    caller_type: str = "UNKNOWN"
    facility_ids: Optional[List[int]] = None

    # 1. Check Service-to-Service Scheduler Authentication
    if x_scheduler_token:
        configured_secret = getattr(settings, "SCHEDULER_API_SECRET", None)
        if not configured_secret or not str(configured_secret).strip():
            raise HTTPException(
                status_code=401,
                detail="Scheduler API secret chưa được cấu hình trên hệ thống."
            )
        token_valid = hmac.compare_digest(
            str(x_scheduler_token).strip().encode("utf-8"),
            str(configured_secret).strip().encode("utf-8")
        )
        if not token_valid:
            raise HTTPException(
                status_code=401,
                detail="Mã định danh Scheduler (X-Scheduler-Token) không hợp lệ."
            )
        caller_type = "SCHEDULER"
        facility_ids = None

    else:
        # 2. Check Administrative User Authentication via JWT
        auth_header = request.headers.get("Authorization", "")
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

        if not token:
            raise HTTPException(
                status_code=401,
                detail="Yêu cầu xác thực (JWT Token hoặc X-Scheduler-Token) để kích hoạt quét hết hạn."
            )

        payload = decode_token(token)
        if not payload:
            raise HTTPException(
                status_code=401,
                detail="Token xác thực không hợp lệ hoặc đã hết hạn."
            )

        user_id = int(payload.get("sub"))
        user_res = await db.execute(sa_select(User).where(User.id == user_id))
        user = user_res.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="Người dùng không tồn tại.")

        if user.role not in ("ADMIN", "OWNER", "STAFF"):
            raise HTTPException(
                status_code=403,
                detail="Chỉ quản trị viên (ADMIN, OWNER, STAFF) mới có quyền kích hoạt quét hết hạn."
            )

        caller_type = user.role

        # Enforce facility scoping for OWNER / STAFF
        if user.role in ("OWNER", "STAFF"):
            fac_stmt = sa_select(Facility.id).where(Facility.owner_id == user.id)
            fac_res = await db.execute(fac_stmt)
            facility_ids = fac_res.scalars().all()
            if not facility_ids:
                return {
                    "status": "no_facilities",
                    "caller_type": caller_type,
                    "message": "Bạn chưa quản lý cơ sở nào. Không có đơn đặt sân nào trong phạm vi quản lý.",
                    "expired_count": 0,
                    "processed_booking_ids": [],
                    "skipped_booking_ids": []
                }
        else:
            facility_ids = None

    # 3. Execute Scoped Expiry Scan (Fail-closed: respects server-side config only)
    res = await expire_pending_bookings(
        db=db,
        batch_limit=batch_limit,
        facility_ids=facility_ids,
        force_enabled=False,
        _internal_force_enabled=False
    )
    res["caller_type"] = caller_type
    return res
