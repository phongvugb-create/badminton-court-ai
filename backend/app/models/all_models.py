from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class UserRole(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    OWNER = "OWNER"
    STAFF = "STAFF"
    ADMIN = "ADMIN"

class SlotStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    HELD = "HELD"
    BOOKED = "BOOKED"
    MAINTENANCE = "MAINTENANCE"

class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    DEPOSITED = "DEPOSITED"
    PAID = "PAID"
    REFUNDED = "REFUNDED"
    CANCELLED = "CANCELLED"

class RoomStatus(str, enum.Enum):
    OPEN = "OPEN"
    FULL = "FULL"
    CLOSED = "CLOSED"

# 1. USERS
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    email = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="CUSTOMER", nullable=False)
    elo_rating = Column(Integer, default=1000)
    is_approved = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    facilities = relationship("Facility", back_populates="owner")
    bookings = relationship("Booking", back_populates="user")
    hosted_rooms = relationship("MatchmakingRoom", back_populates="host")

# 2. FACILITIES
class Facility(Base):
    __tablename__ = "facilities"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False, index=True)
    address = Column(String(500), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    open_time = Column(String(10), default="06:00")
    close_time = Column(String(10), default="23:00")
    image_url = Column(String(500), nullable=True)
    rating = Column(Float, default=4.8)
    is_approved = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="facilities")
    courts = relationship("Court", back_populates="facility", cascade="all, delete-orphan")
    equipment = relationship("Equipment", back_populates="facility")
    rooms = relationship("MatchmakingRoom", back_populates="facility")

# 3. COURTS
class Court(Base):
    __tablename__ = "courts"

    id = Column(Integer, primary_key=True, index=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=False)
    court_number = Column(String(50), nullable=False)
    surface_type = Column(String(100), default="Thảm PVC chuyên dụng Enlio")
    is_active = Column(Boolean, default=True)

    facility = relationship("Facility", back_populates="courts")
    slots = relationship("TimeSlot", back_populates="court", cascade="all, delete-orphan")

# 4. TIME_SLOTS
class TimeSlot(Base):
    __tablename__ = "time_slots"

    id = Column(Integer, primary_key=True, index=True)
    court_id = Column(Integer, ForeignKey("courts.id"), nullable=False)
    date = Column(String(20), nullable=False, index=True) # YYYY-MM-DD
    start_time = Column(String(10), nullable=False)        # HH:MM
    end_time = Column(String(10), nullable=False)          # HH:MM
    status = Column(String(50), default="AVAILABLE")        # AVAILABLE, HELD, BOOKED

    court = relationship("Court", back_populates="slots")
    pricing = relationship("SlotPricing", back_populates="slot", uselist=False, cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="slot")

# 5. SLOT_PRICING
class SlotPricing(Base):
    __tablename__ = "slot_pricing"

    id = Column(Integer, primary_key=True, index=True)
    slot_id = Column(Integer, ForeignKey("time_slots.id"), nullable=False, unique=True)
    base_price = Column(Float, nullable=False)
    dynamic_price = Column(Float, nullable=False)
    adjustment_reason = Column(String(255), default="AI Base Rate")
    is_ai_applied = Column(Boolean, default=True)

    slot = relationship("TimeSlot", back_populates="pricing")

# 6. BOOKINGS
class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    slot_id = Column(Integer, ForeignKey("time_slots.id"), nullable=False)
    total_amount = Column(Float, nullable=False)
    deposit_amount = Column(Float, nullable=False)
    payment_status = Column(String(50), default="PENDING") # PENDING, DEPOSITED, PAID
    qr_checkin_code = Column(String(100), unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="bookings")
    slot = relationship("TimeSlot", back_populates="bookings")
    rental_items = relationship("RentalItem", back_populates="booking", cascade="all, delete-orphan")

# 7. EQUIPMENT
class Equipment(Base):
    __tablename__ = "equipment"

    id = Column(Integer, primary_key=True, index=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(100), nullable=False) # RACKET, SHUTTLECOCK, SHOES, NET
    total_qty = Column(Integer, default=10)
    available_qty = Column(Integer, default=10)
    rental_price = Column(Float, default=20000)

    facility = relationship("Facility", back_populates="equipment")
    rental_items = relationship("RentalItem", back_populates="equipment")

# 8. RENTAL_ITEMS
class RentalItem(Base):
    __tablename__ = "rental_items"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=False)
    quantity = Column(Integer, default=1)
    price = Column(Float, nullable=False)

    booking = relationship("Booking", back_populates="rental_items")
    equipment = relationship("Equipment", back_populates="rental_items")

