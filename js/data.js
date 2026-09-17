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
    { id: 5, name: "Admin Quản Trị", phone: "0999888777", password: "admin123", role: "ADMIN", avatar: "A", is_approved: true }
  ],

  // 2. BẢNG facilities (Danh sách cụm cơ sở sân thể thao, cầu lông & pickleball)
  facilities: [
    {
      id: 101,
      name: "Catchy Pickleball Club (Sân có mái che)",
      address: "Đối diện ngõ 136 phố Tân Khai, quận Hoàng Mai, Hà Nội",
      distance: "6.7km",
      latitude: 21.0333,
      longitude: 105.7994,
      open_time: "05:00",
      close_time: "24:00",
      open_hours: "05:00 - 24:00",
      is_approved: true,
      rating: 4.6,
      reviews_count: 128,
      img: "images/court1.jpg",
      club_logo: "CAT CHY",
      club_avatar_bg: "#fef3c7",
      club_avatar_color: "#d97706",
      badges: ["Đơn ngày", "Sự kiện"],
      courts_count: 8
    },
    {
      id: 102,
      name: "Family Pickleball Club",
      address: "Số 6/215 P Lê Lai, Máy Chai, Ngô Quyền, Hải Phòng",
      distance: "92.1km",
      latitude: 21.0338,
      longitude: 105.8525,
      open_time: "06:00",
      close_time: "22:00",
      open_hours: "06:00 - 22:00",
      is_approved: true,
      rating: 4.8,
      reviews_count: 95,
      img: "images/court2.jpg",
      club_logo: "FAMILY",
      club_avatar_bg: "#0f172a",
      club_avatar_color: "#38bdf8",
      badges: ["Đơn ngày", "Sự kiện"],
      courts_count: 6
    },
    {
      id: 103,
      name: "Hường Đỗ Central-418 Bà Triệu",
      address: "Đ. Bà Triệu/418 Phường Hạc Thành, tỉnh Thanh Hóa",
      distance: "135.6km",
      latitude: 21.0252,
      longitude: 105.8561,
      open_time: "05:00",
      close_time: "22:00",
      open_hours: "05:00 - 22:00",
      is_approved: true,
      rating: 5.0,
      reviews_count: 64,
      img: "images/court3.jpg",
      club_logo: "HƯỜNG ĐỖ",
      club_avatar_bg: "#ecfccb",
      club_avatar_color: "#65a30d",
      badges: ["Đơn ngày", "Sự kiện"],
      courts_count: 4
    },
    {
      id: 104,
      name: "Đống Đa Sport Hub Badminton Arena",
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
      courts_count: 10
    },
    {
      id: 105,
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
      club_avatar_bg: "#fdf2f8",
      club_avatar_color: "#db2777",
      badges: ["Đơn ngày", "Sự kiện"],
      courts_count: 8
    },
    {
      id: 106,
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
      club_avatar_bg: "#eff6ff",
      club_avatar_color: "#2563eb",
      badges: ["Đơn ngày", "Sự kiện"],
      courts_count: 12
    },
    {
      id: 107,
      name: "Nhà Thi Đấu Cầu Lông Bách Khoa Yonex Pro",
      address: "219 Phố Lê Thanh Nghị, Phường Bách Khoa, Quận Hai Bà Trưng, Hà Nội",
      latitude: 21.0028,
      longitude: 105.8475,
      open_time: "06:00",
      close_time: "22:30",
      is_approved: true,
      rating: 4.9,
      reviews_count: 175,
      img: "images/court7.jpg",
      courts_count: 10
    },
    {
      id: 108,
      name: "Thanh Xuân Sport Center & Fuji Badminton Club",
      address: "159 Lê Văn Lương, Phường Nhân Chính, Quận Thanh Xuân, Hà Nội",
      latitude: 21.0062,
      longitude: 105.8085,
      open_time: "05:30",
      close_time: "23:00",
      is_approved: true,
      rating: 4.9,
      reviews_count: 210,
      img: "images/court8.jpg",
      courts_count: 14
    },
    {
      id: 109,
      name: "CLB Cầu Lông Tây Hồ Arena - Quảng An",
      address: "48 Đặng Thai Mai, Phường Quảng An, Quận Tây Hồ, Hà Nội",
      latitude: 21.0645,
      longitude: 105.8241,
      open_time: "06:00",
      close_time: "22:30",
      is_approved: true,
      rating: 4.7,
      reviews_count: 92,
      img: "images/court9.jpg",
      courts_count: 8
    },
    {
      id: 110,
      name: "Hà Đông Cyber Badminton Club - Văn Quán",
      address: "215 Trần Phú, Phường Văn Quán, Quận Hà Đông, Hà Nội",
      latitude: 20.9812,
      longitude: 105.7891,
      open_time: "05:00",
      close_time: "23:30",
      is_approved: true,
      rating: 4.9,
      reviews_count: 185,
      img: "images/court10.jpg",
      courts_count: 12
    },
    {
      id: 111,
      name: "Cụm Sân Cầu Lông Đông Anh Sport Center",
      address: "55 Đường Cao Lỗ, Xã Đông Anh, Hà Nội",
      latitude: 21.1412,
      longitude: 105.8451,
      open_time: "06:00",
      close_time: "22:30",
      is_approved: false,
      rating: 4.8,
      reviews_count: 15,
      img: "images/court1.jpg",
      courts_count: 6
    },
    {
      id: 112,
      name: "CLB Cầu Lông Gia Lâm Yonex Club",
      address: "340 Đường Nguyễn Đức Thuận, Xã Gia Lâm, Hà Nội",
      latitude: 21.0454,
      longitude: 105.9125,
      open_time: "05:30",
      close_time: "23:00",
      is_approved: false,
      rating: 4.7,
      reviews_count: 10,
      img: "images/court3.jpg",
      courts_count: 8
    },
    {
      id: 113,
      name: "Sân Cầu Lông Thanh Trì Cyber Arena",
      address: "120 Đường Ngọc Hồi, Xã Thanh Trì, Hà Nội",
      latitude: 20.9521,
      longitude: 105.8412,
      open_time: "06:00",
      close_time: "23:00",
      is_approved: false,
      rating: 4.9,
      reviews_count: 22,
      img: "images/court5.jpg",
      courts_count: 10
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
      facility_name: "Sân Cầu Lông AI Badminton Arena",
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
      facility_name: "Sân Cầu Lông AI Badminton Arena",
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
      facility_name: "Sân Cầu Lông Sài Gòn Star",
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
      facility_name: "Pro Badminton Center",
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
      facility_name: "Phú Nhuận Sport Center",
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
      facility_name: "Smashing Arena",
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

  // 8. BẢNG matchmaking_rooms
  matchmaking_rooms: [
    {
      id: 701,
      room_name: "Giao lưu Trình độ Khá (ELO 1400 - 1600)",
      facility_name: "Smashing Arena (Quận Thủ Đức)",
      match_date: "12/09/2026",
      match_time: "18:00 - 20:00",
      required_elo_min: 1400,
      required_elo_max: 1600,
      match_type: "Đôi Nam/Nữ",
      current_players: 3,
      max_players: 4,
      status: "OPEN",
      host_name: "Nguyễn Văn Hùng",
      host_elo: 1450,
      chat_messages: [
        { sender: "Nguyễn Văn Hùng", text: "Chào mọi người, nhóm mình còn thiếu 1 tay vợt ELO 1450+ đánh đôi nhé!", time: "16:45" },
        { sender: "Trần Thị Mai", text: "Mình ELO 1680 vừa tham gia rồi nha!", time: "16:50" }
      ]
    },
    {
      id: 702,
      room_name: "Săn Kèo Đơn Nam ELO Cao (1700+)",
      facility_name: "Pro Badminton Center (Quận 1)",
      match_date: "12/09/2026",
      match_time: "19:00 - 21:00",
      required_elo_min: 1700,
      required_elo_max: 2000,
      match_type: "Đơn Nam",
      current_players: 1,
      max_players: 2,
      status: "OPEN",
      host_name: "Hoàng Văn Nam",
      host_elo: 1780,
      chat_messages: [
        { sender: "Hoàng Văn Nam", text: "Cần tìm đối thủ cọ xát giao lưu đơn nam tối mai!", time: "15:10" }
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

// Luu va Tai du lieu tu dong vao LocalStorage de khong bi mat du lieu khi F5 / Reload
function loadMockDataFromLocalStorage() {
  try {
    const savedData = localStorage.getItem('badminton_mock_data');
    if (savedData) {
      const parsed = JSON.parse(savedData);
      if (parsed.users && Array.isArray(parsed.users) && parsed.users.length > 0) MockData.users = parsed.users;
      if (parsed.facilities && Array.isArray(parsed.facilities) && parsed.facilities.length > 0) MockData.facilities = parsed.facilities;
      if (parsed.bookings && Array.isArray(parsed.bookings)) MockData.bookings = parsed.bookings;
      if (parsed.orders && Array.isArray(parsed.orders)) MockData.orders = parsed.orders;
    }
  } catch (e) {
    console.warn('Could not load mock data from localStorage:', e);
  }
}

function saveMockDataToLocalStorage() {
  try {
    localStorage.setItem('badminton_mock_data', JSON.stringify({
      users: MockData.users,
      facilities: MockData.facilities,
      bookings: MockData.bookings,
      orders: MockData.orders
    }));
  } catch (e) {
    console.warn('Could not save mock data to localStorage:', e);
  }
}

// Khoi tao load du lieu ngay khi nap file data.js
loadMockDataFromLocalStorage();

