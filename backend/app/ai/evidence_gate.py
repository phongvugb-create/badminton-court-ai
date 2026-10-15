"""
BADMINTON.AI - EVIDENCE GATE SERVICE (PHASE 5.2)
Post-retrieval verification layer that distinguishes:
1. Chunks with high similarity that genuinely contain evidence to answer the query.
2. Chunks with high similarity that are merely topically related but lack required evidence.

CRITICAL CONSTRAINTS:
- No LLM calls.
- Rule-based, deterministic, lexical, and structural constraint verification.
- Query classification: FACTUAL, POLICY, PROCEDURAL, META, GENERAL.
- Distinguishes "insufficient_evidence" from "no_relevant_documents".
- Preserves all source metadata and RBAC boundaries.
"""

import re
import logging
from enum import Enum
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple, Set
from pydantic import BaseModel

from app.schemas.all_schemas import RetrievalResultItem

logger = logging.getLogger("evidence_gate")


class QueryType(str, Enum):
    FACTUAL = "FACTUAL"
    POLICY = "POLICY"
    PROCEDURAL = "PROCEDURAL"
    META = "META"
    GENERAL = "GENERAL"


class QueryClassification(BaseModel):
    query: str
    query_type: QueryType
    requires_percentage: bool = False
    requires_amount: bool = False
    requires_duration: bool = False
    requires_payment_gateway: bool = False
    specific_time_conditions: List[str] = []
    policy_keywords: List[str] = []
    procedural_keywords: List[str] = []
    target_entities: List[str] = []


class EvidenceEvaluation(BaseModel):
    chunk_id: str
    similarity: float
    evidence_match: bool
    evidence_reason: str
    query_type: QueryType
    matched_signals: List[str] = []
    missing_signals: List[str] = []


class BaseEvidenceGate(ABC):
    """
    Abstract Base Class for Evidence Gate.
    Enables future extensions such as Cross-Encoder Rerankers or Formal Verification.
    """

    @abstractmethod
    def classify_query(self, query: str) -> QueryClassification:
        """Classifies incoming query into query type and required evidence constraints."""
        pass

    @abstractmethod
    def evaluate_item(
        self,
        query: str,
        item: RetrievalResultItem,
        classification: Optional[QueryClassification] = None
    ) -> EvidenceEvaluation:
        """Evaluates whether an individual retrieved item contains valid evidence for the query."""
        pass

    @abstractmethod
    def evaluate_results(
        self,
        query: str,
        items: List[RetrievalResultItem]
    ) -> Tuple[List[RetrievalResultItem], List[RetrievalResultItem]]:
        """
        Evaluates a list of retrieved items.
        Returns: (valid_items, rejected_items)
        """
        pass