# 9. MATCHMAKING_ROOMS
class MatchmakingRoom(Base):
    __tablename__ = "matchmaking_rooms"

    id = Column(Integer, primary_key=True, index=True)
    host_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=False)
    title = Column(String(255), default="Giao lưu cầu lông vui vẻ")
    target_elo = Column(Integer, default=1200)
    current_players = Column(Integer, default=1)
    max_players = Column(Integer, default=4)
    play_date = Column(String(20), nullable=False)
    play_time = Column(String(50), nullable=False)
    status = Column(String(50), default="OPEN") # OPEN, FULL, CLOSED
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    host = relationship("User", back_populates="hosted_rooms")
    facility = relationship("Facility", back_populates="rooms")

# 10. PLAYER_PROFILES (Hồ sơ người chơi ELO & Kỹ năng)
class PlayerProfile(Base):
    __tablename__ = "player_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    gender = Column(String(20), default="Khác")
    birth_year = Column(Integer, nullable=True)
    preferred_area = Column(String(255), default="Cầu Giấy, Hà Nội")
    skill_level = Column(String(100), default="Trung Bình Khá")
    current_elo = Column(Integer, default=1200)
    games_played = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    rating_confidence = Column(Float, default=0.20)
    is_searching = Column(Boolean, default=False)
    available_time = Column(String(100), default="18:00 - 21:00")
    preferred_court = Column(String(255), nullable=True)
    play_style = Column(String(100), default="Công thủ toàn diện")
    streak = Column(String(50), default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# 11. MATCH_REQUESTS (Yêu cầu tìm trận của người chơi)
class MatchRequest(Base):
    __tablename__ = "match_requests"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    match_type = Column(String(50), default="SINGLES") # SINGLES (1v1), DOUBLES (2v2)
    preferred_date = Column(String(20), nullable=False)
    start_time = Column(String(10), nullable=False)
    end_time = Column(String(10), nullable=False)
    preferred_area = Column(String(255), nullable=False)
    min_elo = Column(Integer, default=1100)
    max_elo = Column(Integer, default=1300)
    status = Column(String(50), default="SEARCHING") # SEARCHING, MATCHED, CANCELLED, EXPIRED
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 12. MATCHES (Trận đấu đã được ghép cặp)
class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    court_id = Column(Integer, ForeignKey("courts.id"), nullable=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=True)
    match_type = Column(String(50), default="SINGLES") # SINGLES, DOUBLES
    start_time = Column(String(50), nullable=True)
    end_time = Column(String(50), nullable=True)
    match_date = Column(String(20), nullable=True)
    status = Column(String(50), default="SCHEDULED") # SCHEDULED, PLAYING, PENDING_CONFIRMATION, CONFIRMED, DISPUTED
    final_score = Column(String(100), nullable=True)
    winner_team = Column(String(10), nullable=True) # A, B
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 13. MATCH_PLAYERS (Thành viên tham gia trận đấu & kết quả cá nhân)
class MatchPlayer(Base):
    __tablename__ = "match_players"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    team = Column(String(10), default="A") # Team A, Team B
    elo_before = Column(Integer, nullable=False)
    elo_after = Column(Integer, nullable=True)
    elo_change = Column(Integer, default=0)
    score_claimed = Column(String(50), nullable=True)
    result = Column(String(20), default="PENDING") # WIN, LOSS, DRAW, PENDING
    confirmation_status = Column(String(50), default="PENDING") # PENDING, CONFIRMED, DISPUTED
    submitted_at = Column(DateTime(timezone=True), nullable=True)

# 14. ELO_HISTORIES (Sổ cái lịch sử biến động ELO)
class ELOHistory(Base):
    __tablename__ = "elo_histories"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=True)
    old_elo = Column(Integer, nullable=False)
    new_elo = Column(Integer, nullable=False)
    elo_change = Column(Integer, nullable=False)
    reason = Column(String(255), default="Match Result")
    opponent_info = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 15. MATCHMAKING_QUEUES (Hàng đợi tìm trận trực tiếp với Dynamic Range)
class MatchmakingQueue(Base):
    __tablename__ = "matchmaking_queues"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    match_request_id = Column(Integer, ForeignKey("match_requests.id"), nullable=True)
    current_range = Column(Integer, default=50) # 50 -> 100 -> 150 -> 200
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(50), default="WAITING") # WAITING, MATCHED, CANCELLED

