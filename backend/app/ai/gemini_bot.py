import os
import json
import asyncio
import urllib.request
import urllib.error
from app.config import settings
import logging

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """Bạn là Trợ lý AI Thông Minh (BADMINTON.AI Virtual Assistant) của nền tảng Quản Lý & Cho Thuê Sân Cầu Lông & Pickleball BADMINTON.AI.
Nhiệm vụ của bạn:
- Tư vấn nhiệt tình, ngắn gọn, thân thiện và chính xác cho khách hàng.
- Nắm vững kiến thức hệ thống:
  + Danh sách 48+ cụm sân cầu lông tại Hà Nội (Cầu Giấy, Hoàng Mai, Đống Đa, Thanh Xuân, Nam Từ Liêm, Ba Đình, Long Biên, Tây Hồ...).
  + Bảng giá thuê sân: 70.000đ - 160.000đ/giờ.
  + Cơ chế AI Dynamic Pricing (UC003): Tự động giảm giá 15% giờ hành chính (8h-14h) để kích cầu, phụ thu 25% khung giờ vàng (17h-21h) tối ưu doanh thu.
  + Giữ chỗ 10 phút (UC005): Khóa nguyên tử chống xung đột đặt trùng, cọc 50% qua VNPay/Chuyển khoản.
  + AI Matchmaking & Điểm ELO (UC006): Ghép kèo đấu công bằng, tìm bạn chơi theo trình độ ELO 1000 - 2000+.
  + Tư vấn dụng cụ: Chọn vợt công (Smash - nặng đầu 3U/4U), thủ (phản tạt - nhẹ đầu 4U/5U), cân bằng, căng dây 10.5 - 11.5 kg.
  + Chính sách hoàn cọc: Hoàn 100% khi hủy trước 24 giờ thi đấu.
- Luôn trả lời bằng tiếng Việt, định dạng Markdown rõ ràng, dùng emoji thể thao sinh động."""

def _sync_gemini_call(api_key: str, question: str, full_system_prompt: str) -> str:
    models = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-pro"]
    for model_name in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": question}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1000}
        }
        if "pro" not in model_name:
            payload["systemInstruction"] = {"parts": [{"text": full_system_prompt}]}
        else:
            payload["contents"][0]["parts"][0]["text"] = f"[HƯỚNG DẪN]: {full_system_prompt}\n\n[CÂU HỎI]: {question}"

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and parts[0].get("text"):
                            return parts[0].get("text")
        except Exception as e:
            continue
    return ""

