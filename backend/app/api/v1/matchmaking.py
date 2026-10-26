from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.all_models import (
    MatchmakingRoom, Facility, User, PlayerProfile, Match, 
    MatchPlayer, ELOHistory, MatchRequest
)
from app.schemas.all_schemas import (
    MatchmakingRoomCreate, MatchmakingRoomResponse,
    PlayerProfileCreateOrUpdate, PlayerProfileResponse,
    MatchFindRequest, MatchFindResponse, MatchCandidate,
    MatchResultSubmitRequest, MatchResultConfirmRequest,
    ELOHistoryItem
)
from app.api.v1.auth import get_current_user
from app.ai.elo_engine import (
    DEFAULT_ELO_TIERS, get_tier_for_elo, get_tier_by_name, calculate_expected_score,
    update_elo, calculate_team_elo, update_doubles_elo,
    calculate_match_score,
    detect_match_anomalies, calculate_rating_confidence,
    get_dynamic_k_factor
)

router = APIRouter(prefix="/matchmaking", tags=["AI Matchmaking & ELO Engine"])

# =============================================================================
# 1. ELO TIERS & CONFIGURATION
# =============================================================================
@router.get("/tiers")
async def get_elo_tiers():
    """Returns the 6 ELO tiers with names, thresholds, and descriptions."""
    return {"tiers": DEFAULT_ELO_TIERS}


