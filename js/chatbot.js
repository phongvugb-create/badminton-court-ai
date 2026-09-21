/**
 * ==========================================================================
 * BADMINTON.AI - GEMINI AI CHATBOT ASSISTANT CONTROLLER
 * Integrates with Backend Gemini 1.5 Flash API Endpoint (/api/chat)
 * ==========================================================================
 */

class BadmintonAIChatbot {
  constructor() {
    this.isOpen = false;
    this.isProcessing = false;
    this.messages = [];
    this.storageKey = 'badminton_ai_chat_history_v1';
    this.apiEndpoint = '/api/chat'; // Secure server-side proxy
    
    this.init();
  }

  init() {
    this.loadHistory();
    this.renderWidget();
    this.attachEventListeners();
  }

  loadHistory() {
    try {
      const saved = sessionStorage.getItem(this.storageKey);
      if (saved) {
        this.messages = JSON.parse(saved);
      }
    } catch (e) {
      this.messages = [];
    }

    // Default welcome message if history is empty
    if (!this.messages || this.messages.length === 0) {
      this.messages = [
        {
          sender: 'bot',
          text: '👋 Xin chào bạn! Tôi là **Trợ lý AI Thông Minh BADMINTON.AI**.\n\nTôi sẵn sàng giải đáp mọi thắc mắc về **đặt sân, bảng giá giờ vàng, tư vấn chọn vợt & tìm phòng ghép kèo ELO**! Hãy chọn gợi ý bên dưới hoặc đặt câu hỏi trực tiếp cho tôi nhé! ✨🏸',
          time: this.getCurrentTimeString()
        }
      ];
    }
  }

  saveHistory() {
    try {
      sessionStorage.setItem(this.storageKey, JSON.stringify(this.messages));
    } catch (e) {}
  }

