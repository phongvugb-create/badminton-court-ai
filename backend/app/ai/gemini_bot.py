import os
import aiohttp
from app.config import settings
import logging

logger = logging.getLogger(__name__)

async def ask_gemini_badminton(question: str, system_context: str = "") -> str:
    """
    Query Google Gemini API for intelligent badminton court assistance.
    Falls back to smart rule-based assistant if API key is not configured.
    """
    api_key = settings.GEMINI_API_KEY
    
    if not api_key:
        return get_fallback_answer(question)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
    
    prompt = f"""
    Bạn là AI Trợ Lý Tư Vấn Sân Cầu Lông & Pickleball (Đề tài 36).
    Thông tin ngữ cảnh hệ thống:
    {system_context}
    
    Câu hỏi của khách hàng: {question}
    Hãy trả lời nhiệt tình, súc tích, ngắn gọn, chuẩn xác bằng tiếng Việt.
    """

    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        return text
                else:
                    logger.warning(f"Gemini API returned error code {response.status}")
    except Exception as e:
        logger.error(f"Error connecting to Gemini API: {e}")

    return get_fallback_answer(question)

def get_fallback_answer(question: str) -> str:
    q = question.lower()
    if "giá" in q or "tiền" in q or "bảng giá" in q:
        return "🏸 Giá thuê sân dao động từ 70.000đ - 160.000đ/giờ tùy vào khung giờ. Hệ thống tự động giảm giá 15% vào giờ hành chính (8h-14h) và phụ thu 25% vào khung giờ vàng (17h-21h)!"
    elif "đặt sân" in q or "giữ chỗ" in q:
        return "⏰ Bạn có thể chọn ngày, sân và khung giờ trực tiếp trên hệ thống. Khung giờ bạn chọn sẽ được khóa giữ chỗ nguyên tử trong vòng 10 phút để bạn hoàn tất đặt cọc 50%!"
    elif "ghép kèo" in q or "tìm bạn" in q or "elo" in q:
        return "🏆 Tính năng AI Matchmaking sẽ phân tích điểm ELO của bạn (mặc định 1000 - 1500) để gợi ý các phòng ghép kèo phù hợp nhất, tránh tình trạng chênh lệch trình độ!"
    elif "hủy sân" in q or "đổi giờ" in q:
        return "📋 Bạn được hủy sân miễn phí và hoàn cọc 100% trước 24 giờ so với giờ thi đấu đã đặt. Vui lòng vào mục 'Lịch Đặt Của Tôi' để thao tác nhé!"
    else:
        return "Xin chào! Em là AI Trợ Lý Sân Cầu Lông. Em có thể hỗ trợ bạn tìm sân gần nhất theo định vị GPS, kiểm tra giá động thông minh, hoặc gợi ý phòng ghép kèo ELO phù hợp. Bạn cần trợ giúp gì ạ?"