# =============================================================================
# 2. PLAYER PROFILE & RATING CONFIDENCE
# =============================================================================
@router.get("/profile/{user_id}", response_model=PlayerProfileResponse)
async def get_player_profile(user_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Retrieves or auto-initializes the player profile for a given user."""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Bạn chỉ có thể xem hồ sơ thi đấu của mình.")
    stmt = select(PlayerProfile).where(PlayerProfile.user_id == user_id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()

    user_stmt = select(User).where(User.id == user_id)
    user_res = await db.execute(user_stmt)
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Người dùng không tồn tại!")

    if not profile:
        profile = PlayerProfile(
            user_id=user.id,
            gender="Khác",
            preferred_area="Cầu Giấy, Hà Nội",
            skill_level="CHƯA CHỌN",
            current_elo=user.elo_rating or 1200,
            games_played=0,
            wins=0,
            losses=0,
            rating_confidence=calculate_rating_confidence(0),
            is_searching=False,
            available_time="18:00 - 21:00",
            play_style="Công thủ toàn diện",
            streak="0"
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    tier = get_tier_by_name(profile.skill_level) if profile.skill_level != "CHƯA CHỌN" else None
    win_rate = round((profile.wins / max(1, profile.games_played)) * 100, 1)

    conf_text = "Tân thủ (Thử việc)"
    if profile.rating_confidence >= 0.85:
        conf_text = "Độ tin cậy Cao (Xác thực)"
    elif profile.rating_confidence >= 0.50:
        conf_text = "Đang hiệu chỉnh"

    return PlayerProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        full_name=user.full_name,
        gender=profile.gender,
        birth_year=profile.birth_year,
        preferred_area=profile.preferred_area,
        skill_level=profile.skill_level,
        tier_display=tier["display"] if tier else None,
        current_elo=profile.current_elo,
        games_played=profile.games_played,
        wins=profile.wins,
        losses=profile.losses,
        win_rate_percent=win_rate,
        rating_confidence=profile.rating_confidence,
        confidence_level=conf_text,
        is_searching=profile.is_searching,
        available_time=profile.available_time,
        preferred_court=profile.preferred_court,
        play_style=profile.play_style,
        streak=profile.streak
    )

@router.post("/profile", response_model=PlayerProfileResponse)
async def update_my_profile(
    req: PlayerProfileCreateOrUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Updates current user's player profile & preferred play settings."""
    stmt = select(PlayerProfile).where(PlayerProfile.user_id == current_user.id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()

    if not profile:
        profile = PlayerProfile(user_id=current_user.id)
        db.add(profile)

    if req.gender: profile.gender = req.gender
    if req.birth_year: profile.birth_year = req.birth_year
    if req.preferred_area: profile.preferred_area = req.preferred_area
    if req.selected_tier is not None:
        profile.skill_level = DEFAULT_ELO_TIERS[req.selected_tier - 1]["name"]
    elif req.skill_level:
        valid_names = {
            value.strip().lower()
            for tier in DEFAULT_ELO_TIERS
            for value in (tier["name"], tier["level"], tier["sub"])
            if value
        }
        if req.skill_level.strip().lower() not in valid_names:
            raise HTTPException(status_code=422, detail="Vui lòng chọn một trong 7 hạng thi đấu có sẵn.")
        profile.skill_level = get_tier_by_name(req.skill_level)["name"]
    if req.available_time: profile.available_time = req.available_time
    if req.preferred_court: profile.preferred_court = req.preferred_court
    if req.play_style: profile.play_style = req.play_style
    if req.is_searching is not None: profile.is_searching = req.is_searching
    if profile.is_searching and profile.skill_level == "CHƯA CHỌN":
        raise HTTPException(status_code=422, detail="Hãy chọn hạng thi đấu trước khi bật tìm trận.")
    # Match rank is user-selected; match outcomes do not change it.

    await db.commit()
    await db.refresh(profile)
    return await get_player_profile(current_user.id, current_user=current_user, db=db)


# =============================================================================
# 3. SAME-TIER PLAYER DISCOVERY
# =============================================================================
@router.post("/find", response_model=MatchFindResponse)
async def find_matches(
    req: MatchFindRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Finds players who selected the same skill tier and opted into matchmaking.
    Preferences can order candidates, but ELO gaps never exclude same-tier players.
    """
    profile_res = await db.execute(select(PlayerProfile).where(PlayerProfile.user_id == current_user.id))
    player_profile = profile_res.scalar_one_or_none()
    if not player_profile:
        player_profile = PlayerProfile(
            user_id=current_user.id,
            skill_level="CHƯA CHỌN",
            current_elo=current_user.elo_rating or 1200,
            games_played=0,
            wins=0,
            losses=0,
            rating_confidence=calculate_rating_confidence(0),
            is_searching=False,
        )
        db.add(player_profile)
        await db.flush()

    if player_profile.skill_level == "CHƯA CHỌN":
        raise HTTPException(status_code=409, detail="Hãy chọn hạng thi đấu trong hồ sơ trước khi tìm người chơi.")

    user_elo = current_user.elo_rating or 1200
    user_tier = get_tier_by_name(player_profile.skill_level)

    # Search existing users or matchmaking rooms
    stmt = (
        select(User, PlayerProfile)
        .join(PlayerProfile, PlayerProfile.user_id == User.id)
        .where(User.id != current_user.id, User.role == "CUSTOMER", PlayerProfile.is_searching.is_(True))
    )
    res = await db.execute(stmt)
    other_players = res.all()

    player_data = {
        "id": current_user.id,
        "name": current_user.full_name,
        "elo": user_elo,
        "preferred_time": req.preferred_time,
        "preferred_area": req.preferred_area,
        "match_type": req.match_type
    }

    scored_candidates: List[MatchCandidate] = []

    for u, candidate_profile in other_players:
        if candidate_profile.skill_level == "CHƯA CHỌN":
            continue
        u_elo = u.elo_rating or 1200
        candidate_tier = get_tier_by_name(candidate_profile.skill_level)
        # Skill rank is selected by the player; ELO is used only to order
        # people within that rank, never to exclude a same-rank player.
        if candidate_tier["tier"] == user_tier["tier"]:
            cand_data = {
                "id": u.id,
                "name": u.full_name,
                "elo": u_elo,
                "preferred_time": candidate_profile.available_time,
                "preferred_area": candidate_profile.preferred_area,
                "match_type": req.match_type,
            }
            res_score = calculate_match_score(player_data, cand_data)
            candidate_item = MatchCandidate(
                candidate_id=u.id,
                candidate_name=u.full_name,
                candidate_tier=candidate_tier["display"],
                match_score=res_score["match_score"],
                sub_scores=res_score["sub_scores"],
                is_recommended=res_score["is_recommended"]
            )
            scored_candidates.append(candidate_item)

    # Sort descending by match_score
    scored_candidates.sort(key=lambda x: x.match_score, reverse=True)

    best_match = scored_candidates[0] if scored_candidates else None
    ai_recom = {
        "summary": (
            f"Tìm thấy {len(scored_candidates)} người chơi đang tìm trận cùng hạng {user_tier['display']}."
            if scored_candidates else
            f"Chưa có người chơi nào đang tìm trận cùng hạng {user_tier['display']}."
        ),
        "suggestion": "Bạn có thể giữ trạng thái tìm trận để người cùng hạng tìm thấy bạn." if not best_match else "Chọn một người chơi cùng hạng để kết nối và sắp xếp trận đấu.",
        "best_match_id": best_match.candidate_id if best_match else None,
        "best_match_name": best_match.candidate_name if best_match else None,
    }

    return MatchFindResponse(
        player_elo=user_elo,
        player_tier=user_tier["display"],
        dynamic_elo_range=0,
        wait_time_seconds=req.wait_time_seconds or 0,
        total_candidates=len(scored_candidates),
        candidates=scored_candidates[:10],
        ai_recommendation=ai_recom,
        matching_tier=user_tier["display"]
    )


# =============================================================================
# 4. MATCH SIMULATION & PREDICTOR
# =============================================================================
@router.get("/simulate")
async def simulate_matchup(elo_a: int = 1500, elo_b: int = 1510):
    """Calculates expected win rates, handicap, and potential ELO changes for a match."""
    exp_a = calculate_expected_score(elo_a, elo_b)
    exp_b = 1.0 - exp_a

    k_a = get_dynamic_k_factor(20, elo_a)
    k_b = get_dynamic_k_factor(20, elo_b)

    win_delta_a = round(k_a * (1.0 - exp_a))
    loss_delta_a = round(k_a * (0.0 - exp_a))
    win_delta_b = round(k_b * (1.0 - exp_b))
    loss_delta_b = round(k_b * (0.0 - exp_b))

    diff = abs(elo_a - elo_b)
    handicap = "Đồng banh (0 điểm)"
    if diff > 150:
        handicap = f"AI Handicap: Chấp {round(diff / 40)} điểm/set"

    return {
        "player_a": {
            "elo": elo_a,
            "win_probability": round(exp_a * 100, 1),
            "if_win_delta": f"+{win_delta_a}",
            "if_loss_delta": f"{loss_delta_a}",
            "tier": get_tier_for_elo(elo_a)["display"]
        },
        "player_b": {
            "elo": elo_b,
            "win_probability": round(exp_b * 100, 1),
            "if_win_delta": f"+{win_delta_b}",
            "if_loss_delta": f"{loss_delta_b}",
            "tier": get_tier_for_elo(elo_b)["display"]
        },
        "elo_difference": diff,
        "handicap_suggestion": handicap
    }


# =============================================================================
# 5. MATCH RESULT ENDPOINTS (NOT USED)
# =============================================================================
@router.post("/matches/submit-result")
async def submit_match_result(
    req: MatchResultSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Matchmaking connects players; the system does not collect match results."""
    raise HTTPException(
        status_code=410,
        detail="Hệ thống chỉ kết nối người chơi cùng hạng; không thu thập hoặc cập nhật kết quả trận đấu."
    )


@router.post("/matches/confirm-result")
async def confirm_match_result(
    req: MatchResultConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Result confirmation is disabled because match outcomes are not tracked."""
    raise HTTPException(
        status_code=410,
        detail="Hệ thống chỉ kết nối người chơi cùng hạng; không thu thập hoặc cập nhật kết quả trận đấu."
    )


# =============================================================================
# 6. ELO HISTORY & AUDIT LOGS
# =============================================================================
@router.get("/history/{user_id}", response_model=List[ELOHistoryItem])
async def get_elo_history(user_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Fetches full historical timeline of ELO changes for a player."""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Bạn chỉ có thể xem lịch sử ELO của mình.")
    stmt = (
        select(ELOHistory)
        .where(ELOHistory.player_id == user_id)
        .order_by(ELOHistory.id.desc())
        .limit(30)
    )
    res = await db.execute(stmt)
    return res.scalars().all()


# =============================================================================
# 7. ANTI-CHEAT & ABNORMAL MATCH RESULT CHECKER
# =============================================================================
@router.get("/anti-cheat/audit/{user_id}")
async def audit_player_anti_cheat(user_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Audits player's recent matches for abnormal win-trading, rapid surges, or smurfing."""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Bạn chỉ có thể xem kiểm tra chống gian lận của mình.")
    stmt = (
        select(ELOHistory)
        .where(ELOHistory.player_id == user_id)
        .order_by(ELOHistory.id.desc())
        .limit(10)
    )
    res = await db.execute(stmt)
    histories = res.scalars().all()

    matches_data = []
    for history in histories:
        if not history.match_id:
            continue
        match_players_res = await db.execute(
            select(MatchPlayer).where(MatchPlayer.match_id == history.match_id)
        )
        match_players = match_players_res.scalars().all()
        own_player = next((p for p in match_players if p.player_id == user_id), None)
        if not own_player:
            continue
        opponents = [p for p in match_players if p.team != own_player.team]
        matches_data.append({
            "match_id": history.match_id,
            "opponent_id": ",".join(str(p.player_id) for p in opponents),
            "elo_delta": history.elo_change,
            "result": own_player.result,
            "my_elo_before": history.old_elo,
            "opponent_elo": round(sum(p.elo_before for p in opponents) / len(opponents)) if opponents else 0
        })

    anomaly_report = detect_match_anomalies(user_id, matches_data)
    return anomaly_report


# =============================================================================
# 8. LEGACY / ROOM-BASED MATCHMAKING COMPATIBILITY
# =============================================================================
@router.get("/rooms", response_model=List[MatchmakingRoomResponse])
async def list_rooms(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    profile_res = await db.execute(select(PlayerProfile).where(PlayerProfile.user_id == current_user.id))
    profile = profile_res.scalar_one_or_none()
    if not profile or profile.skill_level == "CHƯA CHỌN":
        raise HTTPException(status_code=409, detail="Hãy chọn hạng thi đấu trước khi xem phòng.")
    selected_tier = get_tier_by_name(profile.skill_level)["tier"]
    stmt = (
        select(MatchmakingRoom, Facility.name.label("facility_name"))
        .outerjoin(Facility, MatchmakingRoom.facility_id == Facility.id)
        .where(MatchmakingRoom.status == "OPEN")
        .order_by(MatchmakingRoom.id.desc())
    )
    res = await db.execute(stmt)
    results = []
    for room, fac_name in res.all():
        if get_tier_for_elo(room.target_elo)["tier"] != selected_tier:
            continue
        data = MatchmakingRoomResponse.model_validate(room)
        data.facility_name = fac_name or "Cụm Sân Thi Đấu Tiêu Chuẩn"
        results.append(data)
    return results

@router.post("/rooms", response_model=MatchmakingRoomResponse)
async def create_room(
    req: MatchmakingRoomCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    profile_res = await db.execute(select(PlayerProfile).where(PlayerProfile.user_id == current_user.id))
    profile = profile_res.scalar_one_or_none()
    if not profile or profile.skill_level == "CHƯA CHỌN":
        raise HTTPException(status_code=409, detail="Hãy chọn hạng thi đấu trước khi tạo phòng.")
    tier = get_tier_by_name(profile.skill_level)
    target_elo = tier["min_elo"] if tier["max_elo"] >= 9999 else (tier["min_elo"] + tier["max_elo"]) // 2
    room = MatchmakingRoom(
        host_user_id=current_user.id,
        facility_id=req.facility_id,
        title=req.title,
        target_elo=target_elo,
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
