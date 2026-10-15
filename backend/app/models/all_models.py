from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, Enum, Index
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum
import json

try:
    from pgvector.sqlalchemy import Vector
    _HAS_PGVECTOR = True
except ImportError:
    _HAS_PGVECTOR = False

class VectorType(TypeDecorator):
    """
    Dialect-aware Vector column:
    - On PostgreSQL: maps to native pgvector VECTOR(dim) if pgvector is installed.
    - On SQLite: maps to TEXT with JSON serialization of float vectors.
    """
    impl = Text
    cache_ok = True
    comparator_factory = Vector.comparator_factory if _HAS_PGVECTOR else None

    def __init__(self, dim: int = 768, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dim = dim

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql" and _HAS_PGVECTOR:
            return dialect.type_descriptor(Vector(self.dim))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql" and _HAS_PGVECTOR:
            return value
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                if value.startswith("[") and value.endswith("]"):
                    return json.loads(value)
            except Exception:
                pass
        return value

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

class TransactionStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    REQUIRES_RECONCILIATION = "REQUIRES_RECONCILIATION"

class RoomStatus(str, enum.Enum):
    OPEN = "OPEN"
    FULL = "FULL"
    CLOSED = "CLOSED"

# 1. USERS
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column("name", String(255), nullable=False)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    email = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="CUSTOMER", nullable=False)
    elo_rating = Column(Integer, default=1000)
    is_approved = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    @property
    def name(self):
        return self.full_name

    @name.setter
    def name(self, value):
        self.full_name = value

    facilities = relationship("Facility", back_populates="owner")
    bookings = relationship("Booking", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    hosted_rooms = relationship("MatchmakingRoom", back_populates="host")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="owner")

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
    idempotency_key = Column(String(100), unique=True, index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="bookings")
    slot = relationship("TimeSlot", back_populates="bookings")
    rental_items = relationship("RentalItem", back_populates="booking", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="booking", cascade="all, delete-orphan")

# 6.1. PAYMENTS (Phase 7.4A)
class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String(50), nullable=False) # SANDBOX, VNPAY, MOMO, ZALOPAY
    transaction_id = Column(String(100), unique=True, index=True, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="VND")
    payment_type = Column(String(50), default="DEPOSIT") # DEPOSIT, FULL
    status = Column(String(50), default="PENDING", index=True) # PENDING, SUCCESS, FAILED, EXPIRED, CANCELLED, REQUIRES_RECONCILIATION
    idempotency_key = Column(String(100), unique=True, index=True, nullable=True)
    provider_response = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    booking = relationship("Booking", back_populates="payments")
    user = relationship("User", back_populates="payments")

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


# 16. CONVERSATIONS (Quản lý cuộc hội thoại AI)
class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), default="Cuộc trò chuyện mới")
    status = Column(String(50), default="ACTIVE") # ACTIVE, ARCHIVED
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="conversations")
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="ChatMessage.created_at")


# 17. CHAT_MESSAGES (Lưu trữ tin nhắn người dùng và trợ lý)
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(64), primary_key=True, index=True)
    conversation_id = Column(String(64), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False) # user, assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        Index("ix_chat_messages_conv_created", "conversation_id", "created_at"),
    )


# 18. DOCUMENTS (Quản lý tài liệu tri thức tĩnh phục vụ RAG)
class Document(Base):
    __tablename__ = "documents"

    id = Column(String(64), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    source_type = Column(String(50), default="policy", nullable=False) # policy, manual, faq, srs, file_upload
    mime_type = Column(String(100), default="text/plain", nullable=False)
    storage_path = Column(String(500), nullable=True)
    checksum = Column(String(64), nullable=False, index=True)
    version = Column(Integer, default=1)
    status = Column(String(32), default="PENDING", index=True) # PENDING, PROCESSING, READY, FAILED
    error_message = Column(Text, nullable=True)
    total_chunks = Column(Integer, default=0)
    access_scope = Column(String(50), default="public") # public, internal, admin
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan", order_by="DocumentChunk.chunk_index")


# 19. DOCUMENT_CHUNKS (Lưu trữ các phân đoạn văn bản phục vụ RAG)
class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(64), primary_key=True, index=True)
    document_id = Column(String(64), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    section = Column(String(255), nullable=True)
    meta_info = Column(Text, nullable=True) # JSON string chứa metadata mở rộng
    token_estimate = Column(Integer, default=0)

    # Cột Vector nhúng & Metadata phục vụ RAG Retrieval (Phase 4 & Phase 4.1)
    embedding = Column(VectorType(dim=768), nullable=True)
    embedding_model = Column(String(64), nullable=True) # e.g. gemini-embedding-2 / text-embedding-004
    embedding_dimension = Column(Integer, nullable=True) # e.g. 768
    embedding_version = Column(String(32), nullable=True) # e.g. v1
    embedded_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("ix_document_chunks_doc_idx", "document_id", "chunk_index"),
        Index("ix_document_chunks_embedded", "document_id", "embedding_model"),
    )

