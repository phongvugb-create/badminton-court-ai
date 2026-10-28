"""Read-only answers from the website's public catalogue, independent of the LLM.

Prices are catalogue prices, not quotes or claims of real-time stock. Never pass
the full central dataset (users, payments, messages) to a language model.
"""
import asyncio
import math
import re
import unicodedata
import sys
from pathlib import Path
from typing import Optional


def normalize(value):
    text = unicodedata.normalize("NFD", str(value).lower().replace("đ", "d"))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", "".join(c for c in text if not unicodedata.combining(c))).split())


def load_catalog():
    # Use the same persistence manager as /api/database, not client-supplied context.
    root = str(Path(__file__).resolve().parents[3])
    if root not in sys.path:
        sys.path.append(root)
    from db_engine import db_manager
    return db_manager.load_data()


ITEMS = {
    "vot": "vợt", "yonex": "vợt", "victor": "vợt", "lining": "vợt",
    "li ning": "vợt", "kumpoo": "vợt", "astrox": "vợt", "nanoflare": "vợt",
    "arcsaber": "vợt", "ryuga": "vợt", "axforce": "vợt",
    "nuoc": "nước", "pocari": "nước", "cau long": "cầu", "ong cau": "cầu",
    "hop cau": "cầu", "dung cu": "", "thiet bi": "", "do thue": "",
}
BRANDS = ("yonex", "victor", "li ning", "lining", "kumpoo", "astrox", "nanoflare", "arcsaber", "ryuga", "axforce", "pocari")


def equipment_intent(message):
    q = normalize(message)
    if re.search(r"\b(cach|quy trinh|huong dan|chinh sach|quy dinh|lam sao|nhu the nao|hu hong|boi thuong|hoan|huy)\b", q):
        return False  # policy/workflow questions belong to RAG
    has_item = any(re.search(r"\b" + re.escape(k) + r"\b", q) for k in ITEMS if k != "cau long")
    wants_catalog = bool(re.search(r"\b(gia|bao nhieu|may tien|thue|mua|ban|co|loai|danh sach|con|ton kho)\b", q))
    return has_item and wants_catalog


def resolve_followup(message, history):
    """Only use a recent user's question; never website context or bot output."""
    q = normalize(message)
    if len(q.split()) > 12 or not re.match(r"^(con |loai |gia |bao nhieu|o |tai |ben |cai |vot |yonex|victor|kumpoo)", q):
        return message
    if equipment_intent(message):
        return message
    for item in reversed((history or [])[-8:]):
        if item.get("role", item.get("sender")) not in ("user", "customer"):
            continue
        previous = str(item.get("content") or item.get("text") or item.get("message") or "")
        if normalize(previous) == q:
            continue  # browser includes the current user message
        if equipment_intent(previous):
            return f"{previous} {message}"
        break  # no resurrection of an old topic after a new one
    return message


def _response(answer, status="success", retrieval="supported"):
    return {"answer": answer, "reply": answer, "status": status,
            "retrieval_status": retrieval, "sources": [], "provider": "catalog"}


def _named_facilities(query, facilities):
    ignored = {"san", "cau", "long", "clb", "club", "badminton", "arena", "center", "sport", "sports", "minh", "thue", "quan", "huyen"}
    names = {fid: [w for w in normalize(f.get("name", "")).split() if w not in ignored]
             for fid, f in facilities.items()}
    matches = []
    for fid, words in names.items():
        phrases = [" ".join(words[i:i+2]) for i in range(len(words)-1)]
        unique = [w for w in words if len(w) >= 5 and w not in BRANDS and sum(w in others for others in names.values()) == 1]
        if any(re.search(r"\b" + re.escape(term) + r"\b", query) for term in phrases + unique):
            matches.append(fid)
    return matches


def answer_equipment(message, data):
    q = normalize(message)
    facilities = {str(f.get("id")): f for f in data.get("facilities", [])
                  if isinstance(f, dict) and f.get("is_approved") in (True, 1)}
    # Match distinctive names in the question, not addresses with common words.
    named = _named_facilities(q, facilities)
    explicit_id = re.search(r"\b(?:co so|facility id)\s+(\d+)\b", q)
    if explicit_id:
        named = [explicit_id.group(1)]
    location = re.search(r"\b(?:o|tai)\s+(.+)$", q)
    if location and not named:
        key = location.group(1).removesuffix(" khong").strip()
        named = [fid for fid, f in facilities.items() if key in normalize(f.get("name", "") + " " + f.get("address", ""))]
        if not named:
            return _response("Tôi chưa xác định được cơ sở bạn hỏi. Bạn cho biết tên cụm sân hoặc địa chỉ cụ thể nhé.", "clarification_required", "no_results")
    brand_terms = [b for b in BRANDS if re.search(r"\b" + re.escape(b) + r"\b", q)]
    model_terms = re.findall(r"\b(?:\d{2,3}[a-z]|[a-z]\d{3})\b", q)
    category = next((v for k, v in ITEMS.items() if re.search(r"\b" + re.escape(k) + r"\b", q)), "")
    matches = []
    for row in data.get("equipments", []):
        if not isinstance(row, dict):
            continue
        fid = str(row.get("facility_id"))
        if fid not in facilities or (named and fid not in named):
            continue
        name = normalize(row.get("name", ""))
        if model_terms and not all(re.search(r"\b" + m + r"\b", name) for m in model_terms):
            continue
        if brand_terms and not all(b.replace("lining", "li ning") in name or b in name for b in brand_terms):
            continue
        if not brand_terms and category and normalize(category) not in name:
            continue
        matches.append((row, facilities[fid]))
    if not matches:
        return _response("Danh mục hiện tại chưa có dụng cụ phù hợp với câu hỏi này. Bạn cho biết tên vợt/dụng cụ và cơ sở muốn thuê để tôi tra cứu chính xác hơn nhé.", retrieval="no_results")
    lines = ["**Giá dụng cụ trong danh mục hệ thống:**"]
    for row, facility in matches[:20]:
        price = row.get("price")
        unit = row.get("unit")
        if price is None:
            price = row.get("price_per_slot")
            unit = unit or "khung giờ"
        try:
            amount = float(price)
            if not math.isfinite(amount) or amount < 0:
                raise ValueError()
            label = f"{amount:,.0f}".replace(",", ".") + "đ"
        except (TypeError, ValueError):
            label = "Chưa cập nhật giá"
        lines.append(f"- **{row.get('name', 'Dụng cụ')}**: {label}" + (f"/{unit}" if unit else " (chưa có đơn vị tính)") + f" — {facility.get('name', 'Cơ sở')}")
    if len(matches) > 20:
        lines.append("Danh sách còn tiếp; bạn cho biết cơ sở hoặc loại dụng cụ để thu hẹp kết quả.")
    lines.append("\nNguồn: danh mục dụng cụ của hệ thống. Giá theo từng cơ sở và đơn vị niêm yết; số lượng còn cho thuê cần xác nhận khi đặt.")
    return _response("\n".join(lines))


