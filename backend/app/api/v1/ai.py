from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.schemas.all_schemas import (
    AIChatRequest,
    AIChatResponse,
    ConversationCreate,
    ConversationResponse,
    ConversationDetailResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    DocumentResponse,
    DocumentChunkResponse,
    DocumentIngestResponse,
    DocumentIngestTextRequest,
    EmbeddingJobResponse,
    EmbeddingTriggerRequest,
    RetrievalSearchRequest,
    RetrievalSearchResponse,
    SlotHoldConfirmRequest,
    SlotHoldConfirmResponse
)
from app.ai.tools.pending_hold_manager import execute_slot_hold
from app.ai.chatbot_service import get_chatbot_service
from app.ai.conversation_service import get_conversation_service
from app.ai.context_manager import get_context_manager
from app.ai.ingestion_service import get_ingestion_service
from app.ai.embedding_ingestion_service import get_embedding_ingestion_service
from app.ai.retrieval_service import get_retrieval_service
from app.api.v1.auth import get_current_user
from app.core.security import oauth2_scheme, decode_token
from app.core.database import get_db
from app.models.all_models import User

router = APIRouter(prefix="/ai", tags=["AI Assistant"])

async def get_optional_chat_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Tích hợp cơ chế xác thực linh hoạt:
    - Nếu có token: Kiểm tra tính hợp lệ bằng decode_token. Token sai -> 401 Unauthorized.
    - Nếu không gửi token: Cho phép trò chuyện với vai trò Guest.
    """
    if not token:
        return None

    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn"
        )

    try:
        user_id = int(payload.get("sub"))
        stmt = select(User).where(User.id == user_id)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Người dùng không tồn tại"
            )
        return user
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không đúng định dạng"
        )

# Alias for backward compatibility
get_chat_user = get_optional_chat_user


# =============================================================================
# CONVERSATION MANAGEMENT ENDPOINTS (PHASE 2)
# =============================================================================

@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Tạo cuộc hội thoại mới cho người dùng hiện tại.
    """
    conv_svc = get_conversation_service()
    conv = await conv_svc.create_conversation(
        db=db,
        user_id=current_user.id,
        title=payload.title
    )
    return conv


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy danh sách các cuộc hội thoại thuộc quyền sở hữu của người dùng hiện tại.
    """
    conv_svc = get_conversation_service()
    return await conv_svc.list_conversations(db=db, user_id=current_user.id)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation_detail(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy chi tiết cuộc hội thoại và lịch sử tin nhắn.
    Bảo mật: Từ chối 403 nếu hội thoại thuộc về user khác.
    """
    conv_svc = get_conversation_service()
    conv = await conv_svc.get_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
        load_messages=True
    )
    return conv


