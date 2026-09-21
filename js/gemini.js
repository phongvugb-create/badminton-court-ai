// Tự động dọn dẹp key hỏng hoặc placeholder cũ trong localStorage
try {
  if (typeof localStorage !== 'undefined') {
    const rawKey = localStorage.getItem('gemini_api_key');
    if (rawKey && (!rawKey.startsWith('AIzaSy') || rawKey.length < 35)) {
      localStorage.removeItem('gemini_api_key');
    }
  }
} catch (e) {}

class GeminiAIAssistant {
  constructor() {
    // Configured Google Gemini API Key
    let stored = '';
    try {
      stored = localStorage.getItem('gemini_api_key') || '';
    } catch (e) {}

    // Dọn dẹp key cũ không hợp lệ nếu từng lưu
    if (stored && !this.isValidKey(stored)) {
      try { localStorage.removeItem('gemini_api_key'); } catch (e) {}
      stored = '';
    }

    const windowKey = (typeof window !== 'undefined' && window.GEMINI_API_KEY) ? window.GEMINI_API_KEY : '';
    const candidate = stored || windowKey || '';
    this.apiKey = this.isValidKey(candidate) ? candidate : '';

    this.primaryModel = 'gemini-1.5-flash';
    this.fallbackModel = 'gemini-2.0-flash';

    this.systemInstruction = `
      Bạn là Smashing AI Assistant - Trợ lý Trí Tuệ Nhân Tạo chính thức của Hệ thống Quản lý & Cho Thuê Sân Cầu Lông BADMINTON.AI.

      DỮ LIỆU THỰC TẾ CHI TIẾT TỪNG CỤM SÂN TRÊN HỆ THỐNG THỦ ĐÔ HÀ NỘI (MOCKDATA.FACILITIES):
      1. Sân Cầu Lông AI Badminton Arena Cầu Giấy - 123 Đường Cầu Giấy | 8 sân | 4.9⭐
      2. CLB Cầu Lông Đống Đa Sport Hub - 102 Láng Hạ, Đống Đa | 10 sân | 4.9⭐
      3. Sân Cầu Lông Tràng Tiền Star Arena - 88 Tràng Tiền, Hoàn Kiếm | 4 sân | 4.6⭐
      4. Nhà Thi Đấu Cầu Lông Bách Khoa Yonex Pro - 219 Lê Thanh Nghị, Hai Bà Trưng | 10 sân | 4.9⭐
      5. Smash Zone Cyber Badminton Mỹ Đình - 15 Lê Đức Thọ, Nam Từ Liêm | 8 sân | 4.8⭐
      6. CLB Cầu Lông Ba Đình Star Arena - 178 Điện Biên Phủ, Ba Đình | 12 sân | 4.8⭐
      7. Thanh Xuân Sport Center & Fuji Club - 159 Lê Văn Lương, Thanh Xuân | 14 sân | 4.9⭐
      8. CLB Cầu Lông Tây Hồ Arena - 48 Đặng Thai Mai, Tây Hồ | 8 sân | 4.7⭐
      9. Hà Đông Cyber Badminton Club - 215 Trần Phú, Hà Đông | 12 sân | 4.9⭐
      10. Sân Cầu Lông Cầu Giấy Pro Arena - 35 Dịch Vọng Hậu, Cầu Giấy | 8 sân | 4.8⭐
      11. CLB Cầu Lông Hoàng Gia Cổ Nhuế - 18 Cổ Nhuế, Bắc Từ Liêm | 6 sân | 4.9⭐
      12. Sân Cầu Lông Quần Ngựa Liễu Giai - 30 Văn Cao, Ba Đình | 8 sân | 4.7⭐
      13. CLB Cầu Lông Định Công Arena - KĐT Định Công, Hoàng Mai | 8 sân | 4.8⭐
      14. Sân Cầu Lông Ciputra Club - KĐT Ciputra, Bắc Từ Liêm | 12 sân | 5.0⭐
      15. Sân Cầu Lông Long Biên Riverside Pro - Đường Cổ Linh, Long Biên | 10 sân | 4.8⭐
      16. Sân cầu lông Đại học Công Đoàn - 169 Tây Sơn, Đống Đa | 2 sân | Giá: 80.000đ/h
      17. Sân cầu lông Trung Kính - Ngõ 218 Trung Kính, Cầu Giấy | 3 sân | Giá: 70.000đ/h
      18. Sân cầu lông Quang Trung 178 đường Láng - 178 Đường Láng, Đống Đa | 3 sân | Giá: 50.000 - 80.000đ/h
      19. Sân cầu lông 105 Láng Hạ - 105 Láng Hạ, Đống Đa | 1 sân | Giá: 90.000đ/h
      20. Sân cầu lông Ban Cơ Yếu Chính Phủ - 105 Nguyễn Chí Thanh, Đống Đa | 2 sân | Giá: 90.000đ/h
      21. Sân cầu lông Học Viện Ngân Hàng – Ambition - 12 Chùa Bộc, Đống Đa | 3 sân | Giá: 80.000 - 100.000đ/h
      22. Sân cầu lông Ngoại Thương - 91 Chùa Láng, Đống Đa | 3 sân | Giá: 90.000đ/h
      23. Sân cầu lông Fleet - Ngõ 1194 Đường Láng, Đống Đa | 1 sân | Giá: 100.000đ/h
      24. Sân cầu lông Bộ Công An - 47 Phạm Văn Đồng, Cầu Giấy | 5 sân | Giá: 80.000 - 110.000đ/h
      25. Sân cầu lông Bệnh Viện Phụ Sản Hà Nội - 929 La Thành, Ba Đình | 3 sân | Giá: 50.000 - 80.000đ/h
      26. Sân cầu lông Đại học Thủy Lợi - 175 Tây Sơn, Đống Đa | 4 sân | Giá: 50.000đ/h
      27. Sân cầu lông Đại học Xây Dựng - 55 Giải Phóng, Hai Bà Trưng | 4 sân | Giá: 90.000đ/h
      28. Sân cầu lông Đường Sông & Đường Sông 2 - Cảng Hà Nội / Lương Yên, Hai Bà Trưng | 2-4 sân | Giá: 50.000 - 90.000đ/h
      29. Sân cầu lông Hồng Hà - Phố Hồng Hà, Hoàn Kiếm | 4 sân | Giá: 50.000 - 90.000đ/h
      30. Trung Tâm TDTT Sân Cầu Lông 521 Minh Khai - 521 Minh Khai, Hai Bà Trưng | 7 sân | Giá: 40.000 - 80.000đ/h
      31. Sân cầu lông Pháo đài Láng - Ngõ 102 Pháo Đài Láng, Đống Đa | 3 sân | Giá: 50.000 - 80.000đ/h
      32. Sân cầu lông trường THPT Lý Thái Tổ - 165 Hoàng Ngân, Cầu Giấy | 3 sân | Giá: 50.000 - 80.000đ/h
      33. Sân cầu lông 266 phố Vũ Hữu - 266 Vũ Hữu, Thanh Xuân / Nam Từ Liêm | 3 sân | Giá: 50.000 - 80.000đ/h
      34. Sân CLB Cầu Lông TCSP Mẫu giáo - 387 Hoàng Quốc Việt, Cầu Giấy | 3 sân | Giá: 50.000 - 80.000đ/h
      35. Sân cầu lông 134 Quan Nhân - 134 Quan Nhân, Thanh Xuân | 3 sân | Giá: 50.000 - 80.000đ/h
      36. Sân cầu lông Hà Đông - Phố Tô Hiệu, Hà Đông | 3 sân | Giá: 80.000 - 120.000đ/h
      37. Sân cầu lông La Khê – Hà Đông - KĐT Văn Khê, Hà Đông | 3 sân | Giá: 70.000 - 130.000đ/h
      38. Sân cầu lông Nhà thi đấu Hà Đông - 182 Quang Trung, Hà Đông | 4 sân | Giá: 70.000 - 130.000đ/h
      39. Sân cầu lông trường THCS Lê Quý Đôn - KĐT Dương Nội, Hà Đông | 3 sân | Giá: 80.000 - 130.000đ/h
      40. Sân cầu lông trường Chuyên Nguyễn Huệ – Hà Đông - 560 Quang Trung, Hà Đông | 3 sân | Giá: 70.000 - 120.000đ/h
      41. Sân cầu lông trường Tiểu học Nguyễn Quý Đức - Đại Mỗ, Nam Từ Liêm | 1 sân | Giá: 80.000 - 130.000đ/h
      42. Sân cầu lông Việt Hưng - KĐT Việt Hưng, Long Biên | 3 sân | Giá: 70.000 - 130.000đ/h
      43. Sân Trung tâm quản lý bay - Nguyễn Sơn, Long Biên | 2 sân | Giá: 70.000 - 120.000đ/h
      44. Sân cầu lông Trường Hải - 1 Ngô Gia Tự, Long Biên | 2 sân | Giá: 50.000 - 80.000đ/h
      45. Sân cầu lông Đoàn Kết – Thạch Bàn - Thạch Bàn, Long Biên | 3 sân | Giá: 70.000 - 130.000đ/h
      46. Sân cầu lông trường Tiểu học Đoàn Khuê – Long Biên - KĐT Việt Hưng, Long Biên | 3 sân | Giá: 70.000 - 110.000đ/h
      47. Sân cầu lông Thượng Thanh - Thượng Thanh, Long Biên | 3 sân | Giá: 70.000 - 130.000đ/h
      48. Sân cầu lông trường Tiểu học Ngọc Lâm - 24 Hoàng Như Tiếp, Long Biên | 3 sân | Giá: 70.000 - 140.000đ/h

      BẢNG GIÁ THUÊ SÂN:
      - Khung giờ bình thường (05:00 sáng - 17:00 chiều): 120.000đ/giờ.
      - Khung giờ cao điểm (18:00 tối - 22:00 đêm): 160.000đ/giờ (áp dụng AI Dynamic Pricing).

      DANH MỤC VỢT CHO THUÊ VÀ PHỤ KIỆN TẠI QUẦY:
      1. Vợt Yonex Astrox 88D Pro (35.000đ/cây/giờ) - 🔥 Nặng đầu, chuyên công đập cầu bộc phát uy lực.
      2. Vợt Yonex Nanoflare 800 Pro (35.000đ/cây/giờ) - ⚡ Tốc độ, phản tạt nhanh & điều cầu linh hoạt trên lưới.
      3. Vợt Yonex Arcsaber 11 Pro (35.000đ/cây/giờ) - 🎯 Công thủ toàn diện, kiểm soát điểm rơi chính xác.
      4. Vợt Victor Thruster Ryuga II (40.000đ/cây/giờ) - 💥 Siêu tấn công uy lực, smash cắm sân.
      5. Vợt Li-Ning Axforce 90 Max (40.000đ/cây/giờ) - 🚀 Tấn công đỉnh cao bộc phát cực mạnh.
      6. Vợt Kumpoo Power Control K520 Pro (20.000đ/cây/giờ) - 🌱 Trợ lực tốt, dễ chơi (người mới).
      - Hộp Cầu Lông Thành Công 12 quả: 300.000đ/hộp.
      - Nước khoáng Pocari Sweat 500ml: 10.000đ/chai | Khăn lau mồ hôi: 10.000đ/cái.

      QUY TẮC PHẢN HỒI THÔNG MINH (GEMINI AI ASSISTANT):
      1. THÂN THIỆN, LINH HOẠT & THÔNG MINH NHƯ MỘT TRỢ LÝ THỰC THỤ: Bạn có thể chào hỏi, trò chuyện tự nhiên, giải đáp mọi thắc mắc của người dùng (từ kỹ thuật chơi, chọn vợt, chiến thuật cầu lông, sức khỏe, thể thao nói chung đến các câu hỏi giao tiếp đời sống thông thường).
      2. ĐỐI VỚI HỆ THỐNG SÂN: Bạn nắm rõ toàn bộ hệ thống 48+ cụm sân cầu lông tại Hà Nội của BADMINTON.AI, bảng giá (120k/h thường, 160k/h giờ cao điểm 18-22h), chính sách AI Dynamic Pricing, cách tính điểm ELO và các loại vợt cho thuê.
      3. ĐỐI VỚI CÂU HỎI CHUNG / NGOÀI CẦU LÔNG: Trả lời nhiệt tình, thông minh, lịch sự và hữu ích như một trợ lý AI chuẩn Google Gemini; không từ chối thô cứng, có thể khéo léo gắn kết nhẹ nhàng với tinh thần thể thao thể lực nếu phù hợp.
      4. ĐỊNH DẠNG: Trình bày rõ ràng, dùng bullet points, emoji sinh động và Markdown **in đậm** (không dùng cú pháp LaTeX).
    `;
  }

