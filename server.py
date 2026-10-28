import http.server
import json
import os
import sys
import re
import secrets
import urllib.request
import urllib.error
import urllib.parse
import http.cookies
import threading
import queue
import time

# Ensure backend directory is in path if needed
backend_dir = os.path.join(os.path.dirname(__file__), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import asyncio
try:
    from backend.app.ai import elo_engine
    from backend.app.ai.chatbot_service import get_chatbot_service
    from backend.app.core.security import decode_token, create_access_token, verify_password
    from backend.app.core.login_lockout import clear_failed_logins, record_failed_login, remaining_lock_seconds
except ImportError:
    # pyrefly: ignore [missing-import]
    from app.ai import elo_engine
    from app.ai.chatbot_service import get_chatbot_service
    from app.core.security import decode_token, create_access_token, verify_password
    from app.core.login_lockout import clear_failed_logins, record_failed_login, remaining_lock_seconds

from db_engine import db_manager
try:
    from backend.app.config import settings
except ImportError:
    from app.config import settings
PORT = int(os.environ.get("PORT", 8085))
DATA_FILE = os.path.join(os.path.dirname(__file__), "database.json")
CENTRAL_DATABASE_LOCK = threading.RLock()
CHAT_SUBSCRIBERS_LOCK = threading.Lock()
CHAT_SUBSCRIBERS = {}


def _publish_room_chat_message(room_id, message):
    with CHAT_SUBSCRIBERS_LOCK:
        subscribers = list(CHAT_SUBSCRIBERS.get(str(room_id), set()))
    for subscriber in subscribers:
        try:
            subscriber.put_nowait(message)
        except queue.Full:
            try:
                subscriber.get_nowait()
                subscriber.put_nowait(message)
            except (queue.Empty, queue.Full):
                pass


def _add_chat_subscriber(room_id, subscriber):
    with CHAT_SUBSCRIBERS_LOCK:
        CHAT_SUBSCRIBERS.setdefault(str(room_id), set()).add(subscriber)


def _remove_chat_subscriber(room_id, subscriber):
    with CHAT_SUBSCRIBERS_LOCK:
        subscribers = CHAT_SUBSCRIBERS.get(str(room_id))
        if subscribers:
            subscribers.discard(subscriber)
            if not subscribers:
                CHAT_SUBSCRIBERS.pop(str(room_id), None)


def _merge_records_by_id(existing, incoming):
    """Merge append/update records without dropping records from a stale browser snapshot."""
    records = {}
    for item in existing if isinstance(existing, list) else []:
        if isinstance(item, dict) and item.get("id") is not None:
            records[str(item["id"])] = item
    for item in incoming if isinstance(incoming, list) else []:
        if not isinstance(item, dict) or item.get("id") is None:
            continue
        key = str(item["id"])
        previous = records.get(key)
        if previous is None:
            records[key] = item
            continue
        merged = {**previous, **item}
        if "players" in previous or "players" in item:
            players = {}
            for player in (previous.get("players") or []) + (item.get("players") or []):
                if not isinstance(player, dict):
                    continue
                player_id = player.get("id")
                player_name = str(player.get("name") or "").strip().casefold()
                # Older rooms did not persist an id on the host player. Keep those
                # roster entries too, using the name as a stable fallback key.
                player_key = f"id:{player_id}" if player_id is not None else f"name:{player_name}" if player_name else None
                if player_key:
                    players[player_key] = player
            host_name = str(merged.get("host_name") or "").strip()
            if host_name and not any(
                str(player.get("name") or "").strip().casefold() == host_name.casefold()
                for player in players.values()
            ):
                host_id = merged.get("host_id") or merged.get("host_user_id")
                host_player = {
                    "name": host_name,
                    "role": "Host",
                    "tier": merged.get("host_tier"),
                    "tier_id": merged.get("host_tier_id"),
                    "elo": merged.get("host_elo"),
                    "photo": merged.get("host_photo"),
                }
                if host_id is not None:
                    host_player["id"] = host_id
                players[f"id:{host_id}" if host_id is not None else f"name:{host_name.casefold()}"] = host_player
            merged["players"] = list(players.values())
            # The roster is the source of truth; a stale counter must not show
            # phantom members or mark a room full when its slots are empty.
            merged["current_players"] = len(players)
        if "chat_messages" in previous or "chat_messages" in item:
            messages = {}
            for message in (previous.get("chat_messages") or []) + (item.get("chat_messages") or []):
                message_id = message.get("id") if isinstance(message, dict) else None
                marker = f"id:{message_id}" if message_id else json.dumps(message, ensure_ascii=False, sort_keys=True)
                messages[marker] = message
            merged["chat_messages"] = list(messages.values())
        if "invited_player_ids" in previous or "invited_player_ids" in item:
            invited = {str(value): value for value in (previous.get("invited_player_ids") or [])}
            invited.update({str(value): value for value in (item.get("invited_player_ids") or [])})
            merged["invited_player_ids"] = list(invited.values())
        max_players = int(merged.get("max_players") or 0)
        if max_players and int(merged.get("current_players") or 0) >= max_players:
            merged["status"] = "MATCHED"
        elif previous.get("status") in ("CANCELLED", "CLOSED", "MATCHED") and item.get("status") == "OPEN":
            merged["status"] = previous["status"]
        records[key] = merged
    return list(records.values())


def _merge_notifications(existing, incoming):
    merged = {str(item["id"]): item for item in existing if isinstance(item, dict) and item.get("id") is not None}
    for item in incoming:
        if not isinstance(item, dict) or item.get("id") is None:
            continue
        key = str(item["id"])
        previous = merged.get(key, {})
        notification = {**previous, **item}
        if previous.get("is_read"):
            notification["is_read"] = True
        previous_status = previous.get("invite_status")
        if previous_status in ("ACCEPTED", "DECLINED", "EXPIRED") and item.get("invite_status") == "PENDING":
            notification["invite_status"] = previous_status
        merged[key] = notification
    return list(merged.values())


def _save_central_database_update(incoming_data):
    with CENTRAL_DATABASE_LOCK:
        current_data = db_manager.load_data() or {}
        merged_database = {**current_data}

        if isinstance(incoming_data.get("users"), list):
            sanitized_users = []
            for user in incoming_data["users"]:
                if not isinstance(user, dict):
                    continue
                password = user.get("password")
                if not password or str(password).strip() in ["", "undefined", "null"]:
                    password = "02092006" if user.get("phone") == "0123456789" else "123456"
                user_copy = {**user, "password": str(password)}
                if "elo_rating" not in user_copy or user_copy["elo_rating"] is None or str(user_copy["elo_rating"]) == "undefined":
                    user_copy["elo_rating"] = 1200 if user_copy.get("role") == "CUSTOMER" else "N/A"
                sanitized_users.append(user_copy)
            merged_database["users"] = sanitized_users

        if isinstance(incoming_data.get("facilities"), list):
            merged_database["facilities"] = incoming_data["facilities"]

        for key, value in incoming_data.items():
            if key in ("users", "facilities") or not isinstance(value, list):
                continue
            if key == "matchmaking_rooms":
                merged_database[key] = _merge_records_by_id(merged_database.get(key, []), value)
            elif key == "notifications":
                merged_database[key] = _merge_notifications(merged_database.get(key, []), value)
            else:
                merged_database[key] = value

        db_manager.save_data(merged_database)
        return merged_database

SYSTEM_INSTRUCTION = """Bạn là Trợ lý AI Thông Minh (BADMINTON.AI Virtual Assistant) của nền tảng Quản Lý & Cho Thuê Sân Cầu Lông & Pickleball BADMINTON.AI.
Nhiệm vụ của bạn:
- Tư vấn nhiệt tình, ngắn gọn, thân thiện, lịch sự và giải đáp mọi thắc mắc về sản phẩm/dịch vụ của website.
- Nắm vững kiến thức hệ thống:
  + Danh sách 48+ cụm sân cầu lông tại Hà Nội (Cầu Giấy, Hoàng Mai, Đống Đa, Thanh Xuân, Nam Từ Liêm, Bắc Từ Liêm, Ba Đình, Long Biên, Tây Hồ, Hai Bà Trưng, Hà Đông, Hoàn Kiếm...).
  + Bảng giá thuê sân: 50.000đ - 180.000đ/giờ.
  + Cơ chế AI Dynamic Pricing (UC003): Tự động giảm giá 15% giờ hành chính (8h-14h) để kích cầu, phụ thu 25% khung giờ vàng (17h-21h) tối ưu doanh thu.
  + Giữ chỗ 10 phút (UC005): Khóa nguyên tử (Atomic Slot Lock) chống xung đột đặt trùng, cọc 50% qua VNPay/Chuyển khoản QR.
  + AI Matchmaking & Điểm ELO (UC006): Ghép kèo đấu công bằng, tìm bạn chơi theo trình độ ELO 1000 - 2000+.
  + Dịch vụ & Dụng cụ: Cho thuê wife tiêu chuẩn 20k-30k/buổi, thuê giày 20k, bán phụ kiện cầu/quấn cán, căng cước điện tử 10.5 - 11.5 kg.
  + Tiện ích cơ sở vật chất: Đạt chuẩn BWF, thảm PVC Enlio VIP/Yonex Pro chống trơn, đèn LED chống chói 300+ Lux, máy lạnh/quạt công nghiệp, phòng tắm nóng lạnh miễn phí, bãi đỗ xe ô tô/xe máy rộng rãi 24/7.
  + Giờ hoạt động: 05:00 Sáng - 24:00 Đêm tất cả các ngày trong tuần (kể cả Thứ 7, CN, Lễ Tết).
  + Chính sách hoàn cọc (UC008): Hoàn 100% khi hủy trước 24 giờ thi đấu, hoàn 50% trước 12-24h.
  + Hotline hỗ trợ 24/7: 1900 6868 - 098.358.2321.
- Luôn trả lời bằng tiếng Việt, định dạng Markdown cơ bản rõ ràng, dùng emoji thể thao sinh động."""

DISTRICT_KEYWORDS = {
    "Cầu Giấy": ["cầu giấy", "cau giay", "dịch vọng", "trung kính", "mai dịch", "nghĩa tân", "hoàng quốc việt", "trần quý kiên", "duy tân", "trần thái tông", "hoàng ngân"],
    "Hoàng Mai": ["hoàng mai", "hoang mai", "tân khai", "định công", "đền lừ", "vĩnh hưng", "giáp bát", "linh đàm"],
    "Đống Đa": ["đống đa", "dong da", "láng hạ", "đường láng", "chùa láng", "tây sơn", "chùa bộc", "nguyễn chí thanh", "thủy lợi", "công đoàn", "ngân hàng", "ngoại thương", "pháo đài láng"],
    "Ba Đình": ["ba đình", "ba dinh", "điện biên phủ", "văn cao", "liễu giai", "đội cấn", "la thành", "phụ sản", "quần ngựa"],
    "Thanh Xuân": ["thanh xuân", "thanh xuan", "lê văn lương", "quan nhân", "khương đình", "nhân chính", "vũ hữu", "nguyễn trãi"],
    "Nam Từ Liêm": ["nam từ liêm", "nam tu liem", "mỹ đình", "lê đức thọ", "đại mỗ", "mễ trì"],
    "Bắc Từ Liêm": ["bắc từ liêm", "bac tu liem", "cổ nhuế", "ciputra", "xuân đỉnh"],
    "Hai Bà Trưng": ["hai bà trưng", "hai ba trung", "bách khoa", "lê thanh nghị", "minh khai", "xây dựng", "bạch đằng", "lương yên"],
    "Tây Hồ": ["tây hồ", "tay ho", "quảng an", "đặng thai mai", "lạc long quân", "ven hồ"],
    "Hà Đông": ["hà đông", "ha dong", "văn quán", "trần phú", "tô hiệu", "la khê", "văn khê", "dương nội", "nguyễn huệ"],
    "Long Biên": ["long biên", "long bien", "cổ linh", "việt hưng", "ngô gia tự", "thạch bàn", "doàn khuê", "thượng thanh", "ngọc lâm", "bồ đề"],
    "Hoàn Kiếm": ["hoàn kiếm", "hoan kiem", "hồng hà", "chương dương"]
}

def load_facilities():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("facilities", [])
        except Exception:
            pass
    return []

def extract_price_threshold(query: str):
    q = query.lower()
    match_k = re.search(r'(?:dưới|<|nhỏ hơn|tầm|khoảng|<=)\s*(\d{2,3})\s*(?:k|nghìn|ngàn|kđ|000)?', q)
    if match_k:
        val = int(match_k.group(1))
        return val * 1000 if val < 1000 else val
    match_full = re.search(r'(\d{2,3})\.?000', q)
    if match_full:
        return int(match_full.group(1)) * 1000
    if "giá rẻ" in q or "sinh viên" in q or "rẻ nhất" in q or "tiết kiệm" in q:
        return 80000
    return None

def detect_districts(query: str):
    q = query.lower()
    matched = []
    for district, kws in DISTRICT_KEYWORDS.items():
        if any(kw in q for kw in kws):
            matched.append(district)
    return matched

def get_gemini_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "")
    if key and not key.startswith("YEAR_"):
        return key.strip()
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val and not val.startswith("YEAR_"):
                            return val
        except Exception:
            pass
    return ""

