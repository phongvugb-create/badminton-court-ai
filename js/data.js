/* ==========================================================================
   BADMINTON AI MANAGEMENT SYSTEM - CENTRAL DATABASE STORE & CACHE (14 DATABASE TABLES)
   ========================================================================== */

const MockData = {
  // 1. BẢNG users
  users: [
    { id: 1, name: "Nguyễn Văn Hùng", phone: "0901234567", password: "123456", role: "CUSTOMER", skill_tier: "Khá", skill_tier_id: 5, elo_rating: 1650, avatar: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=300&q=80", photo: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=300&q=80", is_approved: true },
    { id: 2, name: "Trần Thị Mai", phone: "0912345678", password: "123456", role: "CUSTOMER", skill_tier: "Khá", skill_tier_id: 5, elo_rating: 1680, avatar: "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=300&q=80", photo: "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=300&q=80", is_approved: true },
    { id: 3, name: "Lê Hoàng Nam (Chủ Sân)", phone: "0988888888", password: "owner123", role: "OWNER", facility_id: 101, avatar: "N", is_approved: true, elo_rating: "N/A" },
    { id: 4, name: "Phạm Quốc Tuấn (Thu Ngân)", phone: "0922334455", password: "staff123", role: "STAFF", facility_id: 101, avatar: "T", is_approved: true, elo_rating: "N/A" },
    { id: 5, name: "Admin Quản Trị", phone: "0999888777", password: "admin123", role: "ADMIN", avatar: "A", is_approved: true, elo_rating: "N/A" },
    { id: 6, name: "Vũ Nhất Phong", phone: "0983582321", password: "password123", role: "CUSTOMER", skill_tier: "Trung bình khá", skill_tier_id: 4, elo_rating: 1450, avatar: "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?auto=format&fit=crop&w=300&q=80", photo: "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?auto=format&fit=crop&w=300&q=80", is_approved: true },
    { id: 7, name: "Trương Quốc Khánh (Chủ Sân)", phone: "0123456789", password: "02092006", role: "OWNER", facility_id: 101, elo_rating: "N/A", avatar: "K", is_approved: true }
  ],

  // 2. BẢNG facilities (Danh mục cụm cơ sở Sân Cầu Lông chuyên nghiệp toàn khu vực)
  facilities: [
    {
        "id": 101,
        "name": "CLB Cầu Lông Catchy Badminton Arena",
        "address": "Số 136 Phố Tân Khai, Quận Hoàng Mai, Hà Nội",
        "distance": "2.5km",
        "latitude": 20.9856,
        "longitude": 105.858,
        "open_time": "05:00",
        "close_time": "24:00",
        "open_hours": "05:00 - 24:00",
        "is_approved": true,
        "rating": 4.9,
        "reviews_count": 148,
        "img": "images/court1.jpg",
        "club_logo": "CATCHY",
        "club_avatar_bg": "#f0fdf4",
        "club_avatar_color": "#16a34a",
        "badges": [
            "Đơn ngày",
            "Thảm Enlio VIP"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 8,
        "price_range": "70.000đ - 140.000đ/giờ",
        "base_price": 70000
    },
    {
        "id": 102,
        "name": "CLB Cầu Lông Đống Đa Sport Hub",
        "address": "102 Phố Láng Hạ, Phường Láng Hạ, Quận Đống Đa, Hà Nội",
        "distance": "4.8km",
        "latitude": 21.0153,
        "longitude": 105.8152,
        "open_time": "05:00",
        "close_time": "23:00",
        "open_hours": "05:00 - 23:00",
        "is_approved": true,
        "rating": 4.9,
        "reviews_count": 142,
        "img": "images/court4.jpg",
        "club_logo": "SPORT HUB",
        "club_avatar_bg": "#f0fdf4",
        "club_avatar_color": "#16a34a",
        "badges": [
            "Đơn ngày",
            "Sự kiện"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 10,
        "price_range": "80.000đ - 150.000đ/giờ",
        "base_price": 80000
    },
    {
        "id": 103,
        "name": "Smash Zone Cyber Badminton Mỹ Đình",
        "address": "15 Lê Đức Thọ, Phường Mỹ Đình, Quận Nam Từ Liêm, Hà Nội",
        "distance": "8.3km",
        "latitude": 21.0285,
        "longitude": 105.7682,
        "open_time": "06:00",
        "close_time": "23:30",
        "open_hours": "06:00 - 23:30",
        "is_approved": true,
        "rating": 4.8,
        "reviews_count": 88,
        "img": "images/court5.jpg",
        "club_logo": "SMASH",
        "club_avatar_bg": "#ecfdf5",
        "club_avatar_color": "#15803d",
        "badges": [
            "Đơn ngày",
            "Thảm Yonex"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 8,
        "price_range": "80.000đ - 160.000đ/giờ",
        "base_price": 80000
    },
    {
        "id": 104,
        "name": "CLB Cầu Lông Ba Đình Star Arena",
        "address": "178 Điện Biên Phủ, Phường Điện Biên, Quận Ba Đình, Hà Nội",
        "distance": "3.2km",
        "latitude": 21.0315,
        "longitude": 105.8398,
        "open_time": "05:30",
        "close_time": "23:00",
        "open_hours": "05:30 - 23:00",
        "is_approved": true,
        "rating": 4.8,
        "reviews_count": 116,
        "img": "images/court6.jpg",
        "club_logo": "BA ĐÌNH",
        "club_avatar_bg": "#f0fdf4",
        "club_avatar_color": "#167946",
        "badges": [
            "Đơn ngày",
            "Sự kiện"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 12,
        "price_range": "90.000đ - 150.000đ/giờ",
        "base_price": 90000
    },
    {
        "id": 105,
        "name": "Nhà Thi Đấu Cầu Lông Bách Khoa Yonex Pro",
        "address": "219 Phố Lê Thanh Nghị, Phường Bách Khoa, Quận Hai Bà Trưng, Hà Nội",
        "distance": "5.1km",
        "latitude": 21.0028,
        "longitude": 105.8475,
        "open_time": "06:00",
        "close_time": "22:30",
        "open_hours": "06:00 - 22:30",
        "is_approved": true,
        "rating": 4.9,
        "reviews_count": 175,
        "img": "images/court7.jpg",
        "club_logo": "BÁCH KHOA",
        "club_avatar_bg": "#dcfce7",
        "club_avatar_color": "#15803d",
        "badges": [
            "Đơn ngày",
            "Sự kiện"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 10,
        "price_range": "80.000đ - 140.000đ/giờ",
        "base_price": 80000
    },
    {
        "id": 106,
        "name": "Thanh Xuân Badminton Club & Fuji Pro",
        "address": "159 Lê Văn Lương, Phường Nhân Chính, Quận Thanh Xuân, Hà Nội",
        "distance": "6.4km",
        "latitude": 21.0062,
        "longitude": 105.8085,
        "open_time": "05:30",
        "close_time": "23:00",
        "open_hours": "05:30 - 23:00",
        "is_approved": true,
        "rating": 4.9,
        "reviews_count": 210,
        "img": "images/court8.jpg",
        "club_logo": "THANH XUÂN",
        "club_avatar_bg": "#f0fdf4",
        "club_avatar_color": "#16a34a",
        "badges": [
            "Đơn ngày",
            "Thảm Enlio"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 14,
        "price_range": "80.000đ - 150.000đ/giờ",
        "base_price": 80000
    },
    {
        "id": 107,
        "name": "CLB Cầu Lông Tây Hồ Arena - Quảng An",
        "address": "48 Đặng Thai Mai, Phường Quảng An, Quận Tây Hồ, Hà Nội",
        "distance": "4.2km",
        "latitude": 21.0645,
        "longitude": 105.8241,
        "open_time": "06:00",
        "close_time": "22:30",
        "open_hours": "06:00 - 22:30",
        "is_approved": true,
        "rating": 4.7,
        "reviews_count": 92,
        "img": "images/court9.jpg",
        "club_logo": "TÂY HỒ",
        "club_avatar_bg": "#f0fdf4",
        "club_avatar_color": "#167946",
        "badges": [
            "Đơn ngày",
            "Sân ven hồ"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 8,
        "price_range": "90.000đ - 160.000đ/giờ",
        "base_price": 90000
    },
    {
        "id": 108,
        "name": "Hà Đông Cyber Badminton Club - Văn Quán",
        "address": "215 Trần Phú, Phường Văn Quán, Quận Hà Đông, Hà Nội",
        "distance": "9.5km",
        "latitude": 20.9812,
        "longitude": 105.7891,
        "open_time": "05:00",
        "close_time": "23:30",
        "open_hours": "05:00 - 23:30",
        "is_approved": true,
        "rating": 4.9,
        "reviews_count": 185,
        "img": "images/court10.jpg",
        "club_logo": "HÀ ĐÔNG",
        "club_avatar_bg": "#ecfdf5",
        "club_avatar_color": "#15803d",
        "badges": [
            "Đơn ngày",
            "Máy lạnh"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 12,
        "price_range": "70.000đ - 130.000đ/giờ",
        "base_price": 70000
    },
    {
        "id": 109,
        "name": "Sân Cầu Lông Cầu Giấy Pro Arena",
        "address": "35 Dịch Vọng Hậu, Cầu Giấy, Hà Nội",
        "distance": "5.8km",
        "latitude": 21.0345,
        "longitude": 105.7852,
        "open_time": "05:00",
        "close_time": "23:00",
        "open_hours": "05:00 - 23:00",
        "is_approved": true,
        "rating": 4.8,
        "reviews_count": 80,
        "img": "images/court1.jpg",
        "club_logo": "CẦU GIẤY",
        "club_avatar_bg": "#f0fdf4",
        "club_avatar_color": "#16a34a",
        "badges": [
            "Đơn ngày",
            "Sự kiện"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 8,
        "price_range": "80.000đ - 150.000đ/giờ",
        "base_price": 80000
    },
    {
        "id": 110,
        "name": "CLB Cầu Lông Hoàng Gia Cổ Nhuế",
        "address": "Số 18 Đường Cổ Nhuế, Bắc Từ Liêm, Hà Nội",
        "distance": "7.5km",
        "latitude": 21.065,
        "longitude": 105.772,
        "open_time": "05:30",
        "close_time": "23:00",
        "open_hours": "05:30 - 23:00",
        "is_approved": true,
        "rating": 4.9,
        "reviews_count": 65,
        "img": "images/court2.jpg",
        "club_logo": "CỔ NHUẾ",
        "club_avatar_bg": "#dcfce7",
        "club_avatar_color": "#15803d",
        "badges": [
            "Đơn ngày",
            "Thảm Yonex"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 6,
        "price_range": "70.000đ - 130.000đ/giờ",
        "base_price": 70000
    },
    {
        "id": 111,
        "name": "Sân Cầu Lông Quần Ngựa Liễu Giai",
        "address": "30 Văn Cao, Liễu Giai, Ba Đình, Hà Nội",
        "distance": "3.9km",
        "latitude": 21.0392,
        "longitude": 105.8174,
        "open_time": "05:30",
        "close_time": "22:30",
        "open_hours": "05:30 - 22:30",
        "is_approved": true,
        "rating": 4.7,
        "reviews_count": 90,
        "img": "images/court3.jpg",
        "club_logo": "QUẦN NGỰA",
        "club_avatar_bg": "#f0fdf4",
        "club_avatar_color": "#167946",
        "badges": [
            "Đơn ngày",
            "Sự kiện"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 8,
        "price_range": "80.000đ - 140.000đ/giờ",
        "base_price": 80000
    },
    {
        "id": 112,
        "name": "CLB Cầu Lông Định Công Arena",
        "address": "Khu đô thị Định Công, Hoàng Mai, Hà Nội",
        "distance": "5.5km",
        "latitude": 20.995,
        "longitude": 105.831,
        "open_time": "05:00",
        "close_time": "23:00",
        "open_hours": "05:00 - 23:00",
        "is_approved": true,
        "rating": 4.8,
        "reviews_count": 67,
        "img": "images/court4.jpg",
        "club_logo": "ĐỊNH CÔNG",
        "club_avatar_bg": "#f0fdf4",
        "club_avatar_color": "#16a34a",
        "badges": [
            "Đơn ngày",
            "Sự kiện"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 8,
        "price_range": "70.000đ - 130.000đ/giờ",
        "base_price": 70000
    },
    {
        "id": 113,
        "name": "Sân Cầu Lông Ciputra Badminton Club",
        "address": "Khu Đô Thị Ciputra, Bắc Từ Liêm, Hà Nội",
        "distance": "7.2km",
        "latitude": 21.0782,
        "longitude": 105.795,
        "open_time": "06:00",
        "close_time": "23:00",
        "open_hours": "06:00 - 23:00",
        "is_approved": true,
        "rating": 5.0,
        "reviews_count": 140,
        "img": "images/court5.jpg",
        "club_logo": "CIPUTRA",
        "club_avatar_bg": "#dcfce7",
        "club_avatar_color": "#15803d",
        "badges": [
            "Đơn ngày",
            "VIP"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 12,
        "price_range": "100.000đ - 180.000đ/giờ",
        "base_price": 100000
    },
    {
        "id": 114,
        "name": "Sân Cầu Lông Long Biên Riverside Pro",
        "address": "Đường Cổ Linh, Long Biên, Hà Nội",
        "distance": "6.8km",
        "latitude": 21.031,
        "longitude": 105.885,
        "open_time": "05:30",
        "close_time": "23:00",
        "open_hours": "05:30 - 23:00",
        "is_approved": true,
        "rating": 4.8,
        "reviews_count": 85,
        "img": "images/court6.jpg",
        "club_logo": "LONG BIÊN",
        "club_avatar_bg": "#f0fdf4",
        "club_avatar_color": "#15803d",
        "badges": [
            "Đơn ngày",
            "Sự kiện"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 10,
        "price_range": "80.000đ - 140.000đ/giờ",
        "base_price": 80000
    },
    {
        "id": 115,
        "name": "Sân cầu lông Đại học Công Đoàn",
        "address": "169 Tây Sơn, Phường Quang Trung, Quận Đống Đa, Hà Nội",
        "distance": "3.8km",
        "latitude": 21.0118,
        "longitude": 105.8236,
        "open_time": "05:30",
        "close_time": "22:30",
        "open_hours": "05:30 - 22:30",
        "price_range": "80.000đ/giờ",
        "base_price": 80000,
        "is_approved": true,
        "rating": 4.8,
        "reviews_count": 62,
        "img": "images/court1.jpg",
        "club_logo": "CÔNG ĐOÀN",
        "club_avatar_bg": "#f0fdf4",
        "club_avatar_color": "#16a34a",
        "badges": [
            "Đơn ngày",
            "Giá sinh viên",
            "Thảm Yonex"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 2
    },
    {
        "id": 116,
        "name": "Sân cầu lông Trung Kính",
        "address": "Ngõ 218 Trung Kính, Phường Yên Hòa, Quận Cầu Giấy, Hà Nội",
        "distance": "5.2km",
        "latitude": 21.0185,
        "longitude": 105.7942,
        "open_time": "05:00",
        "close_time": "23:00",
        "open_hours": "05:00 - 23:00",
        "price_range": "70.000đ/giờ",
        "base_price": 70000,
        "is_approved": true,
        "rating": 4.7,
        "reviews_count": 78,
        "img": "images/court2.jpg",
        "club_logo": "TRUNG KÍNH",
        "club_avatar_bg": "#dcfce7",
        "club_avatar_color": "#15803d",
        "badges": [
            "Đơn ngày",
            "Giá tốt",
            "Thảm Enlio"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 3
    },
    {
        "id": 121,
        "name": "Sân cầu lông Ngoại Thương",
        "address": "91 Phố Chùa Láng, Phường Láng Thượng, Quận Đống Đa, Hà Nội",
        "distance": "5.0km",
        "latitude": 21.0264,
        "longitude": 105.8035,
        "open_time": "05:30",
        "close_time": "22:30",
        "open_hours": "05:30 - 22:30",
        "price_range": "90.000đ/giờ",
        "base_price": 90000,
        "is_approved": true,
        "rating": 4.8,
        "reviews_count": 110,
        "img": "images/court7.jpg",
        "club_logo": "FTU",
        "club_avatar_bg": "#f0fdf4",
        "club_avatar_color": "#167946",
        "badges": [
            "Đơn ngày",
            "Giá sinh viên"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 3
    },
    {
        "id": 123,
        "name": "Sân cầu lông Bộ Công An",
        "address": "47 Phạm Văn Đồng, Mai Dịch, Cầu Giấy, Hà Nội",
        "distance": "6.9km",
        "latitude": 21.047,
        "longitude": 105.7795,
        "open_time": "05:00",
        "close_time": "23:00",
        "open_hours": "05:00 - 23:00",
        "price_range": "80.000đ - 110.000đ/giờ",
        "base_price": 90000,
        "is_approved": true,
        "rating": 4.9,
        "reviews_count": 160,
        "img": "images/court9.jpg",
        "club_logo": "BCA",
        "club_avatar_bg": "#dcfce7",
        "club_avatar_color": "#15803d",
        "badges": [
            "Đơn ngày",
            "Quy mô lớn",
            "Thảm Yonex Pro"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 5
    },
    {
        "id": 125,
        "name": "Sân cầu lông Đại học Thủy Lợi",
        "address": "175 Tây Sơn, Phường Trung Liệt, Quận Đống Đa, Hà Nội",
        "distance": "3.7km",
        "latitude": 21.0095,
        "longitude": 105.8242,
        "open_time": "05:00",
        "close_time": "22:30",
        "open_hours": "05:00 - 22:30",
        "price_range": "50.000đ/giờ",
        "base_price": 50000,
        "is_approved": true,
        "rating": 4.8,
        "reviews_count": 145,
        "img": "images/court1.jpg",
        "club_logo": "THỦY LỢI",
        "club_avatar_bg": "#ecfdf5",
        "club_avatar_color": "#15803d",
        "badges": [
            "Đơn ngày",
            "Giá siêu rẻ",
            "Sự kiện"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 4
    },
    {
        "id": 126,
        "name": "Sân cầu lông Đại học Xây Dựng",
        "address": "55 Đường Giải Phóng, Đồng Tâm, Hai Bà Trưng, Hà Nội",
        "distance": "4.3km",
        "latitude": 21.0035,
        "longitude": 105.8426,
        "open_time": "05:00",
        "close_time": "22:30",
        "open_hours": "05:00 - 22:30",
        "price_range": "90.000đ/giờ",
        "base_price": 90000,
        "is_approved": true,
        "rating": 4.9,
        "reviews_count": 120,
        "img": "images/court2.jpg",
        "club_logo": "XÂY DỰNG",
        "club_avatar_bg": "#dcfce7",
        "club_avatar_color": "#167946",
        "badges": [
            "Đơn ngày",
            "Thảm Yonex",
            "Giá tốt"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 4
    },
    {
        "id": 129,
        "name": "Sân cầu lông Hồng Hà",
        "address": "Phố Hồng Hà, Phường Chương Dương, Hoàn Kiếm, Hà Nội",
        "distance": "2.8km",
        "latitude": 21.025,
        "longitude": 105.86,
        "open_time": "05:00",
        "close_time": "22:30",
        "open_hours": "05:00 - 22:30",
        "price_range": "50.000đ - 90.000đ/giờ",
        "base_price": 70000,
        "is_approved": true,
        "rating": 4.8,
        "reviews_count": 88,
        "img": "images/court5.jpg",
        "club_logo": "HỒNG HÀ",
        "club_avatar_bg": "#f0fdf4",
        "club_avatar_color": "#15803d",
        "badges": [
            "Đơn ngày",
            "Thoáng mát"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 4
    },
    {
        "id": 130,
        "name": "Trung Tâm TDTT Sân Cầu Lông 521 Minh Khai",
        "address": "521 Minh Khai, Phường Vĩnh Tuy, Hai Bà Trưng, Hà Nội",
        "distance": "4.6km",
        "latitude": 20.9995,
        "longitude": 105.869,
        "open_time": "05:00",
        "close_time": "23:00",
        "open_hours": "05:00 - 23:00",
        "price_range": "40.000đ - 80.000đ/giờ",
        "base_price": 60000,
        "is_approved": true,
        "rating": 4.9,
        "reviews_count": 175,
        "img": "images/court6.jpg",
        "club_logo": "521 MINH KHAI",
        "club_avatar_bg": "#dcfce7",
        "club_avatar_color": "#167946",
        "badges": [
            "Đơn ngày",
            "Quy mô 7 sân",
            "Giá cực rẻ"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 7
    },
    {
        "id": 132,
        "name": "Sân cầu lông trường THPT Lý Thái Tổ",
        "address": "165 Phố Hoàng Ngân, Trung Hòa, Cầu Giấy, Hà Nội",
        "distance": "5.5km",
        "latitude": 21.0098,
        "longitude": 105.8035,
        "open_time": "06:00",
        "close_time": "22:00",
        "open_hours": "06:00 - 22:00",
        "price_range": "50.000đ - 80.000đ/giờ",
        "base_price": 65000,
        "is_approved": true,
        "rating": 4.8,
        "reviews_count": 72,
        "img": "images/court8.jpg",
        "club_logo": "LÝ THÁI TỔ",
        "club_avatar_bg": "#dcfce7",
        "club_avatar_color": "#15803d",
        "badges": [
            "Đơn ngày",
            "Sân trường học"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 3
    },
    {
        "id": 133,
        "name": "Sân cầu lông 266 phố Vũ Hữu",
        "address": "266 Phố Vũ Hữu, Trung Văn, Nam Từ Liêm / Thanh Xuân, Hà Nội",
        "distance": "6.8km",
        "latitude": 20.9972,
        "longitude": 105.7915,
        "open_time": "05:00",
        "close_time": "22:30",
        "open_hours": "05:00 - 22:30",
        "price_range": "50.000đ - 80.000đ/giờ",
        "base_price": 65000,
        "is_approved": true,
        "rating": 4.8,
        "reviews_count": 80,
        "img": "images/court9.jpg",
        "club_logo": "VŨ HỮU",
        "club_avatar_bg": "#f0fdf4",
        "club_avatar_color": "#167946",
        "badges": [
            "Đơn ngày",
            "Thảm Enlio"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 3
    },
    {
        "id": 135,
        "name": "Sân cầu lông 134 Quan Nhân",
        "address": "134 Phố Quan Nhân, Nhân Chính, Thanh Xuân, Hà Nội",
        "distance": "5.1km",
        "latitude": 21.0042,
        "longitude": 105.8112,
        "open_time": "05:30",
        "close_time": "22:30",
        "open_hours": "05:30 - 22:30",
        "price_range": "50.000đ - 80.000đ/giờ",
        "base_price": 65000,
        "is_approved": true,
        "rating": 4.8,
        "reviews_count": 65,
        "img": "images/court1.jpg",
        "club_logo": "QUAN NHÂN",
        "club_avatar_bg": "#dcfce7",
        "club_avatar_color": "#16a34a",
        "badges": [
            "Đơn ngày",
            "Thảm Yonex"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 3
    },
    {
        "id": 137,
        "name": "Sân cầu lông La Khê – Hà Đông",
        "address": "Khu đô thị Văn Khê, Phường La Khê, Hà Đông, Hà Nội",
        "distance": "9.2km",
        "latitude": 20.9765,
        "longitude": 105.7625,
        "open_time": "05:30",
        "close_time": "22:30",
        "open_hours": "05:30 - 22:30",
        "price_range": "70.000đ - 130.000đ/giờ",
        "base_price": 85000,
        "is_approved": true,
        "rating": 4.8,
        "reviews_count": 92,
        "img": "images/court3.jpg",
        "club_logo": "LA KHÊ",
        "club_avatar_bg": "#dcfce7",
        "club_avatar_color": "#167946",
        "badges": [
            "Đơn ngày",
            "Thảm Yonex Pro"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 3
    },
    {
        "id": 138,
        "name": "Sân cầu lông Nhà thi đấu Hà Đông",
        "address": "182 Quang Trung, Phường Quang Trung, Quận Hà Đông, Hà Nội",
        "distance": "8.6km",
        "latitude": 20.9685,
        "longitude": 105.7725,
        "open_time": "05:00",
        "close_time": "23:00",
        "open_hours": "05:00 - 23:00",
        "price_range": "70.000đ - 130.000đ/giờ",
        "base_price": 85000,
        "is_approved": true,
        "rating": 4.9,
        "reviews_count": 148,
        "img": "images/court4.jpg",
        "club_logo": "NTĐ HÀ ĐÔNG",
        "club_avatar_bg": "#ecfdf5",
        "club_avatar_color": "#15803d",
        "badges": [
            "Đơn ngày",
            "Nhà thi đấu chuẩn",
            "Có máy lạnh"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 4
    },
    {
        "id": 141,
        "name": "Sân cầu lông trường Tiểu học Nguyễn Quý Đức",
        "address": "Phường Đại Mỗ, Nam Từ Liêm, Hà Nội",
        "distance": "8.2km",
        "latitude": 20.993,
        "longitude": 105.76,
        "open_time": "06:00",
        "close_time": "22:00",
        "open_hours": "06:00 - 22:00",
        "price_range": "80.000đ - 130.000đ/giờ",
        "base_price": 85000,
        "is_approved": true,
        "rating": 4.7,
        "reviews_count": 35,
        "img": "images/court7.jpg",
        "club_logo": "QUÝ ĐỨC",
        "club_avatar_bg": "#f0fdf4",
        "club_avatar_color": "#167946",
        "badges": [
            "Đơn ngày"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 1
    },
    {
        "id": 142,
        "name": "Sân cầu lông Việt Hưng",
        "address": "Khu đô thị mới Việt Hưng, Quận Long Biên, Hà Nội",
        "distance": "7.8km",
        "latitude": 21.056,
        "longitude": 105.905,
        "open_time": "05:00",
        "close_time": "23:00",
        "open_hours": "05:00 - 23:00",
        "price_range": "70.000đ - 130.000đ/giờ",
        "base_price": 85000,
        "is_approved": true,
        "rating": 4.8,
        "reviews_count": 88,
        "img": "images/court8.jpg",
        "club_logo": "VIỆT HƯNG",
        "club_avatar_bg": "#dcfce7",
        "club_avatar_color": "#15803d",
        "badges": [
            "Đơn ngày",
            "Thảm Enlio VIP"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 3
    },
    {
        "id": 143,
        "name": "Sân Trung tâm quản lý bay",
        "address": "Đường Nguyễn Sơn, Phường Bồ Đề, Quận Long Biên, Hà Nội",
        "distance": "5.8km",
        "latitude": 21.0375,
        "longitude": 105.882,
        "open_time": "05:30",
        "close_time": "22:30",
        "open_hours": "05:30 - 22:30",
        "price_range": "70.000đ - 120.000đ/giờ",
        "base_price": 85000,
        "is_approved": true,
        "rating": 4.9,
        "reviews_count": 95,
        "img": "images/court9.jpg",
        "club_logo": "QUẢN LÝ BAY",
        "club_avatar_bg": "#f0fdf4",
        "club_avatar_color": "#16a34a",
        "badges": [
            "Đơn ngày",
            "Thảm Yonex Pro",
            "Có máy lạnh"
        ],
        "sport_type": "badminton",
        "sport_icon": "🏸",
        "courts_count": 2
    }
],

  // 3. BẢNG courts
  courts: [
    { id: 201, facility_id: 101, name: "Sân 01 - Thảm Yonex Pro", court_type: "Standard Matte", base_price: 120000, status: "Hoạt Động" },
    { id: 202, facility_id: 101, name: "Sân 02 - Thảm Yonex Pro", court_type: "Standard Matte", base_price: 120000, status: "Hoạt Động" },
    { id: 203, facility_id: 101, name: "Sân 03 - Thảm VIP Enlio", court_type: "VIP Cushion", base_price: 120000, status: "Hoạt Động" },
    { id: 204, facility_id: 101, name: "Sân 04 - Thảm VIP Enlio", court_type: "VIP Cushion", base_price: 120000, status: "Đang Bảo Trì" },
    { id: 205, facility_id: 102, name: "Sân A1 - Pro Flex", court_type: "Standard Matte", base_price: 120000, status: "Hoạt Động" }
  ],

  // 4. BẢNG time_slots (Giờ bình thường 5h-17h: 120k/h, Giờ vàng 18h-22h: 160k/h)
  time_slots: [
    { id: 300, court_id: 201, start_time: "05:00", end_time: "06:00", status: "AVAILABLE", price: 120000, base_price: 120000, is_ai_dynamic: false, price_type: "offpeak" },
    { id: 301, court_id: 201, start_time: "06:00", end_time: "07:00", status: "AVAILABLE", price: 120000, base_price: 120000, is_ai_dynamic: false, price_type: "offpeak" },
    { id: 302, court_id: 201, start_time: "07:00", end_time: "08:00", status: "AVAILABLE", price: 120000, base_price: 120000, is_ai_dynamic: false, price_type: "offpeak" },
    { id: 303, court_id: 201, start_time: "08:00", end_time: "09:00", status: "AVAILABLE", price: 120000, base_price: 120000, is_ai_dynamic: false, price_type: "offpeak" },
    { id: 304, court_id: 201, start_time: "09:00", end_time: "10:00", status: "AVAILABLE", price: 120000, base_price: 120000, is_ai_dynamic: false, price_type: "offpeak" },
    { id: 305, court_id: 201, start_time: "14:00", end_time: "15:00", status: "AVAILABLE", price: 120000, base_price: 120000, is_ai_dynamic: false, price_type: "offpeak" },
    { id: 306, court_id: 201, start_time: "16:00", end_time: "17:00", status: "AVAILABLE", price: 120000, base_price: 120000, is_ai_dynamic: false, price_type: "offpeak" },
    { id: 307, court_id: 201, start_time: "17:00", end_time: "18:00", status: "AVAILABLE", price: 120000, base_price: 120000, is_ai_dynamic: false, price_type: "offpeak" },
    { id: 308, court_id: 201, start_time: "18:00", end_time: "19:00", status: "AVAILABLE", price: 160000, base_price: 120000, is_ai_dynamic: true, price_type: "peak", adjustment: "+33% (18h-22h)", held_until: "17:28:45" },
    { id: 309, court_id: 201, start_time: "19:00", end_time: "20:00", status: "AVAILABLE", price: 160000, base_price: 120000, is_ai_dynamic: true, price_type: "peak", adjustment: "+33% (18h-22h)" },
    { id: 310, court_id: 201, start_time: "20:00", end_time: "21:00", status: "AVAILABLE", price: 160000, base_price: 120000, is_ai_dynamic: true, price_type: "peak", adjustment: "+33% (18h-22h)" },
    { id: 311, court_id: 201, start_time: "21:00", end_time: "22:00", status: "AVAILABLE", price: 160000, base_price: 120000, is_ai_dynamic: true, price_type: "peak", adjustment: "+33% (18h-22h)" },
    { id: 312, court_id: 201, start_time: "22:00", end_time: "23:00", status: "AVAILABLE", price: 120000, base_price: 120000, is_ai_dynamic: false, price_type: "offpeak" }
  ],

  // 5. BẢNG equipments (Danh mục vợt đa dạng & dụng cụ)
  equipments: [
    { id: 401, facility_id: 101, name: "Vợt Yonex Astrox 88D Pro", price: 35000, quantity: 12, unit: "Cây/giờ", style: "🔥 Chuyên Công - Nặng Đầu" },
    { id: 402, facility_id: 101, name: "Vợt Yonex Nanoflare 800 Pro", price: 35000, quantity: 10, unit: "Cây/giờ", style: "⚡ Tốc Độ - Phản Tạt Lưới" },
    { id: 403, facility_id: 101, name: "Vợt Yonex Arcsaber 11 Pro", price: 35000, quantity: 8, unit: "Cây/giờ", style: "🎯 Công Thủ Toàn Diện" },
    { id: 404, facility_id: 101, name: "Vợt Victor Thruster Ryuga II", price: 40000, quantity: 6, unit: "Cây/giờ", style: "💥 Siêu Tấn Công Uy Lực" },
    { id: 405, facility_id: 101, name: "Vợt Li-Ning Axforce 90 Max", price: 40000, quantity: 6, unit: "Cây/giờ", style: "🚀 Tấn Công Đỉnh Cao Bộc Phát" },
    { id: 406, facility_id: 101, name: "Vợt Kumpoo Power Control K520 Pro", price: 20000, quantity: 15, unit: "Cây/giờ", style: "🌱 Trợ Lực Dễ Chơi (Người Mới)" },
    { id: 407, facility_id: 101, name: "Hộp Cầu Lông Thành Công (12 quả)", price: 300000, quantity: 25, unit: "Hộp", style: "🏸 Cầu Chuẩn Thi Đấu" },
    { id: 408, facility_id: 101, name: "Nước khoáng Pocari Sweat 500ml", price: 10000, quantity: 50, unit: "Chai", style: "🥤 Bù Khoáng Điện Giải" },
    { id: 409, facility_id: 101, name: "Khăn lau mồ hôi cao cấp", price: 10000, quantity: 20, unit: "Cái", style: "🧻 Khăn Cotton Thấm Thấu" }
  ],

  // 6. BẢNG booking_orders
  booking_orders: [
    {
      id: 501,
      booking_code: "BK-20260911-001",
      user_name: "Nguyễn Văn Hùng",
      user_phone: "0901234567",
      facility_name: "CLB Cầu Lông Catchy Badminton Arena",
      court_name: "Sân 01 - Thảm Yonex Pro",
      slot_time: "17:30 - 18:30",
      booking_date: "11/09/2026",
      total_amount: 126500,
      deposit_amount: 50000,
      deposit_status: "Đã Cọc 50K",
      order_status: "Đã Xác Nhận",
      created_at: "17:15:00",
      qr_ticket_code: "TICKET-BADMINTON-8899"
    },
    {
      id: 502,
      booking_code: "BK-20260911-002",
      user_name: "Trần Thị Mai",
      user_phone: "0912345678",
      facility_name: "CLB Cầu Lông Catchy Badminton Arena",
      court_name: "Sân 03 - Thảm VIP Enlio",
      slot_time: "19:30 - 20:30",
      booking_date: "11/09/2026",
      total_amount: 150000,
      deposit_amount: 50000,
      deposit_status: "Chờ Cọc",
      order_status: "Chờ Xác Nhận",
      created_at: "17:20:00",
      qr_ticket_code: "TICKET-BADMINTON-9911"
    },
    {
      id: 503,
      booking_code: "BK-20260911-003",
      user_name: "Lê Hoàng Nam",
      user_phone: "0987654321",
      facility_name: "CLB Cầu Lông Đống Đa Sport Hub",
      court_name: "Sân 02 - Thảm Yonex Pro",
      slot_time: "07:00 - 08:00",
      booking_date: "11/09/2026",
      total_amount: 99000,
      deposit_amount: 50000,
      deposit_status: "Đã Cọc 50K",
      order_status: "Đã Xác Nhận",
      created_at: "06:45:00",
      qr_ticket_code: "TICKET-BADMINTON-1002"
    },
    {
      id: 504,
      booking_code: "BK-20260911-004",
      user_name: "Phạm Quốc Tuấn",
      user_phone: "0933445566",
      facility_name: "Smash Zone Cyber Badminton Mỹ Đình",
      court_name: "Sân A1 - Pro Flex",
      slot_time: "18:00 - 19:00",
      booking_date: "11/09/2026",
      total_amount: 120000,
      deposit_amount: 50000,
      deposit_status: "Đã Cọc 50K",
      order_status: "Đã Xác Nhận",
      created_at: "15:30:00",
      qr_ticket_code: "TICKET-BADMINTON-1003"
    },
    {
      id: 505,
      booking_code: "BK-20260911-005",
      user_name: "Vũ Hoàng My",
      user_phone: "0966778899",
      facility_name: "CLB Cầu Lông Ba Đình Star Arena",
      court_name: "Sân 05 - Yonex Pro",
      slot_time: "20:00 - 21:00",
      booking_date: "11/09/2026",
      total_amount: 115000,
      deposit_amount: 50000,
      deposit_status: "Đã Cọc 50K",
      order_status: "Đã Xác Nhận",
      created_at: "16:10:00",
      qr_ticket_code: "TICKET-BADMINTON-1004"
    }
  ],

  // 7. BẢNG invoices
  invoices: [
    {
      id: 601,
      invoice_code: "INV-20260911-88",
      booking_code: "BK-20260911-001",
      customer_name: "Nguyễn Văn Hùng",
      facility_name: "CLB Cầu Lông Catchy Badminton Arena",
      checkin_time: "17:28:10",
      checkout_time: "18:45:00",
      booking_fee: 122000,
      deposit_deducted: 50000,
      extra_fee: 30000,
      overtime_fee: 23000,
      final_amount: 125000,
      payment_method: "CASH",
      staff_name: "Phạm Quốc Tuấn",
      created_at: "18:46:12"
    }
  ],

  // 8. BẢNG matchmaking_rooms (Danh mục phòng ghép kèo AI thông minh theo 7 Cấp Bậc Trình Độ)
  matchmaking_rooms: [
    {
      id: 701,
      room_name: "Giao lưu Đôi Nam Nữ Cân Kèo Cấp [Khá]",
      facility_id: 101,
      facility_name: "CLB Cầu Lông Catchy Badminton Arena",
      district: "Hoàng Mai, Hà Nội",
      match_date: "Hôm nay, 22/09/2026",
      match_time: "18:00 - 20:00",
      required_tier: "Khá",
      required_tier_id: 5,
      required_elo_min: 1551,
      required_elo_max: 1750,
      match_type: "Đôi Nam/Nữ",
      court_number: "Sân 03 (Thảm Enlio VIP)",
      price_per_slot: "45.000đ",
      current_players: 3,
      max_players: 4,
      status: "OPEN",
      host_name: "Lê Hoàng Quân",
      host_tier: "Khá",
      host_tier_id: 5,
      host_elo: 1650,
      host_photo: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=300&q=80",
      ai_compatibility: 99,
      ai_prediction: "Cân kèo hoàn hảo cùng hạng mức Khá (Cấp 5). Tốc độ trận đấu cao, giằng co hấp dẫn.",
      ai_handicap: "Đồng banh (0 điểm)",
      category: "doubles",
      is_ai_recommended: true,
      players: [
        { name: "Lê Hoàng Quân", skill_tier: "Khá", tier_id: 5, elo: 1650, avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=300&q=80", photo: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=300&q=80", role: "Host", style: "Công thủ toàn diện", team: "A" },
        { name: "Trần Thị Mai", skill_tier: "Khá", tier_id: 5, elo: 1680, avatar: "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=300&q=80", photo: "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=300&q=80", role: "Member", style: "Bắt lưới & Tạt cầu", team: "A" },
        { name: "Phạm Quốc Tuấn", skill_tier: "Khá", tier_id: 5, elo: 1620, avatar: "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?auto=format&fit=crop&w=300&q=80", photo: "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?auto=format&fit=crop&w=300&q=80", role: "Member", style: "Phòng thủ dẻo dai", team: "B" }
      ],
      chat_messages: [
        { sender: "🤖 AI Match Referee", text: "Chào mừng các tay vợt! AI đã thẩm định: Phòng thi đấu chuẩn cấp bậc [Khá], 100% người chơi cùng hạng mức!", time: "16:30" },
        { sender: "Lê Hoàng Quân", text: "Chào mọi người, phòng mình cần thêm 1 bạn cùng cấp Khá để đánh đôi cân kèo nhé!", time: "16:45" },
        { sender: "Trần Thị Mai", text: "Mình cấp Khá vừa vào phòng rồi, ảnh nhận diện ở avatar nhé!", time: "16:50" },
        { sender: "Phạm Quốc Tuấn", text: "Mình bên đội B rồi, chào đón đồng đội cùng hạng vào quẩy nhiệt tình!", time: "17:05" }
      ]
    },
    {
      id: 702,
      room_name: "Săn Kèo Đơn Nam Cấp [Giỏi - Thành thạo]",
      facility_id: 103,
      facility_name: "CLB Cầu Lông Ba Đình Star Arena",
      district: "Ba Đình, Hà Nội",
      match_date: "Hôm nay, 22/09/2026",
      match_time: "19:30 - 21:30",
      required_tier: "Giỏi - Thành thạo",
      required_tier_id: 6,
      required_elo_min: 1751,
      required_elo_max: 1950,
      match_type: "Đơn Nam",
      court_number: "Sân 01 (Thảm Yonex Tour)",
      price_per_slot: "90.000đ",
      current_players: 1,
      max_players: 2,
      status: "OPEN",
      host_name: "Hoàng Văn Nam",
      host_tier: "Giỏi - Thành thạo",
      host_tier_id: 6,
      host_elo: 1820,
      host_photo: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=300&q=80",
      ai_compatibility: 95,
      ai_prediction: "Kèo solo chất lượng cao giữa các tay vợt Giỏi - Thành thạo. Lối đánh tốc độ cao, smash sắc nét.",
      ai_handicap: "Đồng banh (0 điểm)",
      category: "singles",
      is_ai_recommended: false,
      players: [
        { name: "Hoàng Văn Nam", skill_tier: "Giỏi - Thành thạo", tier_id: 6, elo: 1820, avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=300&q=80", photo: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=300&q=80", role: "Host", style: "Tấn công dồn dập & Smash uy lực", team: "A" }
      ],
      chat_messages: [
        { sender: "🤖 AI Match Referee", text: "AI Matchmaking: Đã kích hoạt xét kèo theo cấp [Giỏi - Thành thạo].", time: "15:00" },
        { sender: "Hoàng Văn Nam", text: "Cần tìm bạn cùng hạng Giỏi - Thành thạo solo đơn nam tối nay, có ảnh diện mạo đối chiếu ở avatar!", time: "15:10" }
      ]
    },
    {
      id: 703,
      room_name: "Kèo Đôi Nam Tốc Độ Cao Cấp [Khá]",
      facility_id: 105,
      facility_name: "CLB Cầu Lông Cầu Giấy Pro Center",
      district: "Cầu Giấy, Hà Nội",
      match_date: "Hôm nay, 22/09/2026",
      match_time: "20:00 - 22:00",
      required_tier: "Khá",
      required_tier_id: 5,
      required_elo_min: 1551,
      required_elo_max: 1750,
      match_type: "Đôi Nam",
      court_number: "Sân 05 (Thảm Victor Quốc Tế)",
      price_per_slot: "50.000đ",
      current_players: 2,
      max_players: 4,
      status: "OPEN",
      host_name: "Đỗ Minh Đức",
      host_tier: "Khá",
      host_tier_id: 5,
      host_elo: 1670,
      host_photo: "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=300&q=80",
      ai_compatibility: 97,
      ai_prediction: "Cân bằng tuyệt đối cùng cấp Khá. Đấu pháp phối hợp phản tạt nhanh và kiểm soát cầu giữa sân.",
      ai_handicap: "Đồng banh (0 điểm)",
      category: "doubles",
      is_ai_recommended: true,
      players: [
        { name: "Đỗ Minh Đức", skill_tier: "Khá", tier_id: 5, elo: 1670, avatar: "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=300&q=80", photo: "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=300&q=80", role: "Host", style: "Đập cầu uy lực", team: "A" },
        { name: "Ngô Quốc Khánh", skill_tier: "Khá", tier_id: 5, elo: 1640, avatar: "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?auto=format&fit=crop&w=300&q=80", photo: "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?auto=format&fit=crop&w=300&q=80", role: "Member", style: "Điều cầu góc xa", team: "B" }
      ],
      chat_messages: [
        { sender: "Đỗ Minh Đức", text: "Kèo đánh đôi cùng cấp Khá nhé anh em, chuẩn bị sẵn vợt căng 11kg!", time: "14:20" }
      ]
    },
    {
      id: 704,
      room_name: "Giao Lưu Cuối Ngày Cấp [Trung bình khá]",
      facility_id: 102,
      facility_name: "CLB Cầu Lông Đống Đa Sport Hub",
      district: "Đống Đa, Hà Nội",
      match_date: "Hôm nay, 22/09/2026",
      match_time: "21:00 - 23:00",
      required_tier: "Trung bình khá",
      required_tier_id: 4,
      required_elo_min: 1351,
      required_elo_max: 1550,
      match_type: "Đôi Nam/Nữ",
      court_number: "Sân 02 (Thảm Xanh Lá)",
      price_per_slot: "40.000đ",
      current_players: 3,
      max_players: 4,
      status: "OPEN",
      host_name: "Bùi Đình Trọng",
      host_tier: "Trung bình khá",
      host_tier_id: 4,
      host_elo: 1480,
      host_photo: "https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?auto=format&fit=crop&w=300&q=80",
      ai_compatibility: 99,
      ai_prediction: "Khớp 100% với cấp Trung bình khá. Trận đấu giao lưu cực kỳ vui vẻ, chia sẻ tiền sân tự động.",
      ai_handicap: "Đồng banh (0 điểm)",
      category: "doubles",
      is_ai_recommended: true,
      players: [
        { name: "Bùi Đình Trọng", skill_tier: "Trung bình khá", tier_id: 4, elo: 1480, avatar: "https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?auto=format&fit=crop&w=300&q=80", photo: "https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?auto=format&fit=crop&w=300&q=80", role: "Host", style: "Bền bỉ thể lực", team: "A" },
        { name: "Vũ Hải Yến", skill_tier: "Trung bình khá", tier_id: 4, elo: 1440, avatar: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=300&q=80", photo: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=300&q=80", role: "Member", style: "Khống chế lưới", team: "A" },
        { name: "Lê Minh Tuấn", skill_tier: "Trung bình khá", tier_id: 4, elo: 1510, avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=300&q=80", photo: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=300&q=80", role: "Member", style: "Công thủ linh hoạt", team: "B" }
      ],
      chat_messages: [
        { sender: "Bùi Đình Trọng", text: "Anh em cùng hạng Trung bình khá vào giao lưu dưỡng sinh giải tỏa căng thẳng sau giờ làm nào!", time: "17:15" },
        { sender: "Vũ Hải Yến", text: "Mình có ảnh đại diện rồi nhé, nhận diện gặp nhau ở cổng sân!", time: "17:20" }
      ]
    },
    {
      id: 705,
      room_name: "Kèo Giao Hữu AI Chấp Điểm (Khá vs TB Khá)",
      facility_id: 104,
      facility_name: "CLB Cầu Lông Thanh Xuân Sport Arena",
      district: "Thanh Xuân, Hà Nội",
      match_date: "Ngày mai, 23/09/2026",
      match_time: "17:30 - 19:30",
      required_tier: "Trung bình khá",
      required_tier_id: 4,
      required_elo_min: 1351,
      required_elo_max: 1550,
      match_type: "Đơn Nam",
      court_number: "Sân 04 (Thảm Enlio)",
      price_per_slot: "60.000đ",
      current_players: 1,
      max_players: 2,
      status: "OPEN",
      host_name: "Phan Anh Vũ",
      host_tier: "Khá",
      host_tier_id: 5,
      host_elo: 1660,
      host_photo: "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?auto=format&fit=crop&w=300&q=80",
      ai_compatibility: 88,
      ai_prediction: "Hệ thống AI tự động cân bằng: Người chơi cấp Trung bình khá được cộng +3 điểm mỗi set khi đấu với Host cấp Khá.",
      ai_handicap: "AI Handicap: Chấp +3 điểm/set",
      category: "handicap",
      is_ai_recommended: true,
      players: [
        { name: "Phan Anh Vũ", skill_tier: "Khá", tier_id: 5, elo: 1660, avatar: "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?auto=format&fit=crop&w=300&q=80", photo: "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?auto=format&fit=crop&w=300&q=80", role: "Host", style: "Chiến thuật & Kỹ thuật", team: "A" }
      ],
      chat_messages: [
        { sender: "Phan Anh Vũ", text: "Kèo chấp điểm AI tính toán rất công bằng, hoan nghênh anh em cấp Trung bình khá giao lưu học hỏi!", time: "13:00" }
      ]
    },
    {
      id: 706,
      room_name: "Kèo Đôi Cân Bằng Cấp [Trung bình]",
      facility_id: 106,
      facility_name: "CLB Cầu Lông Nam Từ Liêm Smash Center",
      district: "Nam Từ Liêm, Hà Nội",
      match_date: "Hôm nay, 22/09/2026",
      match_time: "19:00 - 21:00",
      required_tier: "Trung bình",
      required_tier_id: 3,
      required_elo_min: 1151,
      required_elo_max: 1350,
      match_type: "Đôi Nam/Nữ",
      court_number: "Sân 06 (Thảm Đỏ Thi Đấu)",
      price_per_slot: "45.000đ",
      current_players: 2,
      max_players: 4,
      status: "OPEN",
      host_name: "Nguyễn Thành Long",
      host_tier: "Trung bình",
      host_tier_id: 3,
      host_elo: 1300,
      host_photo: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=300&q=80",
      ai_compatibility: 98,
      ai_prediction: "Cân bằng tuyệt hảo cùng cấp Trung bình (Cấp 3). Nhịp độ thi đấu vừa sức, rèn luyện cảm giác cầu.",
      ai_handicap: "Đồng banh (0 điểm)",
      category: "doubles",
      is_ai_recommended: true,
      players: [
        { name: "Nguyễn Thành Long", skill_tier: "Trung bình", tier_id: 3, elo: 1300, avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=300&q=80", photo: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=300&q=80", role: "Host", style: "Điều cầu", team: "A" },
        { name: "Trịnh Diệu Linh", skill_tier: "Trung bình", tier_id: 3, elo: 1280, avatar: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=300&q=80", photo: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=300&q=80", role: "Member", style: "Tạt lưới", team: "B" }
      ],
      chat_messages: [
        { sender: "Nguyễn Thành Long", text: "Phòng đang có 2 bạn rồi, cần thêm 2 bạn cùng cấp Trung bình nữa là đẹp đội hình!", time: "16:00" }
      ]
    },
    {
      id: 707,
      room_name: "Tập Luyện Cơ Bản Cấp [Trung Bình Yếu - Cơ bản]",
      facility_id: 107,
      facility_name: "CLB Cầu Lông Tây Hồ View Arena",
      district: "Tây Hồ, Hà Nội",
      match_date: "Ngày mai, 23/09/2026",
      match_time: "06:00 - 08:00",
      required_tier: "Trung Bình Yếu - Cơ bản",
      required_tier_id: 2,
      required_elo_min: 951,
      required_elo_max: 1150,
      match_type: "Giao Lưu Tự Do",
      court_number: "Sân 02 (Thảm Xám)",
      price_per_slot: "35.000đ",
      current_players: 3,
      max_players: 4,
      status: "OPEN",
      host_name: "Hoàng Thu Trang",
      host_tier: "Trung Bình Yếu - Cơ bản",
      host_tier_id: 2,
      host_elo: 1050,
      host_photo: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=300&q=80",
      ai_compatibility: 96,
      ai_prediction: "Phù hợp cho cấp Trung Bình Yếu - Cơ bản (Cấp 2). Giao lưu nhẹ nhàng buổi sáng, cùng tiến bộ.",
      ai_handicap: "Đồng banh (0 điểm)",
      category: "doubles",
      is_ai_recommended: true,
      players: [
        { name: "Hoàng Thu Trang", skill_tier: "Trung Bình Yếu - Cơ bản", tier_id: 2, elo: 1050, avatar: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=300&q=80", photo: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=300&q=80", role: "Host", style: "Tân thủ", team: "A" },
        { name: "Phạm Hải Đăng", skill_tier: "Trung Bình Yếu - Cơ bản", tier_id: 2, elo: 1020, avatar: "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=300&q=80", photo: "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=300&q=80", role: "Member", style: "Cơ bản", team: "A" },
        { name: "Nguyễn Mai Anh", skill_tier: "Trung Bình Yếu - Cơ bản", tier_id: 2, elo: 1080, avatar: "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=300&q=80", photo: "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=300&q=80", role: "Member", style: "Tập luyện", team: "B" }
      ],
      chat_messages: [
        { sender: "Hoàng Thu Trang", text: "Chào cả nhà, sáng mai đánh nhẹ nhàng 6h sáng tại Tây Hồ cùng cấp nhé!", time: "18:00" }
      ]
    },
    {
      id: 708,
      room_name: "Đại Chiến Đỉnh Cao Cấp [Tốt - Chuyên nghiệp]",
      facility_id: 108,
      facility_name: "CLB Cầu Lông Hà Đông Master Club",
      district: "Hà Đông, Hà Nội",
      match_date: "Hôm nay, 22/09/2026",
      match_time: "20:30 - 22:30",
      required_tier: "Tốt - Chuyên nghiệp",
      required_tier_id: 7,
      required_elo_min: 1951,
      required_elo_max: 9999,
      match_type: "Đơn Nam",
      court_number: "Sân VIP 01 (Thảm Yonex Pro)",
      price_per_slot: "100.000đ",
      current_players: 1,
      max_players: 2,
      status: "OPEN",
      host_name: "Vũ Quang Huy",
      host_tier: "Tốt - Chuyên nghiệp",
      host_tier_id: 7,
      host_elo: 2050,
      host_photo: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=300&q=80",
      ai_compatibility: 92,
      ai_prediction: "Trận so tài đỉnh cao giữa các tay vợt Tốt - Chuyên nghiệp (Cấp 7). Tốc độ cầu > 300km/h.",
      ai_handicap: "Đồng banh (0 điểm)",
      category: "singles",
      is_ai_recommended: false,
      players: [
        { name: "Vũ Quang Huy", skill_tier: "Tốt - Chuyên nghiệp", tier_id: 7, elo: 2050, avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=300&q=80", photo: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=300&q=80", role: "Host", style: "Bán chuyên đỉnh cao", team: "A" }
      ],
      chat_messages: [
        { sender: "Vũ Quang Huy", text: "Tìm đối thủ solo đơn nam cùng hạng Chuyên nghiệp cọ xát tối nay!", time: "16:20" }
      ]
    },
    {
      id: 709,
      room_name: "Giao Lưu Nhập Môn Cấp [Yếu - Tân thủ]",
      facility_id: 101,
      facility_name: "CLB Cầu Lông Catchy Badminton Arena",
      district: "Hoàng Mai, Hà Nội",
      match_date: "Hôm nay, 22/09/2026",
      match_time: "17:00 - 19:00",
      required_tier: "Yếu - Tân thủ",
      required_tier_id: 1,
      required_elo_min: 0,
      required_elo_max: 950,
      match_type: "Đôi Nam/Nữ",
      court_number: "Sân 04 (Thảm Enlio)",
      price_per_slot: "35.000đ",
      current_players: 2,
      max_players: 4,
      status: "OPEN",
      host_name: "Trần Bảo Nam",
      host_tier: "Yếu - Tân thủ",
      host_tier_id: 1,
      host_elo: 800,
      host_photo: "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?auto=format&fit=crop&w=300&q=80",
      ai_compatibility: 98,
      ai_prediction: "Phòng ghép dành riêng cho các bạn Yếu - Tân thủ mới làm quen cầu lông, không áp lực điểm số.",
      ai_handicap: "Đồng banh (0 điểm)",
      category: "doubles",
      is_ai_recommended: true,
      players: [
        { name: "Trần Bảo Nam", skill_tier: "Yếu - Tân thủ", tier_id: 1, elo: 800, avatar: "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?auto=format&fit=crop&w=300&q=80", photo: "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?auto=format&fit=crop&w=300&q=80", role: "Host", style: "Mới chơi", team: "A" },
        { name: "Lê Thu Hà", skill_tier: "Yếu - Tân thủ", tier_id: 1, elo: 820, avatar: "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=300&q=80", photo: "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=300&q=80", role: "Member", style: "Tập giao cầu", team: "B" }
      ],
      chat_messages: [
        { sender: "Trần Bảo Nam", text: "Chào mọi người, tụi mình mới tập chơi, hoan nghênh các bạn cùng cấp Tân thủ vào rèn luyện!", time: "15:30" }
      ]
    }
  ],

  // 9. Dữ liệu Heatmap lấp đầy sân
  occupancy_heatmap: [
    { hour: "06:00 - 08:00", rate: 45, status: "low" },
    { hour: "08:00 - 10:00", rate: 30, status: "low" },
    { hour: "10:00 - 14:00", rate: 20, status: "low" },
    { hour: "14:00 - 17:00", rate: 60, status: "mid" },
    { hour: "17:00 - 19:00", rate: 95, status: "high" },
    { hour: "19:00 - 21:00", rate: 98, status: "high" },
    { hour: "21:00 - 23:00", rate: 70, status: "mid" }
  ],

  // 10. BẢNG matches & match_players (Xác nhận kết quả 2 chiều & Anti-Cheat)
  matches: [
    {
      id: 103,
      court_id: 201,
      facility_id: 101,
      match_type: "SINGLES",
      start_time: "18:30",
      end_time: "19:30",
      match_date: "29/09/2026 (18:30 - 19:30)",
      status: "PENDING_CONFIRMATION",
      final_score: "21-18, 19-21, 21-19",
      winner_name: "Nguyễn Văn Hùng",
      reporter_name: "Nguyễn Văn Hùng",
      summary: "Hùng thắng chung cuộc 2 - 1",
      player_a_name: "Nguyễn Văn Hùng",
      player_a_elo: 1450,
      player_a_gain: 16,
      player_b_name: "Đỗ Minh Đức",
      player_b_elo: 1520,
      player_b_gain: -16,
      created_at: "2026-09-29 19:35:00"
    }
  ],

  match_players: [
    {
      id: 1,
      match_id: 103,
      player_id: 1,
      team: "A",
      player_name: "Nguyễn Văn Hùng",
      elo_before: 1450,
      elo_after: 1466,
      elo_change: 16,
      score_claimed: "21-18, 19-21, 21-19 (Thắng 2-1)",
      result: "WIN",
      confirmation_status: "CONFIRMED",
      submitted_at: "2026-09-29 19:35:00"
    },
    {
      id: 2,
      match_id: 103,
      player_id: 8,
      team: "B",
      player_name: "Đỗ Minh Đức",
      elo_before: 1520,
      elo_after: 1504,
      elo_change: -16,
      score_claimed: null,
      result: "LOSS",
      confirmation_status: "PENDING",
      submitted_at: null
    }
  ]
};

// Luu va Tai du lieu tu dong vao LocalStorage & May chu Backend tap trung (Central Server)
const CENTRAL_API_URL = "/api/database";

function loadMockDataFromLocalStorage() {
  try {
    const savedData = localStorage.getItem('badminton_mock_data');
    if (savedData) {
      const parsed = JSON.parse(savedData);
      // Failsafe: Neu localStorage bi luu facilities rong hoac duoi 5 san, xoa de khoi phuc 30 san goc
      if (!parsed.facilities || !Array.isArray(parsed.facilities) || parsed.facilities.length < 5) {
        delete parsed.facilities;
        try { localStorage.removeItem('badminton_mock_data'); } catch(e){}
      }
      applyDataToMockData(parsed);
    }
  } catch (e) {
    console.warn('Could not load mock data from localStorage:', e);
  }
}

function applyDataToMockData(sourceData) {
  if (!sourceData) return;
  const keys = ['courts', 'time_slots', 'equipments', 'booking_orders', 'invoices', 'occupancy_heatmap', 'bookings', 'orders', 'player_profiles', 'elo_histories', 'matches', 'match_players'];
  keys.forEach(k => {
    if (sourceData[k] && Array.isArray(sourceData[k])) {
      MockData[k] = sourceData[k];
    }
  });

  if (sourceData.matchmaking_rooms && Array.isArray(sourceData.matchmaking_rooms)) {
    MockData.matchmaking_rooms = sourceData.matchmaking_rooms;
  }

  // 1. Cap nhat danh sach co so san (facilities) - Failsafe: Khong ghi de neu tap nguon bi rong
  if (sourceData.facilities && Array.isArray(sourceData.facilities) && sourceData.facilities.length > 0) {
    MockData.facilities = sourceData.facilities;
  }

  // 2. Cap nhat danh sach nguoi dung (users) & chuan hoa mat khau / ELO
  if (sourceData.users && Array.isArray(sourceData.users)) {
    sourceData.users.forEach(u => {
      // Chuan hoa mat khau neu bi null / undefined
      if (!u.password || u.password === 'undefined' || u.password === 'null' || typeof u.password !== 'string' || !u.password.trim()) {
        u.password = (u.phone === '0123456789' ? '02092006' : '123456');
      }
      // Chuan hoa ELO neu bi undefined
      if (u.elo_rating === undefined || u.elo_rating === null || u.elo_rating === 'undefined') {
        u.elo_rating = (u.role === 'CUSTOMER' ? 1200 : 'N/A');
      }
    });
    MockData.users = sourceData.users;
  }
}

function saveMockDataToLocalStorage() {
  try {
    const payload = {};
    const keys = ['users', 'facilities', 'courts', 'time_slots', 'equipments', 'booking_orders', 'invoices', 'matchmaking_rooms', 'occupancy_heatmap', 'player_profiles', 'elo_histories', 'matches', 'match_players', 'bookings', 'orders'];
    keys.forEach(k => {
      if (MockData[k]) payload[k] = MockData[k];
    });
    localStorage.setItem('badminton_mock_data', JSON.stringify(payload));

    // Dong thoi tu dong gui du lieu len May chu Backend de dong bo tat ca trinh duyet
    syncDataToCentralServer(payload);
  } catch (e) {
    console.warn('Could not save mock data to localStorage:', e);
  }
}

// Gui du lieu len Server tap trung
async function syncDataToCentralServer(payload) {
  try {
    const res = await fetch(CENTRAL_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      console.log('⚡ Central server synced successfully');
    }
  } catch (err) {
    // Neu chua chay server.py thi van chay muot ma offline qua localStorage
  }
}

// Lay du lieu tu Server tap trung ve de dong bo voi bat ky trinh duyet nao (Brave, Chrome, Edge)
async function fetchCentralServerDatabase() {
  try {
    const res = await fetch(CENTRAL_API_URL);
    if (res.ok) {
      const serverData = await res.json();
      if (serverData && (serverData.users || serverData.facilities)) {
        const prevUsersCount = MockData.users.length;
        const prevFacsCount = MockData.facilities.length;

        applyDataToMockData(serverData);
        localStorage.setItem('badminton_mock_data', JSON.stringify(MockData));

        // Re-render moi giao dien neu co du lieu thay doi
        if (window.app) {
          const hasChanges = (prevUsersCount !== MockData.users.length) || (prevFacsCount !== MockData.facilities.length);
          if (hasChanges || window.app.currentView === 'ui-02' || window.app.currentView === 'ui-03' || window.app.currentView === 'ui-20' || window.app.currentView === 'ui-19') {
            if (window.app.renderCustomerFacilities) window.app.renderCustomerFacilities();
            if (window.app.initLeafletMap) window.app.initLeafletMap();
            if (window.app.renderAdminUsers) window.app.renderAdminUsers();
            if (window.app.renderDatabaseInspector) window.app.renderDatabaseInspector();
            if (window.app.renderAdminOverviewFacilities) window.app.renderAdminOverviewFacilities();
          }
        }
      } else if (MockData.users && MockData.users.length > 0) {
        // Neu server chua co du lieu, day toan bo du lieu hien tai len server
        saveMockDataToLocalStorage();
      }
    }
  } catch (err) {
    // Server chua khoi chay thi dung localStorage
  }
}

// Lang nghe su kien storage tu tab / cua so khac tren cung trinh duyet de dong bo lap tuc
window.addEventListener('storage', (e) => {
  if (e.key === 'badminton_mock_data') {
    loadMockDataFromLocalStorage();
    if (window.app) {
      if (app.renderAdminUsers) app.renderAdminUsers();
      if (app.renderDatabaseInspector) app.renderDatabaseInspector();
      if (app.renderAdminOverviewFacilities) app.renderAdminOverviewFacilities();
      if (app.renderCustomerFacilities) app.renderCustomerFacilities();
      if (app.renderAdminApprovals) app.renderAdminApprovals();
    }
  }
});

// Khoi tao load du lieu ngay khi nap file data.js
loadMockDataFromLocalStorage();
fetchCentralServerDatabase();

// Tu dong dong bo theo chu ky 3 giay voi may chu de dam bao moi trinh duyet deu cap nhat tuc thi
setInterval(() => {
  fetchCentralServerDatabase();
}, 3000);