  isValidKey(key) {
    return typeof key === 'string' && key.trim().startsWith('AIzaSy') && key.trim().length >= 35;
  }

  getAPIKey() {
    return this.isValidKey(this.apiKey) ? this.apiKey : '';
  }

  setAPIKey(key) {
    const cleanKey = (key || '').trim();
    if (this.isValidKey(cleanKey)) {
      this.apiKey = cleanKey;
      localStorage.setItem('gemini_api_key', this.apiKey);
      return true;
    } else {
      this.apiKey = '';
      localStorage.removeItem('gemini_api_key');
      return false;
    }
  }

  isOtherProvinceQuery(prompt) {
    const p = prompt.toLowerCase();
    
    // Nếu trong câu có nhắc đến Hà Nội / HN thì là địa bàn chính
    if (p.includes('hà nội') || p.includes('ha noi') || p.includes('hanoi') || p.includes('thủ đô')) {
      return false;
    }

    const otherLocations = [
      'tphcm', 'tp.hcm', 'hồ chí minh', 'sài gòn', 'sai gon', 'thủ đức',
      'đà nẵng', 'da nang', 'bình dương', 'binh duong', 'đồng nai', 'dong nai',
      'vũng tàu', 'vung tau', 'bà rịa', 'cần thơ', 'can tho', 'hải phòng', 'hai phong', 'nha trang',
      'đà lạt', 'da lat', 'lâm đồng', 'quảng ninh', 'hải dương', 'bắc ninh', 'thái nguyên', 'huế',
      'nghệ an', 'vinh', 'thanh hóa', 'nam định', 'thái bình', 'phú thọ', 'quảng nam', 'quy nhơn',
      'bình định', 'phú yên', 'phan thiết', 'bình thuận', 'tây ninh', 'long an', 'tiền giang',
      'mỹ tho', 'bến tre', 'vĩnh long', 'trà vinh', 'đồng tháp', 'an giang', 'long xuyên',
      'kiên giang', 'phú quốc', 'hậu giang', 'sóc trăng', 'bạc liêu', 'cà mau', 'tỉnh khác',
      'thành phố khác', 'ở nam', 'miền nam', 'miền tây', 'sài thành'
    ];
    return otherLocations.some(loc => p.includes(loc));
  }