@router.post("/conversations/{conversation_id}/messages", response_model=AIChatResponse)
async def send_message_in_conversation(
    conversation_id: str,
    payload: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Gửi tin nhắn vào cuộc hội thoại cụ thể (Tuân thủ flow 8 bước):
    1. Authenticate user (qua dependency current_user)
    2. Validate conversation_id
    3. Kiểm tra conversation thuộc quyền sở hữu user (raise 403 nếu không phải)
    4. Load conversation history
    5. Lưu user message
    6. Gọi LLM với recent context
    7. Lưu assistant message
    8. Trả response
    """
    user_msg_content = (payload.message or "").strip()
    if not user_msg_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tin nhắn không được để trống"
        )

    conv_svc = get_conversation_service()
    context_mgr = get_context_manager()
    chatbot_svc = get_chatbot_service()

    # 2 & 3. Validate & Check ownership (403 nếu của user khác, 404 nếu không tồn tại)
    conv = await conv_svc.get_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
        load_messages=False
    )

    # 4. Load recent history
    db_messages = await conv_svc.get_recent_messages(db=db, conversation_id=conv.id, limit=10)
    history_for_llm = context_mgr.select_context_messages(db_messages)

    # 5. Lưu user message
    user_chat_msg = await conv_svc.add_message(
        db=db,
        conversation_id=conv.id,
        role="user",
        content=user_msg_content
    )

    user_info = {
        "id": current_user.id,
        "name": current_user.full_name,
        "phone": current_user.phone,
        "role": current_user.role,
        "elo_rating": current_user.elo_rating
    }

    # 6. Gọi RAG Chatbot Service
    result = await chatbot_svc.handle_message(
        message=user_msg_content,
        conversation_id=conv.id,
        history=history_for_llm,
        user_info=user_info,
        db=db,
        user_role=current_user.role
    )

    # 7. Lưu assistant message
    assistant_msg = await conv_svc.add_message(
        db=db,
        conversation_id=conv.id,
        role="assistant",
        content=result["answer"],
        msg_id=result.get("message_id")
    )

    # 8. Trả response
    return AIChatResponse(
        answer=result["answer"],
        reply=result["reply"],
        conversation_id=conv.id,
        message_id=assistant_msg.id,
        user_id=str(current_user.id),
        status=result["status"],
        retrieval_status=result.get("retrieval_status"),
        sources=result.get("sources", []),
        action_type=result.get("action_type"),
        pending_intent_id=result.get("pending_intent_id"),
        preview_data=result.get("preview_data"),
        hold_result=result.get("hold_result")
    )


# =============================================================================
# BACKWARD COMPATIBLE CHAT API (PHASE 1 + PHASE 2 MEMORY INTEGRATION)
# =============================================================================

@router.post("/chat", response_model=AIChatResponse)
async def chat_with_ai(
    req: AIChatRequest,
    current_user: Optional[User] = Depends(get_optional_chat_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Chat API (Tương thích ngược 100% với Phase 1, tích hợp Conversation Memory):
    - Nếu đã đăng nhập: Tự động khởi tạo/gắn vào conversation của user, kiểm tra ownership, lưu vết tin nhắn.
    - Nếu là khách vãng lai: Xử lý phản hồi nhanh mà không làm hỏng tính toàn vẹn của DB.
    """
    user_msg = (req.message or "").strip()
    if not user_msg:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tin nhắn không được để trống"
        )

    chatbot_svc = get_chatbot_service()
    conv_svc = get_conversation_service()
    context_mgr = get_context_manager()

    user_info = None
    history_for_llm = req.messages or []
    real_db = db if (db is not None and hasattr(db, "execute")) else None

    # TRƯỜNG HỢP 1: NGƯỜI DÙNG ĐÃ ĐĂNG NHẬP
    if current_user:
        user_info = {
            "id": current_user.id,
            "name": current_user.full_name,
            "phone": current_user.phone,
            "role": current_user.role,
            "elo_rating": current_user.elo_rating
        }

        session_to_use = real_db
        should_close_local = False
        if session_to_use is None:
            from app.core.database import AsyncSessionLocal
            session_to_use = AsyncSessionLocal()
            should_close_local = True

        try:
            # Lấy hoặc tạo cuộc hội thoại (kiểm tra chặt chẽ ownership)
            conv = await conv_svc.get_or_create_conversation(
                db=session_to_use,
                conversation_id=req.conversation_id,
                user_id=current_user.id
            )

            # Lấy tin nhắn gần nhất từ DB nếu client không tự truyền history
            if not history_for_llm:
                db_messages = await conv_svc.get_recent_messages(db=session_to_use, conversation_id=conv.id, limit=10)
                history_for_llm = context_mgr.select_context_messages(db_messages)

            # Lưu tin nhắn người dùng vào database
            await conv_svc.add_message(
                db=session_to_use,
                conversation_id=conv.id,
                role="user",
                content=user_msg
            )

            # Gọi RAG Chatbot Service
            result = await chatbot_svc.handle_message(
                message=user_msg,
                conversation_id=conv.id,
                context=req.context,
                history=history_for_llm,
                user_info=user_info,
                db=session_to_use,
                user_role=current_user.role,
                similarity_threshold=req.similarity_threshold
            )

            # Lưu tin nhắn phản hồi của trợ lý vào database
            assistant_msg = await conv_svc.add_message(
                db=session_to_use,
                conversation_id=conv.id,
                role="assistant",
                content=result["answer"],
                msg_id=result.get("message_id")
            )

            return AIChatResponse(
                answer=result["answer"],
                reply=result["reply"],
                conversation_id=conv.id,
                message_id=assistant_msg.id,
                user_id=str(current_user.id),
                status=result["status"],
                retrieval_status=result.get("retrieval_status"),
                sources=result.get("sources", []),
                action_type=result.get("action_type"),
                pending_intent_id=result.get("pending_intent_id"),
                preview_data=result.get("preview_data"),
                hold_result=result.get("hold_result")
            )
        finally:
            if should_close_local and session_to_use is not None:
                await session_to_use.close()

    # TRƯỜNG HỢP 2: KHÁCH VÃNG LAI (GUEST - PHASE 1 COMPATIBILITY)
    result = await chatbot_svc.handle_message(
        message=user_msg,
        conversation_id=req.conversation_id,
        context=req.context,
        history=history_for_llm,
        user_info=None,
        db=real_db,
        user_role="GUEST",
        similarity_threshold=req.similarity_threshold
    )

    return AIChatResponse(
        answer=result["answer"],
        reply=result["reply"],
        conversation_id=result["conversation_id"],
        message_id=result["message_id"],
        user_id=None,
        status=result["status"],
        retrieval_status=result.get("retrieval_status"),
        sources=result.get("sources", []),
        action_type=result.get("action_type"),
        pending_intent_id=result.get("pending_intent_id"),
        preview_data=result.get("preview_data"),
        hold_result=result.get("hold_result")
    )


