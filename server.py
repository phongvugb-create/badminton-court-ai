import http.server
import json
import os
import sys
import re
import urllib.request
import urllib.error

# Ensure backend directory is in path if needed
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

PORT = int(os.environ.get("PORT", 8085))
DATA_FILE = os.path.join(os.path.dirname(__file__), "database.json")

SYSTEM_INSTRUCTION = """Bạn là Trợ lý AI Thông Minh (BADMINTON.AI Virtual Assistant) của nền tảng Quản Lý & Cho Thuê Sân Cầu Lông & Pickleball BADMINTON.AI.
Nhiệm vụ của bạn:
- Tư vấn nhiệt tình, ngắn gọn, thân thiện, lịch sự và giải đáp mọi thắc mắc về sản phẩm/dịch vụ của website.
- Nắm vững kiến thức hệ thống:
  + Danh sách 48+ cụm sân cầu lông tại Hà Nội (Cầu Giấy, Hoàng Mai, Đống Đa, Thanh Xuân, Nam Từ Liêm, Bắc Từ Liêm, Ba Đình, Long Biên, Tây Hồ, Hai Bà Trưng, Hà Đông, Hoàn Kiếm...).
  + Bảng giá thuê sân: 50.000đ - 180.000đ/giờ.
  + Cơ chế AI Dynamic Pricing (UC003): Tự động giảm giá 15% giờ hành chính (8h-14h) để kích cầu, phụ thu 25% khung giờ vàng (17h-21h) tối ưu doanh thu.
  + Giữ chỗ 10 phút (UC005): Khóa nguyên tử (Atomic Slot Lock) chống xung đột đặt trùng, cọc 50% qua VNPay/Chuyển khoản QR.
  + AI Matchmaking & Điểm ELO (UC006): Ghép kèo đấu công bằng, tìm bạn chơi theo trình độ ELO 1000 - 2000+.
  + Dịch vụ & Dụng cụ: Cho thuê vợt tiêu chuẩn 20k-30k/buổi, thuê giày 20k, bán phụ kiện cầu/quấn cán, căng cước điện tử 10.5 - 11.5 kg.
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

def get_gemini_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "")
    if key and not key.startswith("YOUR_"):
        return key.strip()
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val and not val.startswith("YOUR_"):
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
            "   - **Thuê vợt cầu lông**: 20.000đ - 30.000đ/buổi (Vợt Yonex, Lining, Victor chính hãng căng sẵn 10.5kg).\n"
            "   - **Thuê giày cầu lông**: 20.000đ/buổi (Đầy đủ size 38 - 44, đế kếp bám sân, khử khuẩn 100% sau mỗi ca).\n"
            "   - **Bán phụ kiện tại quầy**: Cầu Hải Yến, Thành Công (25k-30k/quả), quấn cán chống trượt, nước bù khoáng Pocari/Revive.\n"
            "   - **Căng cước điện tử**: Nhận căng cước Yonex BG65, BG65Ti, Nanogy 98 (lấy ngay sau 15 phút).\n\n"
            "2. 🎯 **Tư vấn chọn vợt theo lối đánh**:\n"
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
            "- 🌿 **Mặt sàn thi đấu**: Thảm PVC chuyên dụng Enlio VIP / Yonex Pro dày 4.5mm - 5.0mm, chống trơn trượt và giảm chấn khớp gối tối đa.\n"
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
            "2. 🏸 **Chọn vợt cho người mới**: Nên chọn vợt nhẹ 4U hoặc 5U, thân dẻo (Medium/Flexible) để dễ phát lực và không bị mỏi cổ tay.\n"
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
        "- 🛒 **Dịch vụ tiện ích**: Thuê vợt 20k/buổi, thuê giày, mua phụ kiện cầu và căng cước tại chỗ.\n"
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
        ("gemini-2.0-flash", True),
        ("gemini-1.5-pro", True),
        ("gemini-2.5-flash", True)
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
            with urllib.request.urlopen(req, timeout=10) as response:
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
        except urllib.error.HTTPError as he:
            continue
        except Exception as e:
            continue

    return get_smart_fallback(user_message, context)

class BadmintonServerHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Cache-Control")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/database":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    self.wfile.write(f.read().encode("utf-8"))
            else:
                self.wfile.write(b"{}")
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

        return super().do_GET()

    def do_POST(self):
        # AI CHATBOT PROXY ENDPOINT (Secures GEMINI_API_KEY on Server)
        if self.path == "/api/chat" or self.path == "/api/v1/ai/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            user_msg = ""
            context = ""
            try:
                incoming = json.loads(post_data.decode("utf-8"))
                user_msg = incoming.get("message", "")
                messages = incoming.get("messages", [])
                context = incoming.get("context", "")
                
                reply = ask_gemini(user_msg, context=context, messages=messages)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": True,
                    "reply": reply
                }, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                fallback_reply = get_smart_fallback(user_msg, context)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": True,
                    "reply": fallback_reply,
                    "fallback": True,
                    "error": str(e)
                }, ensure_ascii=False).encode("utf-8"))
            return

        if self.path == "/api/database":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            try:
                incoming_data = json.loads(post_data.decode("utf-8"))
                current_data = {}
                if os.path.exists(DATA_FILE):
                    try:
                        with open(DATA_FILE, "r", encoding="utf-8") as f:
                            current_data = json.load(f)
                    except Exception:
                        current_data = {}

                merged_database = {**current_data}

                # 1. Authoritative sync for users (preserves deletions and sanitizes passwords)
                if "users" in incoming_data and isinstance(incoming_data["users"], list):
                    sanitized_users = []
                    for u in incoming_data["users"]:
                        pwd = u.get("password")
                        if not pwd or str(pwd).strip() in ["", "undefined", "null"]:
                            pwd = "02092006" if u.get("phone") == "0123456789" else "123456"
                        
                        user_copy = {**u, "password": str(pwd)}
                        if "elo_rating" not in user_copy or user_copy["elo_rating"] is None or str(user_copy["elo_rating"]) == "undefined":
                            user_copy["elo_rating"] = 1200 if user_copy.get("role") == "CUSTOMER" else "N/A"
                        sanitized_users.append(user_copy)
                    merged_database["users"] = sanitized_users

                # 2. Authoritative sync for facilities (preserves deletions)
                if "facilities" in incoming_data and isinstance(incoming_data["facilities"], list):
                    merged_database["facilities"] = incoming_data["facilities"]

                # 3. Other tables: courts, bookings, booking_orders, etc
                other_keys = ['courts', 'time_slots', 'equipments', 'booking_orders', 'invoices', 'matchmaking_rooms', 'occupancy_heatmap', 'bookings', 'orders']
                for k in other_keys:
                    if k in incoming_data and isinstance(incoming_data[k], list):
                        merged_database[k] = incoming_data[k]
                    elif k in current_data:
                        merged_database[k] = current_data[k]

                # Save merged data to JSON
                with open(DATA_FILE, "w", encoding="utf-8") as f:
                    json.dump(merged_database, f, ensure_ascii=False, indent=2)

                # Also sync directly to SQLite database
                try:
                    import sqlite_sync
                    conn = sqlite_sync.get_connection()
                    sqlite_sync.sync_json_to_sqlite(merged_database, conn)
                    conn.close()
                except Exception as sqle:
                    print(f"Warning: could not sync to SQLite: {sqle}")

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": True, 
                    "database_type": "SQLite3 + JSON",
                    "sqlite_file": "badminton.db",
                    "users_count": len(merged_users),
                    "facilities_count": len(merged_facilities)
                }).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    try:
        with http.server.ThreadingHTTPServer(("0.0.0.0", PORT), BadmintonServerHandler) as httpd:
            print(f"🏸 Badminton AI Threading Server running on http://localhost:{PORT}")
            httpd.serve_forever()
    except Exception as e:
        print(f"Failed to start server on port {PORT}: {e}")