  isBadmintonRelated(prompt) {
    const p = prompt.toLowerCase();
    const badmintonKeywords = [
      'cầu lông', 'sân', 'vợt', 'cầu', 'smash', 'đập', 'phông', 'bỏ nhỏ', 'chặt cầu', 'cắt cầu',
      'lưới', 'dây', 'đan', 'căng', 'lbs', 'kg', 'yonex', 'lining', 'victor', 'mizuno', 'astrox',
      'arcsaber', 'duora', 'voltric', 'halbertec', 'tectonic', '88d', '99', '100zz', 'nanoflare',
      'ryuga', 'axforce', 'kumpoo', 'k520', 'elo', 'ghép', 'kèo', 'cọc', 'vnpay', 'đặt', 'cầu giấy', 'đống đa', 'ba đình', 'hai bà trưng',
      'nam từ liêm', 'bắc từ liêm', 'thanh xuân', 'tây hồ', 'hà đông', 'hoàng mai', 'long biên', 'hoàn kiếm', 'luật', 'giao cầu', 'trọng tài', 'đơn', 'đôi',
      'thể lực', 'khởi động', 'chấn thương', 'cổ tay', 'đầu gối', 'bước chân', 'dậm nhảy',
      'lee chong wei', 'lin dan', 'momota', 'axelsen', 'tiến minh', 'thùy linh', 'bwf', 'badminton',
      'bóng', 'thiết bị', 'tư vấn', 'giờ', 'giá', 'giảm giá', 'đánh', 'chơi', 'tập', 'phòng',
      'rẻ', 'rẻ nhất', 'mấy sân', 'nhiều nhất', 'chi nhánh', 'địa chỉ', 'hệ thống', 'bao nhiêu',
      'pocari', 'nước', 'khăn', 'thành công'
    ];
    return badmintonKeywords.some(keyword => p.includes(keyword));
  }