  getCurrentTimeString() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const mins = String(now.getMinutes()).padStart(2, '0');
    return `${hours}:${mins}`;
  }

  renderWidget() {
    // If widget container already exists, don't duplicate
    let root = document.getElementById('badminton-ai-chatbot-root');
    if (!root) {
      root = document.createElement('div');
      root.id = 'badminton-ai-chatbot-root';
      document.body.appendChild(root);
    }

    root.innerHTML = `
      <!-- Floating Bubble Button -->
      <button class="ai-chat-bubble-btn" id="ai-chat-trigger-btn" title="Hỏi Trợ Lý Gemini AI" aria-label="Mở Trợ lý AI">
        <i class="fa-solid fa-wand-magic-sparkles" id="ai-bubble-icon"></i>
        <span class="ai-chat-badge" id="ai-unread-badge" style="display: none;">1</span>
      </button>

      <!-- Chatbot Dialog Window -->
      <div class="ai-chat-window" id="ai-chat-window-box" role="dialog" aria-labelledby="ai-chat-header-title">
        <!-- Header -->
        <div class="ai-chat-header">
          <div class="ai-chat-header-left">
            <div class="ai-chat-avatar">
              <i class="fa-solid fa-robot"></i>
              <span class="ai-chat-online-dot" title="Đang trực tuyến"></span>
            </div>
            <div class="ai-chat-title-group">
              <h4 id="ai-chat-header-title">
                BADMINTON.AI
                <span style="font-size: 0.65rem; background: rgba(16, 185, 129, 0.2); color: #10b981; padding: 2px 6px; border-radius: 6px; font-weight: 700; border: 1px solid rgba(16, 185, 129, 0.4);">
                  ⚡ Gemini Flash
                </span>
              </h4>
              <p>Trợ lý AI Hỗ Trợ 24/7</p>
            </div>
          </div>
          <div class="ai-chat-header-actions">
            <button class="ai-chat-btn-icon" id="ai-chat-clear-btn" title="Làm mới đoạn hội thoại" aria-label="Làm mới đoạn chat">
              <i class="fa-solid fa-rotate-right"></i>
            </button>
            <button class="ai-chat-btn-icon" id="ai-chat-close-btn" title="Thu nhỏ khung chat" aria-label="Đóng khung chat">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>
        </div>

        <!-- Messages Area -->
        <div class="ai-chat-messages" id="ai-chat-messages-body"></div>

        <!-- Quick Prompt Chips -->
        <div class="ai-chat-chips">
          <button class="ai-chip" data-prompt="🤖 Tìm giúp tôi sân gần Hoàng Mai / Cầu Giấy có giá tốt nhất?">
            📍 Sân gần tôi (Hà Nội)
          </button>
          <button class="ai-chip" data-prompt="⚡ Cơ chế AI Dynamic Pricing tính giá giờ vàng và giờ hành chính như thế nào?">
            ⚡ Giá giờ vàng & Giờ HC
          </button>
          <button class="ai-chip" data-prompt="🏸 Tư vấn cách chọn vợt cầu lông phù hợp lối chơi Smash tấn công?">
            🏸 Tư vấn chọn vợt smash
          </button>
          <button class="ai-chip" data-prompt="🏆 Điểm ELO của tôi 1450, hệ thống gợi ý phòng ghép kèo như thế nào?">
            🏆 Ghép kèo ELO 1450
          </button>
          <button class="ai-chip" data-prompt="📋 Quy định đặt cọc 50% và chính sách hủy sân hoàn cọc ra sao?">
            📋 Quy định hoàn hủy cọc
          </button>
        </div>

        <!-- Input Area Form -->
        <form class="ai-chat-input-form" id="ai-chat-form">
          <input 
            type="text" 
            id="ai-chat-input-field" 
            class="ai-chat-input" 
            placeholder="Nhập câu hỏi về đặt sân, giá thuê, vợt..." 
            autocomplete="off" 
            required 
          />
          <button type="submit" class="ai-chat-send-btn" id="ai-chat-send-submit" title="Gửi tin nhắn">
            <i class="fa-solid fa-paper-plane"></i>
          </button>
        </form>
      </div>
    `;

    this.renderMessages();
  }

  attachEventListeners() {
    const triggerBtn = document.getElementById('ai-chat-trigger-btn');
    const closeBtn = document.getElementById('ai-chat-close-btn');
    const clearBtn = document.getElementById('ai-chat-clear-btn');
    const form = document.getElementById('ai-chat-form');
    const chips = document.querySelectorAll('.ai-chip');

    if (triggerBtn) {
      triggerBtn.addEventListener('click', () => this.toggle());
    }

    if (closeBtn) {
      closeBtn.addEventListener('click', () => this.toggle(false));
    }

    if (clearBtn) {
      clearBtn.addEventListener('click', () => this.clearChat());
    }

    if (form) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        const input = document.getElementById('ai-chat-input-field');
        if (!input) return;
        const text = input.value.trim();
        if (text && !this.isProcessing) {
          input.value = '';
          this.sendMessage(text);
        }
      });
    }

    chips.forEach(chip => {
      chip.addEventListener('click', () => {
        const prompt = chip.getAttribute('data-prompt');
        if (prompt && !this.isProcessing) {
          this.sendMessage(prompt);
        }
      });
    });
  }

  toggle(forceState) {
    this.isOpen = typeof forceState === 'boolean' ? forceState : !this.isOpen;
    const windowEl = document.getElementById('ai-chat-window-box');
    const triggerIcon = document.getElementById('ai-bubble-icon');
    const badge = document.getElementById('ai-unread-badge');
    const inputField = document.getElementById('ai-chat-input-field');

    if (windowEl) {
      if (this.isOpen) {
        windowEl.classList.add('active');
        if (triggerIcon) {
          triggerIcon.className = 'fa-solid fa-chevron-down';
        }
        if (badge) badge.style.display = 'none';
        this.scrollToBottom();
        setTimeout(() => {
          if (inputField) inputField.focus();
        }, 150);
      } else {
        windowEl.classList.remove('active');
        if (triggerIcon) {
          triggerIcon.className = 'fa-solid fa-wand-magic-sparkles';
        }
      }
    }
  }

  renderMessages() {
    const container = document.getElementById('ai-chat-messages-body');
    if (!container) return;

    container.innerHTML = this.messages.map(msg => {
      const isUser = msg.sender === 'user';
      const formattedText = isUser ? this.escapeHtml(msg.text) : this.formatMarkdown(msg.text);

      return `
        <div class="ai-msg-row ${isUser ? 'user' : 'bot'}">
          ${!isUser ? `
            <div class="ai-msg-avatar">
              <i class="fa-solid fa-robot"></i>
            </div>
          ` : ''}
          <div class="ai-msg-content">
            <div>${formattedText}</div>
            <div class="ai-msg-time">${msg.time || ''}</div>
          </div>
        </div>
      `;
    }).join('');

    this.scrollToBottom();
  }

  async sendMessage(text) {
    if (!text || this.isProcessing) return;

    // 1. Append user message
    const userMsg = {
      sender: 'user',
      text: text,
      time: this.getCurrentTimeString()
    };
    this.messages.push(userMsg);
    this.saveHistory();
    this.renderMessages();

    // 2. Show Typing Indicator
    this.isProcessing = true;
    this.setSendButtonState(false);
    this.showTypingIndicator();

    // 3. Build Site Context
    let siteContext = "";
    if (typeof app !== 'undefined' && app.currentUser) {
      siteContext += `Khách hàng hiện tại: ${app.currentUser.name} (Điểm ELO: ${app.currentUser.elo || 1200}). `;
    }
    if (typeof app !== 'undefined' && app.selectedFacility) {
      siteContext += `Đang xem cụm sân: ${app.selectedFacility.name} (${app.selectedFacility.address}). `;
    }

    // 4. Call Secure Server Endpoint
    try {
      const response = await fetch(this.apiEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: text,
          context: siteContext,
          messages: this.messages
        })
      });

      let replyText = "";
      if (response.ok) {
        const data = await response.json();
        replyText = data.reply || "Tôi đã ghi nhận câu hỏi. Bạn có thể tham khảo thêm trên menu hoặc bản đồ sân nhé!";
      } else {
        replyText = "🤖 Xin lỗi bạn, kết nối tới máy chủ AI đang bận. Bạn vui lòng thử lại sau giây lát hoặc xem trực tiếp thông tin sân trên bảng giá nhé!";
      }

      this.removeTypingIndicator();
      this.messages.push({
        sender: 'bot',
        text: replyText,
        time: this.getCurrentTimeString()
      });
      this.saveHistory();
      this.renderMessages();

    } catch (err) {
      console.warn("API Call Failed, fallback:", err);
      this.removeTypingIndicator();
      
      this.messages.push({
        sender: 'bot',
        text: "⚡ **Phản Hồi Tức Thì**:\nHệ thống sẵn sàng hỗ trợ bạn tìm sân tại Hà Nội, đặt cọc giữ chỗ 10 phút và tư vấn ghép kèo thi đấu ELO! Hãy nhắn chi tiết hơn nhu cầu của bạn nhé!",
        time: this.getCurrentTimeString()
      });
      this.saveHistory();
      this.renderMessages();
    } finally {
      this.isProcessing = false;
      this.setSendButtonState(true);
    }
  }

  showTypingIndicator() {
    const container = document.getElementById('ai-chat-messages-body');
    if (!container) return;

    const typingDiv = document.createElement('div');
    typingDiv.className = 'ai-msg-row bot';
    typingDiv.id = 'ai-typing-indicator-node';
    typingDiv.innerHTML = `
      <div class="ai-msg-avatar">
        <i class="fa-solid fa-robot"></i>
      </div>
      <div class="ai-msg-content" style="padding: 0.5rem 0.8rem;">
        <div class="ai-typing-indicator">
          <span style="font-size: 0.76rem; color: #94a3b8; margin-right: 4px;">Gemini đang trả lời</span>
          <span class="ai-typing-dot"></span>
          <span class="ai-typing-dot"></span>
          <span class="ai-typing-dot"></span>
        </div>
      </div>
    `;
    container.appendChild(typingDiv);
    this.scrollToBottom();
  }

  removeTypingIndicator() {
    const node = document.getElementById('ai-typing-indicator-node');
    if (node) node.remove();
  }

  setSendButtonState(enabled) {
    const sendBtn = document.getElementById('ai-chat-send-submit');
    const inputField = document.getElementById('ai-chat-input-field');
    if (sendBtn) sendBtn.disabled = !enabled;
    if (inputField) inputField.disabled = !enabled;
  }

  clearChat() {
    if (confirm("Bạn có muốn làm mới đoạn hội thoại với Trợ lý AI không?")) {
      this.messages = [
        {
          sender: 'bot',
          text: '✨ **Đoạn hội thoại đã được làm mới!**\n\nTôi có thể giúp gì cho bạn về đặt sân, bảng giá, chọn vợt hay ghép kèo thi đấu hôm nay? 🏸',
          time: this.getCurrentTimeString()
        }
      ];
      this.saveHistory();
      this.renderMessages();
    }
  }

  scrollToBottom() {
    const container = document.getElementById('ai-chat-messages-body');
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }

  escapeHtml(unsafe) {
    return unsafe
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  formatMarkdown(text) {
    if (!text) return "";
    let safe = this.escapeHtml(text);

    // Headers ### -> <h4>, ## -> <h4>, # -> <h4>
    safe = safe.replace(/^###\s+(.*?)$/gm, '<h4>$1</h4>');
    safe = safe.replace(/^##\s+(.*?)$/gm, '<h4>$1</h4>');
    safe = safe.replace(/^#\s+(.*?)$/gm, '<h4>$1</h4>');

    // Bold **text**
    safe = safe.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Italic *text*
    safe = safe.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Code `code`
    safe = safe.replace(/`([^`]+)`/g, '<code style="background: rgba(0,0,0,0.3); padding: 2px 4px; border-radius: 4px; color: #38bdf8; font-size: 0.8rem;">$1</code>');

    // List items - item
    safe = safe.replace(/^\s*-\s+(.*?)$/gm, '<li>$1</li>');
    safe = safe.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

    // Convert newlines to <br>
    safe = safe.replace(/\n/g, '<br>');

    // Clean up excessive <br> inside list
    safe = safe.replace(/<\/li><br>/g, '</li>');
    safe = safe.replace(/<ul><br>/g, '<ul>');
    safe = safe.replace(/<\/ul><br>/g, '</ul>');

    return safe;
  }
}

// Instantiate global chatbot instance
window.badmintonAIChatbot = new BadmintonAIChatbot();
