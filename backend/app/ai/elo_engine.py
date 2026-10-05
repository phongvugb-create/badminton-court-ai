"""
AI MATCHMAKING & ELO RATING ENGINE (UC006 - Re-architected)
============================================================
Architecture Highlights:
1. 6-Tier ELO Ranking System with configurable thresholds.
2. Standard logistic ELO update with Dynamic K-Factor & Rating Confidence.
3. Singles (1v1) and Doubles (2v2) Team ELO evaluation.
4. Multi-factor Matchmaking Score Engine (ELO 50%, Time 20%, Location 15%, Skill 10%, History 5%).
5. Dynamic ELO Range expansion over wait time (0-30s: ±50, 30-60s: ±100, 60-120s: ±150, >120s: ±200).
6. Anti-Cheat & Abnormal Match Result detection (win trading, rapid surge, smurf suspect).
7. Two-way Result Confirmation & Dispute state management.
8. Explainable AI Recommendation Layer on top of deterministic algorithms.
"""

import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

# =============================================================================
# 1. 7 SKILL TIERS (CẤP BẬC TRÌNH ĐỘ MATCHMAKING) & CONFIGURATION
# =============================================================================
DEFAULT_ELO_TIERS = [
    {
        "tier": 1,
        "name": "Yếu - Tân thủ",
        "level": "Yếu",
        "sub": "Tân thủ",
        "display": "🟢 Cấp 1: Yếu - Tân thủ",
        "min_elo": 0,
        "max_elo": 950,
        "color": "#16a34a",
        "badge_bg": "#dcfce7",
        "description": "Mới tập chơi, nắm bắt kỹ thuật phát cầu & phản tạt cơ bản."
    },
    {
        "tier": 2,
        "name": "Trung Bình Yếu - Cơ bản",
        "level": "Trung Bình Yếu",
        "sub": "Cơ bản",
        "display": "🔵 Cấp 2: Trung Bình Yếu - Cơ bản",
        "min_elo": 951,
        "max_elo": 1150,
        "color": "#0284c7",
        "badge_bg": "#e0f2fe",
        "description": "Nắm vững luật thi đấu, phông cầu cơ bản, di chuyển bước đầu ổn định."
    },
    {
        "tier": 3,
        "name": "Trung bình",
        "level": "Trung bình",
        "sub": "",
        "display": "🟡 Cấp 3: Trung bình",
        "min_elo": 1151,
        "max_elo": 1350,
        "color": "#ca8a04",
        "badge_bg": "#fef9c3",
        "description": "Đánh cầu đều tay, di chuyển thanh thoát, phông cầu sâu và bỏ nhỏ ổn định."
    },
    {
        "tier": 4,
        "name": "Trung bình khá",
        "level": "Trung bình khá",
        "sub": "",
        "display": "🟠 Cấp 4: Trung bình khá",
        "min_elo": 1351,
        "max_elo": 1550,
        "color": "#ea580c",
        "badge_bg": "#ffedd5",
        "description": "Có nền tảng thể lực, bọc lót linh hoạt, smash cơ bản và tạt lưới sắc bén."
    },
    {
        "tier": 5,
        "name": "Khá",
        "level": "Khá",
        "sub": "",
        "display": "🔴 Cấp 5: Khá",
        "min_elo": 1551,
        "max_elo": 1750,
        "color": "#dc2626",
        "badge_bg": "#fee2e2",
        "description": "Kỹ thuật toàn diện, smash uy lực, điều tiết nhịp độ và kiểm soát thế trận vững vàng."
    },
    {
        "tier": 6,
        "name": "Giỏi - Thành thạo",
        "level": "Giỏi",
        "sub": "Thành thạo",
        "display": "🟣 Cấp 6: Giỏi - Thành thạo",
        "min_elo": 1751,
        "max_elo": 1950,
        "color": "#9333ea",
        "badge_bg": "#f3e8ff",
        "description": "Kỹ năng chuyên sâu, thi đấu giải phong trào nhiều năm, phản xạ cực nhạy."
    },
    {
        "tier": 7,
        "name": "Tốt - Chuyên nghiệp",
        "level": "Tốt",
        "sub": "Chuyên nghiệp",
        "display": "👑 Cấp 7: Tốt - Chuyên nghiệp",
        "min_elo": 1951,
        "max_elo": 9999,
        "color": "#4f46e5",
        "badge_bg": "#e0e7ff",
        "description": "Đẳng cấp kiện tướng, vận động viên bán chuyên / chuyên nghiệp hoặc HLV đẳng cấp cao."
    }
]