  async generateResponse(userPrompt) {
    try {
      const currentKey = this.getAPIKey();

      // CHẾ ĐỘ 1: SIÊU TỐC NỘI BỘ (Chưa có key hoặc key chưa kích hoạt)
      // Trả lời lập tức với tri thức nghiệp vụ cầu lông chuẩn xác, phản hồi cực nhanh ~50ms
      if (!currentKey) {
        await new Promise(r => setTimeout(r, 50));
        return this.getFallbackResponse(userPrompt);
      }

      // CHẾ ĐỘ 2: GOOGLE GEMINI 1.5 FLASH TRỰC TUYẾN (Khi có API Key cá nhân hợp lệ)
      const requestBody = {
        contents: [
          {
            role: 'user',
            parts: [{ text: `${this.systemInstruction}\n\nKhách hỏi: ${userPrompt}` }]
          }
        ],
        generationConfig: {
          maxOutputTokens: 800,
          temperature: 0.4
        }
      };

      const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/${this.primaryModel}:generateContent?key=${currentKey}`;
      try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 2500); // 2.5s tối đa

        const response = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(requestBody),
          signal: controller.signal
        });
        clearTimeout(timer);

        if (response.ok) {
          const data = await response.json();
          let reply = data.candidates?.[0]?.content?.parts?.[0]?.text;
          if (reply) {
            return this.cleanReplyText(reply);
          }
        }
      } catch (e) {
        console.warn(`Gemini online timeout hoặc không thể kết nối (${e.message}), chuyển ngay sang AI nội bộ siêu tốc.`);
      }

      return this.getFallbackResponse(userPrompt);
    } catch (globalErr) {
      console.error("Lỗi generateResponse:", globalErr);
      return this.getFallbackResponse(userPrompt);
    }
  }

  cleanReplyText(text) {
    return text
      .replace(/\$\s*\\?([><=]=?)\s*(\d+)\\text\{\s*(\w+)\}\s*\$/g, '$1 $2 $3')
      .replace(/\$([^\$]+)\$/g, (match, p1) => p1.replace(/\\text\{([^\}]+)\}/g, '$1').replace(/\\/g, '').trim())
      .replace(/^###\s*(.*$)/gim, '🎯 **$1**')
      .replace(/^##\s*(.*$)/gim, '📌 **$1**')
      .replace(/^#\s*(.*$)/gim, '🏸 **$1**');
  }

  getFallbackResponse(prompt) {
    const p = prompt.toLowerCase().trim();

    // Phản hồi thân thiện cho câu chào
    if (p === 'xin chào' || p === 'chào' || p === 'hello' || p === 'hi' || p.startsWith('chào bạn') || p.startsWith('xin chào')) {
      return "👋 Xin chào bạn! Rất vui được hỗ trợ bạn hôm nay. Tôi là **Trợ lý Trí Tuệ Nhân Tạo Google Gemini AI** của hệ thống sân cầu lông BADMINTON.AI.\n\nTôi có thể giúp gì cho bạn? Bạn có thể hỏi tôi về bất kỳ thông tin nào: gợi ý sân gần bạn, hướng dẫn chọn vợt, chiến thuật thi đấu, luật chơi hay bất kỳ câu hỏi nào bạn đang thắc mắc nhé! 🏸✨";
    }

    // 0. Khớp dữ liệu sân cụ thể hoặc quận/huyện đúng trọng tâm tại Hà Nội
    if (typeof MockData !== 'undefined' && MockData.facilities) {
      const isLocationOrCourtQuery = p.includes('sân') || p.includes('địa chỉ') || p.includes('ở đâu') || p.includes('mấy giờ') || p.includes('mở cửa') || p.includes('đóng cửa') || p.includes('đánh giá') || p.includes('mấy sân') || p.includes('tọa độ') || p.includes('hà nội') || p.includes('cầu giấy') || p.includes('đống đa') || p.includes('ba đình') || p.includes('hai bà trưng') || p.includes('nam từ liêm') || p.includes('bắc từ liêm') || p.includes('thanh xuân') || p.includes('tây hồ') || p.includes('hà đông') || p.includes('hoàng mai') || p.includes('long biên') || p.includes('hoàn kiếm');

      const isEquipmentOrGeneralQuery = p.includes('vợt') || p.includes('thành công') || p.includes('pocari') || p.includes('khăn') || p.includes('elo') || p.includes('đập') || p.includes('smash');

      if (isLocationOrCourtQuery && !isEquipmentOrGeneralQuery) {
        const matched = MockData.facilities.filter(fac => {
          const nameLower = fac.name.toLowerCase();
          const addrLower = fac.address.toLowerCase();

          // Theo khu vực / Quận tại Hà Nội
          if (p.includes('cầu giấy') && (addrLower.includes('cầu giấy') || nameLower.includes('cầu giấy'))) return true;
          if (p.includes('đống đa') && (addrLower.includes('đống đa') || nameLower.includes('đống đa'))) return true;
          if (p.includes('ba đình') && (addrLower.includes('ba đình') || nameLower.includes('ba đình'))) return true;
          if ((p.includes('hai bà trưng') || p.includes('hbt')) && (addrLower.includes('hai bà trưng') || nameLower.includes('hai bà trưng'))) return true;
          if ((p.includes('nam từ liêm') || p.includes('mỹ đình')) && (addrLower.includes('nam từ liêm') || nameLower.includes('mỹ đình'))) return true;
          if (p.includes('bắc từ liêm') && (addrLower.includes('bắc từ liêm') || nameLower.includes('bắc từ liêm'))) return true;
          if (p.includes('thanh xuân') && (addrLower.includes('thanh xuân') || nameLower.includes('thanh xuân'))) return true;
          if (p.includes('tây hồ') && (addrLower.includes('tây hồ') || nameLower.includes('tây hồ'))) return true;
          if (p.includes('hà đông') && (addrLower.includes('hà đông') || nameLower.includes('hà đông'))) return true;
          if (p.includes('hoàng mai') && (addrLower.includes('hoàng mai') || nameLower.includes('hoàng mai'))) return true;
          if (p.includes('long biên') && (addrLower.includes('long biên') || nameLower.includes('long biên'))) return true;
          if (p.includes('hoàn kiếm') && (addrLower.includes('hoàn kiếm') || nameLower.includes('hoàn kiếm'))) return true;

          // Theo tên cụ thể hoặc từ khóa đặc trưng của cụm sân Hà Nội
          if (p.includes('catchy') || p.includes('tân khai')) return fac.id === 101;
          if (p.includes('sport hub') || p.includes('láng hạ')) return fac.id === 102;
          if (p.includes('mỹ đình') || p.includes('lê đức thọ')) return fac.id === 103;
          if (p.includes('ba đình star') || p.includes('điện biên phủ')) return fac.id === 104;
          if (p.includes('bách khoa') || p.includes('lê thanh nghị')) return fac.id === 105;
          if (p.includes('thanh xuân') || p.includes('lê văn lương')) return fac.id === 106;
          if (p.includes('tây hồ') || p.includes('đặng thai mai')) return fac.id === 107;
          if (p.includes('hà đông') || p.includes('trần phú') || p.includes('văn quán')) return fac.id === 108;
          if (p.includes('cầu giấy pro') || p.includes('dịch vọng hậu')) return fac.id === 109;
          if (p.includes('hoàng gia') || p.includes('cổ nhuế')) return fac.id === 110;
          if (p.includes('quần ngựa') || p.includes('văn cao') || p.includes('liễu giai')) return fac.id === 111;
          if (p.includes('định công')) return fac.id === 112;
          if (p.includes('ciputra')) return fac.id === 113;
          if (p.includes('long biên') || p.includes('cổ linh')) return fac.id === 114;

          return false;
        });

        if (matched.length > 0) {
          let reply = `🏟️ **Thông Tin Chi Tiết Cụm Sân Hà Nội Theo Yêu Cầu Của Bạn**:\n\n`;
          matched.forEach((fac, idx) => {
            reply += `${idx + 1}. **${fac.name}**\n` +
                     `📍 **Địa chỉ**: ${fac.address}\n` +
                     `⏰ **Giờ mở cửa**: ${fac.open_time} - ${fac.close_time}\n` +
                     `🏸 **Quy mô**: ${fac.courts_count} sân con thi đấu (thảm tiêu chuẩn)\n` +
                     `⭐ **Đánh giá**: ${fac.rating}/5.0 (${fac.reviews_count} đánh giá)\n` +
                     `💰 **Bảng giá thuê sân**:\n` +
                     `   - Giờ bình thường (05:00 - 17:00): **120.000đ/giờ**\n` +
                     `   - Giờ cao điểm (18:00 - 22:00): **160.000đ/giờ**\n\n`;
          });
          reply += `👉 Bạn có thể chọn cụm sân này trên giao diện chính để chọn slot giờ, giữ chỗ 10 phút và đặt cọc 50k qua VNPay!`;
          return reply;
        }
      }
    }

    // 1. Hỏi cụ thể Hộp cầu Thành Công
    if (p.includes('thành công') || p.includes('hộp cầu') || p.includes('quả cầu')) {
      return "🏸 **Hộp Cầu Lông Thành Công (12 quả)** tại hệ thống **BADMINTON.AI** có giá là **300.000đ/hộp** (chất lượng lông bền, đường bay đằm chuẩn thi đấu).";
    }

    // 2. Hỏi cụ thể Nước khoáng / Pocari
    if (p.includes('pocari') || p.includes('nước khoáng') || (p.includes('nước') && !p.includes('nước ngoài'))) {
      return "🥤 **Nước khoáng Pocari Sweat 500ml** tại quầy dịch vụ **BADMINTON.AI** có giá là **10.000đ/chai**.";
    }

    // 3. Hỏi cụ thể Khăn lau
    if (p.includes('khăn')) {
      return "🧻 **Khăn lau mồ hôi cao cấp** tại quầy dịch vụ **BADMINTON.AI** có giá là **10.000đ/cái**.";
    }

    // 4. Hỏi cụ thể Vợt / Thuê các loại vợt
    if (p.includes('vợt') || p.includes('astrox') || p.includes('yonex') || p.includes('victor') || p.includes('lining') || p.includes('kumpoo') || p.includes('loại vợt') || p.includes('thuê vợt')) {
      return "🏸 **Danh Sách Đa Dạng Các Loại Vợt Cho Thuê Tại Quầy BADMINTON.AI**:\n\n" +
        "1. 🔥 **Yonex Astrox 88D Pro** (35.000đ/h): Nặng đầu, chuyên công đập cầu bộc phát uy lực.\n" +
        "2. ⚡ **Yonex Nanoflare 800 Pro** (35.000đ/h): Thân cứng vừa, tốc độ phản tạt & thủ lưới linh hoạt.\n" +
        "3. 🎯 **Yonex Arcsaber 11 Pro** (35.000đ/h): Công thủ toàn diện, điều cầu & kiểm soát chính xác.\n" +
        "4. 💥 **Victor Thruster Ryuga II** (40.000đ/h): Dành cho tay vợt thích smash bộc phát cực mạnh.\n" +
        "5. 🚀 **Li-Ning Axforce 90 Max** (40.000đ/h): Cực phẩm tấn công đỉnh cao thi đấu chuyên nghiệp.\n" +
        "6. 🌱 **Kumpoo Power Control K520 Pro** (20.000đ/h): Thân dẻo trợ lực tốt, giá rẻ phù hợp người mới / học viên.";
    }

    // 5. Tư vấn giá sân / bảng giá giờ bình thường & giờ 18h-22h
    if (p.includes('rẻ') || p.includes('giá') || p.includes('bao nhiêu') || p.includes('chi phí') || p.includes('18h') || p.includes('22h') || p.includes('5h') || p.includes('17h')) {
      return "💰 **Bảng Giá Thuê Sân Trên BADMINTON.AI**:\n\n" +
        "- **Giờ bình thường (05:00 Sáng - 17:00 Chiều)**: **120.000đ/giờ**.\n" +
        "- **Giờ cao điểm (18:00 Tối - 22:00 Đêm)**: **160.000đ/giờ** (áp dụng AI Dynamic Pricing đề xuất giá biến động).\n\n" +
        "📦 **Giá Dịch Vụ Thuê Đồ Kèm Theo**:\n" +
        "- **Vợt cầu lông (Yonex/Victor/Li-Ning/Kumpoo)**: Từ **20.000đ - 40.000đ/cây/giờ**.\n" +
        "- **Hộp Cầu Lông Thành Công (12 quả)**: **300.000đ/hộp**.\n" +
        "- **Nước Pocari Sweat 500ml**: **10.000đ/chai** | **Khăn lau**: **10.000đ/cái**.\n\n" +
        "👉 Chọn cụm sân & slot giờ bạn muốn để giữ chỗ 10 phút và cọc 50k VNPay nhé!";
    }

    // 6. Tư vấn danh sách cụm sân / địa chỉ chung
    if (p.includes('sân nào') || p.includes('danh sách') || p.includes('chi nhánh') || p.includes('nhiều nhất') || p.includes('địa chỉ') || p.includes('các sân') || p.includes('mấy sân')) {
      return "🏟️ **Danh Sách Các Cụm Sân Cầu Lông Thủ Đô Hà Nội Trên BADMINTON.AI**:\n\n" +
        "- Giá giờ bình thường (5h - 17h): **120.000đ/giờ** | Giá giờ cao điểm (18h - 22h): **160.000đ/giờ**.\n\n" +
        "1. **CLB Cầu Lông Catchy Badminton Arena** - 136 Tân Khai, Hoàng Mai (8 sân)\n" +
        "2. **CLB Cầu Lông Đống Đa Sport Hub** - 102 Láng Hạ, Đống Đa (10 sân)\n" +
        "3. **Smash Zone Cyber Badminton Mỹ Đình** - 15 Lê Đức Thọ, Nam Từ Liêm (8 sân)\n" +
        "4. **CLB Cầu Lông Ba Đình Star Arena** - 178 Điện Biên Phủ, Ba Đình (12 sân)\n" +
        "5. **Nhà Thi Đấu Cầu Lông Bách Khoa Yonex Pro** - 219 Lê Thanh Nghị, Hai Bà Trưng (10 sân)\n" +
        "6. **Thanh Xuân Badminton Club & Fuji Pro** - 159 Lê Văn Lương, Thanh Xuân (14 sân - Nhiều sân nhất!)\n" +
        "7. **CLB Cầu Lông Tây Hồ Arena** - 48 Đặng Thai Mai, Tây Hồ (8 sân)\n" +
        "8. **Hà Đông Cyber Badminton Club** - 215 Trần Phú, Hà Đông (12 sân)\n" +
        "9. **Sân Cầu Lông Cầu Giấy Pro Arena** - 35 Dịch Vọng Hậu, Cầu Giấy (8 sân)\n" +
        "10. **CLB Cầu Lông Hoàng Gia Cổ Nhuế** - 18 Cổ Nhuế, Bắc Từ Liêm (6 sân)\n" +
        "11. **Sân Cầu Lông Quần Ngựa Liễu Giai** - 30 Văn Cao, Ba Đình (8 sân)\n" +
        "12. **CLB Cầu Lông Định Công Arena** - KĐT Định Công, Hoàng Mai (8 sân)\n" +
        "13. **Sân Cầu Lông Ciputra Club** - KĐT Ciputra, Bắc Từ Liêm (12 sân)\n" +
        "14. **Sân Cầu Lông Long Biên Riverside Pro** - Đường Cổ Linh, Long Biên (10 sân)\n\n" +
        "👉 Bạn có thể gõ tên sân hoặc tên Quận tại Hà Nội (VD: 'Sân ở Cầu Giấy', 'Sân Đống Đa Sport Hub địa chỉ mấy?') để tôi tư vấn chính xác từng sân!";
    }

    // 7. Tư vấn đập cầu / kỹ thuật
    if (p.includes('đập') || p.includes('smash') || p.includes('tấn công')) {
      return "🏸 **Tư Vấn Chọn Vợt & Kỹ Thuật Đập Cầu Uy Lực**:\n\n" +
        "1. **Dòng Vợt Chuyên Đập**: Bạn nên chọn dòng vợt **Nặng đầu (Head-heavy)** tại quầy như **Yonex Astrox 88D Pro** (35k/h), **Victor Ryuga II** (40k/h) hoặc **Li-Ning Axforce 90 Max** (40k/h) để bộc phát lực dồn tối đa 🔥\n" +
        "2. **Độ cứng thân vợt**: Chọn thân vợt cứng trung bình đến cứng.\n" +
        "3. **Cầu thi đấu**: Dùng **Hộp Cầu Lông Thành Công (300.000đ/hộp)** cho đường cầu chuẩn xác!";
    }

    // 8. Tư vấn ghép kèo ELO & AI Matchmaking
    if (p.includes('elo') || p.includes('ghép') || p.includes('kèo')) {
      return "⚔️ **Hệ Thống AI Matchmaking & ELO Rating (UC006)**:\n" +
        "- Hệ thống áp dụng thuật toán phân phối Logistic ELO chuẩn quốc tế: `P(A) = 1 / (1 + 10^((R_B - R_A)/400))`.\n" +
        "- Tự động ghép phòng giao lưu thể thao cân bằng trình độ (chênh lệch dưới ±100 ELO).\n" +
        "- Dự báo trước tỷ lệ thắng (%) và ước tính số điểm ELO tăng/giảm sau trận đấu (K-Factor = 32).\n" +
        "👉 Bấm vào nút **'AI Dự Đoán Tỉ Lệ Thắng'** tại mục Nổi bật để trực tiếp chạy mô phỏng trận đấu!";
    }

    // 9. Tư vấn cơ chế AI Dynamic Pricing (UC003)
    if (p.includes('dynamic') || p.includes('biến động') || p.includes('giờ vàng') || p.includes('cơ chế ai') || p.includes('tính giá')) {
      return "⚡ **Cơ Chế AI Dynamic Pricing Engine (UC003)**:\n\n" +
        "1. **Tự động theo dõi tải lấp đầy**: Khi hệ thống phát hiện khung giờ 18:00 - 22:00 có tỷ lệ giữ chỗ vượt quá 85%, thuật toán kích hoạt mức giá biến động (+25% đến +33%) tương ứng **160.000đ/giờ**.\n" +
        "2. **Khuyến mãi kích cầu giờ thấp điểm**: Khung giờ sáng và giờ trưa (05:00 - 17:00) được giữ ở mức giá tiêu chuẩn **120.000đ/giờ** (hoặc flash sale giảm tới -17%).\n" +
        "3. **Tối ưu doanh thu**: Giúp chủ sân tăng trung bình **+18.5% doanh thu hàng tháng**, đồng thời đảm bảo người chơi luôn có sân trống vào giờ linh hoạt!";
    }

    // 10. Hướng dẫn cách đặt sân & giữ chỗ
    if (p.includes('cách đặt') || p.includes('đặt như thế nào') || p.includes('hướng dẫn đặt') || (p.includes('đặt') && p.includes('bước'))) {
      return "📅 **Quy Trình Đặt Sân Siêu Nhanh Trên BADMINTON.AI**:\n\n" +
        "1. **Chọn cụm sân**: Bấm vào bất kỳ cụm sân nào bạn yêu thích trên trang chủ hoặc bản đồ Hà Nội.\n" +
        "2. **Chọn ngày & slot giờ**: Nhấp 'Đặt sân', chọn ngày chơi và khung giờ trống bạn muốn.\n" +
        "3. **Khóa giữ chỗ 10 phút**: Hệ thống tự động khóa vị trí đó để đảm bảo không ai trùng sân với bạn.\n" +
        "4. **Đặt cọc VNPay**: Quét mã QR cọc 50.000đ để nhận ngay Vé điện tử QR Code check-in tại sân!\n\n" +
        "👉 Rất nhanh chóng và tiện lợi, chỉ mất chưa đầy 1 phút!";
    }

    // 11. Chính sách hủy sân & hoàn tiền
    if (p.includes('hủy sân') || p.includes('hoàn tiền') || p.includes('đổi giờ') || p.includes('dời lịch') || p.includes('hoàn cọc')) {
      return "🛡️ **Chính Sách Hủy Sân & Đổi Lịch Minh Bạch**:\n\n" +
        "- **Hủy trước 24 giờ**: Hoàn cọc **100%** tự động về ví hoặc tài khoản ngân hàng.\n" +
        "- **Đổi lịch trước 6 - 24 giờ**: Được hỗ trợ dời lịch sang giờ hoặc ngày khác hoàn toàn **miễn phí**.\n" +
        "- **Hủy gấp dưới 6 giờ**: Không hoàn cọc theo quy định giữ chỗ của cụm sân.\n\n" +
        "👉 Quản lý vé và hủy sân dễ dàng ngay trong mục **'Vé của tôi'** trên menu tài khoản!";
    }

    // 12. Giờ mở cửa & hotline hỗ trợ
    if (p.includes('mấy giờ') || p.includes('mở cửa') || p.includes('đóng cửa') || p.includes('hotline') || p.includes('liên hệ') || p.includes('số điện thoại') || p.includes('sđt')) {
      return "⏰ **Thời Gian Hoạt Động & Kênh Hỗ Trợ 24/7**:\n\n" +
        "- **Giờ mở cửa toàn hệ thống**: **05:00 Sáng - 23:00 Đêm** (tất cả các ngày trong tuần, kể cả ngày Lễ).\n" +
        "- 📞 **Hotline CSKH 24/7**: **1900 6868** hoặc **0988.123.456**\n" +
        "- 📧 **Email**: support@badminton.ai\n" +
        "- 💬 **Chat trực tuyến**: Bạn có thể hỏi trực tiếp tôi ở đây bất cứ lúc nào!";
    }

    // 13. Dịch vụ căng cước & phụ kiện
    if (p.includes('căng cước') || p.includes('đan vợt') || p.includes('quấn cán') || p.includes('cước') || p.includes('dây')) {
      return "🏸 **Dịch Vụ Căng Cước & Phụ Kiện Tại Sân**:\n\n" +
        "- **Căng cước máy điện tử 4 nút chuẩn Yonex**: Lấy ngay sau 15 - 20 phút.\n" +
        "- **Các loại cước có sẵn**: Yonex BG65 (110k), BG65Ti (130k), BG80 (160k), Nanogy 98 (170k), Lining No.1 (140k).\n" +
        "- **Mức căng khuyến nghị**: Người mới (9.0 - 10.0 kg), Phong trào (10.5 - 11.5 kg), Nâng cao (11.5 - 12.5 kg).\n" +
        "- **Quấn cán**: Yonex AC102EX (20.000đ/cái) có nhân viên quấn thay tại chỗ!";
    }

    return "🤖 **Google Gemini AI Assistant**:\nChào bạn! Tôi là trợ lý Trí Tuệ Nhân Tạo của hệ thống **BADMINTON.AI**. Tôi có thể hỗ trợ bạn giải đáp bất kỳ thắc mắc nào, từ đặt sân, tư vấn chọn vợt, chiến thuật thi đấu, điểm ELO, đến các câu hỏi giao lưu đời sống và thể thao. Hãy nhắn cho tôi bất kỳ điều gì bạn muốn tìm hiểu nhé! ✨🏸";
  }
}

// Global Instance
const geminiAI = new GeminiAIAssistant();
