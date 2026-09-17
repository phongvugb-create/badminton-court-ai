from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uuid
from typing import List
from app.core.database import get_db
from app.core.redis import release_slot_lock, get_slot_lock_holder
from app.models.all_models import Booking, TimeSlot, SlotPricing, Equipment, RentalItem, User
from app.schemas.all_schemas import BookingCreate, BookingResponse
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/bookings", tags=["Bookings & Payments"])

@router.post("", response_model=BookingResponse)
async def create_booking(
    req: BookingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify slot
    stmt = select(TimeSlot).where(TimeSlot.id == req.slot_id)
    res = await db.execute(stmt)
    slot = res.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="Khung giờ không tồn tại!")
    if slot.status == "BOOKED":
        raise HTTPException(status_code=400, detail="Khung giờ này đã được đặt rồi!")

    # Check lock: must either be free or locked by this user
    holder = await get_slot_lock_holder(slot.id)
    if holder and holder != str(current_user.id):
        raise HTTPException(status_code=409, detail="Khung giờ đang bị giữ bởi khách hàng khác!")

    # Calculate court price
    price_stmt = select(SlotPricing).where(SlotPricing.slot_id == slot.id)
    p_res = await db.execute(price_stmt)
    pricing = p_res.scalar_one_or_none()
    court_price = pricing.dynamic_price if pricing else 80000.0

    # Calculate equipment rentals
    equip_total = 0.0
    rental_records = []
    if req.equipment_ids:
        for eq_id in req.equipment_ids:
            eq_stmt = select(Equipment).where(Equipment.id == eq_id)
            eq_res = await db.execute(eq_stmt)
            eq = eq_res.scalar_one_or_none()
            if eq and eq.available_qty > 0:
                equip_total += eq.rental_price
                eq.available_qty -= 1
                rental_records.append((eq.id, 1, eq.rental_price))

    total_amount = court_price + equip_total
    deposit_amount = round(total_amount * 0.5, -3) # 50% deposit

    # Generate Check-in QR code token
    qr_code = f"QR-ALB-{uuid.uuid4().hex[:10].upper()}"

    booking = Booking(
        user_id=current_user.id,
        slot_id=slot.id,
        total_amount=total_amount,
        deposit_amount=deposit_amount,
        payment_status="DEPOSITED",
        qr_checkin_code=qr_code
    )
    db.add(booking)
    await db.flush()

    # Create rental items
    for eq_id, qty, price in rental_records:
        r_item = RentalItem(
            booking_id=booking.id,
            equipment_id=eq_id,
            quantity=qty,
            price=price
        )
        db.add(r_item)

    # Mark slot as booked
    slot.status = "BOOKED"

    # Release Redis atomic lock
    await release_slot_lock(slot.id, current_user.id)

    await db.commit()
    await db.refresh(booking)

    return booking

@router.get("/my", response_model=List[BookingResponse])
async def get_my_bookings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Booking)
        .where(Booking.user_id == current_user.id)
        .order_by(Booking.id.desc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()
