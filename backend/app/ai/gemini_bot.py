import os
import json
import asyncio
import re
import urllib.request
import urllib.error
from app.config import settings
import logging

logger = logging.getLogger(__name__)

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "database.json")

SYSTEM_INSTRUCTION = """Bạn là Trợ lý AI Thông Minh (BADMINTON.AI Virtual Assistant) của nền tảng Quản Lý & Cho Thuê Sân Cầu Lông & Pickleball BADMINTON.AI.
Nhiệm vụ của bạn:
- Tư vấn nhiệt tình, ngắn gọn, thân thiện và chính xác cho khách hàng.
- Nắm vững kiến thức hệ thống:
  + Danh sách 48+ cụm sân cầu lông tại Hà Nội (Cầu Giấy, Hoàng Mai, Đống Đa, Thanh Xuân, Nam Từ Liêm, Bắc Từ Liêm, Ba Đình, Long Biên, Tây Hồ, Hai Bà Trưng, Hà Đông, Hoàn Kiếm...).
  + Bảng giá thuê sân: 50.000đ - 180.000đ/giờ.
  + Cơ chế AI Dynamic Pricing (UC003): Tự động giảm giá 15% giờ hành chính (8h-14h) để kích cầu, phụ thu 25% khung giờ vàng (17h-21h) tối ưu doanh thu.
  + Giữ chỗ 10 phút (UC005): Khóa nguyên tử chống xung đột đặt trùng, cọc 50% qua VNPay/Chuyển khoản QR.
  + AI Matchmaking & Điểm ELO (UC006): Ghép kèo đấu công bằng, tìm bạn chơi theo trình độ ELO 1000 - 2000+.
  + Tư vấn dụng cụ: Chọn vợt công (Smash - nặng đầu 3U/4U), thủ (phản tạt - nhẹ đầu 4U/5U), cân bằng, căng dây 10.5 - 11.5 kg.
  + Chính sách hoàn cọc (UC008): Hoàn 100% khi hủy trước 24 giờ thi đấu.
- Luôn trả lời bằng tiếng Việt, định dạng Markdown rõ ràng, dùng emoji thể thao sinh động."""

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
    "Long Biên": ["long biên", "long bien", "cổ linh", "việt hưng", "ngô gia tự", "thạch bàn", "đoàn khuê", "thượng thanh", "ngọc lâm", "bồ đề"],
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

def _sync_gemini_call(api_key: str, question: str, full_system_prompt: str) -> str:
    models = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-2.5-flash"]
    for model_name in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": question}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1000},
            "systemInstruction": {"parts": [{"text": full_system_prompt}]}
        }

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
        except Exception:
            continue
    return ""

async def ask_gemini_badminton(question: str, system_context: str = "") -> str:
    api_key = settings.GEMINI_API_KEY
    if not api_key or api_key.startswith("YOUR_"):
        api_key = os.getenv("GEMINI_API_KEY", "")

    if not api_key:
        return get_fallback_answer(question, system_context)

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

    context_addon = f"\nThông tin ngữ cảnh hiện tại từ trang web:\n{system_context}" if system_context else ""
    full_system_prompt = SYSTEM_INSTRUCTION + f"\n\nDANH SÁCH SÂN NỔI BẬT:\n{json.dumps(summary_facilities, ensure_ascii=False)}" + context_addon

    try:
        reply = await asyncio.to_thread(_sync_gemini_call, api_key, question, full_system_prompt)
        if reply:
            return reply
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")

    return get_fallback_answer(question, system_context)