async def ask_gemini_badminton(question: str, system_context: str = "") -> str:
    """
    Query Google Gemini 1.5 Flash API with systemInstruction.
    Falls back to smart rule-based assistant if API key is not configured or network error occurs.
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key or api_key.startswith("YOUR_"):
        api_key = os.getenv("GEMINI_API_KEY", "")

    if not api_key:
        return get_fallback_answer(question)

    context_addon = f"\nThông tin ngữ cảnh hiện tại từ trang web:\n{system_context}" if system_context else ""
    full_system_prompt = SYSTEM_INSTRUCTION + context_addon

    try:
        reply = await asyncio.to_thread(_sync_gemini_call, api_key, question, full_system_prompt)
        if reply:
            return reply
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")

    return get_fallback_answer(question)

def get_fallback_answer(question: str) -> str:
    q = (question or "").lower()
    if "giá" in q or "tiền" in q or "bảng giá" in q or "chi phí" in q:
        return "🏸 **Bảng Giá Thuê Sân BADMINTON.AI**:\n- **Giờ hành chính (8h - 14h)**: ~70.000đ - 100.000đ/h *(AI giảm giá 15% kích cầu)*\n- **Giờ bình thường (14h - 17h)**: ~100.000đ - 120.000đ/h\n- **Giờ vàng cao điểm (17h - 21h)**: ~130.000đ - 160.000đ/h *(Phụ thu AI +25%)*\n\nBạn có thể vào mục **Đặt Sân** để xem biểu đồ giá trực tiếp theo thời gian thực nhé!"
    elif "đặt sân" in q or "giữ chỗ" in q or "cọc" in q or "thanh toán" in q:
        return "⏰ **Quy Trình Giữ Chỗ & Đặt Sân**:\n1. Chọn cụm sân & khung giờ mong muốn.\n2. Hệ thống áp dụng **Khóa Giữ Chỗ Nguyên Tử (10 Phút)** để chống trùng lịch.\n3. Thanh toán đặt cọc 50% qua cổng VNPay hoặc Chuyển khoản QR.\n4. Nhận mã QR check-in vào sân tức thì!"
    elif "ghép kèo" in q or "tìm bạn" in q or "elo" in q or "đội" in q:
        return "🏆 **AI Matchmaking & Xếp Hạng ELO**:\n- Hệ thống tự động phân tích điểm ELO (1000 - 2000+) để gợi ý phòng ghép kèo công bằng nhất.\n- Bạn có thể tạo phòng mới hoặc tham gia phòng ghép tại tab **AI Ghép Đội / Kèo Đấu** để giao lưu với các tay vợt cùng trình độ!"
    elif "vợt" in q or "chọn vợt" in q or "dụng cụ" in q or "smash" in q:
        return "🏸 **Tư Vấn Chọn Vợt Cầu Lông Phù Hợp**:\n- **Lối chơi Tấn công / Smash mạnh**: Vợt nặng đầu (Head-Heavy, điểm cân bằng > 295mm), trọng lượng 3U/4U, thân cứng (ví dụ: Yonex Astrox 88D/99/100ZZ, Lining Tectonic 7).\n- **Lối chơi Thủ / Phản tạt / Linh hoạt**: Vợt nhẹ đầu (Head-Light, < 285mm), trọng lượng 4U/5U, thân dẻo (ví dụ: Yonex Nanoflare 700/800).\n- **Lối chơi Toàn diện**: Vợt cân bằng 290mm (Arcsaber 11 Pro, Lining Halbertec 8000).\n- **Độ căng cước**: Người mới chơi 9.5 - 10.5 kg, phong trào 10.5 - 11.5 kg."
    elif "hủy sân" in q or "đổi giờ" in q or "hoàn cọc" in q:
        return "📋 **Chính Sách Hoàn Hủy Sân**:\n- **Trước 24 giờ**: Miễn phí hủy, hoàn cọc **100%** vào ví tài khoản.\n- **Trước 12 - 24 giờ**: Hoàn cọc 50%.\n- **Dưới 12 giờ**: Không hỗ trợ hoàn cọc theo quy định của ban quản lý sân.\n\nBạn có thể quản lý tại mục **Lịch Đặt Của Tôi**."
    elif "gần" in q or "địa chỉ" in q or "khu vực" in q or "hà nội" in q:
        return "📍 **Cụm Sân Nổi Bật Tại Hà Nội**:\n- **Cầu Giấy**: Sân Cầu Lông Cầu Giấy Arena (Duy Tân), Nhà Thi Đấu Cầu Giấy (Trần Quý Kiên).\n- **Hoàng Mai**: Sân Cầu Lông Tân Khai (136 Tân Khai), Sân Đền Lừ.\n- **Đống Đa**: Sân Đại Học Y Hà Nội (Tôn Thất Tùng), Sân Hoàng Cầu.\n- **Thanh Xuân**: Sân Thể Thao Khương Đình, Sân Nhân Chính.\n\nHãy bấm vào tab **Bản Đồ** để định vị sân gần bạn nhất theo GPS nhé!"
    else:
        return "👋 Xin chào! Tôi là **Trợ lý AI Thông Minh BADMINTON.AI**.\n\nTôi có thể hỗ trợ bạn:\n- 📍 Tìm cụm sân gần nhất & xem sân còn trống.\n- ⚡ Tra cứu bảng giá thuê giờ hành chính / giờ vàng.\n- 🏸 Tư vấn chọn vợt & dụng cụ phù hợp phong cách chơi.\n- 🏆 Hướng dẫn ghép kèo giao lưu theo điểm ELO.\n- 📋 Quy định đặt cọc, thanh toán và hoàn hủy 24h.\n\nBạn muốn tìm hiểu thông tin gì ạ? Hãy nhắn cho tôi nhé! ✨🏸"
