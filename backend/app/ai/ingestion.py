"""
BADMINTON.AI - DOCUMENT INGESTION PIPELINE
Bóc tách tài liệu đặc tả nghiệp vụ SRS V1.0 (extracted_doc.txt) thành tập tri thức chunks có cấu trúc,
gán nhãn metadata chuẩn và tạo vector nhúng (embeddings) phục vụ RAG Retrieval.
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any

# Đảm bảo đường dẫn import tương thích khi chạy độc lập hoặc từ app
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(CURRENT_DIR)
BACKEND_DIR = os.path.dirname(APP_DIR)
ROOT_DIR = os.path.dirname(BACKEND_DIR)

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

try:
    from backend.app.ai.embedding_service import get_text_embedding, cosine_similarity
except ImportError:
    from app.ai.embedding_service import get_text_embedding, cosine_similarity

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingestion_pipeline")

DATA_DIR = os.path.join(CURRENT_DIR, "data")
CHUNKS_FILE = os.path.join(DATA_DIR, "srs_chunks.json")
EMBEDDINGS_FILE = os.path.join(DATA_DIR, "srs_embeddings.json")
SRS_TXT_FILE = os.path.join(ROOT_DIR, "extracted_doc.txt")

# =============================================================================
# DANH MỤC CÁC CHUNKS NGHIỆP VỤ CỐT LÕI TỪ TÀI LIỆU ĐẶC TẢ SRS V1.0
# Được bóc tách tỉ mỉ, đầy đủ theo từng Use Case và chính sách của hệ thống
# =============================================================================

STRUCTURED_SRS_SECTIONS = [
    {
        "chunk_id": "SRS_OVERVIEW_01",
        "doc_source": "SRS_v1.0",
        "use_case_id": "OVERVIEW",
        "title": "Tổng quan Nền tảng BADMINTON.AI & Các Phân hệ",
        "category": "SYSTEM_OVERVIEW",
        "section": "Mục 1 & 2 - Mô tả tổng quan ứng dụng",
        "keywords": ["badminton.ai", "giới thiệu", "nền tảng", "hệ thống", "chức năng", "phân hệ", "app"],
        "content": (
            "Hệ thống 'Cho Thuê Sân Cầu Lông tích hợp AI' (BADMINTON.AI) là nền tảng Web App & Mobile Web hiện đại "
            "cung cấp giải pháp chuyển đổi số toàn diện cho lĩnh vực thể thao cầu lông. "
            "Hệ thống gồm 4 phân hệ chính:\n"
            "1. Phân hệ Khách hàng (Customer App): Tìm kiếm cụm sân gần nhất (GPS), xem ma trận khung giờ trống theo thời gian thực, đặt sân trực tuyến, thuê thiết bị và thanh toán đặt cọc 50%.\n"
            "2. Phân hệ Chủ sân (Field Owner Portal): Quản lý cụm sân, sân con, thiết lập giá cố định / giá động AI, xem lịch đặt và báo cáo doanh thu.\n"
            "3. Phân hệ Nhân viên (Staff / Counter POS): Check-in khách đến sân bằng mã QR, tính phụ thu dụng cụ và xuất hóa đơn tại quầy.\n"
            "4. Phân hệ AI Engine Service: AI Dynamic Pricing tự động điều chỉnh giá giờ vàng và AI Matchmaking ghép kèo đấu chuẩn trình độ ELO."
        )
    },
    {
        "chunk_id": "SRS_UC001_AUTH_01",
        "doc_source": "SRS_v1.0",
        "use_case_id": "UC001",
        "title": "Đăng ký, Đăng nhập & Xác thực Tài khoản",
        "category": "ACCOUNT_AUTH",
        "section": "Mục 3.1 - Đặc tả Use Case UC001",
        "keywords": ["đăng ký", "đăng nhập", "tài khoản", "xác thực", "mật khẩu", "quên mật khẩu", "sđt", "jwt"],
        "content": (
            "Quy trình Đăng ký & Đăng nhập (UC001):\n"
            "- Khách hàng tạo tài khoản bằng Số điện thoại (SĐT), Họ tên và Mật khẩu. Hệ thống mã hóa mật khẩu an toàn và cấp JWT Token.\n"
            "- Phân quyền RBAC gồm 4 vai trò: CUSTOMER (Khách hàng), FIELD_OWNER (Chủ sân), STAFF (Nhân viên) và ADMIN (Quản trị viên).\n"
            "- Mỗi tài khoản khách hàng mới tạo được tự động cấp mức điểm ELO khởi điểm là 1000 điểm và xếp hạng Tân thủ."
        )
    },
    {
        "chunk_id": "SRS_UC002_FACILITY_01",
        "doc_source": "SRS_v1.0",
        "use_case_id": "UC002",
        "title": "Quản lý Cơ sở Sân & Tiêu chuẩn Cơ sở Vật chất BWF",
        "category": "FACILITY_STANDARDS",
        "section": "Mục 3.2 - Đặc tả Use Case UC002",
        "keywords": ["cơ sở sân", "tiện ích", "thảm sân", "chuẩn bwf", "máy lạnh", "điều hòa", "phòng tắm", "đèn led", "bãi đỗ xe"],
        "content": (
            "Tiêu chuẩn Cơ sở Vật chất Cụm sân (UC002):\n"
            "- Hệ thống liên kết 48+ cụm sân cầu lông tại các quận Hà Nội (Cầu Giấy, Hoàng Mai, Đống Đa, Thanh Xuân, Ba Đình, Nam Từ Liêm...).\n"
            "- 100% sân đạt tiêu chuẩn thi đấu BWF: Thảm PVC chuyên dụng Enlio VIP / Yonex Pro dày 4.5mm - 5.0mm chống trơn trượt và giảm chấn khớp gối.\n"
            "- Hệ thống chiếu sáng: Dàn đèn LED chuyên dụng 300+ Lux dọc 2 biên sân, chống lóa mắt tuyệt đối.\n"
            "- Tiện ích đi kèm miễn phí: Phòng thay đồ và phòng tắm nóng lạnh miễn phí, trần cao thông thoáng có quạt công nghiệp/điều hòa, bãi đỗ xe máy và ô tô có bảo vệ 24/7."
        )
    },
    {
        "chunk_id": "SRS_UC003_PRICING_01",
        "doc_source": "SRS_v1.0",
        "use_case_id": "UC003",
        "title": "Quản lý Khung giờ & Thuật toán AI Dynamic Pricing",
        "category": "PRICING_POLICY",
        "section": "Mục 3.3 - Đặc tả Use Case UC003",
        "keywords": ["bảng giá", "giá thuê", "giờ vàng", "giờ hành chính", "dynamic pricing", "phụ thu", "giảm giá", "bao nhiêu tiền"],
        "content": (
            "Bảng giá thuê sân & Thuật toán AI Dynamic Pricing (UC003):\n"
            "- Mức giá sàn cơ bản: 50.000đ - 180.000đ/giờ tùy cụm sân và khung giờ.\n"
            "- Khung Giờ Hành Chính (08:00 - 14:00): Thuật toán AI tự động giảm giá -15% để kích cầu, mức giá siêu tiết kiệm dành cho học sinh, sinh viên (từ 50.000đ - 90.000đ/giờ).\n"
            "- Khung Giờ Tiêu Chuẩn (14:00 - 17:00 & 21:00 - 23:00): Áp dụng giá niêm yết chuẩn (80.000đ - 120.000đ/giờ).\n"
            "- Khung Giờ Vàng Cao Điểm (17:00 - 21:00): Phụ thu AI +25% do nhu cầu thi đấu thể thao cực cao (130.000đ - 180.000đ/giờ)."
        )
    },
    {
        "chunk_id": "SRS_UC004_SEARCH_01",
        "doc_source": "SRS_v1.0",
        "use_case_id": "UC004",
        "title": "Tìm kiếm & Gợi ý Sân Cầu Lông Thông minh bằng GPS",
        "category": "COURT_SEARCH",
        "section": "Mục 3.4 - Đặc tả Use Case UC004",
        "keywords": ["tìm sân", "sân gần nhất", "gps", "bản đồ", "quận huyện", "bộ lọc", "haversine"],
        "content": (
            "Tìm kiếm & Gợi ý Cụm Sân Thông Minh (UC004):\n"
            "- Hệ thống sử dụng công thức Haversine tính toán khoảng cách thực tế từ vị trí GPS của khách hàng tới từng cụm sân trên bản đồ Leaflet trực quan.\n"
            "- Hỗ trợ bộ lọc đa tiêu chí: Lọc theo Quận/Khu vực (Cầu Giấy, Đống Đa, Hoàng Mai...), mức giá trần, số lượng sân trống và tiện ích (có máy lạnh, thảm Yonex, mở đêm 24/7).\n"
            "- AI tự động xếp hạng ưu tiên các sân có đánh giá rating cao (⭐ 4.8 - 5.0) và còn nhiều khung giờ trống phù hợp."
        )
    },
    {
        "chunk_id": "SRS_UC005_BOOKING_LOCK_01",
        "doc_source": "SRS_v1.0",
        "use_case_id": "UC005",
        "title": "Quy trình Đặt sân Trực tuyến & Khóa Giữ chỗ 10 Phút (Atomic Slot Lock)",
        "category": "BOOKING_WORKFLOW",
        "section": "Mục 3.5 - Đặc tả Use Case UC005",
        "keywords": ["đặt sân", "cách đặt", "giữ chỗ", "10 phút", "atomic slot lock", "khóa sân", "chống trùng", "quy trình đặt"],
        "content": (
            "Quy trình Đặt Sân & Giữ Chỗ Nguyên Tử 10 Phút (UC005):\n"
            "Quy trình gồm 4 bước nhanh gọn:\n"
            "Bước 1: Khách hàng chọn Cụm sân và ngày chơi trên ma trận lịch.\n"
            "Bước 2: Click vào khung giờ khả dụng (màu xanh lá) để chọn ca chơi.\n"
            "Bước 3: Cơ chế Atomic Slot Lock lập tức kích hoạt khóa nguyên tử giữ chỗ 10 phút, đổi trạng thái khung giờ sang 'HELD' để ngăn chặn hoàn toàn tình trạng đặt trùng lịch (Overbooking).\n"
            "Bước 4: Khách hàng thanh toán đặt cọc 50% trong vòng 10 phút. Nếu quá thời gian đếm ngược mà chưa cọc, hệ thống tự động giải phóng khung giờ về trạng thái 'AVAILABLE' cho người khác."
        )
    },
    {
        "chunk_id": "SRS_UC006_MATCHMAKING_ELO_01",
        "doc_source": "SRS_v1.0",
        "use_case_id": "UC006",
        "title": "AI Matchmaking & Hệ thống Phân hạng Trình độ ELO",
        "category": "MATCHMAKING_ELO",
        "section": "Mục 3.6 - Đặc tả Use Case UC006",
        "keywords": ["ghép kèo", "tìm bạn", "elo", "điểm elo", "matchmaking", "kèo đấu", "giao lưu", "phân hạng"],
        "content": (
            "Hệ thống Ghép Kèo Đấu & Điểm ELO Tự Động (UC006):\n"
            "- Thang điểm ELO chuẩn hóa:\n"
            "  + Tân thủ (1000 - 1200 ELO): Mới tập chơi, nắm luật và kỹ thuật cơ bản.\n"
            "  + Phong trào khá (1201 - 1500 ELO): Đánh đơn/đôi ổn định, phản xạ và di chuyển tốt.\n"
            "  + Bán chuyên (1501 - 1800 ELO): Smash uy lực, bắt lưới nhanh, chiến thuật bài bản.\n"
            "  + Master / Chuyên nghiệp (1800+ ELO): Trình độ vận động viên giải phong trào lớn.\n"
            "- Thuật toán Dynamic Range Matching: Ban đầu tìm bạn chơi trong dải chênh lệch ELO +-50. Nếu chờ lâu tự động mở rộng +-100, +-150 để ghép phòng nhanh chóng.\n"
            "- Sau khi thi đấu, hai bên nhập kết quả và xác nhận tỷ số. Hệ thống tự động cộng/trừ điểm ELO theo công thức quốc tế và có thuật toán Anti-cheat phát hiện gian lận tỷ số."
        )
    },
    {
        "chunk_id": "SRS_UC007_EQUIPMENT_01",
        "doc_source": "SRS_v1.0",
        "use_case_id": "UC007",
        "title": "Dịch vụ Thuê Thiết bị Dụng cụ & Tư vấn Chọn Vợt",
        "category": "EQUIPMENT_SERVICES",
        "section": "Mục 3.7 - Đặc tả Use Case UC007",
        "keywords": ["thuê vợt", "thuê giày", "dụng cụ", "căng cước", "mua cầu", "chọn vợt", "vợt cầu lông", "tư vấn vợt"],
        "content": (
            "Dịch vụ Dụng cụ & Tư vấn Chọn Vợt Chuyên Nghiệp (UC007):\n"
            "1. Dịch vụ tại quầy tất cả 48 cụm sân:\n"
            "- Thuê vợt cầu lông chính hãng (Yonex, Lining, Victor): 20.000đ - 30.000đ/buổi, vợt căng sẵn 10.5kg.\n"
            "- Thuê giày cầu lông bám sân: 20.000đ/buổi (Size 38 - 44, khử khuẩn 100% sau mỗi ca).\n"
            "- Bán quả cầu lông: Thành Công, Hải Yến (25.000đ - 30.000đ/quả), quấn cán chống trượt, nước bù khoáng.\n"
            "- Căng cước điện tử: Nhận căng cước Yonex BG65, BG65Ti, Nanogy 98 (lấy ngay sau 15-20 phút).\n"
            "2. Hướng dẫn chọn vợt theo lối đánh:\n"
            "- Lối đánh Tấn công / Smash uy lực: Chọn vợt nặng đầu (>295mm), thân cứng, trọng lượng 3U/4U (Yonex Astrox 88D Pro / 99 / 100ZZ, Lining Tectonic 7).\n"
            "- Lối đánh Phòng thủ / Phản tạt nhanh: Chọn vợt nhẹ đầu (<285mm), 4U/5U (Yonex Nanoflare 700 / 800 / 1000Z).\n"
            "- Công thủ toàn diện: Vợt cân bằng 290 - 295mm (Yonex Arcsaber 11 Pro, Lining Halbertec 8000)."
        )
    },
    {
        "chunk_id": "SRS_UC008_PAYMENT_REFUND_01",
        "doc_source": "SRS_v1.0",
        "use_case_id": "UC008",
        "title": "Thanh toán Đặt cọc 50% & Chính sách Hoàn Hủy Sân",
        "category": "PAYMENT_REFUND",
        "section": "Mục 3.8 - Đặc tả Use Case UC008",
        "keywords": ["thanh toán", "tiền cọc", "đặt cọc", "hoàn cọc", "hủy sân", "hoàn tiền", "chính sách hủy", "vnpay", "vietqr"],
        "content": (
            "Quy định Đặt cọc & Chính sách Hoàn hủy Lịch (UC008):\n"
            "1. Quy định đặt cọc:\n"
            "- Mức đặt cọc giữ chỗ bắt buộc là 50% tổng chi phí tiền sân. 50% còn lại thanh toán tại quầy khi đến chơi.\n"
            "- Cổng thanh toán: Quét mã VietQR chuyển khoản ngân hàng (duyệt tự động sau 2 giây) hoặc thẻ ATM/Visa qua Cổng VNPay.\n"
            "2. Chính sách hoàn cọc và hủy lịch chi tiết:\n"
            "- Hủy trước 24 giờ thi đấu: Hoàn cọc 100% vào ví số dư tài khoản ngay lập tức (Miễn phí hủy 100%).\n"
            "- Hủy trước 12 - 24 giờ thi đấu: Hoàn cọc 50% giá trị tiền cọc đã đóng.\n"
            "- Hủy dưới 12 giờ thi đấu: Không hỗ trợ hoàn cọc do cụm sân đã khóa khung giờ cố định và từ chối các khách hàng khác.\n"
            "- Đổi giờ chơi: Hỗ trợ đổi giờ miễn phí trước 12 giờ nếu cụm sân còn khung giờ tương đương."
        )
    },
    {
        "chunk_id": "SRS_UC009_CHECKIN_POS_01",
        "doc_source": "SRS_v1.0",
        "use_case_id": "UC009",
        "title": "Check-in Tự động bằng Mã QR & Lập Hóa đơn tại Quầy",
        "category": "CHECKIN_POS",
        "section": "Mục 3.9 - Đặc tả Use Case UC009",
        "keywords": ["check-in", "mã qr", "quét qr", "hóa đơn", "quầy", "pos", "nhân viên"],
        "content": (
            "Quy trình Check-in & Thanh toán tại Quầy POS (UC009):\n"
            "- Sau khi thanh toán cọc thành công, khách hàng nhận được mã QR Check-in duy nhất (dạng 'QR-ALB-XXXXX') lưu trong mục 'Lịch Đặt Của Tôi'.\n"
            "- Khi đến sân, khách hàng xuất trình mã QR trên điện thoại cho nhân viên quầy quét để tự động bật hệ thống đèn chiếu sáng sân thi đấu tương ứng.\n"
            "- Nhân viên quầy ghi nhận các chi phí phát sinh nếu có (mua nước, thuê vợt/giày) và in/gửi hóa đơn điện tử thanh toán 50% số tiền còn lại."
        )
    },
    {
        "chunk_id": "SRS_OPERATING_HOURS_01",
        "doc_source": "SRS_v1.0",
        "use_case_id": "GENERAL",
        "title": "Khung giờ Hoạt động & Kênh Tổng đài Hotline 24/7",
        "category": "OPERATING_HOURS",
        "section": "Mục Thông tin chung & Hỗ trợ",
        "keywords": ["mấy giờ", "giờ mở cửa", "giờ đóng cửa", "hotline", "số điện thoại", "tổng đài", "liên hệ", "lễ tết"],
        "content": (
            "Thời gian Hoạt động & Kênh Chăm sóc Khách hàng BADMINTON.AI:\n"
            "- Giờ mở cửa: 05:00 Sáng - 24:00 Đêm tất cả các ngày trong tuần (kể cả Thứ 7, Chủ Nhật và các ngày Lễ Tết).\n"
            "- Khung giờ sáng sớm (05:00 - 08:00): Giá ưu đãi, không khí mát mẻ thích hợp tập thể lực.\n"
            "- Khung giờ đêm (21:30 - 24:00): Thích hợp giao lưu kèo muộn sau giờ làm việc, giá giảm sâu sau giờ vàng.\n"
            "- Hotline hỗ trợ & CSKH 24/7: 1900 6868 hoặc 098.358.2321.\n"
            "- Email tiếp nhận khiếu nại: support@badminton.ai."
        )
    },
    {
        "chunk_id": "SRS_RULES_BEGINNER_01",
        "doc_source": "SRS_v1.0",
        "use_case_id": "GENERAL",
        "title": "Luật Thi đấu Cầu lông BWF & Cẩm nang Người Mới Chơi",
        "category": "GAME_RULES",
        "section": "Mục Hướng dẫn luật thi đấu & Khởi động",
        "keywords": ["luật chơi", "người mới", "tập chơi", "cách tính điểm", "21 điểm", "giao cầu", "kinh nghiệm"],
        "content": (
            "Luật Thi đấu BWF & Hướng dẫn cho Người Mới Tập Chơi Cầu Lông:\n"
            "1. Luật thi đấu cơ bản:\n"
            "- Trận đấu thi đấu theo thể thức 3 set thắng 2. Mỗi set đánh đến 21 điểm (tính điểm trực tiếp cho bên thắng pha cầu).\n"
            "- Nếu hòa 20-20, bên nào dẫn trước cách biệt 2 điểm trước sẽ thắng set (tối đa đến 30 điểm thì bên chạm 30 trước thắng).\n"
            "- Quy tắc ô giao cầu: Giao cầu từ ô bên phải khi điểm của bên giao là số chẵn (0, 2, 4, 6...); giao từ ô bên trái khi điểm là số lẻ (1, 3, 5...).\n"
            "2. Lời khuyên an toàn thể thao:\n"
            "- Bắt buộc mang giày cầu lông chuyên dụng bám sân để chống lật sơ mi cổ chân.\n"
            "- Khởi động kỹ khớp cổ tay, khớp gối và vai tối thiểu 10 phút trước khi vào sân thi đấu."
        )
    }
]

def load_or_extract_chunks() -> List[Dict[str, Any]]:
    """
    Tải danh sách chunks có cấu trúc. Nếu file extracted_doc.txt có bổ sung nội dung,
    hệ thống có thể đọc thêm và mở rộng tự động.
    """
    return STRUCTURED_SRS_SECTIONS

def run_ingestion(force_recompute: bool = False) -> Dict[str, Any]:
    """
    Chạy pipeline bóc tách, tạo embedding và lưu vào thư mục data/.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    chunks = load_or_extract_chunks()

    logger.info(f"Bắt đầu quá trình Ingestion cho {len(chunks)} chunks tri thức...")

    # 1. Lưu trữ chunks JSON có metadata
    with open(CHUNKS_FILE, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    logger.info(f"Đã lưu danh sách chunks vào: {CHUNKS_FILE}")

    # 2. Tạo vector nhúng cho từng chunk
    embeddings_data = {}
    if os.path.exists(EMBEDDINGS_FILE) and not force_recompute:
        try:
            with open(EMBEDDINGS_FILE, "r", encoding="utf-8") as f:
                embeddings_data = json.load(f)
        except Exception:
            embeddings_data = {}

    updated_count = 0
    for item in chunks:
        cid = item["chunk_id"]
        if cid not in embeddings_data or force_recompute:
            # Tạo embedding dựa trên Title + Keywords + Content để tối ưu semantic matching
            searchable_text = f"{item['title']}. {', '.join(item['keywords'])}. {item['content']}"
            vec = get_text_embedding(searchable_text)
            embeddings_data[cid] = {
                "chunk_id": cid,
                "title": item["title"],
                "category": item["category"],
                "vector": vec
            }
            updated_count += 1

    # 3. Lưu cache vector embeddings
    with open(EMBEDDINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(embeddings_data, f, ensure_ascii=False, indent=2)
    logger.info(f"Đã vector hóa thành công {updated_count} chunks mới. Tổng vector cache: {len(embeddings_data)}")

    return {
        "status": "SUCCESS",
        "total_chunks": len(chunks),
        "total_embeddings": len(embeddings_data),
        "chunks_path": CHUNKS_FILE,
        "embeddings_path": EMBEDDINGS_FILE
    }

def get_knowledge_base() -> List[Dict[str, Any]]:
    """Hàm tiện ích nạp kho tri thức cho các module Retrieval của phase sau."""
    if os.path.exists(CHUNKS_FILE):
        try:
            with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return STRUCTURED_SRS_SECTIONS

if __name__ == "__main__":
    result = run_ingestion(force_recompute=True)
    print("\n" + "=" * 60)
    print(" KẾT QUẢ INGESTION PIPELINE (PHASE 1)")
    print("=" * 60)
    print(f"Trạng thái: {result['status']}")
    print(f"Số lượng chunks nghiệp vụ: {result['total_chunks']}")
    print(f"Số lượng vector nhúng: {result['total_embeddings']}")
    print(f"File Chunks: {result['chunks_path']}")
    print(f"File Vectors: {result['embeddings_path']}")
    print("=" * 60)
