/* ==========================================================================
   BADMINTON GEMINI AI ASSISTANT INTEGRATION (DEDICATED WEBSITE & BADMINTON AI)
   ========================================================================== */

class GeminiAIAssistant {
  constructor() {
    this.apiKey = localStorage.getItem('gemini_api_key') || window.GEMINI_API_KEY || '';

    this.primaryModel = 'gemini-2.5-flash';
    this.fallbackModel = 'gemini-1.5-flash';

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

      QUY TẮC BẮT BUỘC KHI TRẢ LỜI:
      1. TRẢ LỜI ĐÚNG TRỌNG TÂM: Khi khách hỏi về một cụm sân cụ thể hoặc địa điểm/quận cụ thể, CHỈ TRẢ LỜI ĐÚNG THÔNG TIN CỦA CỤM SÂN ĐÓ (Tên sân, Địa chỉ chính xác, Giờ mở/đóng cửa, Số sân, Bảng giá 120k từ 5h-17h và 160k từ 18h-22h). KHÔNG liệt kê tràn lan các sân ở quận khác.
      2. GIỚI HẠN ĐỊA LÝ KHU VỰC: Hệ thống BADMINTON.AI CHỈ hỗ trợ đặt sân và tư vấn các cụm sân tại khu vực THỦ ĐÔ HÀ NỘI. Nếu người dùng hỏi về sân ở các TỈNH / THÀNH PHỐ KHÁC ngoài Hà Nội (như TP.HCM, Đà Nẵng, Hải Phòng, Bình Dương, Đồng Nai, Vũng Tàu, Cần Thơ, Nha Trang, Đà Lạt...), bạn BẮT BUỘC TỪ CHỐI TƯ VẤN và trả lời:
         "Dạ xin lỗi bạn, hiện tại hệ thống BADMINTON.AI chỉ hỗ trợ đặt sân và tư vấn các cụm sân cầu lông tại khu vực Hà Nội thôi ạ! 📍"
      3. Nếu câu hỏi KHÔNG LIÊN QUAN ĐẾN CẦU LÔNG HOẶC HỆ THỐNG SÂN CẦU LÔNG, trả lời đúng 1 câu nguyên văn:
         "Dạ xin lỗi bạn, câu hỏi này nằm ngoài phạm vi hỗ trợ của tôi. Tôi chỉ có thể tư vấn các vấn đề về đặt sân, dụng cụ và kỹ thuật cầu lông thôi ạ!"
      4. KHÔNG XUẤT CÚ PHÁP LATEX/MATH. Dùng emoji và định dạng Markdown **in đậm**.
    `;
  }

  getAPIKey() {
    return this.apiKey;
  }

  setAPIKey(key) {
    this.apiKey = key.trim();
    localStorage.setItem('gemini_api_key', this.apiKey);
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
      'ryuga', 'axforce', 'kumpoo', 'k520', 'elo', 'ghép', 'kèo', 'cọc', 'vnpay', 'đặt', 'thủ đức', 'quận 1', 'tân bình', 'quận 7',
      'gò vấp', 'quận 10', 'phú nhuận', 'bình thạnh', 'luật', 'giao cầu', 'trọng tài', 'đơn', 'đôi',
      'thể lực', 'khởi động', 'chấn thương', 'cổ tay', 'đầu gối', 'bước chân', 'dậm nhảy',
      'lee chong wei', 'lin dan', 'momota', 'axelsen', 'tiến minh', 'thùy linh', 'bwf', 'badminton',
      'bóng', 'thiết bị', 'tư vấn', 'giờ', 'giá', 'giảm giá', 'đánh', 'chơi', 'tập', 'phòng',
      'rẻ', 'rẻ nhất', 'mấy sân', 'nhiều nhất', 'chi nhánh', 'địa chỉ', 'hệ thống', 'bao nhiêu',
      'pocari', 'nước', 'khăn', 'thành công'
    ];
    return badmintonKeywords.some(keyword => p.includes(keyword));
  }

  async generateResponse(userPrompt) {
    if (this.isOtherProvinceQuery(userPrompt)) {
      return "Dạ xin lỗi bạn, hiện tại hệ thống **BADMINTON.AI** tập trung hỗ trợ đặt sân và tư vấn các cụm sân cầu lông tại khu vực **Thủ Đô Hà Nội** ạ! 📍\n\nNếu bạn cần tìm sân cầu lông ở các phường/xã Hà Nội (như Cầu Giấy, Hoàn Kiếm, Đống Đa, Ba Đình, Mỹ Đình, Thanh Xuân, Tây Hồ, Hà Đông, Đông Anh, Gia Lâm...), bạn hãy cho mình biết nhé!";
    }

    if (!this.isBadmintonRelated(userPrompt)) {
      return "Dạ xin lỗi bạn, câu hỏi này nằm ngoài phạm vi hỗ trợ của tôi. Tôi chỉ có thể tư vấn các vấn đề về đặt sân, dụng cụ và kỹ thuật cầu lông thôi ạ!";
    }

    const currentKey = this.getAPIKey();
    if (!currentKey) {
      return this.getFallbackResponse(userPrompt);
    }

    const requestBody = {
      contents: [
        {
          role: 'user',
          parts: [{ text: `${this.systemInstruction}\n\nKhách hỏi: ${userPrompt}` }]
        }
      ],
      generationConfig: {
        maxOutputTokens: 1024,
        temperature: 0.4
      }
    };

    const modelsToTry = [this.primaryModel, this.fallbackModel];

    for (const model of modelsToTry) {
      const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${currentKey}`;
      try {
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(requestBody)
        });

