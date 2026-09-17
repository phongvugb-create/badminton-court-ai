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