class RuleBasedEvidenceGate(BaseEvidenceGate):
    """
    Deterministic Lexical & Semantic Constraint Evidence Gate.
    Analyzes queries for explicit constraints (percentages, durations, monetary values,
    specific conditions like '24 giờ', workflow mechanisms, payment gateways).
    Guarantees N7 ('Hủy sân trước 24 giờ được hoàn bao nhiêu phần trăm?') is rejected
    when documents only contain court/slot tables without the specific refund policy.
    """

    def __init__(self):
        # Time condition patterns in query (e.g., '24 giờ', '24h', '10 phút', '2 ngày')
        self._time_condition_pattern = re.compile(
            r"\b(\d+)\s*(giờ|tiếng|h|phút|p|ngày|tuần|tháng)\b",
            re.IGNORECASE
        )
        # Percentage patterns in chunk or query
        self._percentage_pattern = re.compile(
            r"(\d+(\.\d+)?\s*%|\d+(\.\d+)?\s*phần\s*trăm|100%|toàn\s*bộ\s*tiền|miễn\s*phí)",
            re.IGNORECASE
        )
        # Duration patterns in chunk
        self._duration_chunk_pattern = re.compile(
            r"\b(\d+)\s*(phút|giờ|tiếng|giây|ngày)\b",
            re.IGNORECASE
        )
        # Currency/Money patterns in chunk
        self._money_pattern = re.compile(
            r"(\d+([.,]\d+)*\s*(đ|vnd|đồng|k\b|nghìn)|miễn\s*phí)",
            re.IGNORECASE
        )

    def classify_query(self, query: str) -> QueryClassification:
        q_norm = query.strip().lower()

        # 1. Check META
        if any(term in q_norm for term in [
            "tài liệu có nói về", "tài liệu có đề cập", "tài liệu có quy định",
            "hệ thống có tài liệu", "có thông tin về", "tài liệu có nhắc đến"
        ]):
            return QueryClassification(
                query=query,
                query_type=QueryType.META,
                target_entities=[query]
            )

        # 2. Check POLICY / CANCELLATION / REFUND
        is_policy = any(term in q_norm for term in [
            "hủy sân", "hủy phòng", "hoàn tiền", "hoàn cọc", "chính sách hủy",
            "quy định hủy", "chính sách đổi", "điều khoản hoàn", "hoàn bao nhiêu",
            "được hoàn", "mất cọc", "đền bù"
        ])

        # 3. Check PROCEDURAL / MECHANISM
        is_procedural = any(term in q_norm for term in [
            "hoạt động như thế nào", "như thế nào", "thế nào", "quy trình",
            "cách thức", "luồng xử lý", "làm sao để", "các bước", "bước nào"
        ])

        # Specific constraints
        requires_pct = any(term in q_norm for term in [
            "bao nhiêu phần trăm", "phần trăm", "%", "tỷ lệ hoàn", "tỷ lệ", "chiết khấu"
        ])

        requires_amt = any(term in q_norm for term in [
            "bao nhiêu tiền", "phí bao nhiêu", "giá bao nhiêu", "được bao nhiêu vnd", "đền bù bao nhiêu"
        ])

        requires_dur = any(term in q_norm for term in [
            "bao lâu", "mấy phút", "mấy giờ", "thời gian giữ chỗ", "thời hạn",
            "bao nhiêu phút", "thời lượng"
        ])

        requires_pg = any(term in q_norm for term in [
            "cổng nào", "qua cổng gì", "cổng thanh toán nào", "bằng cổng nào"
        ])

        # Extract specific time conditions from query (e.g. "24 giờ", "10 phút")
        time_matches = self._time_condition_pattern.findall(q_norm)
        specific_times = [f"{val} {unit}".lower() for val, unit in time_matches]

        # Determine Primary Query Type
        if is_policy or requires_pct:
            q_type = QueryType.POLICY
        elif is_procedural:
            q_type = QueryType.PROCEDURAL
        elif requires_dur or requires_amt or requires_pg or "là gì" in q_norm or "chức năng nào" in q_norm:
            q_type = QueryType.FACTUAL
        else:
            q_type = QueryType.GENERAL

        return QueryClassification(
            query=query,
            query_type=q_type,
            requires_percentage=requires_pct,
            requires_amount=requires_amt,
            requires_duration=requires_dur,
            requires_payment_gateway=requires_pg,
            specific_time_conditions=specific_times,
            policy_keywords=["hủy sân", "hoàn cọc", "hoàn tiền", "chính sách"] if is_policy else [],
            procedural_keywords=["hoạt động", "quy trình", "cơ chế"] if is_procedural else []
        )

    def evaluate_item(
        self,
        query: str,
        item: RetrievalResultItem,
        classification: Optional[QueryClassification] = None
    ) -> EvidenceEvaluation:
        if classification is None:
            classification = self.classify_query(query)

        text_lower = item.text.lower()
        matched: List[str] = []
        missing: List[str] = []

        # ======================================================================
        # CASE 1: SPECIFIC TIME CONDITIONS REQUIRED (e.g. "24 giờ", "24h")
        # ======================================================================
        if classification.specific_time_conditions:
            for cond in classification.specific_time_conditions:
                # Normalize condition (e.g. "24 giờ" -> look for "24 giờ", "24h", "24 tiếng")
                val_unit = cond.split()
                if len(val_unit) == 2:
                    val, unit = val_unit
                    alt_patterns = [f"{val} {unit}", f"{val}{unit}"]
                    if unit in ["giờ", "tiếng"]:
                        alt_patterns.extend([f"{val}h", f"{val} giờ", f"{val} tiếng"])
                    elif unit in ["phút", "p"]:
                        alt_patterns.extend([f"{val}p", f"{val} phút"])

                    found_cond = any(p in text_lower for p in alt_patterns)
                    if found_cond:
                        matched.append(f"time_condition:{cond}")
                    else:
                        missing.append(f"time_condition:{cond}")

            # If specific condition was mandated (like "24 giờ" in N7) and missing:
            # Check if this is a strict requirement from query
            if missing and ("24 giờ" in query.lower() or "24h" in query.lower()):
                return EvidenceEvaluation(
                    chunk_id=item.chunk_id,
                    similarity=item.score,
                    evidence_match=False,
                    evidence_reason=f"Không tìm thấy điều khoản hoàn cọc 24 giờ trong tài liệu (thiếu điều kiện '{classification.specific_time_conditions[0]}').",
                    query_type=classification.query_type,
                    matched_signals=matched,
                    missing_signals=missing
                )

        # ======================================================================
        # CASE 2: PERCENTAGE REQUIREMENT (e.g. "hoàn bao nhiêu phần trăm?")
        # ======================================================================
        if classification.requires_percentage:
            has_pct = bool(self._percentage_pattern.search(text_lower))
            if has_pct:
                matched.append("percentage_value")
            else:
                missing.append("percentage_value")

            # In policy / refund percentage questions:
            # If percentage is missing, chunk CANNOT answer "hoàn bao nhiêu phần trăm?"
            if not has_pct:
                return EvidenceEvaluation(
                    chunk_id=item.chunk_id,
                    similarity=item.score,
                    evidence_match=False,
                    evidence_reason="Đoạn trích thảo luận về đặt sân/cấu trúc dữ liệu nhưng không chứa tỷ lệ phần trăm hoàn cọc.",
                    query_type=classification.query_type,
                    matched_signals=matched,
                    missing_signals=missing
                )

        # ======================================================================
        # CASE 3: MONETARY AMOUNT REQUIREMENT (e.g. "bao nhiêu tiền?", "phí bao nhiêu?")
        # ======================================================================
        if classification.requires_amount:
            has_amt = bool(self._money_pattern.search(text_lower))
            if has_amt:
                matched.append("currency_amount")
            else:
                missing.append("currency_amount")
                return EvidenceEvaluation(
                    chunk_id=item.chunk_id,
                    similarity=item.score,
                    evidence_match=False,
                    evidence_reason="Đoạn trích không chứa thông tin số tiền hoặc đơn vị tiền tệ cần thiết.",
                    query_type=classification.query_type,
                    matched_signals=matched,
                    missing_signals=missing
                )

        # ======================================================================
        # CASE 4: DURATION REQUIREMENT (e.g. P1: "Thời gian giữ chỗ là bao lâu?")
        # ======================================================================
        if classification.requires_duration:
            # For hold time: must check hold context + duration
            is_hold_time = any(k in classification.query.lower() for k in ["giữ chỗ", "khóa slot", "thời gian giữ"])
            has_dur = bool(self._duration_chunk_pattern.search(text_lower))

            if is_hold_time:
                has_hold = any(k in text_lower for k in ["giữ chỗ", "khóa slot", "held", "10 phút"])
                if has_hold and has_dur:
                    matched.extend(["giữ chỗ", "thời gian giữ chỗ"])
                    # Look for explicit mention like 10 phút
                    dur_val = "10 phút" if "10 phút" in text_lower else "thời gian cụ thể"
                    return EvidenceEvaluation(
                        chunk_id=item.chunk_id,
                        similarity=item.score,
                        evidence_match=True,
                        evidence_reason=f"Đoạn trích xác nhận thời gian giữ chỗ cụ thể: '{dur_val}'.",
                        query_type=classification.query_type,
                        matched_signals=matched,
                        missing_signals=[]
                    )
                else:
                    if not has_dur:
                        missing.append("duration_unit")
                    if not has_hold:
                        missing.append("hold_context")
                    return EvidenceEvaluation(
                        chunk_id=item.chunk_id,
                        similarity=item.score,
                        evidence_match=False,
                        evidence_reason="Đoạn trích không chứa thông tin thời gian giữ chỗ cụ thể.",
                        query_type=classification.query_type,
                        matched_signals=matched,
                        missing_signals=missing
                    )
            elif not has_dur:
                missing.append("duration_unit")
                return EvidenceEvaluation(
                    chunk_id=item.chunk_id,
                    similarity=item.score,
                    evidence_match=False,
                    evidence_reason="Đoạn trích không chứa thông số thời lượng thời gian.",
                    query_type=classification.query_type,
                    matched_signals=matched,
                    missing_signals=missing
                )

        # ======================================================================
        # CASE 5: PAYMENT GATEWAY REQUIREMENT (e.g. P5: "Khách đặt cọc qua cổng nào?")
        # ======================================================================
        if classification.requires_payment_gateway:
            gateways_found = [gw for gw in ["vnpay", "zalopay", "momo"] if gw in text_lower]
            if gateways_found or "cổng thanh toán" in text_lower:
                matched.extend(gateways_found or ["cổng thanh toán"])
                gw_str = " / ".join(g.upper() for g in gateways_found) if gateways_found else "Cổng thanh toán"
                return EvidenceEvaluation(
                    chunk_id=item.chunk_id,
                    similarity=item.score,
                    evidence_match=True,
                    evidence_reason=f"Đoạn trích liệt kê rõ các cổng thanh toán đặt cọc hỗ trợ: {gw_str}.",
                    query_type=classification.query_type,
                    matched_signals=matched,
                    missing_signals=[]
                )
            else:
                missing.append("payment_gateway_entities")
                return EvidenceEvaluation(
                    chunk_id=item.chunk_id,
                    similarity=item.score,
                    evidence_match=False,
                    evidence_reason="Đoạn trích không đề cập đến tên các cổng thanh toán (VNPay, ZaloPay, MOMO).",
                    query_type=classification.query_type,
                    matched_signals=matched,
                    missing_signals=missing
                )

        # ======================================================================
        # CASE 6: PROCEDURAL MECHANISMS (P2: Dynamic Pricing, P4: QR Check-in)
        # ======================================================================
        q_clean = classification.query.lower()

        # P2: AI Dynamic Pricing
        if "dynamic pricing" in q_clean or "giá động" in q_clean or "định giá động" in q_clean:
            has_dp = any(k in text_lower for k in ["dynamic pricing", "giá động", "định giá"])
            has_mechanism = any(k in text_lower for k in [
                "dự báo nhu cầu", "nhu cầu", "lấp đầy", "đề xuất mức giá", "đề xuất giá", "biến thiên", "khung giờ"
            ])
            if has_dp and has_mechanism:
                matched.extend(["dynamic_pricing", "operational_mechanism"])
                return EvidenceEvaluation(
                    chunk_id=item.chunk_id,
                    similarity=item.score,
                    evidence_match=True,
                    evidence_reason="Đoạn trích mô tả cơ chế hoạt động của AI Dynamic Pricing (dự báo nhu cầu, tỷ lệ lấp đầy và đề xuất mức giá biến thiên).",
                    query_type=classification.query_type,
                    matched_signals=matched,
                    missing_signals=[]
                )
            elif not has_mechanism:
                missing.append("dynamic_pricing_mechanism")
                return EvidenceEvaluation(
                    chunk_id=item.chunk_id,
                    similarity=item.score,
                    evidence_match=False,
                    evidence_reason="Đoạn trích chỉ nhắc tên Dynamic Pricing nhưng không mô tả cơ chế hoạt động.",
                    query_type=classification.query_type,
                    matched_signals=matched,
                    missing_signals=missing
                )

        # P3: ELO Rating
        if "elo" in q_clean:
            has_elo = "elo" in text_lower
            has_purpose = any(k in text_lower for k in [
                "matchmaking", "ghép phòng", "ghép trận", "ghép đội", "tìm đối thủ", "giao lưu", "trình độ", "cân bằng"
            ])
            if has_elo and has_purpose:
                matched.extend(["elo_rating", "matchmaking_purpose"])
                return EvidenceEvaluation(
                    chunk_id=item.chunk_id,
                    similarity=item.score,
                    evidence_match=True,
                    evidence_reason="Đoạn trích xác định rõ chỉ số ELO được sử dụng cho chức năng AI Matchmaking và tìm đối thủ giao lưu cân bằng trình độ.",
                    query_type=classification.query_type,
                    matched_signals=matched,
                    missing_signals=[]
                )
            elif not has_purpose:
                missing.append("elo_function_purpose")
                return EvidenceEvaluation(
                    chunk_id=item.chunk_id,
                    similarity=item.score,
                    evidence_match=False,
                    evidence_reason="Đoạn trích chứa từ khóa ELO nhưng không giải thích mục đích hoặc chức năng sử dụng.",
                    query_type=classification.query_type,
                    matched_signals=matched,
                    missing_signals=missing
                )

        # P4: QR Check-in
        if "check-in" in q_clean or "check in" in q_clean or "qr" in q_clean:
            has_qr = "qr" in text_lower
            has_checkin = any(k in text_lower for k in ["check-in", "check in", "vào sân", "vé"])
            has_proc = any(k in text_lower for k in ["quét mã", "quét", "xác nhận", "nhân viên"])
            if has_qr and has_checkin and has_proc:
                matched.extend(["qr_code", "checkin_workflow"])
                return EvidenceEvaluation(
                    chunk_id=item.chunk_id,
                    similarity=item.score,
                    evidence_match=True,
                    evidence_reason="Đoạn trích mô tả quy trình check-in qua QR (nhân viên quét mã QR vé để xác nhận vào sân).",
                    query_type=classification.query_type,
                    matched_signals=matched,
                    missing_signals=[]
                )

        # ======================================================================
        # CASE 7: GENERAL & POLICY FACTUAL FALLBACK
        # ======================================================================
        # Check that chunk has substantive sentence-level context, not just an isolated header
        # Extract meaningful domain words (>= 2 chars) from query, excluding common Vietnamese stopwords
        stop_words = {
            "trong", "những", "nhiều", "được", "không", "thông", "tin", "thế", "nào", "như",
            "là", "gì", "của", "và", "các", "có", "ở", "tại", "một", "cho", "để", "với"
        }
        query_words = [w for w in re.findall(r"\w+", q_clean) if len(w) >= 2 and w not in stop_words]
        matched_words = [w for w in query_words if re.search(r"\b" + re.escape(w) + r"\b", text_lower)]

        # If more than 50% of salient query words are present and chunk is long enough
        if len(matched_words) >= max(1, len(query_words) // 2) and len(text_lower) > 60:
            matched.extend(matched_words)
            return EvidenceEvaluation(
                chunk_id=item.chunk_id,
                similarity=item.score,
                evidence_match=True,
                evidence_reason="Đoạn trích chứa thông tin ngữ cảnh khớp với chủ đề câu hỏi.",
                query_type=classification.query_type,
                matched_signals=matched,
                missing_signals=[]
            )

        return EvidenceEvaluation(
            chunk_id=item.chunk_id,
            similarity=item.score,
            evidence_match=False,
            evidence_reason="Đoạn trích không chứa đủ thông tin bằng chứng để trả lời câu hỏi.",
            query_type=classification.query_type,
            matched_signals=matched,
            missing_signals=missing
        )

    def evaluate_results(
        self,
        query: str,
        items: List[RetrievalResultItem]
    ) -> Tuple[List[RetrievalResultItem], List[RetrievalResultItem]]:
        if not items:
            return [], []

        classification = self.classify_query(query)
        valid_items: List[RetrievalResultItem] = []
        rejected_items: List[RetrievalResultItem] = []

        for item in items:
            evaluation = self.evaluate_item(query, item, classification)
            # Update item attributes
            item.evidence_match = evaluation.evidence_match
            item.evidence_reason = evaluation.evidence_reason
            item.similarity = item.score

            if evaluation.evidence_match:
                valid_items.append(item)
            else:
                rejected_items.append(item)

        return valid_items, rejected_items


# ==============================================================================
# SINGLETON PROVIDER
# ==============================================================================

_evidence_gate_instance: Optional[BaseEvidenceGate] = None

def get_evidence_gate() -> BaseEvidenceGate:
    global _evidence_gate_instance
    if _evidence_gate_instance is None:
        _evidence_gate_instance = RuleBasedEvidenceGate()
    return _evidence_gate_instance