        if (response.ok) {
          const data = await response.json();
          let reply = data.candidates?.[0]?.content?.parts?.[0]?.text;
          if (reply) {
            return this.cleanReplyText(reply);
          }
        }
      } catch (e) {
        console.warn(`Model ${model} fail, trying next...`);
      }
    }

    return this.getFallbackResponse(userPrompt);
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
    if (this.isOtherProvinceQuery(prompt)) {
      return "Dạ xin lỗi bạn, hiện tại hệ thống **BADMINTON.AI** chỉ hỗ trợ đặt sân và tư vấn các cụm sân cầu lông tại khu vực **TP. Hồ Chí Minh** thôi ạ! 📍\n\nNếu bạn cần tìm sân cầu lông ở khu vực TP.HCM (như TP. Thủ Đức, Quận 1, Phú Nhuận, Tân Bình, Gò Vấp, Bình Thạnh, Quận 7, Quận 10...), bạn hãy cho mình biết nhé!";
    }

    if (!this.isBadmintonRelated(prompt)) {
      return "Dạ xin lỗi bạn, câu hỏi này nằm ngoài phạm vi hỗ trợ của tôi. Tôi chỉ có thể tư vấn các vấn đề về đặt sân, dụng cụ và kỹ thuật cầu lông thôi ạ!";
    }

    const p = prompt.toLowerCase();

    // 0. Khớp dữ liệu sân cụ thể hoặc quận/huyện đúng trọng tâm
    if (typeof MockData !== 'undefined' && MockData.facilities) {
      const isLocationOrCourtQuery = p.includes('sân') || p.includes('địa chỉ') || p.includes('ở đâu') || p.includes('mấy giờ') || p.includes('mở cửa') || p.includes('đóng cửa') || p.includes('đánh giá') || p.includes('mấy sân') || p.includes('tọa độ') || p.includes('thủ đức') || p.includes('phú nhuận') || p.includes('tân bình') || p.includes('gò vấp') || p.includes('bình thạnh') || p.includes('quận 1') || p.includes('quận 7') || p.includes('quận 10') || p.includes('tân phú') || p.includes('quận 12') || p.includes('bình tân');

      const isEquipmentOrGeneralQuery = p.includes('vợt') || p.includes('thành công') || p.includes('pocari') || p.includes('khăn') || p.includes('elo') || p.includes('đập') || p.includes('smash');

      if (isLocationOrCourtQuery && !isEquipmentOrGeneralQuery) {
        const matched = MockData.facilities.filter(fac => {
          const nameLower = fac.name.toLowerCase();
          const addrLower = fac.address.toLowerCase();

          // Theo khu vực / Quận
          if (p.includes('thủ đức') && addrLower.includes('thủ đức')) return true;
          if ((p.includes('quận 1') || p.includes('q1') || p.includes('q.1')) && addrLower.includes('quận 1')) return true;
          if ((p.includes('quận 7') || p.includes('q7') || p.includes('q.7')) && addrLower.includes('quận 7')) return true;
          if (p.includes('bình thạnh') && addrLower.includes('bình thạnh')) return true;
          if (p.includes('tân bình') && addrLower.includes('tân bình')) return true;
          if (p.includes('gò vấp') && addrLower.includes('gò vấp')) return true;
          if ((p.includes('quận 10') || p.includes('q10') || p.includes('q.10')) && addrLower.includes('quận 10')) return true;
          if (p.includes('phú nhuận') && addrLower.includes('phú nhuận')) return true;
          if (p.includes('tân phú') && addrLower.includes('tân phú')) return true;
          if ((p.includes('quận 12') || p.includes('q12') || p.includes('q.12')) && addrLower.includes('quận 12')) return true;
          if (p.includes('bình tân') && addrLower.includes('bình tân')) return true;

          // Theo tên cụ thể
          if (p.includes('ai badminton') || p.includes('lê văn việt')) return fac.id === 101;
          if (p.includes('pro badminton') || p.includes('nguyễn thị minh khai')) return fac.id === 102;
          if (p.includes('sài gòn star')) return fac.id === 103;
          if (p.includes('tân bình sport hub') || p.includes('trường chinh')) return fac.id === 104;
          if (p.includes('smash zone') || p.includes('nguyễn hữu thọ')) return fac.id === 105;
          if (p.includes('gò vấp star') || p.includes('nguyễn oanh')) return fac.id === 106;
          if (p.includes('quận 10 yonex') || p.includes('lý thường kiệt')) return fac.id === 107;
          if (p.includes('fuji') || p.includes('phan đăng lưu')) return fac.id === 108;
          if (p.includes('thanh đa') || p.includes('bình quới')) return fac.id === 109;
          if (p.includes('võ văn ngân')) return fac.id === 110;

          return false;
        });

        if (matched.length > 0) {
          let reply = `🏟️ **Thông Tin Chi Tiết Cụm Sân Theo Yêu Cầu Của Bạn**:\n\n`;
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
      return "🏟️ **Danh Sách Các Cụm Sân Cầu Lông Trên BADMINTON.AI**:\n\n" +
        "- Giá giờ bình thường (5h - 17h): **120.000đ/giờ** | Giá giờ cao điểm (18h - 22h): **160.000đ/giờ**.\n\n" +
        "1. **AI Badminton Arena** - 123 Lê Văn Việt, TP. Thủ Đức (8 sân)\n" +
        "2. **Pro Badminton Center** - 45 Nguyễn Thị Minh Khai, Quận 1 (6 sân)\n" +
        "3. **Sài Gòn Star Badminton** - 88 Phạm Văn Đồng, Bình Thạnh (4 sân)\n" +
        "4. **Tân Bình Sport Hub** - 102 Trường Chinh, Tân Bình (10 sân)\n" +
        "5. **Smash Zone D7** - 15 Nguyễn Hữu Thọ, Quận 7 (8 sân)\n" +
        "6. **Gò Vấp Star Arena** - 178 Nguyễn Oanh, Gò Vấp (12 sân)\n" +
        "7. **Nhà Thi Đấu Quận 10 Yonex Pro** - 219 Lý Thường Kiệt, Q.10 (10 sân)\n" +
        "8. **Phú Nhuận Sport Center** - 159 Phan Đăng Lưu, Phú Nhuận (14 sân - Nhiều sân nhất!)\n" +
        "9. **CLB Bình Thạnh Arena** - 48 Bình Quới, Bình Thạnh (8 sân)\n" +
        "10. **Thủ Đức Cyber Club** - 215 Võ Văn Ngân, TP. Thủ Đức (12 sân)\n\n" +
        "👉 Bạn có thể gõ tên sân hoặc tên Quận (VD: 'Sân ở Phú Nhuận', 'Sân AI Badminton Arena địa chỉ mấy?') để tôi tư vấn chính xác từng sân!";
    }

    // 7. Tư vấn đập cầu / kỹ thuật
    if (p.includes('đập') || p.includes('smash') || p.includes('tấn công')) {
      return "🏸 **Tư Vấn Chọn Vợt & Kỹ Thuật Đập Cầu Uy Lực**:\n\n" +
        "1. **Dòng Vợt Chuyên Đập**: Bạn nên chọn dòng vợt **Nặng đầu (Head-heavy)** tại quầy như **Yonex Astrox 88D Pro** (35k/h), **Victor Ryuga II** (40k/h) hoặc **Li-Ning Axforce 90 Max** (40k/h) để bộc phát lực dồn tối đa 🔥\n" +
        "2. **Độ cứng thân vợt**: Chọn thân vợt cứng trung bình đến cứng.\n" +
        "3. **Cầu thi đấu**: Dùng **Hộp Cầu Lông Thành Công (300.000đ/hộp)** cho đường cầu chuẩn xác!";
    }

    // 8. Tư vấn ghép kèo ELO
    if (p.includes('elo') || p.includes('ghép') || p.includes('kèo')) {
      return "⚔️ **Hệ Thống AI Matchmaking ELO**:\nHệ thống tự động xếp bạn vào các phòng ghép đúng dải ELO trình độ (từ 1000 đến 2500+). Hãy sang tab **AI Matchmaking ELO** để tạo phòng hoặc chọn phòng giao lưu gần bạn nhất!";
    }

    return "🤖 **Smashing Badminton AI Assistant**:\nTôi là trợ lý AI chính thức của **BADMINTON.AI**! Giá thuê sân giờ bình thường (5h-17h) là **120.000đ/giờ**, giờ 18h - 22h là **160.000đ/giờ**. Bạn có thể hỏi tôi thông tin chi tiết từng sân (VD: 'Sân ở Phú Nhuận', 'Sân ở Thủ Đức', 'Sân Pro Badminton Center ở đâu?').";
  }
}

// Global Instance
const geminiAI = new GeminiAIAssistant();
