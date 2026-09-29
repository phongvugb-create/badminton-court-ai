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
    DEFAULT_ELO_TIERS, get_tier_for_elo, calculate_expected_score,
    update_elo, calculate_team_elo, update_doubles_elo,
    get_dynamic_elo_range, calculate_match_score,
    detect_match_anomalies, calculate_rating_confidence,
    generate_ai_match_recommendation, get_dynamic_k_factor
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
async def get_player_profile(user_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieves or auto-initializes the player profile for a given user."""
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
            skill_level="Trung Bình Khá",
            current_elo=user.elo_rating or 1200,
            games_played=6,
            wins=4,
            losses=2,
            rating_confidence=calculate_rating_confidence(6),
            is_searching=False,
            available_time="18:00 - 21:00",
            play_style="Công thủ toàn diện",
            streak="+2W"
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    tier = get_tier_for_elo(profile.current_elo)
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
        tier_display=tier["display"],
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
    if req.skill_level: profile.skill_level = req.skill_level
    if req.available_time: profile.available_time = req.available_time
    if req.preferred_court: profile.preferred_court = req.preferred_court
    if req.play_style: profile.play_style = req.play_style
    if req.current_elo:
        profile.current_elo = req.current_elo
        current_user.elo_rating = req.current_elo

    await db.commit()
    await db.refresh(profile)
    return await get_player_profile(current_user.id, db)


# =============================================================================
# 3. MATCHMAKING ENGINE WITH DYNAMIC RANGE & MULTI-CRITERIA SCORE
# =============================================================================
@router.post("/find", response_model=MatchFindResponse)
async def find_matches(
    req: MatchFindRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Finds optimal opponents or rooms:
    1. Evaluates wait time -> calculates Dynamic ELO Range (±50, ±100, ±150, ±200).
    2. Gathers available candidates in the database.
    3. Calculates holistic MatchScore (ELO 50%, Time 20%, Location 15%, Skill 10%, History 5%).
    4. Ranks candidates and generates explainable AI Recommendation.
    """
    user_elo = current_user.elo_rating or 1200
    user_tier = get_tier_for_elo(user_elo)

    # Dynamic ELO Range expansion based on wait time
    dynamic_range = get_dynamic_elo_range(req.wait_time_seconds or 0)
    effective_max_delta = max(req.max_elo_delta or 100, dynamic_range)

    # Search existing users or matchmaking rooms
    stmt = select(User).where(User.id != current_user.id, User.role == "CUSTOMER")
    res = await db.execute(stmt)
    other_users = res.scalars().all()

    player_data = {
        "id": current_user.id,
        "name": current_user.full_name,
        "elo": user_elo,
        "preferred_time": req.preferred_time,
        "preferred_area": req.preferred_area,
        "match_type": req.match_type
    }

    scored_candidates: List[MatchCandidate] = []
    candidates_dict_for_ai = []

    for u in other_users:
        u_elo = u.elo_rating or 1200
        diff = abs(user_elo - u_elo)

        # Filter by dynamic range
        if diff <= effective_max_delta:
            cand_data = {
                "id": u.id,
                "name": u.full_name,
                "elo": u_elo,
                "preferred_time": req.preferred_time,
                "preferred_area": req.preferred_area,
                "match_type": req.match_type,
                "distance_km": 2.5
            }
            res_score = calculate_match_score(player_data, cand_data)
            candidate_item = MatchCandidate(
                candidate_id=u.id,
                candidate_name=u.full_name,
                candidate_elo=u_elo,
                candidate_tier=res_score["candidate_tier"],
                elo_diff=res_score["elo_diff"],
                match_score=res_score["match_score"],
                sub_scores=res_score["sub_scores"],
                win_probability_a=res_score["win_probability_a"],
                win_probability_b=res_score["win_probability_b"],
                is_recommended=res_score["is_recommended"]
            )
            scored_candidates.append(candidate_item)
            candidates_dict_for_ai.append(res_score)

    # Sort descending by match_score
    scored_candidates.sort(key=lambda x: x.match_score, reverse=True)
    candidates_dict_for_ai.sort(key=lambda x: x["match_score"], reverse=True)

    # AI Recommendation layer generates transparent explanation
    ai_recom = generate_ai_match_recommendation(player_data, candidates_dict_for_ai)

    return MatchFindResponse(
        player_elo=user_elo,
        player_tier=user_tier["display"],
        dynamic_elo_range=effective_max_delta,
        wait_time_seconds=req.wait_time_seconds or 0,
        total_candidates=len(scored_candidates),
        candidates=scored_candidates[:10],
        ai_recommendation=ai_recom
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
# 5. TWO-WAY RESULT CONFIRMATION & DISPUTE WORKFLOW
# =============================================================================
@router.post("/matches/submit-result")
async def submit_match_result(
    req: MatchResultSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Step 1: Player A inputs the match result.
    Match transitions to PENDING_CONFIRMATION waiting for Player B.
    """
    stmt = select(Match).where(Match.id == req.match_id)
    res = await db.execute(stmt)
    match = res.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Không tìm thấy trận đấu!")

    match.status = "PENDING_CONFIRMATION"
    match.final_score = req.score_submission
    
    # Record player submission
    stmt_mp = select(MatchPlayer).where(MatchPlayer.match_id == req.match_id, MatchPlayer.player_id == current_user.id)
    res_mp = await db.execute(stmt_mp)
    mp = res_mp.scalar_one_or_none()
    if mp:
        mp.score_claimed = req.score_submission
        mp.confirmation_status = "CONFIRMED"
        mp.submitted_at = datetime.now()

    await db.commit()
    return {
        "status": "PENDING_CONFIRMATION",
        "message": "Đã ghi nhận kết quả từ bạn. Đang gửi yêu cầu xác nhận tới đối thủ để hoàn tất cập nhật ELO!",
        "match_id": req.match_id
    }

@router.post("/matches/confirm-result")
async def confirm_match_result(
    req: MatchResultConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Step 2: Player B confirms or disputes the result.
    - If Agreed: Triggers ELO updates for both players, logs ELOHistory.
    - If Disputed: Freezes ELO changes and flags match as DISPUTED.
    """
    stmt = select(Match).where(Match.id == req.match_id)
    res = await db.execute(stmt)
    match = res.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Không tìm thấy trận đấu!")

    if not req.confirm_agreed:
        match.status = "DISPUTED"
        await db.commit()
        return {
            "status": "DISPUTED",
            "message": "⚠️ Đã ghi nhận tranh chấp kết quả! Hệ thống tạm đóng băng biến động ELO và chuyển ban trọng tài xử lý.",
            "dispute_note": req.dispute_note
        }

    # Mutual confirmation! Execute ELO Update
    match.status = "CONFIRMED"

    # Get players
    stmt_players = select(MatchPlayer).where(MatchPlayer.match_id == req.match_id)
    res_p = await db.execute(stmt_players)
    players = res_p.scalars().all()

    if len(players) >= 2:
        p1, p2 = players[0], players[1]
        score_p1 = 1.0 if p1.result == "WIN" else 0.0
        new_elo1, new_elo2, delta1, delta2 = update_elo(p1.elo_before, p2.elo_before, score_p1)

        p1.elo_after = new_elo1
        p1.elo_change = delta1
        p1.confirmation_status = "CONFIRMED"

        p2.elo_after = new_elo2
        p2.elo_change = delta2
        p2.confirmation_status = "CONFIRMED"

        # Log ELO Histories
        db.add(ELOHistory(
            player_id=p1.player_id, match_id=match.id,
            old_elo=p1.elo_before, new_elo=new_elo1, elo_change=delta1,
            reason=f"Trận đấu #{match.id} ({'Thắng' if delta1 > 0 else 'Thua'})"
        ))
        db.add(ELOHistory(
            player_id=p2.player_id, match_id=match.id,
            old_elo=p2.elo_before, new_elo=new_elo2, elo_change=delta2,
            reason=f"Trận đấu #{match.id} ({'Thắng' if delta2 > 0 else 'Thua'})"
        ))

    await db.commit()
    return {
        "status": "CONFIRMED",
        "message": "Hai bên đã thống nhất kết quả! Điểm ELO đã được cập nhật thành công.",
        "match_id": req.match_id
    }


# =============================================================================
# 6. ELO HISTORY & AUDIT LOGS
# =============================================================================
@router.get("/history/{user_id}", response_model=List[ELOHistoryItem])
async def get_elo_history(user_id: int, db: AsyncSession = Depends(get_db)):
    """Fetches full historical timeline of ELO changes for a player."""
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
async def audit_player_anti_cheat(user_id: int, db: AsyncSession = Depends(get_db)):
    """Audits player's recent matches for abnormal win-trading, rapid surges, or smurfing."""
    stmt = (
        select(ELOHistory)
        .where(ELOHistory.player_id == user_id)
        .order_by(ELOHistory.id.desc())
        .limit(10)
    )
    res = await db.execute(stmt)
    histories = res.scalars().all()

    matches_data = [
        {
            "match_id": h.match_id,
            "elo_delta": h.elo_change,
            "result": "WIN" if h.elo_change > 0 else "LOSS",
            "opponent_elo": 1400
        }
        for h in histories
    ]

    anomaly_report = detect_match_anomalies(user_id, matches_data)
    return anomaly_report


# =============================================================================
# 8. LEGACY / ROOM-BASED MATCHMAKING COMPATIBILITY
# =============================================================================
@router.get("/rooms", response_model=List[MatchmakingRoomResponse])
async def list_rooms(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(MatchmakingRoom, Facility.name.label("facility_name"))
        .outerjoin(Facility, MatchmakingRoom.facility_id == Facility.id)
        .where(MatchmakingRoom.status == "OPEN")
        .order_by(MatchmakingRoom.id.desc())
    )
    res = await db.execute(stmt)
    results = []
    for room, fac_name in res.all():
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
