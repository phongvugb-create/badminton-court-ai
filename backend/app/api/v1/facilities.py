from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from app.core.database import get_db
from app.models.all_models import Facility, Court, Equipment
from app.schemas.all_schemas import FacilityResponse, FacilityCreate
from app.ai.haversine import haversine_distance
from app.api.v1.auth import get_current_user
from app.models.all_models import User

router = APIRouter(prefix="/facilities", tags=["Facilities"])

@router.get("", response_model=List[FacilityResponse])
async def get_facilities(
    user_lat: Optional[float] = Query(None, description="Vĩ độ hiện tại của khách hàng"),
    user_lon: Optional[float] = Query(None, description="Kinh độ hiện tại của khách hàng"),
    search: Optional[str] = Query(None, description="Từ khóa tìm kiếm tên hoặc địa chỉ"),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Facility).where(Facility.is_approved == True)
    res = await db.execute(stmt)
    facilities = res.scalars().all()

    result = []
    for f in facilities:
        if search and (search.lower() not in f.name.lower() and search.lower() not in f.address.lower()):
            continue

        item = FacilityResponse.from_orm(f)
        if user_lat is not None and user_lon is not None:
            dist = haversine_distance(user_lat, user_lon, f.latitude, f.longitude)
            item.distance_km = dist
        result.append(item)

    # Sort by distance if GPS coordinates provided
    if user_lat is not None and user_lon is not None:
        result.sort(key=lambda x: x.distance_km if x.distance_km is not None else 9999)

    return result

@router.get("/{facility_id}", response_model=FacilityResponse)
async def get_facility_detail(facility_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Facility).where(Facility.id == facility_id)
    res = await db.execute(stmt)
    f = res.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="Không tìm thấy cơ sở sân này")
    return f

@router.get("/{facility_id}/courts")
async def get_facility_courts(facility_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Court).where(Court.facility_id == facility_id, Court.is_active == True)
    res = await db.execute(stmt)
    courts = res.scalars().all()
    return [{"id": c.id, "court_number": c.court_number, "surface_type": c.surface_type} for c in courts]

@router.get("/{facility_id}/equipment")
async def get_facility_equipment(facility_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Equipment).where(Equipment.facility_id == facility_id)
    res = await db.execute(stmt)
    items = res.scalars().all()
    return [
        {
            "id": e.id,
            "name": e.name,
            "type": e.type,
            "available_qty": e.available_qty,
            "rental_price": e.rental_price
        } for e in items
    ]
