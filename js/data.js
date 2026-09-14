/* ==========================================================================
   BADMINTON AI MANAGEMENT SYSTEM - MOCK DATA (9 DATABASE TABLES)
   ========================================================================== */

const MockData = {
  // 1. BẢNG users
  users: [
    { id: 1, name: "Nguyễn Văn Hùng", phone: "0901234567", role: "CUSTOMER", elo_rating: 1450, avatar: "H", is_approved: true },
    { id: 2, name: "Trần Thị Mai", phone: "0912345678", role: "CUSTOMER", elo_rating: 1680, avatar: "M", is_approved: true },
    { id: 3, name: "Lê Hoàng Nam (Chủ Sân)", phone: "0912345678", role: "OWNER", facility_id: 101, avatar: "N", is_approved: true },
    { id: 4, name: "Phạm Quốc Tuấn (Thu Ngân)", phone: "0922334455", role: "STAFF", facility_id: 101, avatar: "T", is_approved: true },
    { id: 5, name: "Admin Quản Trị", phone: "0999888777", role: "ADMIN", avatar: "A", is_approved: true }
  ],

  // 2. BẢNG facilities (Danh sách cụm cơ sở sân cầu lông tại TP.HCM)
  facilities: [
    {
      id: 101,
      name: "Sân Cầu Lông AI Badminton Arena",
      address: "123 Đường Lê Văn Việt, Tăng Nhơn Phú A, TP. Thủ Đức, TP.HCM",
      latitude: 10.8456,
      longitude: 106.7925,
      open_time: "06:00",
      close_time: "23:00",
      is_approved: true,
      rating: 4.9,
      reviews_count: 128,
      img: "images/court1.jpg",
      courts_count: 8
    },
    {
      id: 102,
      name: "Cụm Sân Thể Thao Pro Badminton Center",
      address: "45 Nguyễn Thị Minh Khai, Phường Bến Nghé, Quận 1, TP.HCM",
      latitude: 10.7789,
      longitude: 106.6982,
      open_time: "05:30",
      close_time: "22:30",
      is_approved: true,
      rating: 4.7,
      reviews_count: 95,
      img: "images/court2.jpg",
      courts_count: 6
    },
    {
      id: 103,
      name: "Sân Cầu Lông Sài Gòn Star",
      address: "88 Phạm Văn Đồng, Phường 13, Bình Thạnh, TP.HCM",
      latitude: 10.8123,
      longitude: 106.7011,
      open_time: "06:00",
      close_time: "22:00",
      is_approved: true,
      rating: 4.6,
      reviews_count: 64,
      img: "images/court3.jpg",
      courts_count: 4
    },
    {
      id: 104,
      name: "Tân Bình Sport Hub Badminton Arena",
      address: "102 Trường Chinh, Phường 12, Quận Tân Bình, TP.HCM",
      latitude: 10.7985,
      longitude: 106.6532,
      open_time: "05:00",
      close_time: "23:00",
      is_approved: true,
      rating: 4.9,
      reviews_count: 142,
      img: "images/court4.jpg",
      courts_count: 10
    },
    {
      id: 105,
      name: "Smash Zone Cyber Badminton D7",
      address: "15 Nguyễn Hữu Thọ, Phường Tân Hưng, Quận 7, TP.HCM",
      latitude: 10.7321,
      longitude: 106.7025,
      open_time: "06:00",
      close_time: "23:30",
      is_approved: true,
      rating: 4.8,
      reviews_count: 88,
      img: "images/court5.jpg",
      courts_count: 8
    },
    {
      id: 106,
      name: "CLB Cầu Lông Gò Vấp Star Arena",
      address: "178 Nguyễn Oanh, Phường 17, Quận Gò Vấp, TP.HCM",
      latitude: 10.8352,
      longitude: 106.6789,
      open_time: "05:30",
      close_time: "23:00",
      is_approved: true,
      rating: 4.8,
      reviews_count: 116,
      img: "images/court6.jpg",
      courts_count: 12
    },
    {
      id: 107,
      name: "Nhà Thi Đấu Cầu Lông Quận 10 Yonex Pro",
      address: "219 Lý Thường Kiệt, Phường 15, Quận 10, TP.HCM",
      latitude: 10.7723,
      longitude: 106.6588,
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
      name: "Phú Nhuận Sport Center & Fuji Badminton Club",
      address: "159 Phan Đăng Lưu, Phường 1, Quận Phú Nhuận, TP.HCM",
      latitude: 10.7998,
      longitude: 106.6821,
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
      name: "CLB Cầu Lông Bình Thạnh Arena - Thanh Đa",
      address: "48 Bình Quới, Phường 27, Quận Bình Thạnh, TP.HCM",
      latitude: 10.8211,
      longitude: 106.7155,
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
      name: "Thủ Đức Cyber Badminton Club - Võ Văn Ngân",
      address: "215 Võ Văn Ngân, Phường Bình Thọ, TP. Thủ Đức, TP.HCM",
      latitude: 10.8512,
      longitude: 106.7711,
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
      name: "Cụm Sân Cầu Lông Tân Phú Sport Center",
      address: "55 Lê Trọng Tấn, Phường Sơn Kỳ, Quận Tân Phú, TP.HCM",
      latitude: 10.8012,
      longitude: 106.6211,
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
      name: "CLB Cầu Lông Quận 12 Yonex Club",
      address: "340 Hà Huy Giáp, Phường Thạnh Lộc, Quận 12, TP.HCM",
      latitude: 10.8654,
      longitude: 106.6812,
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
      name: "Sân Cầu Lông Bình Tân Cyber Arena",
      address: "120 Đường Tên Lửa, Phường Bình Trị Đông B, Quận Bình Tân, TP.HCM",
      latitude: 10.7456,
      longitude: 106.6089,
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
