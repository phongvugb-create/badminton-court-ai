/**
 * ==========================================================================
 * BADMINTON.AI - GEMINI AI INTEGRATION ADAPTER
 * Proxies requests to secure backend endpoint (/api/chat) & window.badmintonAIChatbot
 * ==========================================================================
 */

class GeminiAIAssistant {
  constructor() {
    this.apiEndpoint = '/api/chat';
    this.modelName = 'gemini-1.5-flash';
  }

  getAPIKey() {
    return localStorage.getItem('gemini_api_key') || '';
  }

  setAPIKey(key) {
    if (key && key.trim()) {
      localStorage.setItem('gemini_api_key', key.trim());
      return true;
    }
    localStorage.removeItem('gemini_api_key');
    return false;
  }

  async generateResponse(prompt, context = "") {
    try {
      const res = await fetch(this.apiEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: prompt, context: context })
      });
      if (res.ok) {
        const data = await res.json();
        return data.reply || this.getFallbackResponse(prompt);
      }
    } catch (e) {
      console.warn("Backend chat call failed, using fallback:", e);
    }
    return this.getFallbackResponse(prompt);
  }

  getFallbackResponse(question) {
    const q = (question || "").toLowerCase();
    if (q.includes("giá") || q.includes("tiền") || q.includes("bảng giá")) {
      return "🏸 **Bảng Giá Thuê Sân BADMINTON.AI**:\n- **Giờ hành chính (8h - 14h)**: ~70.000đ - 100.000đ/h *(AI giảm giá 15%)*\n- **Giờ vàng (17h - 21h)**: ~130.000đ - 160.000đ/h *(Phụ thu AI +25%)*";
    }
    if (q.includes("đặt sân") || q.includes("giữ chỗ")) {
      return "⏰ **Đặt Sân**: Giữ chỗ 10 phút chống xung đột đặt trùng, đặt cọc 50% qua VNPay/QR.";
    }
    if (q.includes("elo") || q.includes("ghép")) {
      return "🏆 **AI Matchmaking**: Tự động ghép phòng theo dải điểm ELO 1000 - 2000+.";
    }
    return "👋 Chào bạn! Tôi là Trợ lý AI BADMINTON.AI sẵn sàng hỗ trợ đặt sân, tư vấn bảng giá và ghép kèo ELO!";
  }
}

// Global instance export
window.geminiAI = new GeminiAIAssistant();
