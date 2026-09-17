from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.core.database import get_db
from app.models.all_models import MatchmakingRoom, Facility, User
from app.schemas.all_schemas import MatchmakingRoomCreate, MatchmakingRoomResponse
from app.api.v1.auth import get_current_user
from app.ai.elo_engine import is_matchmaking_suitable

router = APIRouter(prefix="/matchmaking", tags=["AI Matchmaking & Rooms"])

@router.get("", response_model=List[MatchmakingRoomResponse])
async def list_rooms(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(MatchmakingRoom, Facility.name.label("facility_name"))
        .join(Facility, MatchmakingRoom.facility_id == Facility.id)
        .where(MatchmakingRoom.status == "OPEN")
        .order_by(MatchmakingRoom.id.desc())
    )
    res = await db.execute(stmt)
    results = []
    for room, fac_name in res.all():
        data = MatchmakingRoomResponse.from_orm(room)
        data.facility_name = fac_name
        results.append(data)
    return results

@router.post("", response_model=MatchmakingRoomResponse)
async def create_room(
    req: MatchmakingRoomCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    room = MatchmakingRoom(
        host_user_id=current_user.id,
        facility_id=req.facility_id,
        title=req.title,
        target_elo=req.target_elo or current_user.elo_rating,
        current_players=1,
        max_players=req.max_players,
        play_date=req.play_date,
        play_time=req.play_time,
        status="OPEN"
    )
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return room

@router.post("/{room_id}/join")
async def join_room(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(MatchmakingRoom).where(MatchmakingRoom.id == room_id)
    res = await db.execute(stmt)
    room = res.scalar_one_or_none()

    if not room:
        raise HTTPException(status_code=404, detail="Phòng ghép kèo không tồn tại!")
    if room.status != "OPEN" or room.current_players >= room.max_players:
        raise HTTPException(status_code=400, detail="Phòng đã đủ người tham gia!")

    # Check ELO similarity
    suitable = is_matchmaking_suitable(current_user.elo_rating, room.target_elo, max_diff=250)
    
    room.current_players += 1
    if room.current_players >= room.max_players:
        room.status = "FULL"

    await db.commit()
    return {
        "status": "joined",
        "message": f"Bạn đã tham gia phòng thành công! (Điểm ELO của bạn: {current_user.elo_rating}, mục tiêu: {room.target_elo})",
        "is_elo_matched": suitable
    }
