from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from app.core.database import get_db
from app.core.redis import acquire_slot_lock, release_slot_lock, get_slot_lock_holder
from app.models.all_models import TimeSlot, SlotPricing, Court, User
from app.schemas.all_schemas import TimeSlotResponse, SlotHoldRequest
from app.api.v1.auth import get_current_user
from app.ai.dynamic_pricing import calculate_dynamic_price

router = APIRouter(prefix="/slots", tags=["Time Slots & AI Pricing"])

@router.get("", response_model=List[TimeSlotResponse])
async def get_slots_by_court_and_date(
    court_id: int = Query(..., description="ID của sân con"),
    date: str = Query(..., description="Ngày chơi YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(TimeSlot)
        .where(TimeSlot.court_id == court_id, TimeSlot.date == date)
        .order_by(TimeSlot.start_time)
    )
    res = await db.execute(stmt)
    slots = res.scalars().all()

    response_list = []
    for s in slots:
        # Load pricing
        price_stmt = select(SlotPricing).where(SlotPricing.slot_id == s.id)
        p_res = await db.execute(price_stmt)
        pricing = p_res.scalar_one_or_none()

        base_p = pricing.base_price if pricing else 80000.0
        dyn_p = pricing.dynamic_price if pricing else base_p
        adj_reason = pricing.adjustment_reason if pricing else "Tiêu chuẩn"

        # Check Redis atomic lock status
        holder = await get_slot_lock_holder(s.id)
        effective_status = s.status
        if holder and s.status == "AVAILABLE":
            effective_status = "HELD"

        response_list.append(
            TimeSlotResponse(
                id=s.id,
                court_id=s.court_id,
                date=s.date,
                start_time=s.start_time,
                end_time=s.end_time,
                status=effective_status,
                base_price=base_p,
                dynamic_price=dyn_p,
                adjustment_reason=adj_reason,
                held_by_me=False
            )
        )

    return response_list

@router.post("/hold")
async def hold_slot(
    req: SlotHoldRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Atomic 10-minute hold for a slot (Redis key lock: slot_lock:{id}).
    Prevents race-condition when 2 users book the same court at the same time.
    """
    # Check if slot exists
    stmt = select(TimeSlot).where(TimeSlot.id == req.slot_id)
    res = await db.execute(stmt)
    slot = res.scalar_one_or_none()

    if not slot:
        raise HTTPException(status_code=404, detail="Khung giờ không tồn tại!")
    if slot.status == "BOOKED":
        raise HTTPException(status_code=400, detail="Khung giờ này đã được người khác đặt trước!")

    # Attempt atomic Redis hold for 10 minutes (600s)
    success = await acquire_slot_lock(slot.id, current_user.id, timeout_sec=600)
    if not success:
        raise HTTPException(
            status_code=409, 
            detail="Khung giờ này đang có khách hàng khác giữ chỗ thanh toán. Vui lòng thử lại sau 10 phút!"
        )

    return {
        "status": "success",
        "message": "Giữ chỗ thành công trong 10 phút. Vui lòng hoàn tất đặt cọc!",
        "slot_id": slot.id,
        "held_for_seconds": 600
    }

@router.post("/release")
async def release_slot(
    req: SlotHoldRequest,
    current_user: User = Depends(get_current_user)
):
    """Releases the held slot immediately if user cancels"""
    released = await release_slot_lock(req.slot_id, current_user.id)
    return {"status": "released" if released else "not_found"}