def get_tier_for_elo(elo: int, tiers: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Finds the corresponding tier for a given ELO rating."""
    tiers_to_use = tiers or DEFAULT_ELO_TIERS
    for t in tiers_to_use:
        if t["min_elo"] <= elo <= t["max_elo"]:
            return t
    return tiers_to_use[0] if elo < 950 else tiers_to_use[-1]

def get_tier_by_rank(tier_id: int) -> Dict[str, Any]:
    """Finds the corresponding tier by its tier rank ID (1 to 7)."""
    for t in DEFAULT_ELO_TIERS:
        if t["tier"] == tier_id:
            return t
    return DEFAULT_ELO_TIERS[3]  # default to Trung bình khá

def get_tier_by_name(name: str) -> Dict[str, Any]:
    """Finds tier by its Vietnamese name."""
    clean = name.strip().lower()
    for t in DEFAULT_ELO_TIERS:
        if clean in t["name"].lower() or t["name"].lower() in clean:
            return t
    return DEFAULT_ELO_TIERS[3]


# =============================================================================
# 2. RATING CONFIDENCE & DYNAMIC K-FACTOR
# =============================================================================
def calculate_rating_confidence(games_played: int, last_active_days_ago: int = 0) -> float:
    """
    Calculates Rating Confidence (0.0 to 1.0).
    - Confidence scales up to 1.0 as games_played approaches 30.
    - Minor inactivity decay if player hasn't played in over 30 days.
    """
    if games_played <= 0:
        return 0.10
    
    # Scale from 0.1 to 1.0 based on matches played (reaches 0.95 at 30 games)
    base_confidence = min(1.0, 0.15 + (games_played / 35.0) * 0.85)

    # Inactivity penalty: decay by up to 15% if inactive > 30 days
    if last_active_days_ago > 30:
        decay_factor = max(0.85, 1.0 - ((last_active_days_ago - 30) / 100.0) * 0.15)
        base_confidence *= decay_factor

    return round(max(0.10, min(1.0, base_confidence)), 2)

def get_dynamic_k_factor(games_played: int, elo: int, confidence: Optional[float] = None) -> int:
    """
    Determines K-factor for ELO updates:
    - New players (<10 games): K=48 for fast placement convergence.
    - Developing (10-29 games): K=32.
    - Established (>=30 games): K=24.
    - Top Master Tier (>=1800): K=16 to ensure ranking stability.
    """
    if games_played < 10:
        return 48
    if elo >= 1800:
        return 16
    if games_played >= 30:
        return 24
    return 32


# =============================================================================
# 3. CORE ELO FORMULAS & EXPECTED SCORE
# =============================================================================
def calculate_expected_score(rating_a: float, rating_b: float) -> float:
    """
    Standard International ELO Logistic Curve Formula:
    E_A = 1 / (1 + 10^((R_B - R_A)/400))
    """
    exponent = (rating_b - rating_a) / 400.0
    return 1.0 / (1.0 + math.pow(10.0, exponent))

def update_elo(
    rating_a: int,
    rating_b: int,
    score_a: float,
    games_a: int = 10,
    games_b: int = 10,
    k_factor: Optional[int] = None
) -> Tuple[int, int, int, int]:
    """
    Computes updated ELO for 2 players.
    score_a: 1.0 (win A), 0.5 (draw), 0.0 (win B / loss A)
    Returns: (new_a, new_b, delta_a, delta_b)
    """
    exp_a = calculate_expected_score(rating_a, rating_b)
    exp_b = 1.0 - exp_a
    score_b = 1.0 - score_a

    k_a = k_factor or get_dynamic_k_factor(games_a, rating_a)
    k_b = k_factor or get_dynamic_k_factor(games_b, rating_b)

    delta_a = round(k_a * (score_a - exp_a))
    delta_b = round(k_b * (score_b - exp_b))

    new_a = max(100, rating_a + delta_a)
    new_b = max(100, rating_b + delta_b)

    return (new_a, new_b, delta_a, delta_b)

def calculate_team_elo(player1_elo: int, player2_elo: int) -> int:
    """Calculates Team ELO for doubles (2v2)."""
    return round((player1_elo + player2_elo) / 2.0)

def update_doubles_elo(
    team_a_players: List[Dict[str, Any]],
    team_b_players: List[Dict[str, Any]],
    score_a: float
) -> Dict[str, Any]:
    """
    Updates ELO for 2v2 doubles match.
    team_a_players: [{'id': 1, 'elo': 1500, 'games': 20}, {'id': 2, 'elo': 1600, 'games': 15}]
    """
    team_a_elo = calculate_team_elo(team_a_players[0]['elo'], team_a_players[1]['elo'])
    team_b_elo = calculate_team_elo(team_b_players[0]['elo'], team_b_players[1]['elo'])

    exp_a = calculate_expected_score(team_a_elo, team_b_elo)
    exp_b = 1.0 - exp_a
    score_b = 1.0 - score_a

    updated_players = []

    # Update Team A players
    for p in team_a_players:
        k = get_dynamic_k_factor(p.get('games', 10), p['elo'])
        delta = round(k * (score_a - exp_a))
        updated_players.append({
            "id": p["id"],
            "team": "A",
            "old_elo": p["elo"],
            "new_elo": max(100, p["elo"] + delta),
            "delta": delta
        })

    # Update Team B players
    for p in team_b_players:
        k = get_dynamic_k_factor(p.get('games', 10), p['elo'])
        delta = round(k * (score_b - exp_b))
        updated_players.append({
            "id": p["id"],
            "team": "B",
            "old_elo": p["elo"],
            "new_elo": max(100, p["elo"] + delta),
            "delta": delta
        })

    return {
        "team_a_elo_before": team_a_elo,
        "team_b_elo_before": team_b_elo,
        "expected_a": round(exp_a * 100, 1),
        "expected_b": round(exp_b * 100, 1),
        "player_results": updated_players
    }


# =============================================================================
# 4. DYNAMIC ELO RANGE EXPANSION (BY WAIT TIME)
# =============================================================================
def get_dynamic_elo_range(wait_seconds: int) -> int:
    """
    Expands search radius based on queue waiting time:
    - 0 – 30s:   ±50 ELO (Strict fairness)
    - 30 – 60s:  ±100 ELO
    - 60 – 120s: ±150 ELO
    - > 120s:    ±200 ELO (Maximum allowance)
    """
    if wait_seconds < 30:
        return 50
    elif wait_seconds < 60:
        return 100
    elif wait_seconds < 120:
        return 150
    else:
        return 200


# =============================================================================
# 5. MULTI-FACTOR MATCHMAKING SCORE ENGINE
# =============================================================================
DEFAULT_WEIGHTS = {
    "elo": 0.50,         # 50% ELO Delta
    "time": 0.20,        # 20% Available time overlap
    "location": 0.15,    # 15% Court distance / preferred district
    "skill": 0.10,       # 10% Skill tier compatibility
    "history": 0.05      # 5% History/preferences match
}

def calculate_time_overlap_score(time_a: str, time_b: str) -> float:
    """
    Calculates time compatibility score (0 to 100).
    Expected format: "18:00 - 20:00" or similar.
    """
    if not time_a or not time_b:
        return 50.0
    if time_a.strip().lower() == time_b.strip().lower():
        return 100.0
    
    # Try parsing hours
    try:
        def parse_span(t_str):
            parts = t_str.split("-")
            start = float(parts[0].strip().replace("h", ".").replace(":", "."))
            end = float(parts[1].strip().replace("h", ".").replace(":", "."))
            return start, end
        
        s1, e1 = parse_span(time_a)
        s2, e2 = parse_span(time_b)
        overlap_start = max(s1, s2)
        overlap_end = min(e1, e2)
        
        if overlap_end > overlap_start:
            overlap_duration = overlap_end - overlap_start
            max_duration = max(e1 - s1, e2 - s2, 1.0)
            return min(100.0, round((overlap_duration / max_duration) * 100, 1))
        else:
            diff = min(abs(s1 - e2), abs(s2 - e1))
            return max(10.0, 80.0 - diff * 20.0)
    except Exception:
        return 70.0

def calculate_location_score(loc_a: str, loc_b: str, distance_km: Optional[float] = None) -> float:
    """Calculates location score (0 to 100)."""
    if distance_km is not None:
        # 0km = 100, 5km = 75, 10km = 50, >15km = 20
        return max(10.0, round(100.0 - distance_km * 5.0, 1))
    
    if not loc_a or not loc_b:
        return 60.0
    
    la, lb = loc_a.lower().strip(), loc_b.lower().strip()
    if la == lb:
        return 100.0
    if any(k in la for k in lb.split()) or any(k in lb for k in la.split()):
        return 85.0
    return 50.0

def calculate_match_score(
    player_a: Dict[str, Any],
    candidate_b: Dict[str, Any],
    weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Computes holistic MatchScore:
    MatchScore = w_elo * S_elo + w_time * S_time + w_loc * S_loc + w_skill * S_skill + w_hist * S_hist
    """
    w = weights or DEFAULT_WEIGHTS

    # 1. ELO Score (Max 100 when diff=0, decays linearly to 0 at diff=200)
    elo_a = player_a.get("elo_rating", player_a.get("elo", 1200))
    elo_b = candidate_b.get("elo_rating", candidate_b.get("elo", 1200))
    diff = abs(elo_a - elo_b)
    s_elo = max(0.0, 100.0 - (diff / 2.0))

    # 2. Time Score
    time_a = player_a.get("preferred_time", player_a.get("play_time", ""))
    time_b = candidate_b.get("preferred_time", candidate_b.get("play_time", candidate_b.get("match_time", "")))
    s_time = calculate_time_overlap_score(time_a, time_b)

    # 3. Location Score
    loc_a = player_a.get("preferred_area", player_a.get("district", ""))
    loc_b = candidate_b.get("preferred_area", candidate_b.get("district", candidate_b.get("facility_name", "")))
    dist_km = candidate_b.get("distance_km")
    s_loc = calculate_location_score(loc_a, loc_b, dist_km)

    # 4. Skill Score (tier consistency)
    tier_a = get_tier_for_elo(elo_a)["tier"]
    tier_b = get_tier_for_elo(elo_b)["tier"]
    tier_diff = abs(tier_a - tier_b)
    s_skill = max(20.0, 100.0 - (tier_diff * 25.0))

    # 5. History / Preference match (singles vs doubles, past matchups)
    type_a = player_a.get("match_type", "doubles")
    type_b = candidate_b.get("match_type", candidate_b.get("category", "doubles"))
    s_hist = 100.0 if type_a.lower() in str(type_b).lower() else 50.0

    total_score = (
        w["elo"] * s_elo +
        w["time"] * s_time +
        w["location"] * s_loc +
        w["skill"] * s_skill +
        w["history"] * s_hist
    )
    total_score = round(min(100.0, max(0.0, total_score)), 1)

    exp_a = calculate_expected_score(elo_a, elo_b)

    return {
        "candidate_id": candidate_b.get("id") or candidate_b.get("user_id"),
        "candidate_name": candidate_b.get("name") or candidate_b.get("full_name") or candidate_b.get("host_name"),
        "candidate_elo": elo_b,
        "candidate_tier": get_tier_for_elo(elo_b)["display"],
        "elo_diff": diff,
        "match_score": total_score,
        "sub_scores": {
            "elo_score": round(s_elo, 1),
            "time_score": round(s_time, 1),
            "location_score": round(s_loc, 1),
            "skill_score": round(s_skill, 1),
            "history_score": round(s_hist, 1)
        },
        "win_probability_a": round(exp_a * 100, 1),
        "win_probability_b": round((1.0 - exp_a) * 100, 1),
        "is_recommended": total_score >= 85.0
    }


# =============================================================================
# 6. ANTI-CHEAT & ABNORMAL MATCH RESULT DETECTION
# =============================================================================
def detect_match_anomalies(
    player_id: int,
    recent_matches: List[Dict[str, Any]],
    current_match: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Detects abnormal patterns in player match history:
    1. Win Trading: Playing the same opponent >= 3 times in 48h with 100% win rate.
    2. Rapid ELO Surge: Gaining > 200 ELO in <= 5 matches.
    3. Smurf / Account Sharing: New account (< 5 matches) repeatedly beating >= 1600 ELO veterans.
    4. Suspicious Streak: Extreme win rate (>90%) with exclusively lower ELO opponents.
    """
    flags = []
    risk_level = "LOW"
    details = []

    if not recent_matches:
        return {"risk_level": "LOW", "flags": [], "details": ["Chưa có đủ dữ liệu lịch sử để đánh giá."]}

    # Check 1: Win Trading (Repeated opponent farming)
    opponents_count = {}
    opponent_wins = {}
    for m in recent_matches[-10:]:
        opp_id = m.get("opponent_id")
        won = m.get("result") in ["WIN", 1.0, 1]
        if opp_id:
            opponents_count[opp_id] = opponents_count.get(opp_id, 0) + 1
            if won:
                opponent_wins[opp_id] = opponent_wins.get(opp_id, 0) + 1

    for opp_id, count in opponents_count.items():
        if count >= 3 and opponent_wins.get(opp_id, 0) == count:
            flags.append("ANOMALY_WIN_TRADING")
            details.append(f"Đấu với đối thủ #{opp_id} {count} trận liên tiếp đều thắng 100% (nghi vấn cày điểm/win-trading).")
            risk_level = "HIGH"

    # Check 2: Rapid ELO Surge
    if len(recent_matches) >= 3:
        elo_deltas = [m.get("elo_delta", 0) for m in recent_matches[-5:]]
        total_surge = sum(d for d in elo_deltas if d > 0)
        if total_surge >= 180:
            flags.append("ANOMALY_RAPID_SURGE")
            details.append(f"Điểm ELO tăng đột biến (+{total_surge} ELO trong 5 trận gần nhất).")
            if risk_level != "HIGH":
                risk_level = "MEDIUM"

    # Check 3: Smurf / Account Sharing
    total_games = len(recent_matches)
    if total_games <= 6:
        high_tier_wins = sum(
            1 for m in recent_matches 
            if m.get("opponent_elo", 0) >= 1600 and m.get("result") in ["WIN", 1.0, 1]
        )
        if high_tier_wins >= 2:
            flags.append("ANOMALY_SMURF_SUSPECT")
            details.append(f"Tài khoản mới ({total_games} trận) liên tục thắng đối thủ ELO cao (>=1600).")
            if risk_level != "HIGH":
                risk_level = "MEDIUM"

    # Check 4: One-sided farming (only playing much lower ELO)
    low_elo_matches = [
        m for m in recent_matches[-8:]
        if (m.get("my_elo_before", 1400) - m.get("opponent_elo", 1400)) >= 250
    ]
    if len(low_elo_matches) >= 5 and all(m.get("result") == "WIN" for m in low_elo_matches):
        flags.append("ANOMALY_FARMING_LOW_ELO")
        details.append("Có dấu hiệu chủ ý chỉ ghép và bắt nạt đối thủ ELO thấp hơn >250 điểm.")
        if risk_level == "LOW":
            risk_level = "MEDIUM"

    return {
        "risk_level": risk_level,
        "is_suspicious": len(flags) > 0,
        "flags": flags,
        "details": details if details else ["Hồ sơ thi đấu bình thường, không có dấu hiệu bất thường."]
    }


# =============================================================================
# 7. TWO-WAY RESULT CONFIRMATION & DISPUTE HANDLER
# =============================================================================
class MatchConfirmationStatus:
    PENDING = "PENDING_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    DISPUTED = "DISPUTED"
    RESOLVED = "RESOLVED"

def process_match_result_submission(
    match_record: Dict[str, Any],
    submitting_player_id: int,
    claimed_winner_id: int,
    score_submission: str
) -> Dict[str, Any]:
    """
    Processes match result entry:
    - First player enters result -> State becomes PENDING_CONFIRMATION.
    - Second player confirms matching result -> State becomes CONFIRMED, returns trigger for ELO update.
    - Second player enters conflicting result -> State becomes DISPUTED.
    """
    player_a_id = match_record.get("player_a_id")
    player_b_id = match_record.get("player_b_id")
    
    first_submission = match_record.get("first_submission")

    if not first_submission:
        # First party submitting
        return {
            "status": MatchConfirmationStatus.PENDING,
            "message": "Đã ghi nhận kết quả từ bạn. Đang chờ đối thủ xác nhận để cập nhật ELO!",
            "first_submission": {
                "submitted_by": submitting_player_id,
                "claimed_winner": claimed_winner_id,
                "score": score_submission,
                "submitted_at": datetime.now().isoformat()
            },
            "should_update_elo": False
        }
    else:
        # Second party confirming or disputing
        first_submitter = first_submission.get("submitted_by")
        if first_submitter == submitting_player_id:
            return {
                "status": MatchConfirmationStatus.PENDING,
                "message": "Bạn đã gửi kết quả rồi, vui lòng đợi đối thủ đối soát!",
                "should_update_elo": False
            }

        first_winner = first_submission.get("claimed_winner")
        if first_winner == claimed_winner_id:
            # Mutual agreement!
            return {
                "status": MatchConfirmationStatus.CONFIRMED,
                "message": "Hai bên đã thống nhất kết quả trận đấu! Điểm ELO đã được cập nhật chính thức.",
                "winner_id": claimed_winner_id,
                "final_score": score_submission or first_submission.get("score"),
                "should_update_elo": True
            }
        else:
            # Dispute detected!
            return {
                "status": MatchConfirmationStatus.DISPUTED,
                "message": "⚠️ Xảy ra tranh chấp kết quả! Bên A và Bên B khai báo người thắng khác nhau. Hệ thống tạm khóa cập nhật ELO và chuyển ban trọng tài xem xét.",
                "conflict_details": {
                    "party_1": {"player_id": first_submitter, "claimed_winner": first_winner},
                    "party_2": {"player_id": submitting_player_id, "claimed_winner": claimed_winner_id}
                },
                "should_update_elo": False
            }


# =============================================================================
# 8. EXPLAINABLE AI RECOMMENDATION LAYER
# =============================================================================
def generate_ai_match_recommendation(
    player_profile: Dict[str, Any],
    top_candidates: List[Dict[str, Any]],
    recent_form_streak: Optional[str] = "W-W-L-W"
) -> Dict[str, Any]:
    """
    Generates intelligent, transparent, natural language justification.
    Acts as the presentation and insight layer on top of algorithmic Matchmaking.
    """
    user_name = player_profile.get("full_name") or player_profile.get("name") or "Bạn"
    user_elo = player_profile.get("elo_rating") or player_profile.get("elo", 1200)
    tier_info = get_tier_for_elo(user_elo)
    
    if not top_candidates:
        return {
            "summary": f"{user_name} đang ở mức ELO {user_elo} ({tier_info['display']}). Hiện chưa tìm thấy đối thủ trong dải ELO hiện tại.",
            "suggestion": "Hệ thống đang kích hoạt Dynamic Range để nới rộng khoảng ELO lên ±100 - ±150 trong vài giây tới.",
            "best_match": None
        }

    best = top_candidates[0]
    cand_name = best.get("candidate_name", "Đối thủ")
    cand_elo = best.get("candidate_elo", 1200)
    match_score = best.get("match_score", 90)
    elo_diff = best.get("elo_diff", 0)

    # Narrative generation
    form_desc = "phong độ thi đấu rất ổn định" if "W-W" in (recent_form_streak or "") else "đang tìm kiếm chiến thắng bứt phá"
    
    analysis_text = (
        f"🎯 {user_name} đang có ELO {user_elo} ({tier_info['display']}) và {form_desc}. "
        f"Thuật toán MatchScore đã chấm {match_score}% mức độ tương thích với {cand_name} (ELO {cand_elo}, chênh lệch chỉ {elo_diff} điểm). "
        f"Kèo đấu hứa hẹn tỷ lệ thắng cân bằng {best.get('win_probability_a', 50)}% - {best.get('win_probability_b', 50)}%, "
        f"rất phù hợp để cọ xát nâng cao kỹ năng mà không lo lệch trình."
    )

    tactical_tip = (
        "💡 Gợi ý chiến thuật: Hãy tập trung vào những pha cầu bền ở set 1 để thăm dò lối di chuyển của đối thủ!"
        if elo_diff <= 30 else
        f"💡 Đối thủ có ELO {'cao hơn' if cand_elo > user_elo else 'thấp hơn'} {elo_diff} điểm. Tận dụng các pha bỏ nhỏ góc lưới và smash chéo sân."
    )

    return {
        "analysis_text": analysis_text,
        "tactical_tip": tactical_tip,
        "best_match_id": best.get("candidate_id"),
        "best_match_name": cand_name,
        "compatibility": match_score,
        "elo_balance": f"Δ {elo_diff} ELO ({best.get('win_probability_a')}% vs {best.get('win_probability_b')}%)"
    }
