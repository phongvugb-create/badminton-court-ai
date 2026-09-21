/* ==========================================================================
   BADMINTON AI MANAGEMENT SYSTEM - MOCK DATA (9 DATABASE TABLES)
   ========================================================================== */

const MockData = {
  // 1. BẢNG users
  users: [
    { id: 1, name: "Nguyễn Văn Hùng", phone: "0901234567", password: "123456", role: "CUSTOMER", elo_rating: 1450, avatar: "H", is_approved: true },
    { id: 2, name: "Trần Thị Mai", phone: "0912345678", password: "123456", role: "CUSTOMER", elo_rating: 1680, avatar: "M", is_approved: true },
    { id: 3, name: "Lê Hoàng Nam (Chủ Sân)", phone: "0988888888", password: "owner123", role: "OWNER", facility_id: 101, avatar: "N", is_approved: true },
    { id: 4, name: "Phạm Quốc Tuấn (Thu Ngân)", phone: "0922334455", password: "staff123", role: "STAFF", facility_id: 101, avatar: "T", is_approved: true },
    { id: 5, name: "Admin Quản Trị", phone: "0999888777", password: "admin123", role: "ADMIN", avatar: "A", is_approved: true },
    { id: 6, name: "Vũ Nhất Phong", phone: "0983582321", password: "password123", role: "CUSTOMER", elo_rating: 1200, avatar: "V", is_approved: true },
    { id: 7, name: "Trương Quốc Khánh (Chủ Sân)", phone: "0123456789", password: "02092006", role: "OWNER", facility_id: 101, elo_rating: "N/A", avatar: "K", is_approved: true }
  ],

  // 2. BẢNG facilities (Danh mục cụm cơ sở Sân Cầu Lông chuyên nghiệp toàn khu vực)
  facilities: [
    {
      id: 101,
      name: "CLB Cầu Lông Catchy Badminton Arena",
      address: "Số 136 Phố Tân Khai, Quận Hoàng Mai, Hà Nội",
      distance: "2.5km",
      latitude: 20.9856,
      longitude: 105.8580,
      open_time: "05:00",
      close_time: "24:00",
      open_hours: "05:00 - 24:00",
      is_approved: true,
      rating: 4.9,
      reviews_count: 148,
      img: "images/court1.jpg",
      club_logo: "CATCHY",
      club_avatar_bg: "#f0fdf4",
      club_avatar_color: "#16a34a",
      badges: ["Đơn ngày", "Thảm Enlio VIP"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 8
    },
    {
      id: 102,
      name: "CLB Cầu Lông Đống Đa Sport Hub",
      address: "102 Phố Láng Hạ, Phường Láng Hạ, Quận Đống Đa, Hà Nội",
      distance: "4.8km",
      latitude: 21.0153,
      longitude: 105.8152,
      open_time: "05:00",
      close_time: "23:00",
      open_hours: "05:00 - 23:00",
      is_approved: true,
      rating: 4.9,
      reviews_count: 142,
      img: "images/court4.jpg",
      club_logo: "SPORT HUB",
      club_avatar_bg: "#f0fdf4",
      club_avatar_color: "#16a34a",
      badges: ["Đơn ngày", "Sự kiện"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 10
    },
    {
      id: 103,
      name: "Smash Zone Cyber Badminton Mỹ Đình",
      address: "15 Lê Đức Thọ, Phường Mỹ Đình, Quận Nam Từ Liêm, Hà Nội",
      distance: "8.3km",
      latitude: 21.0285,
      longitude: 105.7682,
      open_time: "06:00",
      close_time: "23:30",
      open_hours: "06:00 - 23:30",
      is_approved: true,
      rating: 4.8,
      reviews_count: 88,
      img: "images/court5.jpg",
      club_logo: "SMASH",
      club_avatar_bg: "#ecfdf5",
      club_avatar_color: "#15803d",
      badges: ["Đơn ngày", "Thảm Yonex"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 8
    },
    {
      id: 104,
      name: "CLB Cầu Lông Ba Đình Star Arena",
      address: "178 Điện Biên Phủ, Phường Điện Biên, Quận Ba Đình, Hà Nội",
      distance: "3.2km",
      latitude: 21.0315,
      longitude: 105.8398,
      open_time: "05:30",
      close_time: "23:00",
      open_hours: "05:30 - 23:00",
      is_approved: true,
      rating: 4.8,
      reviews_count: 116,
      img: "images/court6.jpg",
      club_logo: "BA ĐÌNH",
      club_avatar_bg: "#f0fdf4",
      club_avatar_color: "#167946",
      badges: ["Đơn ngày", "Sự kiện"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 12
    },
    {
      id: 105,
      name: "Nhà Thi Đấu Cầu Lông Bách Khoa Yonex Pro",
      address: "219 Phố Lê Thanh Nghị, Phường Bách Khoa, Quận Hai Bà Trưng, Hà Nội",
      distance: "5.1km",
      latitude: 21.0028,
      longitude: 105.8475,
      open_time: "06:00",
      close_time: "22:30",
      open_hours: "06:00 - 22:30",
      is_approved: true,
      rating: 4.9,
      reviews_count: 175,
      img: "images/court7.jpg",
      club_logo: "BÁCH KHOA",
      club_avatar_bg: "#dcfce7",
      club_avatar_color: "#15803d",
      badges: ["Đơn ngày", "Sự kiện"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 10
    },
    {
      id: 106,
      name: "Thanh Xuân Badminton Club & Fuji Pro",
      address: "159 Lê Văn Lương, Phường Nhân Chính, Quận Thanh Xuân, Hà Nội",
      distance: "6.4km",
      latitude: 21.0062,
      longitude: 105.8085,
      open_time: "05:30",
      close_time: "23:00",
      open_hours: "05:30 - 23:00",
      is_approved: true,
      rating: 4.9,
      reviews_count: 210,
      img: "images/court8.jpg",
      club_logo: "THANH XUÂN",
      club_avatar_bg: "#f0fdf4",
      club_avatar_color: "#16a34a",
      badges: ["Đơn ngày", "Thảm Enlio"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 14
    },
    {
      id: 107,
      name: "CLB Cầu Lông Tây Hồ Arena - Quảng An",
      address: "48 Đặng Thai Mai, Phường Quảng An, Quận Tây Hồ, Hà Nội",
      distance: "4.2km",
      latitude: 21.0645,
      longitude: 105.8241,
      open_time: "06:00",
      close_time: "22:30",
      open_hours: "06:00 - 22:30",
      is_approved: true,
      rating: 4.7,
      reviews_count: 92,
      img: "images/court9.jpg",
      club_logo: "TÂY HỒ",
      club_avatar_bg: "#f0fdf4",
      club_avatar_color: "#167946",
      badges: ["Đơn ngày", "Sân ven hồ"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 8
    },
    {
      id: 108,
      name: "Hà Đông Cyber Badminton Club - Văn Quán",
      address: "215 Trần Phú, Phường Văn Quán, Quận Hà Đông, Hà Nội",
      distance: "9.5km",
      latitude: 20.9812,
      longitude: 105.7891,
      open_time: "05:00",
      close_time: "23:30",
      open_hours: "05:00 - 23:30",
      is_approved: true,
      rating: 4.9,
      reviews_count: 185,
      img: "images/court10.jpg",
      club_logo: "HÀ ĐÔNG",
      club_avatar_bg: "#ecfdf5",
      club_avatar_color: "#15803d",
      badges: ["Đơn ngày", "Máy lạnh"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 12
    },
    {
      id: 109,
      name: "Sân Cầu Lông Cầu Giấy Pro Arena",
      address: "35 Dịch Vọng Hậu, Cầu Giấy, Hà Nội",
      distance: "5.8km",
      latitude: 21.0345,
      longitude: 105.7852,
      open_time: "05:00",
      close_time: "23:00",
      open_hours: "05:00 - 23:00",
      is_approved: true,
      rating: 4.8,
      reviews_count: 80,
      img: "images/court1.jpg",
      club_logo: "CẦU GIẤY",
      club_avatar_bg: "#f0fdf4",
      club_avatar_color: "#16a34a",
      badges: ["Đơn ngày", "Sự kiện"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 8
    },
    {
      id: 110,
      name: "CLB Cầu Lông Hoàng Gia Cổ Nhuế",
      address: "Số 18 Đường Cổ Nhuế, Bắc Từ Liêm, Hà Nội",
      distance: "7.5km",
      latitude: 21.0650,
      longitude: 105.7720,
      open_time: "05:30",
      close_time: "23:00",
      open_hours: "05:30 - 23:00",
      is_approved: true,
      rating: 4.9,
      reviews_count: 65,
      img: "images/court2.jpg",
      club_logo: "CỔ NHUẾ",
      club_avatar_bg: "#dcfce7",
      club_avatar_color: "#15803d",
      badges: ["Đơn ngày", "Thảm Yonex"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 6
    },
    {
      id: 111,
      name: "Sân Cầu Lông Quần Ngựa Liễu Giai",
      address: "30 Văn Cao, Liễu Giai, Ba Đình, Hà Nội",
      distance: "3.9km",
      latitude: 21.0392,
      longitude: 105.8174,
      open_time: "05:30",
      close_time: "22:30",
      open_hours: "05:30 - 22:30",
      is_approved: true,
      rating: 4.7,
      reviews_count: 90,
      img: "images/court3.jpg",
      club_logo: "QUẦN NGỰA",
      club_avatar_bg: "#f0fdf4",
      club_avatar_color: "#167946",
      badges: ["Đơn ngày", "Sự kiện"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 8
    },
    {
      id: 112,
      name: "CLB Cầu Lông Định Công Arena",
      address: "Khu đô thị Định Công, Hoàng Mai, Hà Nội",
      distance: "5.5km",
      latitude: 20.9950,
      longitude: 105.8310,
      open_time: "05:00",
      close_time: "23:00",
      open_hours: "05:00 - 23:00",
      is_approved: true,
      rating: 4.8,
      reviews_count: 67,
      img: "images/court4.jpg",
      club_logo: "ĐỊNH CÔNG",
      club_avatar_bg: "#f0fdf4",
      club_avatar_color: "#16a34a",
      badges: ["Đơn ngày", "Sự kiện"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 8
    },
    {
      id: 113,
      name: "Sân Cầu Lông Ciputra Badminton Club",
      address: "Khu Đô Thị Ciputra, Bắc Từ Liêm, Hà Nội",
      distance: "7.2km",
      latitude: 21.0782,
      longitude: 105.7950,
      open_time: "06:00",
      close_time: "23:00",
      open_hours: "06:00 - 23:00",
      is_approved: true,
      rating: 5.0,
      reviews_count: 140,
      img: "images/court5.jpg",
      club_logo: "CIPUTRA",
      club_avatar_bg: "#dcfce7",
      club_avatar_color: "#15803d",
      badges: ["Đơn ngày", "VIP"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 12
    },
    {
      id: 114,
      name: "Sân Cầu Lông Long Biên Riverside Pro",
      address: "Đường Cổ Linh, Long Biên, Hà Nội",
      distance: "6.8km",
      latitude: 21.0310,
      longitude: 105.8850,
      open_time: "05:30",
      close_time: "23:00",
      open_hours: "05:30 - 23:00",
      is_approved: true,
      rating: 4.8,
      reviews_count: 85,
      img: "images/court6.jpg",
      club_logo: "LONG BIÊN",
      club_avatar_bg: "#f0fdf4",
      club_avatar_color: "#15803d",
      badges: ["Đơn ngày", "Sự kiện"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 10
    },
    // --- 28 SÂN CẦU LÔNG MỚI TÍCH HỢP TỪ BẢNG DỮ LIỆU ---
    // Ảnh 1: Khu vực Đống Đa / Cầu Giấy / Ba Đình
    {
      id: 115,
      name: "Sân cầu lông Đại học Công Đoàn",
      address: "169 Tây Sơn, Phường Quang Trung, Quận Đống Đa, Hà Nội",
      distance: "3.8km",
      latitude: 21.0118,
      longitude: 105.8236,
      open_time: "05:30",
      close_time: "22:30",
      open_hours: "05:30 - 22:30",
      price_range: "80.000đ/giờ",
      base_price: 80000,
      is_approved: true,
      rating: 4.8,
      reviews_count: 62,
      img: "images/court1.jpg",
      club_logo: "CÔNG ĐOÀN",
      club_avatar_bg: "#f0fdf4",
      club_avatar_color: "#16a34a",
      badges: ["Đơn ngày", "Giá sinh viên", "Thảm Yonex"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 2
    },
    {
      id: 116,
      name: "Sân cầu lông Trung Kính",
      address: "Ngõ 218 Trung Kính, Phường Yên Hòa, Quận Cầu Giấy, Hà Nội",
      distance: "5.2km",
      latitude: 21.0185,
      longitude: 105.7942,
      open_time: "05:00",
      close_time: "23:00",
      open_hours: "05:00 - 23:00",
      price_range: "70.000đ/giờ",
      base_price: 70000,
      is_approved: true,
      rating: 4.7,
      reviews_count: 78,
      img: "images/court2.jpg",
      club_logo: "TRUNG KÍNH",
      club_avatar_bg: "#dcfce7",
      club_avatar_color: "#15803d",
      badges: ["Đơn ngày", "Giá tốt", "Thảm Enlio"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 3
    },
    {
      id: 117,
      name: "Sân cầu lông Quang Trung 178 đường Láng",
      address: "178 Đường Láng, Phường Thịnh Quang, Quận Đống Đa, Hà Nội",
      distance: "4.1km",
      latitude: 21.0089,
      longitude: 105.8198,
      open_time: "05:30",
      close_time: "22:30",
      open_hours: "05:30 - 22:30",
      price_range: "50.000đ - 80.000đ/giờ",
      base_price: 65000,
      is_approved: true,
      rating: 4.8,
      reviews_count: 85,
      img: "images/court3.jpg",
      club_logo: "QUANG TRUNG",
      club_avatar_bg: "#f0fdf4",
      club_avatar_color: "#167946",
      badges: ["Đơn ngày", "Giá rẻ"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 3
    },
    {
      id: 118,
      name: "Sân cầu lông 105 Láng Hạ",
      address: "105 Láng Hạ, Phường Láng Hạ, Quận Đống Đa, Hà Nội",
      distance: "4.5km",
      latitude: 21.0146,
      longitude: 105.8145,
      open_time: "06:00",
      close_time: "22:00",
      open_hours: "06:00 - 22:00",
      price_range: "90.000đ/giờ",
      base_price: 90000,
      is_approved: true,
      rating: 4.6,
      reviews_count: 42,
      img: "images/court4.jpg",
      club_logo: "105 LÁNG HẠ",
      club_avatar_bg: "#ecfdf5",
      club_avatar_color: "#15803d",
      badges: ["Đơn ngày", "VIP"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 1
    },
    {
      id: 119,
      name: "Sân cầu lông Ban Cơ Yếu Chính Phủ",
      address: "105 Nguyễn Chí Thanh, Phường Láng Thượng, Quận Đống Đa, Hà Nội",
      distance: "4.6km",
      latitude: 21.0210,
      longitude: 105.8115,
      open_time: "05:30",
      close_time: "22:30",
      open_hours: "05:30 - 22:30",
      price_range: "90.000đ/giờ",
      base_price: 90000,
      is_approved: true,
      rating: 4.9,
      reviews_count: 68,
      img: "images/court5.jpg",
      club_logo: "CƠ YẾU",
      club_avatar_bg: "#f0fdf4",
      club_avatar_color: "#16a34a",
      badges: ["Đơn ngày", "Thảm Yonex Pro"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 2
    },
    {
      id: 120,
      name: "Sân cầu lông Học Viện Ngân Hàng – Ambition",
      address: "12 Chùa Bộc, Phường Quang Trung, Quận Đống Đa, Hà Nội",
      distance: "3.9km",
      latitude: 21.0082,
      longitude: 105.8276,
      open_time: "05:00",
      close_time: "23:00",
      open_hours: "05:00 - 23:00",
      price_range: "80.000đ - 100.000đ/giờ",
      base_price: 90000,
      is_approved: true,
      rating: 4.9,
      reviews_count: 135,
      img: "images/court6.jpg",
      club_logo: "AMBITION",
      club_avatar_bg: "#dcfce7",
      club_avatar_color: "#15803d",
      badges: ["Đơn ngày", "Thảm Yonex Pro", "Có máy lạnh"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 3
    },
    {
      id: 121,
      name: "Sân cầu lông Ngoại Thương",
      address: "91 Phố Chùa Láng, Phường Láng Thượng, Quận Đống Đa, Hà Nội",
      distance: "5.0km",
      latitude: 21.0264,
      longitude: 105.8035,
      open_time: "05:30",
      close_time: "22:30",
      open_hours: "05:30 - 22:30",
      price_range: "90.000đ/giờ",
      base_price: 90000,
      is_approved: true,
      rating: 4.8,
      reviews_count: 110,
      img: "images/court7.jpg",
      club_logo: "FTU",
      club_avatar_bg: "#f0fdf4",
      club_avatar_color: "#167946",
      badges: ["Đơn ngày", "Giá sinh viên"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 3
    },
    {
      id: 122,
      name: "Sân cầu lông Fleet",
      address: "Ngõ 1194 Đường Láng, Láng Thượng, Đống Đa, Hà Nội",
      distance: "5.1km",
      latitude: 21.0280,
      longitude: 105.8010,
      open_time: "06:00",
      close_time: "22:00",
      open_hours: "06:00 - 22:00",
      price_range: "100.000đ/giờ",
      base_price: 100000,
      is_approved: true,
      rating: 4.7,
      reviews_count: 45,
      img: "images/court8.jpg",
      club_logo: "FLEET",
      club_avatar_bg: "#f0fdf4",
      club_avatar_color: "#15803d",
      badges: ["Đơn ngày", "Thảm Fleet VIP"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 1
    },
    {
      id: 123,
      name: "Sân cầu lông Bộ Công An",
      address: "47 Phạm Văn Đồng, Mai Dịch, Cầu Giấy, Hà Nội",
      distance: "6.9km",
      latitude: 21.0470,
      longitude: 105.7795,
      open_time: "05:00",
      close_time: "23:00",
      open_hours: "05:00 - 23:00",
      price_range: "80.000đ - 110.000đ/giờ",
      base_price: 90000,
      is_approved: true,
      rating: 4.9,
      reviews_count: 160,
      img: "images/court9.jpg",
      club_logo: "BCA",
      club_avatar_bg: "#dcfce7",
      club_avatar_color: "#15803d",
      badges: ["Đơn ngày", "Quy mô lớn", "Thảm Yonex Pro"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 5
    },
    {
      id: 124,
      name: "Sân cầu lông Bệnh Viện Phụ Sản Hà Nội",
      address: "929 Đường La Thành, Láng Thượng, Ba Đình, Hà Nội",
      distance: "4.7km",
      latitude: 21.0268,
      longitude: 105.8078,
      open_time: "05:30",
      close_time: "22:00",
      open_hours: "05:30 - 22:00",
      price_range: "50.000đ - 80.000đ/giờ",
      base_price: 65000,
      is_approved: true,
      rating: 4.7,
      reviews_count: 58,
      img: "images/court10.jpg",
      club_logo: "PHỤ SẢN",
      club_avatar_bg: "#f0fdf4",
      club_avatar_color: "#16a34a",
      badges: ["Đơn ngày", "Giá rẻ"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 3
    },
    {
      id: 125,
      name: "Sân cầu lông Đại học Thủy Lợi",
      address: "175 Tây Sơn, Phường Trung Liệt, Quận Đống Đa, Hà Nội",
      distance: "3.7km",
      latitude: 21.0095,
      longitude: 105.8242,
      open_time: "05:00",
      close_time: "22:30",
      open_hours: "05:00 - 22:30",
      price_range: "50.000đ/giờ",
      base_price: 50000,
      is_approved: true,
      rating: 4.8,
      reviews_count: 145,
      img: "images/court1.jpg",
      club_logo: "THỦY LỢI",
      club_avatar_bg: "#ecfdf5",
      club_avatar_color: "#15803d",
      badges: ["Đơn ngày", "Giá siêu rẻ", "Sự kiện"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 4
    },

    // Ảnh 2: Hai Bà Trưng / Minh Khai / Hồng Hà
    {
      id: 126,
      name: "Sân cầu lông Đại học Xây Dựng",
      address: "55 Đường Giải Phóng, Đồng Tâm, Hai Bà Trưng, Hà Nội",
      distance: "4.3km",
      latitude: 21.0035,
      longitude: 105.8426,
      open_time: "05:00",
      close_time: "22:30",
      open_hours: "05:00 - 22:30",
      price_range: "90.000đ/giờ",
      base_price: 90000,
      is_approved: true,
      rating: 4.9,
      reviews_count: 120,
      img: "images/court2.jpg",
      club_logo: "XÂY DỰNG",
      club_avatar_bg: "#dcfce7",
      club_avatar_color: "#167946",
      badges: ["Đơn ngày", "Thảm Yonex", "Giá tốt"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 4
    },
    {
      id: 127,
      name: "Sân cầu lông Đường Sông",
      address: "Cảng Hà Nội, Phường Bạch Đằng, Hai Bà Trưng, Hà Nội",
      distance: "3.5km",
      latitude: 21.0112,
      longitude: 105.8685,
      open_time: "05:30",
      close_time: "22:00",
      open_hours: "05:30 - 22:00",
      price_range: "50.000đ - 90.000đ/giờ",
      base_price: 70000,
      is_approved: true,
      rating: 4.7,
      reviews_count: 49,
      img: "images/court3.jpg",
      club_logo: "ĐƯỜNG SÔNG",
      club_avatar_bg: "#f0fdf4",
      club_avatar_color: "#15803d",
      badges: ["Đơn ngày", "Sân ven sông"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 2
    },
    {
      id: 128,
      name: "Sân cầu lông Đường Sông 2",
      address: "Khu tập thể Đường Sông, Lương Yên, Hai Bà Trưng, Hà Nội",
      distance: "3.4km",
      latitude: 21.0125,
      longitude: 105.8670,
      open_time: "05:30",
      close_time: "22:00",
      open_hours: "05:30 - 22:00",
      price_range: "90.000đ/giờ",
      base_price: 90000,
      is_approved: true,
      rating: 4.8,
      reviews_count: 36,
      img: "images/court4.jpg",
      club_logo: "Đ.SÔNG 2",
      club_avatar_bg: "#ecfdf5",
      club_avatar_color: "#16a34a",
      badges: ["Đơn ngày", "Thảm tiêu chuẩn"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 2
    },
    {
      id: 129,
      name: "Sân cầu lông Hồng Hà",
      address: "Phố Hồng Hà, Phường Chương Dương, Hoàn Kiếm, Hà Nội",
      distance: "2.8km",
      latitude: 21.0250,
      longitude: 105.8600,
      open_time: "05:00",
      close_time: "22:30",
      open_hours: "05:00 - 22:30",
      price_range: "50.000đ - 90.000đ/giờ",
      base_price: 70000,
      is_approved: true,
      rating: 4.8,
      reviews_count: 88,
      img: "images/court5.jpg",
      club_logo: "HỒNG HÀ",
      club_avatar_bg: "#f0fdf4",
      club_avatar_color: "#15803d",
      badges: ["Đơn ngày", "Thoáng mát"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 4
    },
    {
      id: 130,
      name: "Trung Tâm TDTT Sân Cầu Lông 521 Minh Khai",
      address: "521 Minh Khai, Phường Vĩnh Tuy, Hai Bà Trưng, Hà Nội",
      distance: "4.6km",
      latitude: 20.9995,
      longitude: 105.8690,
      open_time: "05:00",
      close_time: "23:00",
      open_hours: "05:00 - 23:00",
      price_range: "40.000đ - 80.000đ/giờ",
      base_price: 60000,
      is_approved: true,
      rating: 4.9,
      reviews_count: 175,
      img: "images/court6.jpg",
      club_logo: "521 MINH KHAI",
      club_avatar_bg: "#dcfce7",
      club_avatar_color: "#167946",
      badges: ["Đơn ngày", "Quy mô 7 sân", "Giá cực rẻ"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 7
    },

    // Ảnh 3: Đống Đa / Thanh Xuân / Cầu Giấy
    {
      id: 131,
      name: "Sân cầu lông Pháo đài Láng",
      address: "Ngõ 102 Pháo Đài Láng, Láng Thượng, Đống Đa, Hà Nội",
      distance: "4.8km",
      latitude: 21.0188,
      longitude: 105.8055,
      open_time: "05:30",
      close_time: "22:00",
      open_hours: "05:30 - 22:00",
      price_range: "50.000đ - 80.000đ/giờ",
      base_price: 65000,
      is_approved: true,
      rating: 4.7,
      reviews_count: 54,
      img: "images/court7.jpg",
      club_logo: "PHÁO ĐÀI",
      club_avatar_bg: "#f0fdf4",
      club_avatar_color: "#16a34a",
      badges: ["Đơn ngày", "Giá rẻ"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 3
    },
    {
      id: 132,
      name: "Sân cầu lông trường THPT Lý Thái Tổ",
      address: "165 Phố Hoàng Ngân, Trung Hòa, Cầu Giấy, Hà Nội",
      distance: "5.5km",
      latitude: 21.0098,
      longitude: 105.8035,
      open_time: "06:00",
      close_time: "22:00",
      open_hours: "06:00 - 22:00",
      price_range: "50.000đ - 80.000đ/giờ",
      base_price: 65000,
      is_approved: true,
      rating: 4.8,
      reviews_count: 72,
      img: "images/court8.jpg",
      club_logo: "LÝ THÁI TỔ",
      club_avatar_bg: "#dcfce7",
      club_avatar_color: "#15803d",
      badges: ["Đơn ngày", "Sân trường học"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 3
    },
    {
      id: 133,
      name: "Sân cầu lông 266 phố Vũ Hữu",
      address: "266 Phố Vũ Hữu, Trung Văn, Nam Từ Liêm / Thanh Xuân, Hà Nội",
      distance: "6.8km",
      latitude: 20.9972,
      longitude: 105.7915,
      open_time: "05:00",
      close_time: "22:30",
      open_hours: "05:00 - 22:30",
      price_range: "50.000đ - 80.000đ/giờ",
      base_price: 65000,
      is_approved: true,
      rating: 4.8,
      reviews_count: 80,
      img: "images/court9.jpg",
      club_logo: "VŨ HỮU",
      club_avatar_bg: "#f0fdf4",
      club_avatar_color: "#167946",
      badges: ["Đơn ngày", "Thảm Enlio"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 3
    },
    {
      id: 134,
      name: "Sân CLB Cầu Lông Đoàn Thanh Niên Trường TCSP Mẫu giáo",
      address: "387 Hoàng Quốc Việt, Nghĩa Tân, Cầu Giấy, Hà Nội",
      distance: "6.5km",
      latitude: 21.0455,
      longitude: 105.7910,
      open_time: "05:30",
      close_time: "22:00",
      open_hours: "05:30 - 22:00",
      price_range: "50.000đ - 80.000đ/giờ",
      base_price: 65000,
      is_approved: true,
      rating: 4.7,
      reviews_count: 46,
      img: "images/court10.jpg",
      club_logo: "MẪU GIÁO",
      club_avatar_bg: "#ecfdf5",
      club_avatar_color: "#15803d",
      badges: ["Đơn ngày", "Giá rẻ"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 3
    },
    {
      id: 135,
      name: "Sân cầu lông 134 Quan Nhân",
      address: "134 Phố Quan Nhân, Nhân Chính, Thanh Xuân, Hà Nội",
      distance: "5.1km",
      latitude: 21.0042,
      longitude: 105.8112,
      open_time: "05:30",
      close_time: "22:30",
      open_hours: "05:30 - 22:30",
      price_range: "50.000đ - 80.000đ/giờ",
      base_price: 65000,
      is_approved: true,
      rating: 4.8,
      reviews_count: 65,
      img: "images/court1.jpg",
      club_logo: "QUAN NHÂN",
      club_avatar_bg: "#dcfce7",
      club_avatar_color: "#16a34a",
      badges: ["Đơn ngày", "Thảm Yonex"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 3
    },

    // Ảnh 4: Quận Hà Đông
    {
      id: 136,
      name: "Sân cầu lông Hà Đông",
      address: "Phố Tô Hiệu, Phường Quang Trung, Quận Hà Đông, Hà Nội",
      distance: "8.5km",
      latitude: 20.9702,
      longitude: 105.7760,
      open_time: "05:00",
      close_time: "23:00",
      open_hours: "05:00 - 23:00",
      price_range: "80.000đ - 120.000đ/giờ",
      base_price: 90000,
      is_approved: true,
      rating: 4.9,
      reviews_count: 115,
      img: "images/court2.jpg",
      club_logo: "HÀ ĐÔNG",
      club_avatar_bg: "#f0fdf4",
      club_avatar_color: "#15803d",
      badges: ["Đơn ngày", "Thảm Enlio VIP"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 3
    },
    {
      id: 137,
      name: "Sân cầu lông La Khê – Hà Đông",
      address: "Khu đô thị Văn Khê, Phường La Khê, Hà Đông, Hà Nội",
      distance: "9.2km",
      latitude: 20.9765,
      longitude: 105.7625,
      open_time: "05:30",
      close_time: "22:30",
      open_hours: "05:30 - 22:30",
      price_range: "70.000đ - 130.000đ/giờ",
      base_price: 85000,
      is_approved: true,
      rating: 4.8,
      reviews_count: 92,
      img: "images/court3.jpg",
      club_logo: "LA KHÊ",
      club_avatar_bg: "#dcfce7",
      club_avatar_color: "#167946",
      badges: ["Đơn ngày", "Thảm Yonex Pro"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 3
    },
    {
      id: 138,
      name: "Sân cầu lông Nhà thi đấu Hà Đông",
      address: "182 Quang Trung, Phường Quang Trung, Quận Hà Đông, Hà Nội",
      distance: "8.6km",
      latitude: 20.9685,
      longitude: 105.7725,
      open_time: "05:00",
      close_time: "23:00",
      open_hours: "05:00 - 23:00",
      price_range: "70.000đ - 130.000đ/giờ",
      base_price: 85000,
      is_approved: true,
      rating: 4.9,
      reviews_count: 148,
      img: "images/court4.jpg",
      club_logo: "NTĐ HÀ ĐÔNG",
      club_avatar_bg: "#ecfdf5",
      club_avatar_color: "#15803d",
      badges: ["Đơn ngày", "Nhà thi đấu chuẩn", "Có máy lạnh"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 4
    },
    {
      id: 139,
      name: "Sân cầu lông trường THCS Lê Quý Đôn",
      address: "Khu Đô Thị Dương Nội, Hà Đông, Hà Nội",
      distance: "9.8km",
      latitude: 20.9832,
      longitude: 105.7485,
      open_time: "06:00",
      close_time: "22:00",
      open_hours: "06:00 - 22:00",
      price_range: "80.000đ - 130.000đ/giờ",
      base_price: 90000,
      is_approved: true,
      rating: 4.8,
      reviews_count: 64,
      img: "images/court5.jpg",
      club_logo: "LÊ QUÝ ĐÔN",
      club_avatar_bg: "#f0fdf4",
      club_avatar_color: "#16a34a",
      badges: ["Đơn ngày", "Sân trường học"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 3
    },
    {
      id: 140,
      name: "Sân cầu lông trường Chuyên Nguyễn Huệ – Hà Đông",
      address: "560 Quang Trung, La Khê, Hà Đông, Hà Nội",
      distance: "9.6km",
      latitude: 20.9630,
      longitude: 105.7612,
      open_time: "05:30",
      close_time: "22:30",
      open_hours: "05:30 - 22:30",
      price_range: "70.000đ - 120.000đ/giờ",
      base_price: 85000,
      is_approved: true,
      rating: 4.9,
      reviews_count: 105,
      img: "images/court6.jpg",
      club_logo: "NGUYỄN HUỆ",
      club_avatar_bg: "#dcfce7",
      club_avatar_color: "#15803d",
      badges: ["Đơn ngày", "Thảm Yonex", "Giá tốt"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 3
    },
    {
      id: 141,
      name: "Sân cầu lông trường Tiểu học Nguyễn Quý Đức",
      address: "Phường Đại Mỗ, Nam Từ Liêm, Hà Nội",
      distance: "8.2km",
      latitude: 20.9930,
      longitude: 105.7600,
      open_time: "06:00",
      close_time: "22:00",
      open_hours: "06:00 - 22:00",
      price_range: "80.000đ - 130.000đ/giờ",
      base_price: 85000,
      is_approved: true,
      rating: 4.7,
      reviews_count: 35,
      img: "images/court7.jpg",
      club_logo: "QUÝ ĐỨC",
      club_avatar_bg: "#f0fdf4",
      club_avatar_color: "#167946",
      badges: ["Đơn ngày"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 1
    },

    // Ảnh 5: Quận Long Biên
    {
      id: 142,
      name: "Sân cầu lông Việt Hưng",
      address: "Khu đô thị mới Việt Hưng, Quận Long Biên, Hà Nội",
      distance: "7.8km",
      latitude: 21.0560,
      longitude: 105.9050,
      open_time: "05:00",
      close_time: "23:00",
      open_hours: "05:00 - 23:00",
      price_range: "70.000đ - 130.000đ/giờ",
      base_price: 85000,
      is_approved: true,
      rating: 4.8,
      reviews_count: 88,
      img: "images/court8.jpg",
      club_logo: "VIỆT HƯNG",
      club_avatar_bg: "#dcfce7",
      club_avatar_color: "#15803d",
      badges: ["Đơn ngày", "Thảm Enlio VIP"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 3
    },
    {
      id: 143,
      name: "Sân Trung tâm quản lý bay",
      address: "Đường Nguyễn Sơn, Phường Bồ Đề, Quận Long Biên, Hà Nội",
      distance: "5.8km",
      latitude: 21.0375,
      longitude: 105.8820,
      open_time: "05:30",
      close_time: "22:30",
      open_hours: "05:30 - 22:30",
      price_range: "70.000đ - 120.000đ/giờ",
      base_price: 85000,
      is_approved: true,
      rating: 4.9,
      reviews_count: 95,
      img: "images/court9.jpg",
      club_logo: "QUẢN LÝ BAY",
      club_avatar_bg: "#f0fdf4",
      club_avatar_color: "#16a34a",
      badges: ["Đơn ngày", "Thảm Yonex Pro", "Có máy lạnh"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 2
    },
    {
      id: 144,
      name: "Sân cầu lông Trường Hải",
      address: "Số 1 Ngô Gia Tự, Phường Đức Giang, Quận Long Biên, Hà Nội",
      distance: "7.2km",
      latitude: 21.0585,
      longitude: 105.8910,
      open_time: "05:30",
      close_time: "22:00",
      open_hours: "05:30 - 22:00",
      price_range: "50.000đ - 80.000đ/giờ",
      base_price: 65000,
      is_approved: true,
      rating: 4.7,
      reviews_count: 52,
      img: "images/court10.jpg",
      club_logo: "TRƯỜNG HẢI",
      club_avatar_bg: "#ecfdf5",
      club_avatar_color: "#15803d",
      badges: ["Đơn ngày", "Giá rẻ"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 2
    },
    {
      id: 145,
      name: "Sân cầu lông Đoàn Kết – Thạch Bàn",
      address: "Tổ 4 Phường Thạch Bàn, Quận Long Biên, Hà Nội",
      distance: "8.1km",
      latitude: 21.0215,
      longitude: 105.9125,
      open_time: "05:00",
      close_time: "22:30",
      open_hours: "05:00 - 22:30",
      price_range: "70.000đ - 130.000đ/giờ",
      base_price: 85000,
      is_approved: true,
      rating: 4.8,
      reviews_count: 76,
      img: "images/court1.jpg",
      club_logo: "ĐOÀN KẾT",
      club_avatar_bg: "#dcfce7",
      club_avatar_color: "#167946",
      badges: ["Đơn ngày", "Thảm Enlio"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 3
    },
    {
      id: 146,
      name: "Sân cầu lông trường Tiểu học Đoàn Khuê – Long Biên",
      address: "Khu đô thị Việt Hưng, Giang Biên, Long Biên, Hà Nội",
      distance: "8.3km",
      latitude: 21.0595,
      longitude: 105.9085,
      open_time: "06:00",
      close_time: "22:00",
      open_hours: "06:00 - 22:00",
      price_range: "70.000đ - 110.000đ/giờ",
      base_price: 80000,
      is_approved: true,
      rating: 4.8,
      reviews_count: 60,
      img: "images/court2.jpg",
      club_logo: "ĐOÀN KHUÊ",
      club_avatar_bg: "#f0fdf4",
      club_avatar_color: "#15803d",
      badges: ["Đơn ngày", "Sân trường học"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 3
    },
    {
      id: 147,
      name: "Sân cầu lông Thượng Thanh",
      address: "Tổ 12 Phường Thượng Thanh, Quận Long Biên, Hà Nội",
      distance: "6.9km",
      latitude: 21.0550,
      longitude: 105.8850,
      open_time: "05:30",
      close_time: "22:30",
      open_hours: "05:30 - 22:30",
      price_range: "70.000đ - 130.000đ/giờ",
      base_price: 85000,
      is_approved: true,
      rating: 4.8,
      reviews_count: 68,
      img: "images/court3.jpg",
      club_logo: "THƯỢNG THANH",
      club_avatar_bg: "#dcfce7",
      club_avatar_color: "#16a34a",
      badges: ["Đơn ngày", "Thảm Yonex"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 3
    },
    {
      id: 148,
      name: "Sân cầu lông trường Tiểu học Ngọc Lâm",
      address: "24 Phố Hoàng Như Tiếp, Bồ Đề, Long Biên, Hà Nội",
      distance: "5.5km",
      latitude: 21.0410,
      longitude: 105.8750,
      open_time: "06:00",
      close_time: "22:00",
      open_hours: "06:00 - 22:00",
      price_range: "70.000đ - 140.000đ/giờ",
      base_price: 90000,
      is_approved: true,
      rating: 4.9,
      reviews_count: 94,
      img: "images/court4.jpg",
      club_logo: "NGỌC LÂM",
      club_avatar_bg: "#f0fdf4",
      club_avatar_color: "#15803d",
      badges: ["Đơn ngày", "Thảm VIP"],
      sport_type: "badminton",
      sport_icon: "🏸",
      courts_count: 3
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

  // 8. BẢNG matchmaking_rooms (Danh mục phòng ghép kèo AI thông minh)
  matchmaking_rooms: [
    {
      id: 701,
      room_name: "Giao lưu Đôi Nam Nữ Cân Kèo (ELO 1400 - 1550)",
      facility_id: 101,
      facility_name: "CLB Cầu Lông Catchy Badminton Arena",
      district: "Hoàng Mai, Hà Nội",
      match_date: "Hôm nay, 22/09/2026",
      match_time: "18:00 - 20:00",
      required_elo_min: 1400,
      required_elo_max: 1550,
      match_type: "Đôi Nam/Nữ",
      court_number: "Sân 03 (Thảm Enlio VIP)",
      price_per_slot: "45.000đ",
      current_players: 3,
      max_players: 4,
      status: "OPEN",
      host_name: "Lê Hoàng Quân",
      host_elo: 1460,
      ai_compatibility: 98,
      ai_prediction: "Tỉ lệ thắng dự kiến 51% - 49%. Độ cân bằng hoàn hảo, nhịp độ công thủ tốc độ cao.",
      ai_handicap: "Đồng banh (0 điểm)",
      category: "doubles",
      is_ai_recommended: true,
      players: [
        { name: "Lê Hoàng Quân", elo: 1460, avatar: "Q", role: "Host", style: "Công thủ toàn diện", team: "A" },
        { name: "Trần Thị Mai", elo: 1480, avatar: "M", role: "Member", style: "Bắt lưới & Tạt cầu", team: "A" },
        { name: "Phạm Quốc Tuấn", elo: 1430, avatar: "T", role: "Member", style: "Phòng thủ dẻo dai", team: "B" }
      ],
      chat_messages: [
        { sender: "🤖 AI Match Referee", text: "Chào mừng các tay vợt! AI đã phân tích kèo đấu: Độ cân bằng 98%, dự kiến trận đấu 3 ván kịch tính!", time: "16:30" },
        { sender: "Lê Hoàng Quân", text: "Chào mọi người, nhóm mình còn thiếu 1 tay vợt ELO quanh 1450 đánh đôi nhé!", time: "16:45" },
        { sender: "Trần Thị Mai", text: "Mình ELO 1480 vừa vào phòng rồi, đánh đôi với Quân nhé!", time: "16:50" },
        { sender: "Phạm Quốc Tuấn", text: "Mình bên đội B rồi, cần thêm 1 bạn ghép cùng quẩy nhiệt tình tối nay!", time: "17:05" }
      ]
    },
    {
      id: 702,
      room_name: "Săn Kèo Đơn Nam Thách Đấu (ELO 1700 - 1950)",
      facility_id: 103,
      facility_name: "CLB Cầu Lông Ba Đình Star Arena",
      district: "Ba Đình, Hà Nội",
      match_date: "Hôm nay, 22/09/2026",
      match_time: "19:30 - 21:30",
      required_elo_min: 1700,
      required_elo_max: 1950,
      match_type: "Đơn Nam",
      court_number: "Sân 01 (Thảm Yonex Tour)",
      price_per_slot: "90.000đ",
      current_players: 1,
      max_players: 2,
      status: "OPEN",
      host_name: "Hoàng Văn Nam",
      host_elo: 1780,
      ai_compatibility: 68,
      ai_prediction: "Kèo thách đấu hạng A. Host có smash tốc độ 320km/h. Cần thể lực bền bỉ và di chuyển nhanh.",
      ai_handicap: "AI Handicap: Chấp 4 điểm/set",
      category: "singles",
      is_ai_recommended: false,
      players: [
        { name: "Hoàng Văn Nam", elo: 1780, avatar: "N", role: "Host", style: "Tấn công dồn dập & Smash uy lực", team: "A" }
      ],
      chat_messages: [
        { sender: "🤖 AI Match Referee", text: "Hệ thống AI Handicap đã kích hoạt: Đối thủ có thể nhận chấp từ 3-5 điểm nếu ELO chênh lệch.", time: "15:00" },
        { sender: "Hoàng Văn Nam", text: "Cần tìm đối thủ cọ xát giao lưu đơn nam tối nay, có chấp điểm thoải mái nhé!", time: "15:10" }
      ]
    },
    {
      id: 703,
      room_name: "Kèo Đôi Nam Tốc Độ Cao & Phản Tạt (ELO 1420 - 1580)",
      facility_id: 105,
      facility_name: "CLB Cầu Lông Cầu Giấy Pro Center",
      district: "Cầu Giấy, Hà Nội",
      match_date: "Hôm nay, 22/09/2026",
      match_time: "20:00 - 22:00",
      required_elo_min: 1420,
      required_elo_max: 1580,
      match_type: "Đôi Nam",
      court_number: "Sân 05 (Thảm Victor Quốc Tế)",
      price_per_slot: "50.000đ",
      current_players: 2,
      max_players: 4,
      status: "OPEN",
      host_name: "Đỗ Minh Đức",
      host_elo: 1490,
      ai_compatibility: 96,
      ai_prediction: "Độ tương thích ELO 96%. Đấu pháp phối hợp phản tạt nhanh và kiểm soát cầu giữa sân.",
      ai_handicap: "Đồng banh (0 điểm)",
      category: "doubles",
      is_ai_recommended: true,
      players: [
        { name: "Đỗ Minh Đức", elo: 1490, avatar: "Đ", role: "Host", style: "Đập cầu uy lực", team: "A" },
        { name: "Ngô Quốc Khánh", elo: 1440, avatar: "K", role: "Member", style: "Điều cầu góc xa", team: "B" }
      ],
      chat_messages: [
        { sender: "Đỗ Minh Đức", text: "Kèo đánh tốc độ cao nhé anh em, chuẩn bị sẵn vợt căng 11kg!", time: "14:20" }
      ]
    },
    {
      id: 704,
      room_name: "Giao Lưu Cuối Ngày - Chia Tiền Sân Vui Vẻ (ELO 1380 - 1500)",
      facility_id: 102,
      facility_name: "CLB Cầu Lông Đống Đa Sport Hub",
      district: "Đống Đa, Hà Nội",
      match_date: "Hôm nay, 22/09/2026",
      match_time: "21:00 - 23:00",
      required_elo_min: 1380,
      required_elo_max: 1500,
      match_type: "Đôi Nam/Nữ",
      court_number: "Sân 02 (Thảm Xanh Lá)",
      price_per_slot: "40.000đ",
      current_players: 3,
      max_players: 4,
      status: "OPEN",
      host_name: "Bùi Đình Trọng",
      host_elo: 1420,
      ai_compatibility: 99,
      ai_prediction: "Khớp ELO 99% với bạn (1450). Trận đấu giao lưu cực kỳ vui vẻ, chia sẻ tiền sân tự động.",
      ai_handicap: "Đồng banh (0 điểm)",
      category: "doubles",
      is_ai_recommended: true,
      players: [
        { name: "Bùi Đình Trọng", elo: 1420, avatar: "T", role: "Host", style: "Bền bỉ thể lực", team: "A" },
        { name: "Vũ Hải Yến", elo: 1410, avatar: "Y", role: "Member", style: "Khống chế lưới", team: "A" },
        { name: "Lê Minh Tuấn", elo: 1470, avatar: "T", role: "Member", style: "Công thủ linh hoạt", team: "B" }
      ],
      chat_messages: [
        { sender: "Bùi Đình Trọng", text: "Anh em vào giao lưu dưỡng sinh giải tỏa căng thẳng sau giờ làm nào!", time: "17:15" },
        { sender: "Vũ Hải Yến", text: "Mình có mang theo nước bù khoáng cho cả sân nha!", time: "17:20" }
      ]
    },
    {
      id: 705,
      room_name: "Kèo Giao Hữu AI Chấp Điểm (ELO Lệch 200+)",
      facility_id: 104,
      facility_name: "CLB Cầu Lông Thanh Xuân Sport Arena",
      district: "Thanh Xuân, Hà Nội",
      match_date: "Ngày mai, 23/09/2026",
      match_time: "17:30 - 19:30",
      required_elo_min: 1300,
      required_elo_max: 1700,
      match_type: "Đơn Nam",
      court_number: "Sân 04 (Thảm Enlio)",
      price_per_slot: "60.000đ",
      current_players: 1,
      max_players: 2,
      status: "OPEN",
      host_name: "Phan Anh Vũ",
      host_elo: 1660,
      ai_compatibility: 85,
      ai_prediction: "Hệ thống AI tự động cân bằng: Người chơi ELO thấp hơn được cộng +3.5 điểm mỗi ván đấu.",
      ai_handicap: "AI Handicap: Chấp +3.5 điểm/set",
      category: "handicap",
      is_ai_recommended: true,
      players: [
        { name: "Phan Anh Vũ", elo: 1660, avatar: "V", role: "Host", style: "Chiến thuật & Kỹ thuật", team: "A" }
      ],
      chat_messages: [
        { sender: "Phan Anh Vũ", text: "Kèo chấp điểm AI tính toán rất công bằng, hoan nghênh anh em ELO 1300-1500 giao lưu học hỏi!", time: "13:00" }
      ]
    },
    {
      id: 706,
      room_name: "Kèo Đôi Nam Nữ Rèn Thể Lực & Phản Xạ (ELO 1400 - 1520)",
      facility_id: 106,
      facility_name: "CLB Cầu Lông Nam Từ Liêm Smash Center",
      district: "Nam Từ Liêm, Hà Nội",
      match_date: "Hôm nay, 22/09/2026",
      match_time: "19:00 - 21:00",
      required_elo_min: 1400,
      required_elo_max: 1520,
      match_type: "Đôi Nam/Nữ",
      court_number: "Sân 06 (Thảm Đỏ Thi Đấu)",
      price_per_slot: "45.000đ",
      current_players: 2,
      max_players: 4,
      status: "OPEN",
      host_name: "Nguyễn Thành Long",
      host_elo: 1445,
      ai_compatibility: 97,
      ai_prediction: "Độ khớp 97%. Nhịp độ trận đấu đều đặn, thích hợp tăng cường cảm giác cầu.",
      ai_handicap: "Đồng banh (0 điểm)",
      category: "doubles",
      is_ai_recommended: true,
      players: [
        { name: "Nguyễn Thành Long", elo: 1445, avatar: "L", role: "Host", style: "Điều cầu", team: "A" },
        { name: "Trịnh Diệu Linh", elo: 1430, avatar: "D", role: "Member", style: "Tạt lưới", team: "B" }
      ],
      chat_messages: [
        { sender: "Nguyễn Thành Long", text: "Phòng đang có 2 bạn rồi, cần thêm 1 cặp nữa là đủ 4 người!", time: "16:00" }
      ]
    },
    {
      id: 707,
      room_name: "Tập Luyện & Sửa Động Tác Cơ Bản (ELO 1100 - 1350)",
      facility_id: 107,
      facility_name: "CLB Cầu Lông Tây Hồ View Arena",
      district: "Tây Hồ, Hà Nội",
      match_date: "Ngày mai, 23/09/2026",
      match_time: "06:00 - 08:00",
      required_elo_min: 1100,
      required_elo_max: 1350,
      match_type: "Giao Lưu Tự Do",
      court_number: "Sân 02 (Thảm Xám)",
      price_per_slot: "35.000đ",
      current_players: 3,
      max_players: 4,
      status: "OPEN",
      host_name: "Hoàng Thu Trang",
      host_elo: 1280,
      ai_compatibility: 74,
      ai_prediction: "Trình độ nhập môn & cơ bản. Phù hợp khởi động ngày mới nhẹ nhàng.",
      ai_handicap: "AI Handicap: Hướng dẫn kỹ thuật",
      category: "handicap",
      is_ai_recommended: false,
      players: [
        { name: "Hoàng Thu Trang", elo: 1280, avatar: "T", role: "Host", style: "Tân thủ", team: "A" },
        { name: "Phạm Hải Đăng", elo: 1250, avatar: "Đ", role: "Member", style: "Cơ bản", team: "A" },
        { name: "Nguyễn Mai Anh", elo: 1300, avatar: "A", role: "Member", style: "Tập luyện", team: "B" }
      ],
      chat_messages: [
        { sender: "Hoàng Thu Trang", text: "Chào cả nhà, sáng mai đánh nhẹ nhàng 6h sáng tại Tây Hồ nhé!", time: "18:00" }
      ]
    },
    {
      id: 708,
      room_name: "Đại Chiến Bán Chuyên - Đơn Nam Hạng A (ELO 1800 - 2100)",
      facility_id: 108,
      facility_name: "CLB Cầu Lông Hà Đông Master Club",
      district: "Hà Đông, Hà Nội",
      match_date: "Hôm nay, 22/09/2026",
      match_time: "20:30 - 22:30",
      required_elo_min: 1800,
      required_elo_max: 2100,
      match_type: "Đơn Nam",
      court_number: "Sân VIP 01 (Thảm Yonex Pro)",
      price_per_slot: "100.000đ",
      current_players: 1,
      max_players: 2,
      status: "OPEN",
      host_name: "Vũ Quang Huy",
      host_elo: 1920,
      ai_compatibility: 55,
      ai_prediction: "Đấu thủ bán chuyên quốc gia. Tốc độ di chuyển cực nhanh, đập cầu cắm sân.",
      ai_handicap: "AI Handicap: Chấp 6 điểm/set",
      category: "singles",
      is_ai_recommended: false,
      players: [
        { name: "Vũ Quang Huy", elo: 1920, avatar: "H", role: "Host", style: "Bán chuyên đỉnh cao", team: "A" }
      ],
      chat_messages: [
        { sender: "Vũ Quang Huy", text: "Tìm đối thủ solo đơn nam cọ xát trình độ cao tối nay!", time: "16:20" }
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
  ]
};

// Luu va Tai du lieu tu dong vao LocalStorage & May chu Backend tap trung (Central Server)
const CENTRAL_API_URL = "/api/database";

function loadMockDataFromLocalStorage() {
  try {
    const savedData = localStorage.getItem('badminton_mock_data');
    if (savedData) {
      const parsed = JSON.parse(savedData);
      applyDataToMockData(parsed);
    }
  } catch (e) {
    console.warn('Could not load mock data from localStorage:', e);
  }
}

function applyDataToMockData(sourceData) {
  if (!sourceData) return;
  const keys = ['courts', 'time_slots', 'equipments', 'booking_orders', 'invoices', 'occupancy_heatmap', 'bookings', 'orders'];
  keys.forEach(k => {
    if (sourceData[k] && Array.isArray(sourceData[k])) {
      MockData[k] = sourceData[k];
    }
  });

  if (sourceData.matchmaking_rooms && Array.isArray(sourceData.matchmaking_rooms)) {
    MockData.matchmaking_rooms = sourceData.matchmaking_rooms;
  }

  // 1. Cap nhat danh sach co so san (facilities)
  if (sourceData.facilities && Array.isArray(sourceData.facilities)) {
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
    const keys = ['users', 'facilities', 'courts', 'time_slots', 'equipments', 'booking_orders', 'invoices', 'matchmaking_rooms', 'occupancy_heatmap', 'bookings', 'orders'];
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
          if (hasChanges || window.app.currentView === 'ui-20' || window.app.currentView === 'ui-19' || window.app.currentView === 'ui-02') {
            if (window.app.renderAdminUsers) window.app.renderAdminUsers();
            if (window.app.renderDatabaseInspector) window.app.renderDatabaseInspector();
            if (window.app.renderAdminOverviewFacilities) window.app.renderAdminOverviewFacilities();
            if (window.app.renderCustomerFacilities) window.app.renderCustomerFacilities();
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