def facility_intent(message):
    q = normalize(message)
    return bool(re.search(r"\b(mo cua|dong cua|gio hoat dong|dia chi|so dien thoai|hotline|tien ich|bao nhieu san)\b", q)) and not re.search(r"\b(cach|thay doi|cap nhat|chinh sua)\b", q)


def answer_facility(message, data):
    q = normalize(message)
    facilities = [f for f in data.get("facilities", []) if isinstance(f, dict) and f.get("is_approved") in (True, 1)]
    by_id = {str(f.get("id")): f for f in facilities}
    matches = [by_id[fid] for fid in _named_facilities(q, by_id)]
    if not matches:
        return _response("Bạn muốn xem thông tin của cụm sân nào? Bạn cho biết tên cụm sân hoặc địa chỉ để tôi tra cứu nhé.", "clarification_required", "no_results")
    lines = ["**Thông tin cơ sở trong hệ thống:**"]
    for f in matches[:10]:
        lines.append(f"\n**{f.get('name', 'Cơ sở')}**")
        lines.append(f"- Địa chỉ: {f.get('address') or 'Chưa cập nhật'}")
        hours = f.get("open_hours") or (f"{f['open_time']} – {f['close_time']}" if f.get("open_time") and f.get("close_time") else "Chưa cập nhật")
        lines.append(f"- Giờ mở cửa: {hours}")
        if "so dien thoai" in q or "hotline" in q:
            lines.append(f"- Liên hệ công khai: {f.get('public_phone') or 'Chưa có số liên hệ công khai trong danh mục'}")
        if "bao nhieu san" in q:
            lines.append(f"- Số sân niêm yết: {f.get('courts_count') if f.get('courts_count') is not None else 'Chưa cập nhật'}")
        if "tien ich" in q:
            lines.append("- Tiện ích: " + ", ".join(str(x) for x in f.get('badges', [])) if f.get('badges') else "- Tiện ích: Chưa cập nhật")
    lines.append("\nNguồn: danh mục cơ sở trên hệ thống; giờ hoạt động niêm yết không xác nhận sân còn trống.")
    return _response("\n".join(lines))


async def try_catalog_answer(message, history=None) -> Optional[dict]:
    if normalize(message) in {"chao", "xin chao", "hello", "hi", "ban giup gi duoc", "ban lam duoc gi", "ban co the lam gi", "tro giup", "help"}:
        return _response("Chào bạn! Tôi có thể hỗ trợ:\n- Hướng dẫn tài khoản, đặt sân, thanh toán, thuê dụng cụ và ghép kèo theo tài liệu hệ thống.\n- Tra giá vợt/dụng cụ, địa chỉ và giờ mở cửa của cơ sở.\n- Tra giá sân, lịch trống theo cơ sở, ngày và giờ.\n- Xem đơn của bạn sau khi đăng nhập; giữ chỗ/đặt sân cần bước xác nhận.\n\nBạn có thể hỏi: **Thuê vợt Yonex giá bao nhiêu?** hoặc **Cách đặt sân như thế nào?**", retrieval=None)
    query = resolve_followup(message, history)
    is_equipment = equipment_intent(query)
    is_facility = facility_intent(message)
    if not is_equipment and not is_facility:
        return None
    try:
        data = await asyncio.to_thread(load_catalog)
        if not isinstance(data, dict) or not isinstance(data.get("facilities"), list) or (is_equipment and not isinstance(data.get("equipments"), list)):
            raise ValueError("Catalogue unavailable")
        return answer_equipment(query, data) if is_equipment else answer_facility(message, data)
    except Exception:
        return _response("Hiện tôi chưa đọc được danh mục hệ thống. Bạn vui lòng thử lại sau hoặc tra cứu trên website.", "error", "data_unavailable")