def get_fallback_answer(question: str, context: str = "") -> str:
    q = (question or "").lower().strip()
    facilities = load_facilities()

    # 1. District / Price / Facility Search
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

    # 2. Dynamic Pricing
    if any(k in q for k in ["giá", "tiền", "bảng giá", "chi phí", "giờ vàng", "giờ hành chính", "phụ thu", "dynamic pricing"]):
        return (
            "🏸 **BẢNG GIÁ THUÊ SÂN & CƠ CHẾ AI DYNAMIC PRICING (UC003)**:\n\n"
            "Hệ thống BADMINTON.AI áp dụng thuật toán AI định giá linh hoạt theo thời gian thực:\n"
            "- 🟢 **Giờ Hành Chính (08:00 - 14:00)**: **50.000đ - 90.000đ/giờ** *(AI tự động giảm giá **15%** để kích cầu)*\n"
            "- 🟡 **Giờ Tiêu Chuẩn (14:00 - 17:00 & 21:00 - 23:00)**: **80.000đ - 110.000đ/giờ** *(Giá niêm yết chuẩn)*\n"
            "- 🔴 **Giờ Vàng Cao Điểm (17:00 - 21:00)**: **120.000đ - 160.000đ/giờ** *(Phụ thu AI **+25%** do nhu cầu cao)*\n\n"
            "💡 *Mẹo: Đặt sân khung giờ 8h - 14h hoặc sau 21h30 để nhận mức giá tiết kiệm nhất!*"
        )

    # 3. Booking & Atomic Lock
    if any(k in q for k in ["đặt sân", "giữ chỗ", "khóa 10 phút", "cọc", "thanh toán", "vnpay", "qr", "check-in"]):
        return (
            "⏰ **QUY TRÌNH ĐẶT SÂN & KHÓA NGUYÊN TỬ 10 PHÚT (UC005)**:\n\n"
            "1. **Chọn Sân & Giờ Chơi**: Duyệt danh sách sân hoặc tìm theo bản đồ GPS.\n"
            "2. **Khóa Giữ Chỗ (10 Phút)**: Cơ chế *Atomic Slot Lock* giữ lịch tức thì, chống hoàn toàn xung đột đặt trùng sân.\n"
            "3. **Thanh Toán Đặt Cọc 50%**: Qua cổng **VNPay**, Quét mã VietQR hoặc Ví số dư tài khoản.\n"
            "4. **Nhận Mã QR Check-in**: Xuất trình QR tại quầy lễ tân để mở đèn sân tự động.\n\n"
            "👉 *Bạn đang muốn đặt sân ở khu vực nào để tôi kiểm tra lịch trống giúp bạn?*"
        )

    # 4. Matchmaking & ELO
    if any(k in q for k in ["ghép kèo", "tìm bạn", "elo", "đội", "trình độ", "matchmaking", "giao lưu"]):
        return (
            "🏆 **HỆ THỐNG AI MATCHMAKING & ĐIỂM XẾP HẠNG ELO (UC006)**:\n\n"
            "BADMINTON.AI tự động phân loại trình độ người chơi qua hệ thống Elo chuẩn quốc tế:\n"
            "- 🥉 **Tân thủ (ELO 1000 - 1200)**: Mới tập chơi, giao lưu rèn luyện phản xạ.\n"
            "- 🥈 **Phong trào khá (ELO 1201 - 1500)**: Đánh đơn/đôi ổn định, nắm chắc kỹ thuật cơ bản.\n"
            "- 🥇 **Bán chuyên / Nâng cao (ELO 1501 - 1800)**: Cầu smash uy lực, phản tạt nhanh, chiến thuật tốt.\n"
            "- 👑 **Chuyên nghiệp / Master (ELO 1800+)**: Đẳng cấp thi đấu các giải phong trào lớn.\n\n"
            "👉 *Vào tab **Ghép Đội / Giao Lưu** để tìm phòng ghép phù hợp hoặc tạo kèo mời bạn chơi nhé!*"
        )

    # 5. Rackets
    if any(k in q for k in ["vợt", "chọn vợt", "smash", "tấn công", "phòng thủ", "dụng cụ", "căng cước", "căng dây", "yonex", "lining", "victor"]):
        return (
            "🏸 **CHUYÊN GIA TƯ VẤN CHỌN VỢT CẦU LÔNG THEO PHONG CÁCH CHƠI**:\n\n"
            "1. 🔥 **Lối chơi Tấn công dồn dập (Smash uy lực)**:\n"
            "   - **Đặc điểm**: Vợt nặng đầu (Head-Heavy, balance point > 295mm), thân cứng (Stiff).\n"
            "   - **Trọng lượng**: 3U (85-89g) hoặc 4U (80-84g).\n"
            "   - **Gợi ý**: *Yonex Astrox 88D Pro / 99 Pro / 100ZZ, Lining Tectonic 7 / Axforce 80 / 90*.\n\n"
            "2. ⚡ **Lối chơi Tốc độ / Phản tạt / Thủ phản công**:\n"
            "   - **Đặc điểm**: Vợt nhẹ đầu (Head-Light, balance < 285mm), đũa vợt dẻo linh hoạt.\n"
            "   - **Trọng lượng**: 4U hoặc 5U (75-79g siêu nhẹ).\n"
            "   - **Gợi ý**: *Yonex Nanoflare 700 / 800 Pro / 1000Z, Lining Aeronaut 9000I*.\n\n"
            "3. 🎯 **Lối chơi Toàn diện (Công thủ toàn diện)**:\n"
            "   - **Đặc điểm**: Điểm cân bằng 290 - 295mm.\n"
            "   - **Gợi ý**: *Yonex Arcsaber 11 Pro / 7 Pro, Lining Halbertec 8000 / Aeronaut 6000*.\n\n"
            "💡 **Mức căng cước khuyến nghị**: Mới chơi (9.5 - 10.5 kg), phong trào (10.5 - 11.5 kg), chuyên nghiệp (12 - 13 kg)."
        )

    # 6. Cancellation
    if any(k in q for k in ["hủy sân", "hoàn cọc", "đổi giờ", "hoàn tiền", "hủy kèo", "chính sách"]):
        return (
            "📋 **CHÍNH SÁCH HOÀN HỦY & ĐỔI LỊCH ĐẶT SÂN (UC008)**:\n\n"
            "- 🟢 **Hủy trước 24 giờ thi đấu**: Hoàn cọc **100%** vào ví tài khoản ngay lập tức.\n"
            "- 🟡 **Hủy trước 12 - 24 giờ**: Hoàn cọc **50%** giá trị đặt cọc.\n"
            "- 🔴 **Hủy dưới 12 giờ**: Không hỗ trợ hoàn cọc (sân đã giữ chỗ cố định cho bạn).\n\n"
            "👉 *Bạn có thể bấm vào mục **Lịch Đặt Của Tôi** để thực hiện yêu cầu hủy hoặc đổi giờ tự động.*"
        )

    # 7. Locations
    if any(k in q for k in ["địa chỉ", "ở đâu", "khu vực", "hà nội", "gần tôi", "bản đồ"]):
        return (
            "📍 **MẠNG LƯỚI 48+ CỤM SÂN CẦU LÔNG PHỦ RỘNG TOÀN HÀ NỘI**:\n\n"
            "- 🏢 **Cầu Giấy**: Sân Trung Kính (218 Trung Kính), Cầu Giấy Pro Arena (Duy Tân), Sân Bộ Công An...\n"
            "- 🏢 **Hoàng Mai**: Catchy Badminton Arena (136 Tân Khai), Sân Định Công Arena...\n"
            "- 🏢 **Đống Đa**: Sport Hub (102 Láng Hạ), Đại học Công Đoàn (169 Tây Sơn), HV Ngân Hàng...\n"
            "- 🏢 **Thanh Xuân**: Fuji Pro (159 Lê Văn Lương), Sân 134 Quan Nhân...\n"
            "- 🏢 **Ba Đình**: Ba Đình Star Arena (178 Điện Biên Phủ), Sân Quần Ngựa (30 Văn Cao)...\n"
            "- 🏢 **Nam & Bắc Từ Liêm**: Smash Zone Mỹ Đình, Sân Cổ Nhuế, Ciputra Badminton Club...\n"
            "- 🏢 **Hà Đông, Long Biên, Hai Bà Trưng, Tây Hồ**: Đầy đủ cụm sân thảm Yonex/Enlio đạt chuẩn BWF.\n\n"
            "👉 *Hãy nhập tên Quận (ví dụ: 'Tìm sân ở Cầu Giấy' hoặc 'Sân dưới 80k') để tôi lọc cụm sân chi tiết cho bạn nhé!*"
        )

    # Default
    return (
        "👋 Xin chào! Tôi là **Trợ lý AI Thông Minh BADMINTON.AI**.\n\n"
        "Tôi có thể hỗ trợ bạn nhanh chóng:\n"
        "- 📍 **Tìm sân theo Quận / Khu vực**: Cầu Giấy, Hoàng Mai, Đống Đa, Thanh Xuân, Hà Đông...\n"
        "- 💰 **Tra cứu giá thuê & Sân giá rẻ**: Lọc sân dưới 100k, biểu phí Giờ Vàng & Giờ Hành Chính.\n"
        "- 🏸 **Tư vấn chọn vợt**: Smash tấn công, Phản tạt linh hoạt, Cân bằng toàn diện.\n"
        "- 🏆 **Ghép kèo thi đấu ELO**: Tìm phòng ghép và đồng đội cùng trình độ.\n"
        "- ⏰ **Quy trình đặt cọc 50% & Giữ chỗ 10 phút chống trùng sân**.\n\n"
        "Bạn muốn tìm thông tin gì ạ? Hãy nhắn cho tôi nhé! ✨🏸"
    )