def get_smart_fallback(question: str, context: str = "") -> str:
    q = (question or "").lower().strip()
    facilities = load_facilities()

    # =========================================================================
    # 1. MATCHMAKING & ELO (High priority to catch "làm sao để ghép kèo", etc.)
    # =========================================================================
    if any(k in q for k in ['ghép kèo', 'tìm bạn', 'tìm đồng đội', 'kèo đấu', 'elo', 'điểm elo', 'cách tính elo', 'matchmaking', 'giao lưu', 'ghép đội']):
        return (
            "🏆 **AI MATCHMAKING & HỆ THỐNG ĐIỂM ELO TỰ ĐỘNG (UC006)**:\n\n"
            "- 🎯 **Cơ chế ghép kèo thông minh**: Thuật toán AI phân tích trình độ ELO của từng thành viên để tự động ghép phòng đấu cân bằng nhất, tránh tình trạng chênh lệch trình độ.\n"
            "- 📊 **Thang điểm ELO chuẩn quốc tế**:\n"
            "  - 🥉 **Tân thủ (1000 - 1200 ELO)**: Mới tập chơi, làm quen nhịp độ và rèn luyện kỹ thuật cơ bản.\n"
            "  - 🥈 **Phong trào khá (1201 - 1500 ELO)**: Đánh đơn/đôi ổn định, phản xạ và di chuyển tốt.\n"
            "  - 🥇 **Bán chuyên (1501 - 1800 ELO)**: Smash cầu uy lực, bắt lưới nhanh, chiến thuật bài bản.\n"
            "  - 👑 **Master / Chuyên nghiệp (1800+ ELO)**: Đẳng cấp thi đấu các giải phong trào lớn.\n\n"
            "👉 **Cách tham gia**: Bạn chỉ cần bấm vào tab **\"AI Ghép Đội / Kèo Đấu\"** trên thanh điều hướng > Chọn phòng đang tìm người hoặc bấm **\"Tạo Phòng Mới\"** để chiêu mộ đồng đội ngay nhé! 🏸"
        )

    # =========================================================================
    # 2. CANCELLATION & REFUND POLICIES
    # =========================================================================
    if any(k in q for k in ['hủy sân', 'hoàn tiền', 'hoàn cọc', 'đổi giờ', 'hủy lịch', 'trả lại cọc', 'chính sách hủy', 'chính sách hoàn']):
        return (
            "📋 **CHÍNH SÁCH HOÀN HỦY & ĐỔI LỊCH ĐẶT SÂN (UC008)**:\n\n"
            "- 🟢 **Hủy trước 24 giờ thi đấu**: Hoàn cọc **100%** vào ví tài khoản ngay lập tức (Miễn phí hủy 100%).\n"
            "- 🟡 **Hủy trước 12 - 24 giờ**: Hoàn cọc **50%** giá trị tiền cọc đã thanh toán.\n"
            "- 🔴 **Hủy dưới 12 giờ**: Không hỗ trợ hoàn cọc (do cụm sân đã khóa khung giờ cố định cho bạn).\n"
            "- 🔄 **Đổi khung giờ chơi**: Hỗ trợ đổi giờ miễn phí trước 12 giờ nếu cụm sân còn sân trống tương đương.\n\n"
            "👉 **Thao tác nhanh**: Vào mục **\"Lịch Đặt Của Tôi\"** > Chọn lịch đặt > Bấm nút **\"Yêu cầu hủy / đổi giờ\"** để hệ thống xử lý tự động trong 3 giây!"
        )

    # =========================================================================
    # 3. PAYMENT & DEPOSIT WORKFLOW
    # =========================================================================
    if any(k in q for k in ['thanh toán', 'chuyển khoản', 'vnpay', 'quét qr', 'cọc bao nhiêu', 'tiền cọc', 'nạp ví', 'tiền đặt cọc', 'đặt cọc như thế nào']):
        return (
            "💳 **QUY ĐỊNH ĐẶT CỌC & CỔNG THANH TOÁN TIỆN LỢI**:\n\n"
            "- 💰 **Mức cọc giữ chỗ**: Bạn chỉ cần đặt cọc trước **50%** tổng tiền sân để kích hoạt khóa giữ chỗ 10 phút. 50% còn lại thanh toán trực tiếp tại sân khi đến chơi.\n"
            "- 📲 **Các hình thức thanh toán hỗ trợ 24/7**:\n"
            "  1. **Quét mã VietQR**: Chuyển khoản liên ngân hàng miễn phí, tự động duyệt giao dịch sau 2 giây.\n"
            "  2. **Cổng thanh toán VNPay**: Hỗ trợ mọi thẻ ATM nội địa, Visa, Mastercard, JCB và ứng dụng ví VNPay.\n"
            "  3. **Ví số dư tài khoản**: Nạp tiền 1 lần, thanh toán giữ sân tức thì chỉ với 1 chạm.\n\n"
            "👉 *Sau khi thanh toán thành công, bạn sẽ nhận được **Mã QR Check-in** để xuất trình tại quầy lễ tân cụm sân!*"
        )

    # =========================================================================
    # 4. HOW TO BOOK / BOOKING WORKFLOW (Action Intent)
    # =========================================================================
    booking_action_patterns = [
        'làm thế nào để đặt', 'thì làm thế nào', 'cách đặt sân', 'hướng dẫn đặt', 
        'muốn đặt sân', 'quy trình đặt', 'các bước đặt', 'bước đặt', 'làm sao để đặt', 
        'tôi muốn đặt sân', 'đặt lịch như thế nào', 'đặt sân sao', 'đặt chỗ thế nào',
        'cách thuê sân', 'làm sao để thuê sân', 'hướng dẫn thuê sân', 'tôi muốn thuê sân'
    ]
    if any(p in q for p in booking_action_patterns) or (('đặt' in q or 'thuê' in q) and any(k in q for k in ['thế nào', 'làm sao', 'hướng dẫn', 'cách', 'quy trình', 'bước']) and not any(k in q for k in ['vợt', 'giày', 'kèo'])):
        return (
            "🏸 **HƯỚNG DẪN 4 BƯỚC ĐẶT SÂN NHANH CHÓNG TRÊN BADMINTON.AI**:\n\n"
            "1. 🔍 **Bước 1: Chọn Cụm Sân**\n"
            "   - Duyệt danh sách trên trang chủ hoặc vào tab **Bản Đồ** để định vị sân gần bạn nhất.\n"
            "   - Bấm nút **\"Đặt Sân\"** trên thẻ sân mong muốn.\n\n"
            "2. 📅 **Bước 2: Chọn Ngày & Khung Giờ Chơi**\n"
            "   - Chọn ngày thi đấu và click vào ô giờ trống (màu xanh lá).\n"
            "   - Hệ thống hiển thị biểu đồ giá trực tiếp theo giờ vàng / giờ hành chính.\n\n"
            "3. 🔒 **Bước 3: Khóa Giữ Chỗ Nguyên Tử (10 Phút)**\n"
            "   - Tính năng *Atomic Slot Lock* tự động giữ sân 10 phút, ngăn chặn hoàn toàn việc người khác đặt trùng lịch.\n\n"
            "4. 💳 **Bước 4: Đặt Cọc 50% & Nhận Mã QR Check-in**\n"
            "   - Quét mã VietQR hoặc thanh toán qua VNPay/Ví tài khoản.\n"
            "   - Nhận mã **QR Check-in** tại mục **\"Sân Đã Đặt\"** để quét mở đèn sân khi đến chơi.\n\n"
            "👉 *Bạn muốn đặt sân ở khu vực nào (Cầu Giấy, Hoàng Mai, Đống Đa, Ba Đình...)? Hãy nhắn cho tôi để tôi lọc sân trống tốt nhất giúp bạn nhé!* ✨"
        )

    # =========================================================================
    # 5. OPENING HOURS & TIMING
    # =========================================================================
    if any(k in q for k in ['mấy giờ', 'giờ mở cửa', 'giờ đóng cửa', 'giờ hoạt động', 'mở đến', 'mở từ', 'mở đêm', '24/7', 'sáng sớm', 'lễ tết', 'ngày tết']):
        return (
            "🕒 **THỜI GIAN HOẠT ĐỘNG CỦA HỆ THỐNG CỤM SÂN**:\n\n"
            "- ⏰ **Giờ mở cửa hàng ngày**: **05:00 Sáng - 24:00 Đêm** (Mở cửa xuyên suốt tất cả các ngày trong tuần, kể cả Thứ 7, Chủ Nhật và các ngày Lễ Tết).\n"
            "- 🌅 **Khung giờ sáng sớm (05:00 - 08:00)**: Không khí mát mẻ, vắng người, giá ưu đãi rất thích hợp tập luyện thể lực.\n"
            "- 🌙 **Khung giờ đêm (21:30 - 24:00)**: Thích hợp giao lưu kèo muộn sau giờ làm việc, giá thuê giảm mạnh sau giờ vàng cao điểm.\n\n"
            "👉 *Bạn có thể bấm vào thẻ sân bất kỳ để xem lịch trống các khung giờ hôm nay nhé!*"
        )

    # =========================================================================
    # 6. EQUIPMENT, RACKET ADVICE & RENTAL SERVICES
    # =========================================================================
    if any(k in q for k in ['thuê vợt', 'thuê giày', 'chọn vợt', 'vợt smash', 'vợt công', 'vợt thủ', 'căng cước', 'căng dây', 'mua cầu', 'quấn cán', 'dụng cụ', 'mua vợt', 'tư vấn vợt', 'vợt cầu lông']):
        return (
            "🏸 **DỊCH VỤ DỤNG CỤ & TƯ VẤN CHỌN VỢT THI ĐẤU CHUYÊN NGHIỆP**:\n\n"
            "1. 🛒 **Dịch vụ tiện ích tại tất cả 48 cụm sân**:\n"
            "   - **Thuê wife cầu lông**: 20.000đ - 30.000đ/buổi (Vợt Yonex, Lining, Victor chính hãng căng sẵn 10.5kg).\n"
            "   - **Thuê giày cầu lông**: 20.000đ/buổi (Đầy đủ size 38 - 44, đế kếp bám sân, khử khuẩn 100% sau mỗi ca).\n"
            "   - **Bán phụ kiện tại quầy**: Cầu Hải Yến, Thành Công (25k-30k/quả), quấn cán chống trượt, nước bù khoáng Pocari/Revive.\n"
            "   - **Căng cước điện tử**: Nhận căng cước Yonex BG65, BG65Ti, Nanogy 98 (lấy ngay sau 15 phút).\n\n"
            "2. 🎯 **Tư vấn chọn wife theo lối đánh**:\n"
            "   - 🔥 **Công / Smash uy lực**: Vợt nặng đầu (>295mm), trọng lượng 3U/4U (*Yonex Astrox 88D Pro / 99 / 100ZZ, Lining Tectonic 7*).\n"
            "   - ⚡ **Thủ / Phản tạt nhanh**: Vợt nhẹ đầu (<285mm), 4U/5U (*Yonex Nanoflare 700 / 800 / 1000Z*).\n"
            "   - ⚖️ **Công thủ toàn diện**: Cân bằng 290 - 295mm (*Arcsaber 11 Pro, Lining Halbertec 8000*).\n"
            "   - 💡 **Mức căng khuyến nghị**: Người mới (9.5 - 10.5 kg), phong trào (10.5 - 11.5 kg)."
        )

    # =========================================================================
    # 7. AMENITIES, FACILITIES & QUALITY
    # =========================================================================
    if any(k in q for k in ['máy lạnh', 'điều hòa', 'phòng tắm', 'nóng lạnh', 'gửi xe', 'bãi đỗ', 'đỗ ô tô', 'thảm gì', 'ánh sáng', 'tiện ích']) and not any(k in q for k in ['tìm sân', 'sân nào ở']):
        return (
            "✨ **TIỆN ÍCH & TIÊU CHUẨN CƠ SỞ VẬT CHẤT CỤM SÂN**:\n\n"
            "Tất cả các cụm sân trong hệ thống BADMINTON.AI đều được thiết kế theo tiêu chuẩn thi đấu BWF:\n"
            "- 🌿 **Mặt sàn thi đấu**: Thảm PVC chuyên dụng Enlio VIP / Yonex Pro dày 4.5mm - 5.0mm, chống trơn trượt và giảm chazan khớp gối tối đa.\n"
            "- 💡 **Hệ thống ánh sáng**: Dàn đèn LED chuyên dụng 300+ Lux bố trí dọc 2 biên, chống chói mắt tuyệt đối khi ngước nhìn cầu.\n"
            "- ❄️ **Không gian & Làm mát**: Trần cao 8m - 11m thông thoáng, trang bị quạt công nghiệp và điều hòa/máy lạnh công suất lớn.\n"
            "- 🚿 **Phòng thay đồ & Tắm**: Phòng thay đồ riêng biệt, phòng tắm nóng lạnh phục vụ **miễn phí 100%** cho vận động viên.\n"
            "- 🚗 **Bãi đỗ xe**: Bãi giữ xe máy & đỗ xe ô tô rộng rãi, có camera an ninh và bảo vệ túc trực 24/7."
        )

    # =========================================================================
    # 8. DYNAMIC PRICING & RATES
    # =========================================================================
    if any(k in q for k in ['bảng giá', 'giá thuê', 'bao nhiêu tiền', 'giờ vàng', 'giờ hành chính', 'phụ thu', 'dynamic pricing', 'tính giá', 'giá 1 tiếng', 'giá 1 giờ']):
        return (
            "🏸 **BẢNG GIÁ THUÊ SÂN & THUẬT TOÁN AI DYNAMIC PRICING (UC003)**:\n\n"
            "Hệ thống BADMINTON.AI tự động điều chỉnh mức giá theo thời gian thực nhằm tối ưu chi phí cho người chơi:\n"
            "- 🟢 **Giờ Hành Chính (08:00 - 14:00)**: **50.000đ - 90.000đ/giờ** *(AI tự động giảm giá **-15%** kích cầu, mức giá siêu tiết kiệm cho sinh viên)*.\n"
            "- 🟡 **Giờ Tiêu Chuẩn (14:00 - 17:00 & 21:00 - 23:00)**: **80.000đ - 120.000đ/giờ** *(Mức giá niêm yết chuẩn của sân)*.\n"
            "- 🔴 **Giờ Vàng Cao Điểm (17:00 - 21:00)**: **130.000đ - 180.000đ/giờ** *(Phụ thu AI **+25%** do nhu cầu thi đấu cao)*.\n\n"
            "💡 *Mẹo: Hãy đặt sân vào khung giờ 08:00 - 14:00 hoặc sau 21:30 để nhận mức giá ưu đãi nhất nhé!*"
        )

    # =========================================================================
    # 9. ACCOUNT, OWNER PARTNER & SUPPORT HOTLINE
    # =========================================================================
    if any(k in q for k in ['đăng ký', 'đăng nhập', 'tạo tài khoản', 'chủ sân', 'hotline', 'số điện thoại', 'tổng đài', 'liên hệ', 'chăm sóc khách hàng', 'hỗ trợ', 'khiếu nại']):
        return (
            "📞 **KÊNH TƯ VẤN HỖ TRỢ & HƯỚNG DẪN TÀI KHOẢN 24/7**:\n\n"
            "- ☎️ **Tổng đài Hotline CSKH**: **1900 6868** hoặc **098.358.2321** (Phục vụ 24/7).\n"
            "- 📧 **Email tiếp nhận phản hồi / khiếu nại**: support@badminton.ai\n"
            "- 👤 **Đăng ký tài khoản người chơi**: Bấm vào nút **\"Đăng Nhập / Đăng Ký\"** ở góc trên bên phải màn hình để tạo tài khoản bằng SĐT trong 30 giây.\n"
            "- 🏢 **Hợp tác chủ sân (Đối tác OWNER)**: Đăng ký liên kết cụm sân lên hệ thống để tiếp cận 50,000+ vợt thủ và tối ưu doanh thu tự động. Vui lòng liên hệ Hotline kinh doanh: **098.358.2321**."
        )

    # =========================================================================
    # 10. BEGINNER GUIDE & BADMINTON RULES
    # =========================================================================
    if any(k in q for k in ['mới chơi', 'người mới', 'tập chơi', 'luật chơi', 'cách tính điểm', 'kinh nghiệm']):
        return (
            "🏸 **HƯỚNG DẪN DÀNH CHO NGƯỜI MỚI BẮT ĐẦU CHƠI CẦU LÔNG**:\n\n"
            "1. 👟 **Trang bị bắt buộc**: Mang giày cầu lông chuyên dụng bám sân để chống trơn trượt và bảo vệ cổ chân.\n"
            "2. 🏸 **Chọn wife cho người mới**: Nên chọn wife nhẹ 4U hoặc 5U, thân dẻo (Medium/Flexible) để dễ phát lực và không bị mỏi cổ tay.\n"
            "3. 📜 **Luật thi đấu BWF cơ bản**:\n"
            "   - Trận đấu gồm 3 set, ai thắng 2 set trước sẽ thắng chung cuộc.\n"
            "   - Mỗi set đánh đến 21 điểm (tính điểm trực tiếp ở mỗi pha cầu). Hòa 20-20 thì cách biệt 2 điểm sẽ thắng (tối đa đến 30 điểm).\n"
            "   - Giao cầu từ ô bên phải khi điểm của bạn là chẵn (0, 2, 4...) và từ ô bên trái khi điểm là lẻ (1, 3, 5...).\n\n"
            "👉 *Bạn có thể vào tab **AI Ghép Đội** tham gia các phòng giao lưu **ELO 1000 - 1200** để tập luyện cùng các bạn mới chơi nhé!*"
        )

    # =========================================================================
    # 11. EXPLICIT COURT / DISTRICT / PRICE SEARCH
    # =========================================================================
    detected_districts = detect_districts(q)
    price_threshold = extract_price_threshold(q)

    if detected_districts or price_threshold or ("sân" in q and any(k in q for k in ["tìm", "danh sách", "gần", "ở", "tại", "nào", "khu vực"])):
        matched_facs = []
        for f in facilities:
            addr = (f.get("address") or "").lower()
            name = (f.get("name") or "").lower()
            badges = [b.lower() for b in f.get("badges", [])]
            base_p = f.get("base_price") or 80000

            dist_match = True
            if detected_districts:
                dist_match = False
                for d in detected_districts:
                    kws = DISTRICT_KEYWORDS.get(d, [])
                    if d.lower() in addr or d.lower() in name or any(kw in addr or kw in name for kw in kws):
                        dist_match = True
                        break

            price_match = True
            if price_threshold is not None:
                price_match = base_p <= price_threshold

            feat_match = True
            if "máy lạnh" in q or "điều hòa" in q:
                feat_match = any("máy lạnh" in b or "điều hòa" in b for b in badges)
            elif "thảm yonex" in q:
                feat_match = any("yonex" in b for b in badges)
            elif "thảm enlio" in q:
                feat_match = any("enlio" in b for b in badges)
            elif "vip" in q:
                feat_match = any("vip" in b for b in badges)

            if dist_match and price_match and feat_match:
                matched_facs.append(f)

        if matched_facs:
            matched_facs.sort(key=lambda x: (-(x.get("rating") or 0), (x.get("base_price") or 80000)))
            top_facs = matched_facs[:5]

            title_parts = []
            if detected_districts:
                title_parts.append(f"khu vực **{', '.join(detected_districts)}**")
            if price_threshold:
                title_parts.append(f"mức giá dưới **{price_threshold:,.0f}đ/h**")

            title_desc = " tại " + " & ".join(title_parts) if title_parts else " phù hợp nhất tại Hà Nội"

            lines = [f"🏸 **Gợi Ý Sân Cầu Lông{title_desc}** (Tìm thấy {len(matched_facs)} sân):\n"]
            for idx, fac in enumerate(top_facs, 1):
                name = fac.get("name", "Sân Cầu Lông")
                addr = fac.get("address", "")
                price = fac.get("price_range") or f"{fac.get('base_price', 80000):,.0f}đ/giờ"
                rating = fac.get("rating", 4.8)
                rev_count = fac.get("reviews_count", 50)
                hours = fac.get("open_hours", "05:00 - 23:00")
                courts = fac.get("courts_count", 6)
                badges_str = " • ".join(fac.get("badges", ["Đơn ngày"]))

                lines.append(f"**{idx}. {name}** ⭐ {rating}/5.0 ({rev_count} đánh giá)")
                lines.append(f"- 📍 **Địa chỉ**: {addr}")
                lines.append(f"- 💰 **Giá thuê**: **{price}** *(Giờ HC 8h-14h giảm 15%)*")
                lines.append(f"- 🕒 **Giờ mở cửa**: {hours} ({courts} sân thi đấu tiêu chuẩn)")
                lines.append(f"- 🏷️ **Tiện ích**: {badges_str}\n")

            lines.append("👉 *Bạn có thể chọn trực tiếp cụm sân trên giao diện trang chủ để xem lịch trống và đặt giữ chỗ nguyên tử 10 phút nhé!*")
            return "\n".join(lines)

    # Default friendly greeting
    return (
        "👋 Xin chào! Tôi là **Trợ lý AI Thông Minh BADMINTON.AI**.\n\n"
        "Tôi sẵn sàng hỗ trợ bạn giải đáp mọi thắc mắc:\n"
        "- 🏸 **Cách đặt sân & Giữ chỗ 10 phút**: Hướng dẫn chọn giờ và nhận mã QR check-in.\n"
        "- 📍 **Tìm sân theo Quận / Khu vực**: Cầu Giấy, Hoàng Mai, Đống Đa, Thanh Xuân, Ba Đình...\n"
        "- 💰 **Bảng giá & Sân giá rẻ**: Tra cứu giá giờ vàng (+25%), giờ hành chính (-15%) hoặc sân dưới 100k.\n"
        "- 🏆 **AI Ghép Đội & Kèo ELO**: Tìm phòng ghép và đồng đội cùng trình độ 1000 - 2000+.\n"
        "- 🛒 **Dịch vụ tiện ích**: Thuê wife 20k/buổi, thuê giày, mua phụ kiện cầu và căng cước tại chỗ.\n"
        "- 📋 **Chính sách hoàn cọc 100% & Hotline hỗ trợ 24/7**.\n\n"
        "Bạn muốn tìm hiểu thông tin gì ạ? Hãy nhắn câu hỏi cho tôi nhé! ✨🏸"
    )

