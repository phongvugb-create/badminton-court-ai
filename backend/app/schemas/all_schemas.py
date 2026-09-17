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
