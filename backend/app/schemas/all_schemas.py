from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# AUTH SCHEMAS
class UserRegister(BaseModel):
    phone: str
    password: str
    full_name: str
    email: Optional[str] = None
    role: str = "CUSTOMER"

class UserLogin(BaseModel):
    phone: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=128)

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

class SlotHoldConfirmRequest(BaseModel):
    intent_id: str

class SlotHoldConfirmResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None

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
    equipment_ids: Optional[List[int]] = Field(default_factory=list)

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

class BookingPreviewRequest(BaseModel):
    slot_id: int
    equipment_ids: Optional[List[int]] = Field(default_factory=list)

class BookingPreviewData(BaseModel):
    booking_intent_id: str
    slot_id: int
    facility_id: int
    facility_name: str
    court_id: int
    court_number: str
    date: str
    start_time: str
    end_time: str
    court_price: float
    equipment_total: float
    total_amount: float
    deposit_amount: float
    expires_at: float

class BookingPreviewResponse(BaseModel):
    status: str
    message: str
    data: Optional[BookingPreviewData] = None

class BookingConfirmRequest(BaseModel):
    booking_intent_id: str
    idempotency_key: Optional[str] = None

class BookingConfirmData(BaseModel):
    booking_id: int
    slot_id: int
    facility_name: Optional[str] = ""
    court_number: Optional[str] = ""
    date: Optional[str] = ""
    start_time: Optional[str] = ""
    end_time: Optional[str] = ""
    total_amount: float
    deposit_amount: float
    payment_status: str

class BookingConfirmResponse(BaseModel):
    status: str
    is_idempotent: Optional[bool] = False
    message: str
    data: Optional[BookingConfirmData] = None


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
    conversation_id: Optional[str] = None
    context: Optional[str] = ""
    messages: Optional[List[Dict[str, Any]]] = None
    similarity_threshold: Optional[float] = None

class RAGSourceCitation(BaseModel):
    document_id: str
    chunk_id: str
    filename: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    similarity: Optional[float] = None
    evidence_match: Optional[bool] = None

class AIChatResponse(BaseModel):
    answer: str
    reply: Optional[str] = None
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    user_id: Optional[str] = None
    status: Optional[str] = "success"
    retrieval_status: Optional[str] = None # supported, no_relevant_documents, insufficient_evidence
    sources: Optional[List[RAGSourceCitation]] = Field(default_factory=list)
    action_type: Optional[str] = None # slot_hold_preview, slot_hold_confirmed, slot_hold_failed
    pending_intent_id: Optional[str] = None
    preview_data: Optional[Dict[str, Any]] = None
    hold_result: Optional[Dict[str, Any]] = None

class ChatMessageCreate(BaseModel):
    message: str

class ChatMessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ConversationCreate(BaseModel):
    title: Optional[str] = "Cuộc trò chuyện mới"

