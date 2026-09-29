from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# AUTH SCHEMAS
class UserRegister(BaseModel):
    phone: str
    password: str
    full_name: str
    email: Optional[str] = None
    role: str = "CUSTOMER"

class UserLogin(BaseModel):
    phone: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class UserResponse(BaseModel):
    id: int
    full_name: str
    phone: str
    email: Optional[str] = None
    role: str
    elo_rating: int
    is_approved: bool

    class Config:
        from_attributes = True

# FACILITY SCHEMAS
class FacilityCreate(BaseModel):
    name: str
    address: str
    latitude: float
    longitude: float
    open_time: str = "06:00"
    close_time: str = "23:00"
    image_url: Optional[str] = None

class FacilityResponse(BaseModel):
    id: int
    owner_id: int
    name: str
    address: str
    latitude: float
    longitude: float
    open_time: str
    close_time: str
    image_url: Optional[str] = None
    rating: float
    distance_km: Optional[float] = None
    is_approved: bool

    class Config:
        from_attributes = True

# TIME SLOT SCHEMAS
class SlotHoldRequest(BaseModel):
    slot_id: int

class TimeSlotResponse(BaseModel):
    id: int
    court_id: int
    date: str
    start_time: str
    end_time: str
    status: str
    base_price: float
    dynamic_price: float
    adjustment_reason: Optional[str] = None
    held_by_me: Optional[bool] = False

# BOOKING SCHEMAS
class BookingCreate(BaseModel):
    slot_id: int
    equipment_ids: Optional[List[int]] = []

class BookingResponse(BaseModel):
    id: int
    slot_id: int
    user_id: int
    total_amount: float
    deposit_amount: float
    payment_status: str
    qr_checkin_code: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# MATCHMAKING SCHEMAS
class MatchmakingRoomCreate(BaseModel):
    facility_id: int
    title: str
    target_elo: int
    max_players: int = 4
    play_date: str
    play_time: str

class MatchmakingRoomResponse(BaseModel):
    id: int
    host_user_id: int
    facility_id: int
    title: str
    target_elo: int
    current_players: int
    max_players: int
    play_date: str
    play_time: str
    status: str
    facility_name: Optional[str] = None

    class Config:
        from_attributes = True

# AI ASSISTANT SCHEMA
class AIChatRequest(BaseModel):
    message: str
    context: Optional[str] = ""

class AIChatResponse(BaseModel):
    reply: str

# =============================================================================
# RE-ARCHITECTED AI MATCHMAKING & ELO SCHEMAS
# =============================================================================
class PlayerProfileCreateOrUpdate(BaseModel):
    gender: Optional[str] = "Khác"
    birth_year: Optional[int] = None
    preferred_area: Optional[str] = "Cầu Giấy, Hà Nội"
    skill_level: Optional[str] = "Trung Bình Khá"
    current_elo: Optional[int] = 1200
    available_time: Optional[str] = "18:00 - 21:00"
    preferred_court: Optional[str] = None
    play_style: Optional[str] = "Công thủ toàn diện"

class PlayerProfileResponse(BaseModel):
    id: int
    user_id: int
    full_name: Optional[str] = None
    gender: str
    birth_year: Optional[int] = None
    preferred_area: str
    skill_level: str
    tier_display: Optional[str] = None
    current_elo: int
    games_played: int
    wins: int
    losses: int
    win_rate_percent: Optional[float] = 0.0
    rating_confidence: float
    confidence_level: Optional[str] = "Calibrating"
    is_searching: bool
    available_time: str
    preferred_court: Optional[str] = None
    play_style: str
    streak: str

    class Config:
        from_attributes = True

class MatchFindRequest(BaseModel):
    match_type: str = "SINGLES" # SINGLES or DOUBLES
    preferred_date: str = "Hôm nay"
    preferred_time: str = "18:00 - 20:00"
    preferred_area: str = "Cầu Giấy"
    max_elo_delta: Optional[int] = 100
    wait_time_seconds: Optional[int] = 0

class MatchCandidate(BaseModel):
    candidate_id: int
    candidate_name: str
    candidate_elo: int
    candidate_tier: str
    elo_diff: int
    match_score: float
    sub_scores: dict
    win_probability_a: float
    win_probability_b: float
    is_recommended: bool

class MatchFindResponse(BaseModel):
    player_elo: int
    player_tier: str
    dynamic_elo_range: int
    wait_time_seconds: int
    total_candidates: int
    candidates: List[MatchCandidate]
    ai_recommendation: dict

class MatchResultSubmitRequest(BaseModel):
    match_id: int
    claimed_winner_id: int
    score_submission: str # e.g. "21-19, 21-18"

class MatchResultConfirmRequest(BaseModel):
    match_id: int
    confirm_agreed: bool # True = agree, False = dispute
    counter_claimed_winner_id: Optional[int] = None
    dispute_note: Optional[str] = None

class ELOHistoryItem(BaseModel):
    id: int
    player_id: int
    match_id: Optional[int] = None
    old_elo: int
    new_elo: int
    elo_change: int
    reason: str
    opponent_info: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