def ask_gemini(user_message: str, context: str = "", messages: list = None) -> str:
    api_key = get_gemini_api_key()
    if not api_key:
        return get_smart_fallback(user_message, context)

    facilities = load_facilities()
    summary_facilities = []
    for f in facilities[:20]:
        summary_facilities.append({
            "id": f.get("id"),
            "name": f.get("name"),
            "address": f.get("address"),
            "price": f.get("price_range") or f"{f.get('base_price', 80000):,.0f}đ/h",
            "rating": f.get("rating"),
            "hours": f.get("open_hours"),
            "badges": f.get("badges", [])
        })

    full_system = SYSTEM_INSTRUCTION + f"\n\nDANH SÁCH 20+ SÂN CẦU LÔNG NỔI BẬT:\n{json.dumps(summary_facilities, ensure_ascii=False)}"
    if context:
        full_system += f"\nNgữ cảnh trang web hiện tại:\n{context}"

    contents = []
    if messages and isinstance(messages, list) and len(messages) > 0:
        for m in messages[-8:]:
            role = "user" if m.get("role") == "user" or m.get("sender") == "user" else "model"
            text = m.get("content") or m.get("text") or m.get("message") or ""
            if text:
                contents.append({
                    "role": role,
                    "parts": [{"text": str(text)}]
                })
    if not contents and user_message:
        contents.append({
            "role": "user",
            "parts": [{"text": user_message}]
        })

    # Models supported in Google AI Studio
    models_to_try = [
        ("gemini-1.5-flash", True),
        ("gemini-2.0-flash", True)
    ]

    for model_name, use_sys_inst in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        payload = {
            "contents": list(contents),
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1000
            }
        }
        if use_sys_inst:
            payload["systemInstruction"] = {
                "parts": [{"text": full_system}]
            }
        else:
            if payload["contents"] and payload["contents"][0]["role"] == "user":
                orig_text = payload["contents"][0]["parts"][0]["text"]
                payload["contents"][0]["parts"][0]["text"] = f"[HƯỚNG DẪN]: {full_system}\n\n[CÂU HỎI]: {orig_text}"

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=3.5) as response:
                if response.status == 200:
                    res_body = response.read()
                    res_json = json.loads(res_body)
                    candidates = res_json.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            reply_text = parts[0].get("text", "")
                            if reply_text:
                                return reply_text
        except urllib.error.URLError:
            break
        except Exception:
            continue

    return get_smart_fallback(user_message, context)

class BadmintonServerHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        try:
            msg = "%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args)
            sys.stdout.write(msg)
            sys.stdout.flush()
        except Exception:
            pass

    def _get_allowed_origin(self):
        """Return the same-origin echo for CORS, or None for non-browser requests."""
        origin = self.headers.get("Origin", "")
        # Only echo back origins that match our own host (same-site)
        host = self.headers.get("Host", "")
        if not origin:
            return None
        # Allow localhost and same host
        allowed = [f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}",
                   f"https://localhost:{PORT}", f"https://127.0.0.1:{PORT}"]
        # Also allow the deployment host if set
        deploy_host = os.environ.get("ALLOWED_ORIGIN", "")
        if deploy_host:
            allowed.append(deploy_host.rstrip("/"))
        if origin in allowed or (host and (f"http://{host}" == origin or f"https://{host}" == origin)):
            return origin
        return None

    def _check_csrf_origin(self):
        """For state-mutating cookie-authenticated requests, verify Origin or Referer.
        Returns True if safe, False if CSRF suspected."""
        origin = self.headers.get("Origin", "")
        referer = self.headers.get("Referer", "")
        host = self.headers.get("Host", "")
        # If no Origin/Referer present and not a same-origin API call, allow
        # (non-browser clients, curl, etc. — they can't carry HttpOnly cookies anyway)
        if not origin and not referer:
            return True
        check_str = origin or referer
        if host and host in check_str:
            return True
        # Allow localhost in dev
        for lh in ["localhost", "127.0.0.1"]:
            if lh in check_str:
                return True
        # Allow configured deploy origin
        deploy_host = os.environ.get("ALLOWED_ORIGIN", "")
        if deploy_host and deploy_host.rstrip("/") in check_str:
            return True
        return False

    def _parse_auth_cookie(self):
        """Parse the HttpOnly auth_token cookie from request headers.
        Returns the raw JWT string or None."""
        cookie_header = self.headers.get("Cookie", "")
        if not cookie_header:
            return None
        try:
            cookie = http.cookies.SimpleCookie(cookie_header)
            if "auth_token" in cookie:
                return cookie["auth_token"].value
        except Exception:
            pass
        return None

    def _authenticate_request(self):
        """Try cookie first, then Authorization Bearer header.
        Returns decoded payload dict or None."""
        # 1. Prefer HttpOnly cookie (most secure)
        token = self._parse_auth_cookie()
        if token:
            payload = decode_token(token)
            if payload:
                return payload
        # 2. Fall back to Authorization header (for backward-compat API clients)
        auth_header = self.headers.get("Authorization", "")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            payload = decode_token(token)
            if payload:
                return payload
        return None

    def _get_authenticated_room_member(self, room_id):
        auth = self._authenticate_request()
        if not auth or not auth.get("sub"):
            return None, None, 401
        with CENTRAL_DATABASE_LOCK:
            data = db_manager.load_data() or {}
        user = next((item for item in data.get("users", [])
                     if isinstance(item, dict) and str(item.get("id")) == str(auth["sub"])), None)
        room = next((item for item in data.get("matchmaking_rooms", [])
                     if isinstance(item, dict) and str(item.get("id")) == str(room_id)), None)
        if not user or not room:
            return user, room, 404 if user else 401
        user_id = str(user.get("id"))
        user_name = str(user.get("name") or "").strip().casefold()
        is_member = user_id == str(room.get("host_id") or "")
        is_member = is_member or (user_name and user_name == str(room.get("host_name") or "").strip().casefold())
        is_member = is_member or any(
            isinstance(player, dict) and (
                user_id == str(player.get("id") or "") or
                (user_name and user_name == str(player.get("name") or "").strip().casefold())
            )
            for player in (room.get("players") or [])
        )
        return (user, room, 200) if is_member else (user, room, 403)

    def _build_auth_cookie(self, token: str, max_age: int = 60 * 60 * 24 * 7) -> str:
        """Build a Set-Cookie header value for the auth token.
        Always sets Secure in production (ENVIRONMENT in production/prod or HTTPS enabled)."""
        env = os.environ.get("ENVIRONMENT", "").strip().lower()
        is_https = os.environ.get("HTTPS", "").lower() in ("1", "true", "yes", "on") or env in ("production", "prod")
        secure_flag = "; Secure" if is_https else ""
        # Use Lax for MoMo redirect (GET-based redirect must carry cookie)
        return (
            f"auth_token={token}; Path=/; HttpOnly; SameSite=Lax"
            f"{secure_flag}; Max-Age={max_age}"
        )

    def _build_clear_cookie(self) -> str:
        """Build a Set-Cookie that immediately expires the auth cookie.
        Preserves identical Path, HttpOnly, SameSite, and Secure flags to guarantee removal."""
        env = os.environ.get("ENVIRONMENT", "").strip().lower()
        is_https = os.environ.get("HTTPS", "").lower() in ("1", "true", "yes", "on") or env in ("production", "prod")
        secure_flag = "; Secure" if is_https else ""
        return (
            f"auth_token=; Path=/; HttpOnly; SameSite=Lax"
            f"{secure_flag}; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT"
        )

    def end_headers(self):
        allowed_origin = self._get_allowed_origin()
        if allowed_origin:
            self.send_header("Access-Control-Allow-Origin", allowed_origin)
            self.send_header("Access-Control-Allow-Credentials", "true")
        else:
            # Non-browser or cross-origin: still need CORS for public API assets
            self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Cache-Control, Authorization")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        chat_events_match = re.fullmatch(r"/api/chat/rooms/([^/]+)/events", urllib.parse.urlsplit(self.path).path)
        if chat_events_match:
            room_id = urllib.parse.unquote(chat_events_match.group(1))
            _, _, auth_status = self._get_authenticated_room_member(room_id)
            if auth_status != 200:
                self.send_response(auth_status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return

            subscriber = queue.Queue(maxsize=100)
            _add_chat_subscriber(room_id, subscriber)
            self.protocol_version = "HTTP/1.1"
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-transform")
            self.send_header("Connection", "keep-alive")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()
            try:
                self.wfile.write(b": connected\n\n")
                self.wfile.flush()
                while True:
                    try:
                        message = subscriber.get(timeout=15)
                        event_data = json.dumps(message, ensure_ascii=False, separators=(",", ":"))
                        self.wfile.write(f"data: {event_data}\n\n".encode("utf-8"))
                    except queue.Empty:
                        self.wfile.write(b": keep-alive\n\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                _remove_chat_subscriber(room_id, subscriber)
            return

        if self.path == "/health" or self.path == "/api/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "healthy",
                "service": "badminton-ai-web",
                "version": "1.0.0"
            }).encode("utf-8"))
            return

        if self.path == "/api/database":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            data = db_manager.load_data()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            return

        if self.path == "/api/db/status" or self.path == "/api/database/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(db_manager.get_status(), ensure_ascii=False, indent=2).encode("utf-8"))
            return

        if self.path == "/api/sqlite/download":
            db_path = os.path.join(os.path.dirname(__file__), "badminton.db")
            if os.path.exists(db_path):
                self.send_response(200)
                self.send_header("Content-Type", "application/x-sqlite3")
                self.send_header("Content-Disposition", 'attachment; filename="badminton.db"')
                with open(db_path, "rb") as f:
                    content = f.read()
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_response(404)
                self.end_headers()
            return

        if self.path == "/api/sqlite/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            try:
                import sqlite_sync
                conn = sqlite_sync.get_connection()
                data = sqlite_sync.export_sqlite_to_dict(conn)
                conn.close()
                self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
            except Exception as e:
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        if self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            db_path = os.path.join(os.path.dirname(__file__), "badminton.db")
            has_sqlite = os.path.exists(db_path)
            has_gemini = bool(get_gemini_api_key())
            self.wfile.write(json.dumps({
                "status": "running",
                "server": "Badminton AI Central DB Server",
                "sqlite_enabled": has_sqlite,
                "sqlite_file": "badminton.db" if has_sqlite else None,
                "gemini_configured": has_gemini,
                "model": "gemini-1.5-flash"
            }).encode("utf-8"))
            return

        # =========================================================================
        # MATCHMAKING GET ROUTES
        # =========================================================================
        if "/matchmaking/tiers" in self.path:
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"tiers": elo_engine.DEFAULT_ELO_TIERS}, ensure_ascii=False).encode("utf-8"))
            return

        if "/matchmaking/profile" in self.path:
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            user_id = 1
            if "user_id=" in self.path:
                try:
                    user_id = int(self.path.split("user_id=")[1].split("&")[0])
                except Exception:
                    pass
            db_data = {}
            if os.path.exists(DATA_FILE):
                try:
                    with open(DATA_FILE, "r", encoding="utf-8") as f:
                        db_data = json.load(f)
                except Exception:
                    pass
            users = db_data.get("users", [])
            profiles = db_data.get("player_profiles", [])
            user = next((u for u in users if str(u.get("id")) == str(user_id)), users[0] if users else {"id": user_id, "name": "Người chơi"})
            profile = next((p for p in profiles if str(p.get("user_id")) == str(user_id)), None)
            if not profile:
                profile = {
                    "id": user_id,
                    "user_id": user_id,
                    "gender": "Nam",
                    "birth_year": 1998,
                    "preferred_area": "Cầu Giấy, Hà Nội",
                    "skill_level": "Trung Bình Khá",
                    "current_elo": user.get("elo_rating") if isinstance(user.get("elo_rating"), int) else 1200,
                    "games_played": 15,
                    "wins": 10,
                    "losses": 5,
                    "rating_confidence": 0.65,
                    "is_searching": True,
                    "available_time": "18:00 - 21:00",
                    "preferred_court": "CLB Cầu Lông Catchy Badminton Arena",
                    "play_style": "Công thủ toàn diện",
                    "streak": "+2W"
                }
            tier = elo_engine.get_tier_for_elo(profile.get("current_elo", 1200))
            profile["tier_display"] = tier["display"]
            profile["full_name"] = user.get("name") or user.get("full_name")
            self.wfile.write(json.dumps(profile, ensure_ascii=False).encode("utf-8"))
            return

        if "/matchmaking/history" in self.path:
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            db_data = {}
            if os.path.exists(DATA_FILE):
                try:
                    with open(DATA_FILE, "r", encoding="utf-8") as f:
                        db_data = json.load(f)
                except Exception:
                    pass
            histories = db_data.get("elo_histories", [])
            self.wfile.write(json.dumps(histories, ensure_ascii=False).encode("utf-8"))
            return

        if "/matchmaking/simulate" in self.path:
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            elo_a = 1500
            elo_b = 1510
            if "elo_a=" in self.path:
                try:
                    elo_a = int(self.path.split("elo_a=")[1].split("&")[0])
                except Exception:
                    pass
            if "elo_b=" in self.path:
                try:
                    elo_b = int(self.path.split("elo_b=")[1].split("&")[0])
                except Exception:
                    pass
            exp_a = elo_engine.calculate_expected_score(elo_a, elo_b)
            k_a = elo_engine.get_dynamic_k_factor(20, elo_a)
            k_b = elo_engine.get_dynamic_k_factor(20, elo_b)
            win_delta_a = round(k_a * (1.0 - exp_a))
            loss_delta_a = round(k_a * (0.0 - exp_a))
            win_delta_b = round(k_b * (1.0 - (1.0 - exp_a)))
            loss_delta_b = round(k_b * (0.0 - (1.0 - exp_a)))
            diff = abs(elo_a - elo_b)
            res = {
                "player_a": {
                    "elo": elo_a, "win_probability": round(exp_a * 100, 1),
                    "if_win_delta": f"+{win_delta_a}", "if_loss_delta": f"{loss_delta_a}",
                    "tier": elo_engine.get_tier_for_elo(elo_a)["display"]
                },
                "player_b": {
                    "elo": elo_b, "win_probability": round((1.0 - exp_a) * 100, 1),
                    "if_win_delta": f"+{win_delta_b}", "if_loss_delta": f"{loss_delta_b}",
                    "tier": elo_engine.get_tier_for_elo(elo_b)["display"]
                },
                "elo_difference": diff,
                "handicap_suggestion": f"AI Handicap: Chấp {round(diff / 40)} điểm/set" if diff > 150 else "Đồng banh (0 điểm)"
            }
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))
            return

        if "/matchmaking/anti-cheat/audit" in self.path:
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            db_data = {}
            if os.path.exists(DATA_FILE):
                try:
                    with open(DATA_FILE, "r", encoding="utf-8") as f:
                        db_data = json.load(f)
                except Exception:
                    pass
            histories = db_data.get("elo_histories", [])
            matches_data = [
                {"match_id": h.get("match_id"), "elo_delta": h.get("elo_change", 0), "result": "WIN" if h.get("elo_change", 0) > 0 else "LOSS", "opponent_elo": 1400}
                for h in histories
            ]
            anomaly_report = elo_engine.detect_match_anomalies(1, matches_data)
            self.wfile.write(json.dumps(anomaly_report, ensure_ascii=False).encode("utf-8"))
            return

        # NEW PAYMENT STATUS ENDPOINT
        if self.path.startswith('/api/payment/status'):
            # Parse query parameters
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            booking_code_list = query_params.get('booking_code')
            if not booking_code_list or not booking_code_list[0]:
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"detail": "Missing booking_code parameter"}).encode("utf-8"))
                return
            booking_code = booking_code_list[0]

            # Authenticate user — cookie first, then Bearer fallback
            payload = self._authenticate_request()
            user_info = None
            if payload:
                user_info = {"id": payload.get("sub"), "role": payload.get("role")}
            if not user_info:
                self.send_response(401)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"detail": "Xác thực thất bại. Vui lòng đăng nhập lại."}).encode("utf-8"))
                return
            user_id = user_info["id"]

            # Load database
            db_data = db_manager.load_data()
            if not db_data:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"detail": "Database not available"}).encode("utf-8"))
                return

            # Find user by ID to get phone
            user = None
            for u in db_data.get("users", []):
                if u.get("id") == user_id:
                    user = u
                    break
            if not user:
                self.send_response(401)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"detail": "User not found"}).encode("utf-8"))
                return
            user_phone = user.get("phone")

            # Find booking by booking_code
            booking = None
            for b in db_data.get("booking_orders", []):
                if b.get("booking_code") == booking_code:
                    booking = b
                    break
            if not booking:
                self.send_response(404)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"detail": "Booking not found"}).encode("utf-8"))
                return

            # Anti-IDOR: check that the booking belongs to the user
            if booking.get("user_phone") != user_phone:
                self.send_response(403)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"detail": "Forbidden: booking does not belong to user"}).encode("utf-8"))
                return

            # Determine payment status
            order_status = booking.get("order_status", "")
            deposit_status = booking.get("deposit_status", "")

            # We'll define success if order_status is "Đã Xác Nhận" and deposit_status indicates paid
            # For simplicity, we'll consider deposit_status containing "Đã Cọc" as paid.
            if "Đã Xác Nhận" in order_status and ("Đã Cọc" in deposit_status or "paid" in deposit_status.lower()):
                payment_status = "success"
                message = "Thanh toán thành công! Đang chuyển bạn đến trang vé QR..."
            elif "Chờ Xác Nhận" in order_status or "Chờ Cọc" in deposit_status:
                payment_status = "pending"
                message = "Thanh toán vẫn đang xử lý. Vui lòng chờ trong giây lát..."
            else:
                payment_status = "failed"
                message = "Thanh toán không thành công. Vui lòng thử lại hoặc chọn phương thức thanh toán khác."

            # Prepare response
            response = {
                "payment_status": payment_status,
                "message": message,
                "booking_code": booking_code,
                # We can also include other info if needed by the frontend
                "order_status": order_status,
                "deposit_status": deposit_status
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))
            return

        # Handle client-side routing for single-page application
        # If it's an API request that wasn't handled above, return 404
        if self.path.startswith('/api/'):
            self.send_response(404)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"detail": "API endpoint not found"}).encode("utf-8"))
            return

        # For non-API requests, check if the requested file exists
        path = urllib.parse.urlparse(self.path).path
        # Remove leading slash and prevent directory traversal
        path = path.lstrip('/')
        if '..' in path or path.startswith('/'):
            # Prevent directory traversal attacks
            self.send_response(403)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Forbidden")
            return

        # Check if file exists
        file_path = os.path.join(os.getcwd(), path)
        if os.path.isfile(file_path) and not os.path.isdir(file_path):
            # File exists, serve it normally
            return super().do_GET()
        else:
            # File doesn't exist, serve index.html for client-side routing
            self.path = '/index.html'
            return super().do_GET()

    def do_POST(self):
        # Enforce CSRF protection for state-mutating requests when client presents auth cookie
        if self._parse_auth_cookie() and not self._check_csrf_origin():
            self.send_response(403)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"detail": "CSRF verification failed: Origin/Referer disallowed"}).encode("utf-8"))
            return

        chat_message_match = re.fullmatch(r"/api/chat/rooms/([^/]+)/messages", urllib.parse.urlsplit(self.path).path)
        if chat_message_match:
            room_id = urllib.parse.unquote(chat_message_match.group(1))
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                if content_length <= 0 or content_length > 20_000:
                    raise ValueError("Nội dung tin nhắn không hợp lệ.")
                incoming = json.loads(self.rfile.read(content_length).decode("utf-8"))
                if not isinstance(incoming, dict):
                    raise ValueError("Dữ liệu tin nhắn không hợp lệ.")
                text = str(incoming.get("text") or "").strip()
                if not text or len(text) > 4_000:
                    raise ValueError("Tin nhắn phải có từ 1 đến 4.000 ký tự.")

                user, room, auth_status = self._get_authenticated_room_member(room_id)
                if auth_status != 200:
                    self.send_response(auth_status)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return

                message_id = str(incoming.get("id") or f"chat_{secrets.token_urlsafe(18)}")[:120]
                is_ai_message = bool(incoming.get("isAI", False))
                requested_sender = str(incoming.get("sender") or "")
                ai_senders = {"🤖 AI Match Referee", "🤖 AI Virtual Coach"}
                message = {
                    "id": message_id,
                    "sender": requested_sender if is_ai_message and requested_sender in ai_senders else str(user.get("name") or "Thành viên"),
                    "text": text,
                    "time": str(incoming.get("time") or time.strftime("%H:%M"))[:16],
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "isAI": is_ai_message,
                }
                existing_messages = room.get("chat_messages") or []
                stored_message = next((item for item in existing_messages
                                       if isinstance(item, dict) and str(item.get("id")) == message_id), None)
                if stored_message:
                    message = stored_message
                else:
                    _save_central_database_update({"matchmaking_rooms": [{"id": room.get("id"), "chat_messages": [message]}]})
                _publish_room_chat_message(room_id, message)

                response_body = json.dumps({"success": True, "message": message}, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(response_body)))
                self.end_headers()
                self.wfile.write(response_body)
            except (ValueError, json.JSONDecodeError) as error:
                response_body = json.dumps({"detail": str(error)}, ensure_ascii=False).encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(response_body)))
                self.end_headers()
                self.wfile.write(response_body)
            except Exception:
                response_body = json.dumps({"detail": "Không thể lưu tin nhắn."}, ensure_ascii=False).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(response_body)))
                self.end_headers()
                self.wfile.write(response_body)
            return

        if self.path == "/api/login":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            try:
                incoming = json.loads(post_data.decode("utf-8"))
            except Exception:
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"detail": "Invalid JSON"}).encode("utf-8"))
                return
            phone = incoming.get("phone")
            password = incoming.get("password")
            if not isinstance(phone, str) or not isinstance(password, str) or not phone.strip() or not password:
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"detail": "Missing phone or password"}).encode("utf-8"))
                return
            phone = phone.strip()
            if len(phone) > 32 or len(password) > 128:
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"detail": "Invalid phone or password format"}).encode("utf-8"))
                return
            try:
                remaining = asyncio.run(remaining_lock_seconds(phone))
            except Exception:
                self.send_response(503)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"detail": "Login protection is temporarily unavailable"}).encode("utf-8"))
                return
            if remaining:
                self.send_response(429)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Retry-After", str(remaining))
                self.end_headers()
                self.wfile.write(json.dumps({"detail": f"Tài khoản tạm khóa. Vui lòng thử lại sau {remaining} giây."}, ensure_ascii=False).encode("utf-8"))
                return
            db_data = db_manager.load_data()
            if not db_data:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"detail": "Database not available"}).encode("utf-8"))
                return
            users = db_data.get("users", [])
            user = None
            for u in users:
                if u.get("phone") == phone:
                    # Verify password
                    if verify_password(password, u.get("password", "")):
                        user = u
                        break
            if not user:
                try:
                    remaining = asyncio.run(record_failed_login(phone))
                except Exception:
                    self.send_response(503)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(json.dumps({"detail": "Login protection is temporarily unavailable"}).encode("utf-8"))
                    return
                self.send_response(429 if remaining else 401)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                if remaining:
                    self.send_header("Retry-After", str(remaining))
                self.end_headers()
                detail = "Bạn đã nhập sai mật khẩu 5 lần. Tài khoản tạm khóa trong 5 phút." if remaining else "Invalid phone or password"
                self.wfile.write(json.dumps({"detail": detail}, ensure_ascii=False).encode("utf-8"))
                return
            try:
                asyncio.run(clear_failed_logins(phone))
            except Exception:
                self.send_response(503)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"detail": "Login protection is temporarily unavailable"}).encode("utf-8"))
                return
            # Create access token
            access_token = create_access_token(
                subject=user.get("id"),
                role=user.get("role")
            )
            # Issue HttpOnly cookie — JS never receives the raw token
            cookie_header = self._build_auth_cookie(access_token)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Set-Cookie", cookie_header)
            self.end_headers()
            # Return ONLY user info — no access_token in JSON body
            self.wfile.write(json.dumps({
                "user": {
                    "id": user.get("id"),
                    "name": user.get("name"),
                    "phone": user.get("phone"),
                    "role": user.get("role")
                }
            }, ensure_ascii=False).encode("utf-8"))
            return
        # =========================================================================
        # LOGOUT ENDPOINT — expires the HttpOnly cookie server-side
        # =========================================================================
        if self.path == "/api/logout":
            clear_cookie = self._build_clear_cookie()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Set-Cookie", clear_cookie)
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "message": "Đã đăng xuất. Cookie xác thực đã được xóa phía server.",
                "note": "JWT stateless: token vẫn hợp lệ nếu bị đánh cắp trước khi hết hạn. Triển khai token denylist nếu cần revocation thực sự."
            }, ensure_ascii=False).encode("utf-8"))
            return

        # AI CHATBOT PROXY ENDPOINT (Secures GEMINI_API_KEY on Server)
        if self.path == "/api/chat" or self.path == "/api/v1/ai/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)

            # Check if explicit credentials were provided (Cookie or Bearer)
            cookie_token = self._parse_auth_cookie()
            auth_header = self.headers.get("Authorization", "")
            bearer_token = auth_header.split(" ", 1)[1].strip() if (auth_header and auth_header.startswith("Bearer ")) else None

            # Authenticate — cookie first, Bearer fallback
            payload_chat = self._authenticate_request()
            if (cookie_token or bearer_token) and not payload_chat:
                self.send_response(401)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "detail": "Token không hợp lệ hoặc đã hết hạn"
                }, ensure_ascii=False).encode("utf-8"))
                return

            user_info = None
            if payload_chat:
                user_info = {"id": payload_chat.get("sub"), "role": payload_chat.get("role")}
            user_msg = ""
            context = ""
            try:
                incoming = json.loads(post_data.decode("utf-8"))
                user_msg = incoming.get("message", "")
                conversation_id = incoming.get("conversation_id", None)
                messages = incoming.get("messages", [])
                context = incoming.get("context", "")

                chatbot_svc = get_chatbot_service()
                result = asyncio.run(chatbot_svc.handle_message(
                    message=user_msg,
                    conversation_id=conversation_id,
                    context=context,
                    history=messages,
                    user_info=user_info
                ))

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": True,
                    "answer": result["answer"],
                    "reply": result["reply"],
                    "conversation_id": result["conversation_id"],
                    "message_id": result["message_id"],
                    "user_id": result.get("user_id"),
                    "status": result["status"],
                    "retrieval_status": result.get("retrieval_status"),
                    "sources": result.get("sources", [])
                }, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                err_msg = str(e)
                if "key=" in err_msg.lower():
                    err_msg = re.sub(r'key=[^&\s]+', 'key=***', err_msg, flags=re.IGNORECASE)
                fallback_reply = (
                    "⚠️ **Thông báo từ Trợ lý AI BADMINTON.AI**:\n\n"
                    "Hiện tại hệ thống AI đang gặp gián đoạn tạm thời khi kết nối với mô hình ngôn ngữ "
                    "nên chưa thể truy xuất dữ liệu xác thực thời gian thực cho câu hỏi của bạn.\n\n"
                    "👉 Để đảm bảo thông tin chính xác nhất, bạn vui lòng:\n"
                    "- Tra cứu trực tiếp danh sách sân, bảng giá và lịch trống tại giao diện chính của website.\n"
                    "- Hoặc liên hệ ban quản lý sân qua thông tin liên hệ trên website.\n\n"
                    "Rất xin lỗi bạn vì sự bất tiện này! 🏸"
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": True,
                    "answer": fallback_reply,
                    "reply": fallback_reply,
                    "conversation_id": incoming.get("conversation_id") if 'incoming' in locals() else None,
                    "message_id": "msg_fallback",
                    "user_id": user_info.get("id") if user_info else None,
                    "status": "fallback",
                    "fallback": True,
                    "retrieval_status": "data_unavailable",
                    "sources": []
                }, ensure_ascii=False).encode("utf-8"))
            return

        if self.path == "/api/database":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            try:
                incoming_data = json.loads(post_data.decode("utf-8"))
                if not isinstance(incoming_data, dict):
                    raise ValueError("Dữ liệu gửi lên phải là một object JSON.")
                merged_database = _save_central_database_update(incoming_data)

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": True, 
                    "database_type": db_manager.db_type,
                    "active_driver": db_manager.active_driver,
                    "users_count": len(merged_database.get("users", [])),
                    "facilities_count": len(merged_database.get("facilities", []))
                }).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
                return
        # =========================================================================
        # MATCHMAKING POST ROUTES
        # =========================================================================
        if "/matchmaking/find" in self.path:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            db_data = {}
            if os.path.exists(DATA_FILE):
                try:
                    with open(DATA_FILE, "r", encoding="utf-8") as f:
                        db_data = json.load(f)
                except Exception:
                    pass
            req = {}
            try:
                req = json.loads(post_data.decode("utf-8"))
            except Exception:
                    pass

            user_elo = req.get("player_elo", 1450)
            wait_time = req.get("wait_time_seconds", 0)
            dynamic_range = elo_engine.get_dynamic_elo_range(wait_time)
            effective_delta = max(req.get("max_elo_delta", 100), dynamic_range)

            users = db_data.get("users", [])
            candidates = []
            cand_dicts = []
            player_profile = {
                "name": req.get("player_name", "Bạn"),
                "elo": user_elo,
                "preferred_time": req.get("preferred_time", "18:00 - 20:00"),
                "preferred_area": req.get("preferred_area", "Cầu Giấy"),
                "match_type": req.get("match_type", "SINGLES")
            }
            for u in users:
                if u.get("role") != "CUSTOMER":
                    continue
                u_elo = u.get("elo_rating") if isinstance(u.get("elo_rating"), int) else 1200
                diff = abs(user_elo - u_elo)
                if diff <= effective_delta and u.get("name") != player_profile["name"]:
                    cand_data = {
                        "id": u.get("id"),
                        "name": u.get("name"),
                        "elo": u_elo,
                        "preferred_time": req.get("preferred_time", "18:00 - 20:00"),
                        "preferred_area": req.get("preferred_area", "Cầu Giấy"),
                        "match_type": req.get("match_type", "SINGLES"),
                        "distance_km": 2.5
                    }
                    score_res = elo_engine.calculate_match_score(player_profile, cand_data)
                    candidates.append(score_res)
                    cand_dicts.append(score_res)

            candidates.sort(key=lambda x: x["match_score"], reverse=True)
            cand_dicts.sort(key=lambda x: x["match_score"], reverse=True)
            ai_recom = elo_engine.generate_ai_match_recommendation(player_profile, cand_dicts)
            response_payload = {
                "player_elo": user_elo,
                "player_tier": elo_engine.get_tier_for_elo(user_elo)["display"],
                "dynamic_elo_range": effective_delta,
                "wait_time_seconds": wait_time,
                "total_candidates": len(candidates),
                "candidates": candidates[:10],
                "ai_recommendation": ai_recom
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(response_payload, ensure_ascii=False).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()


if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))
    db_manager.initialize()
    status = db_manager.get_status()
    print(
        f"📊 Database Engine active: {status['active_driver']} "
        f"({status['database_type']}) - {status['users_count']} users, "
        f"{status['facilities_count']} facilities"
    )

    http.server.ThreadingHTTPServer.allow_reuse_address = True
    with http.server.ThreadingHTTPServer(("0.0.0.0", PORT), BadmintonServerHandler) as httpd:
        print(f"🏸 Badminton AI Threading Server running on port {PORT}")
        httpd.serve_forever()