class ConversationResponse(BaseModel):
    id: str
    user_id: int
    title: str
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ConversationDetailResponse(BaseModel):
    id: str
    user_id: int
    title: str
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    messages: List[ChatMessageResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True

# =============================================================================
# RE-ARCHITECTED AI MATCHMAKING & ELO SCHEMAS
# =============================================================================
class PlayerProfileCreateOrUpdate(BaseModel):
    gender: Optional[str] = None
    birth_year: Optional[int] = None
    preferred_area: Optional[str] = None
    skill_level: Optional[str] = None
    selected_tier: Optional[int] = Field(default=None, ge=1, le=7)
    available_time: Optional[str] = None
    preferred_court: Optional[str] = None
    play_style: Optional[str] = None
    is_searching: Optional[bool] = None

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
    max_elo_delta: Optional[int] = Field(default=100, ge=0, le=200)
    wait_time_seconds: Optional[int] = Field(default=0, ge=0, le=86400)

class MatchCandidate(BaseModel):
    candidate_id: int
    candidate_name: str
    candidate_tier: str
    match_score: float
    sub_scores: dict
    is_recommended: bool

class MatchFindResponse(BaseModel):
    player_elo: int
    player_tier: str
    dynamic_elo_range: int
    wait_time_seconds: int
    total_candidates: int
    candidates: List[MatchCandidate]
    ai_recommendation: dict
    matching_tier: Optional[str] = None

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


# =============================================================================
# PHASE 3: RAG DOCUMENT INGESTION SCHEMAS
# =============================================================================

class DocumentChunkResponse(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    text: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    meta_info: Optional[str] = None
    token_estimate: Optional[int] = 0
    embedding_model: Optional[str] = None
    embedding_dimension: Optional[int] = None
    embedding_version: Optional[str] = None
    embedded_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class EmbeddingJobResponse(BaseModel):
    document_id: str
    total_chunks: int
    embedded_chunks: int
    skipped_chunks: int
    failed_chunks: int
    embedding_model: str
    embedding_dimension: int
    embedding_version: Optional[str] = "v1"
    elapsed_seconds: float
    status: str
    message: str

class EmbeddingTriggerRequest(BaseModel):
    force_reembed: Optional[bool] = False
    batch_size: Optional[int] = 20

class DocumentResponse(BaseModel):
    id: str
    title: str
    filename: str
    source_type: str
    mime_type: str
    storage_path: Optional[str] = None
    checksum: str
    version: int
    status: str
    error_message: Optional[str] = None
    total_chunks: int
    access_scope: str
    owner_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DocumentIngestResponse(BaseModel):
    document_id: str
    title: str
    filename: str
    status: str
    checksum: str
    version: int
    total_chunks: int
    is_duplicate: bool
    access_scope: str
    message: str

class DocumentIngestTextRequest(BaseModel):
    title: str
    content: str
    filename: Optional[str] = "manual_input.txt"
    source_type: Optional[str] = "policy"
    access_scope: Optional[str] = "public"
    reingest: Optional[bool] = False

# ==============================================================================
# RETRIEVAL SCHEMAS (PHASE 5)
# ==============================================================================

class RetrievalSearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = None
    similarity_threshold: Optional[float] = None
    apply_evidence_gate: Optional[bool] = True

class RetrievalResultItem(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    score: float # Cosine similarity = 1 - cosine_distance
    distance: float # Cosine distance
    similarity: Optional[float] = None # Alias for score (Phase 5.2)
    filename: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    source_type: Optional[str] = None
    access_scope: Optional[str] = None
    evidence_match: Optional[bool] = None # Phase 5.2 Evidence Gate match
    evidence_reason: Optional[str] = None # Phase 5.2 Evidence Gate explanation

class RetrievalSearchResponse(BaseModel):
    query: str
    total_candidates: int
    returned_results: int
    top_k: int
    similarity_threshold: float
    results: List[RetrievalResultItem]
    reason: Optional[str] = None
    latency_ms: Optional[Dict[str, float]] = None


# ==============================================================================
# PAYMENT SCHEMAS (PHASE 7.4A)
# ==============================================================================

class PaymentInitiateRequest(BaseModel):
    booking_id: int
    provider: Optional[str] = "SANDBOX"
    payment_type: Optional[str] = "DEPOSIT"
    idempotency_key: Optional[str] = None

class PaymentResponse(BaseModel):
    id: int
    booking_id: int
    user_id: int
    provider: str
    transaction_id: str
    amount: float
    currency: str
    payment_type: str
    status: str
    created_at: Optional[Any] = None

    class Config:
        from_attributes = True

class PaymentSandboxSimulateRequest(BaseModel):
    booking_id: int
    outcome: str = "SUCCESS" # SUCCESS, FAILED, TIMEOUT, MISMATCH_AMOUNT, MISMATCH_CURRENCY
    custom_amount: Optional[float] = None
    custom_currency: Optional[str] = None
    idempotency_key: Optional[str] = None

class PaymentSandboxSimulateResponse(BaseModel):
    status: str
    is_idempotent: Optional[bool] = False
    message: str
    data: Optional[Dict[str, Any]] = None

class PaymentWebhookPayload(BaseModel):
    provider: str
    transaction_id: str
    booking_id: int
    amount: float
    currency: str = "VND"
    status: str
    signature: str


class MoMoIPNPayload(BaseModel):
    partnerCode: str
    orderId: str
    requestId: str
    amount: int
    orderInfo: Optional[str] = ""
    orderType: Optional[str] = ""
    transId: Optional[Any] = None
    resultCode: int
    message: Optional[str] = ""
    payType: Optional[str] = ""
    responseTime: Optional[Any] = None
    extraData: Optional[str] = ""
    signature: str
    accessKey: Optional[str] = None