@router.post("/hold-confirm", response_model=SlotHoldConfirmResponse)
async def ai_confirm_hold_slot(
    req: SlotHoldConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Explicit confirmation endpoint to execute slot hold via AI Assistant workflow (Phase 7.2).
    """
    res = await execute_slot_hold(db=db, user_id=current_user.id, intent_id=req.intent_id)
    if res["status"] == "hold_succeeded":
        return SlotHoldConfirmResponse(
            status="hold_succeeded",
            message=res["message"],
            data=res["data"]
        )
    elif res["status"] == "pending_intent_expired":
        raise HTTPException(status_code=410, detail=res["message"])
    elif res["status"] == "slot_unavailable":
        raise HTTPException(status_code=409, detail=res["message"])
    elif res["status"] == "availability_unverified":
        raise HTTPException(status_code=503, detail=res["message"])
    else:
        raise HTTPException(status_code=400, detail=res["message"])


# =============================================================================
# PHASE 3: DOCUMENT INGESTION PIPELINE ENDPOINTS
# =============================================================================

@router.post("/documents/ingest-text", response_model=DocumentIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_document_text(
    payload: DocumentIngestTextRequest,
    current_user: Optional[User] = Depends(get_optional_chat_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Nạp tài liệu dạng văn bản trực tiếp (Text/Markdown) vào kho tri thức RAG.
    """
    svc = get_ingestion_service()
    user_id = current_user.id if current_user else None

    try:
        res = await svc.ingest_text(
            db=db,
            text_content=payload.content,
            title=payload.title,
            filename=payload.filename or "manual_input.txt",
            source_type=payload.source_type or "policy",
            access_scope=payload.access_scope or "public",
            owner_id=user_id,
            reingest=payload.reingest or False
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Lỗi khi xử lý tài liệu: {str(e)}")


@router.post("/documents/upload", response_model=DocumentIngestResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    source_type: Optional[str] = Form("policy"),
    access_scope: Optional[str] = Form("public"),
    reingest: Optional[bool] = Form(False),
    current_user: Optional[User] = Depends(get_optional_chat_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Tải lên tệp tài liệu (.txt, .md, .docx, .pdf) và thực thi pipeline bóc tách, chuẩn hóa, phân đoạn (chunks).
    """
    svc = get_ingestion_service()
    user_id = current_user.id if current_user else None

    content_bytes = await file.read()
    if not content_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tệp rỗng hoặc không có dữ liệu")

    doc_title = title or file.filename

    try:
        res = await svc.ingest_file(
            db=db,
            content_bytes=content_bytes,
            filename=file.filename,
            title=doc_title,
            source_type=source_type or "policy",
            access_scope=access_scope or "public",
            owner_id=user_id,
            reingest=reingest or False
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Lỗi khi nạp tệp: {str(e)}")


@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    access_scope: Optional[str] = None,
    current_user: Optional[User] = Depends(get_optional_chat_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Xem danh mục các tài liệu đã nạp vào hệ thống có áp dụng Access Control.
    """
    svc = get_ingestion_service()
    user_role = current_user.role if current_user else "CUSTOMER"
    user_id = current_user.id if current_user else None

    docs = await svc.list_documents(
        db=db,
        user_role=user_role,
        user_id=user_id,
        access_scope_filter=access_scope
    )
    return docs


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: Optional[User] = Depends(get_optional_chat_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Xem chi tiết thông tin metadata của một tài liệu.
    """
    svc = get_ingestion_service()
    user_role = current_user.role if current_user else "CUSTOMER"
    user_id = current_user.id if current_user else None

    doc = await svc.get_document(db, document_id=document_id, user_role=user_role, user_id=user_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tài liệu không tồn tại hoặc bạn không có quyền truy cập")
    return doc


@router.get("/documents/{document_id}/chunks", response_model=List[DocumentChunkResponse])
async def get_document_chunks(
    document_id: str,
    current_user: Optional[User] = Depends(get_optional_chat_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Trích xuất toàn bộ các chunks của tài liệu phục vụ kiểm định chất lượng và chuẩn bị cho Phase 4 Embedding.
    """
    svc = get_ingestion_service()
    user_role = current_user.role if current_user else "CUSTOMER"
    user_id = current_user.id if current_user else None

    chunks = await svc.get_document_chunks(db, document_id=document_id, user_role=user_role, user_id=user_id)
    if not chunks:
        doc = await svc.get_document(db, document_id=document_id, user_role=user_role, user_id=user_id)
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tài liệu không tồn tại hoặc bạn không có quyền truy cập")
        return []
    return chunks


# =============================================================================
# PHASE 4: EMBEDDING & VECTOR DATABASE ENDPOINTS
# =============================================================================

@router.post("/documents/{document_id}/embed", response_model=EmbeddingJobResponse)
async def trigger_document_embedding(
    document_id: str,
    payload: Optional[EmbeddingTriggerRequest] = None,
    current_user: Optional[User] = Depends(get_optional_chat_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Kích hoạt tiến trình tạo Vector Embeddings cho một tài liệu cụ thể.
    Yêu cầu vai trò ADMIN hoặc STAFF (hoặc chủ sở hữu tài liệu).
    """
    user_role = current_user.role if current_user else "CUSTOMER"
    user_id = current_user.id if current_user else None

    # Access check: Chỉ Admin, Staff hoặc chủ sở hữu tài liệu mới được kích hoạt embedding
    ingest_svc = get_ingestion_service()
    doc = await ingest_svc.get_document(db, document_id=document_id, user_role=user_role, user_id=user_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tài liệu không tồn tại hoặc bạn không có quyền thao tác")

    if user_role not in ["ADMIN", "STAFF"] and (doc.owner_id != user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chỉ Quản trị viên, Nhân viên hoặc Chủ tài liệu mới có quyền kích hoạt Vectorization")

    force_reembed = payload.force_reembed if payload else False
    batch_size = payload.batch_size if payload and payload.batch_size else 20

    embed_svc = get_embedding_ingestion_service()
    try:
        report = await embed_svc.embed_document_chunks(
            db=db,
            document_id=document_id,
            force_reembed=force_reembed,
            batch_size=batch_size
        )
        return report
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Lỗi xử lý embedding: {str(e)}")


@router.post("/documents/embed-all", response_model=List[EmbeddingJobResponse])
async def trigger_embed_all_documents(
    payload: Optional[EmbeddingTriggerRequest] = None,
    current_user: Optional[User] = Depends(get_optional_chat_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Kích hoạt tiến trình tạo Vector Embeddings hàng loạt cho tất cả tài liệu READY.
    Chỉ dành riêng cho ADMIN.
    """
    user_role = current_user.role if current_user else "CUSTOMER"
    if user_role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chỉ Quản trị viên (ADMIN) mới có quyền kích hoạt embedding toàn hệ thống")

    force_reembed = payload.force_reembed if payload else False
    batch_size = payload.batch_size if payload and payload.batch_size else 20

    embed_svc = get_embedding_ingestion_service()
    try:
        reports = await embed_svc.embed_all_pending_chunks(
            db=db,
            force_reembed=force_reembed,
            batch_size=batch_size
        )
        return reports
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Lỗi xử lý batch embedding: {str(e)}")


@router.get("/documents/{document_id}/embedding-status")
async def get_document_embedding_status(
    document_id: str,
    current_user: Optional[User] = Depends(get_optional_chat_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Kiểm tra trạng thái vector hóa của một tài liệu (tổng chunk, số chunk đã có vector, model).
    """
    ingest_svc = get_ingestion_service()
    user_role = current_user.role if current_user else "CUSTOMER"
    user_id = current_user.id if current_user else None

    doc = await ingest_svc.get_document(db, document_id=document_id, user_role=user_role, user_id=user_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tài liệu không tồn tại hoặc bạn không có quyền truy cập")

    chunks = await ingest_svc.get_document_chunks(db, document_id=document_id, user_role=user_role, user_id=user_id)
    total_chunks = len(chunks)
    embedded_chunks = sum(1 for c in chunks if c.embedding is not None)

    active_models = list({c.embedding_model for c in chunks if c.embedding_model})

    return {
        "document_id": document_id,
        "title": doc.title,
        "status": doc.status,
        "total_chunks": total_chunks,
        "embedded_chunks": embedded_chunks,
        "pending_chunks": total_chunks - embedded_chunks,
        "is_fully_embedded": (total_chunks > 0 and embedded_chunks == total_chunks),
        "embedding_models": active_models
    }


# =============================================================================
# PHASE 5: RETRIEVAL & VECTOR SEARCH ENDPOINTS
# =============================================================================

@router.post("/retrieval/search", response_model=RetrievalSearchResponse)
async def search_retrieval(
    payload: RetrievalSearchRequest,
    current_user: Optional[User] = Depends(get_optional_chat_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Tìm kiếm vector tương đồng (Phase 5 Retrieval Layer).
    Tích hợp RBAC Access Control, exact cosine distance/similarity, metadata traceability.
    KHÔNG sinh câu trả lời bằng LLM.
    """
    retriever = get_retrieval_service()
    user_context = None
    if current_user:
        user_context = {
            "user_id": current_user.id,
            "role": current_user.role
        }

    try:
        response = await retriever.retrieve(
            db=db,
            query=payload.query,
            user_context=user_context,
            top_k=payload.top_k,
            similarity_threshold=payload.similarity_threshold,
            apply_evidence_gate=payload.apply_evidence_gate
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi truy vấn vector retrieval: {str(e)}"
        )

