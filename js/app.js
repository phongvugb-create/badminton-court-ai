/* ==========================================================================
   BADMINTON AI MANAGEMENT SYSTEM - APP LOGIC (19 SCREENS & 4 PORTALS)
   ========================================================================== */

class BadmintonAIApp {
  constructor() {
    this.currentRole = 'CUSTOMER';
    this.currentView = 'ui-02';
    this.currentUser = null; // Default: Chưa đăng nhập (Giao diện Khách hàng vãng lai)
    
    // Booking & State Tracking
    this.selectedFacility = MockData.facilities[0];
    this.selectedSlot = null;
    this.selectedSlots = []; // Multi-slot booking support: Array of selected slot objects
    this.selectedEquipments = {}; // { equipId: qty }
    this.holdTimer = null;
    this.holdTimerSeconds = 600; // 10 minutes (600s)
    this.isAIDynamicPriceActive = true;
    
    // Favorites & Quick Filters
    this.favorites = new Set([101, 102]);
    this.isFavoritesFilterActive = false;

    // Chat & Active Room
    this.activeRoom = MockData.matchmaking_rooms[0];
    this.currentMMFilter = 'all';
    this.currentMMSearch = '';
    this.currentMMSort = 'ai-match';

    // Database Inspector State
    this.currentDBTable = 'facilities';
    this.isDBJSONView = false;
  }

  init() {
    this.initSplashScreen();
    this.updateTopDateDisplay();
    this.updateHeaderUserUI();
    this.renderSidebarNav();
    this.navigateTo(this.currentView);
    this.renderCustomerFacilities();
    this.renderSlotMatrix();
    this.renderEquipmentRentalList();
    this.renderBookingOrdersList();
    this.renderMatchmakingRooms();
    this.renderOwnerCourts();
    this.renderOwnerEquipments();
    this.renderOwnerStaff();
    this.renderHeatmap();
    this.renderAdminApprovals();
    this.renderAdminUsers();
    this.renderAdminOverviewFacilities();
    this.renderOwnerDashboardOrders();
    this.initLeafletMap();
    this.updatePendingMatchesUI();
  }

  copyToClipboard(text, label = "Thông tin") {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => {
        this.showToast(`📋 Đã sao chép ${label}: ${text}`);
      }).catch(() => {
        this.fallbackCopy(text, label);
      });
    } else {
      this.fallbackCopy(text, label);
    }
  }

  fallbackCopy(text, label) {
    try {
      const el = document.createElement('textarea');
      el.value = text;
      el.setAttribute('readonly', '');
      el.style.position = 'absolute';
      el.style.left = '-9999px';
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
      this.showToast(`📋 Đã sao chép ${label}: ${text}`);
    } catch (e) {
      this.showToast(`Mã chuyển khoản: ${text}`);
    }
  }

  openVNPaySandboxModal() {
    const totalAmount = this.currentPendingTotalAmount || 120000;
    const depositAmount = this.currentPendingDepositAmount || 60000;
    const code = this.currentPendingBookingCode || 'BK-20261002-001';
    const modalBody = document.getElementById('modal-body');
    if (!modalBody) return;

    modalBody.innerHTML = `
      <div style="padding: 0.5rem 0;">
        <div style="text-align: center; margin-bottom: 1.25rem;">
          <div style="display: flex; justify-content: center; gap: 8px; margin-bottom: 8px;">
            <span style="background: #0066cc; color: #fff; font-size: 0.78rem; font-weight: 800; padding: 3px 10px; border-radius: 6px;">VNPAY GATEWAY</span>
            <span style="background: #16a34a; color: #fff; font-size: 0.78rem; font-weight: 800; padding: 3px 10px; border-radius: 6px;">BẢO MẬT SSL 256-BIT</span>
          </div>
          <h3 style="margin: 0; font-size: 1.2rem; color: #0f172a;">Cổng Thanh Toán VNPay Sandbox</h3>
          <p style="font-size: 0.82rem; color: #64748b; margin: 4px 0 0;">Mã giao dịch: <strong>${code}</strong> | Tiền cọc giữ chỗ: <strong style="color: #16a34a;">${depositAmount.toLocaleString('vi-VN')} VNĐ</strong></p>
        </div>

        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1rem; margin-bottom: 1.25rem; font-size: 0.85rem; color: #1e293b;">
          <div style="font-weight: 700; margin-bottom: 8px; color: #0f172a;">Chọn kênh thanh toán trực tuyến:</div>
          <div style="display: grid; gap: 8px;">
            <label style="display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: #fff; border: 1.5px solid #0066cc; border-radius: 8px; cursor: pointer;">
              <input type="radio" name="vnpay_method" checked value="VNPAYQR">
              <div>
                <strong>Ứng dụng Ngân hàng hỗ trợ VNPAY-QR</strong>
                <div style="font-size: 0.75rem; color: #64748b;">Hơn 40 ứng dụng ngân hàng: VCB, BIDV, MB, Agribank, VietinBank...</div>
              </div>
            </label>
            <label style="display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: #fff; border: 1px solid #cbd5e1; border-radius: 8px; cursor: pointer;">
              <input type="radio" name="vnpay_method" value="VNBANK">
              <div>
                <strong>Thẻ ATM / Tài khoản Nội địa (NAPAS)</strong>
                <div style="font-size: 0.75rem; color: #64748b;">Thanh toán bằng thẻ ATM có đăng ký Internet Banking</div>
              </div>
            </label>
            <label style="display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: #fff; border: 1px solid #cbd5e1; border-radius: 8px; cursor: pointer;">
              <input type="radio" name="vnpay_method" value="INTCARD">
              <div>
                <strong>Thẻ Quốc Tế (Visa, MasterCard, JCB, UnionPay)</strong>
                <div style="font-size: 0.75rem; color: #64748b;">Hỗ trợ thẻ tín dụng và ghi nợ quốc tế phát hành toàn cầu</div>
              </div>
            </label>
          </div>
        </div>

        <div style="display: flex; gap: 8px;">
          <button class="btn btn-primary" style="flex: 1; padding: 10px; font-weight: 700; background: #0066cc;" onclick="app.confirmVNPayGatewayPayment()">
            <i class="fa-solid fa-lock"></i> Hoàn Tất Thanh Toán ${depositAmount.toLocaleString('vi-VN')}đ
          </button>
          <button class="btn btn-secondary" onclick="app.closeModal()">Đóng</button>
        </div>
      </div>
    `;
    this.openModal();
  }

  confirmVNPayGatewayPayment() {
    this.closeModal();
    this.showToast("⚡ Đang xác thực chứng chỉ bảo mật và nhận phản hồi IPN từ cổng VNPay...");
    setTimeout(() => {
      this.processPaymentConfirmation();
    }, 800);
  }

  updateTopDateDisplay() {
    const dateEl = document.getElementById('top-header-date');
    if (!dateEl) return;
    const days = ['Chủ nhật', 'Thứ hai', 'Thứ ba', 'Thứ tư', 'Thứ năm', 'Thứ sáu', 'Thứ bảy'];
    const now = new Date();
    const dayName = days[now.getDay()];
    const dateStr = String(now.getDate()).padStart(2, '0');
    const monthStr = String(now.getMonth() + 1).padStart(2, '0');
    const yearStr = now.getFullYear();
    dateEl.textContent = `${dayName}, ${dateStr}/${monthStr}/${yearStr}`;
  }

  updateHeaderUserUI() {
    const avatarEl = document.getElementById('header-avatar');
    const nameEl = document.getElementById('header-user-name');
    const roleTagEl = document.getElementById('header-user-role-tag');
    const profileBadge = document.getElementById('header-user-profile-badge');
    const logoutBtn = document.getElementById('header-logout-btn');
    const authPills = document.getElementById('header-auth-pills-group');
    const starBadge = document.getElementById('header-star-badge');

    const roleNames = {
      'CUSTOMER': 'Khách Hàng',
      'OWNER': 'Chủ Sân',
      'STAFF': 'Thu Ngân',
      'ADMIN': 'Quản Trị'
    };

    if (this.currentUser) {
      if (avatarEl) avatarEl.textContent = this.currentUser.avatar || '👤';
      if (nameEl) nameEl.textContent = this.currentUser.name;
      if (roleTagEl) roleTagEl.textContent = roleNames[this.currentUser.role] || this.currentUser.role;
      if (profileBadge) profileBadge.style.display = 'inline-flex';
      if (logoutBtn) logoutBtn.style.display = 'inline-flex';
      if (starBadge) starBadge.style.display = 'flex';
      if (authPills) authPills.style.display = 'none';
    } else {
      if (profileBadge) profileBadge.style.display = 'none';
      if (logoutBtn) logoutBtn.style.display = 'none';
      if (starBadge) starBadge.style.display = 'none';
      if (authPills) authPills.style.display = 'inline-flex';
    }

    this.renderHomeAuthBanner();
    if (this.currentView === 'ui-08') {
      this.renderUserProfilePage();
    }
  }

  renderHomeAuthBanner() {
    const container = document.getElementById('home-auth-status-banner');
    if (!container) return;

    if (!this.currentUser) {
      container.innerHTML = `
        <div class="home-auth-banner guest-banner">
          <div style="display: flex; align-items: center; gap: 14px; flex: 1; min-width: 280px;">
            <div style="width: 48px; height: 48px; border-radius: 12px; background: rgba(255,255,255,0.2); display: flex; align-items: center; justify-content: center; font-size: 1.5rem; flex-shrink: 0; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">
              🏸
            </div>
            <div>
              <div style="font-weight: 800; font-size: 1.05rem; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                <span>Chào mừng bạn đến với Badminton.AI!</span>
                <span style="font-size: 0.72rem; background: rgba(255,255,255,0.25); padding: 2px 8px; border-radius: 9999px; text-transform: uppercase; font-weight: 800;">Chưa Đăng Nhập</span>
              </div>
              <div style="font-size: 0.84rem; opacity: 0.95; margin-top: 3px; line-height: 1.4;">
                Đăng nhập để tự động lưu lịch sử đặt sân, giữ chỗ 10 phút, tra cứu vé QR điện tử và ghép kèo thi đấu ELO!
              </div>
            </div>
          </div>
          <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <button class="btn btn-sm" onclick="app.navigateTo('ui-01')" style="background: #ffffff; color: #0d562e; font-weight: 800; border: none; padding: 8px 18px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.2); cursor: pointer;">
              <i class="fa-solid fa-right-to-bracket"></i> Đăng Nhập
            </button>
            <button class="btn btn-sm" onclick="app.navigateTo('ui-01'); app.switchAuthTab('register')" style="background: rgba(255,255,255,0.15); color: #ffffff; border: 1.5px solid #ffffff; font-weight: 800; padding: 8px 18px; border-radius: 8px; cursor: pointer;">
              <i class="fa-solid fa-user-plus"></i> Đăng Ký Tài Khoản
            </button>
          </div>
        </div>
      `;
    } else {
      const currentElo = typeof this.currentUser.elo_rating === 'number' ? this.currentUser.elo_rating : 1200;
      const tier = typeof this.getEloTierInfo === 'function' ? this.getEloTierInfo(currentElo) : { name: 'Cơ bản', display: 'Cơ bản', bg: '#dbeafe', color: '#2563eb' };
      const roleNames = {
        'CUSTOMER': 'Khách Hàng',
        'OWNER': 'Chủ Sân',
        'STAFF': 'Thu Ngân',
        'ADMIN': 'Quản Trị Viên'
      };

      container.innerHTML = `
        <div class="home-auth-banner member-banner">
          <div style="display: flex; align-items: center; gap: 14px; flex: 1; min-width: 280px;">
            <div style="width: 44px; height: 44px; border-radius: 50%; background: #167946; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 1.25rem; font-weight: 800; flex-shrink: 0; box-shadow: 0 3px 8px rgba(22, 121, 70, 0.3);">
              ${this.currentUser.avatar || '👤'}
            </div>
            <div>
              <div style="font-weight: 800; font-size: 1rem; color: #0f172a; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                <span>Xin chào, ${this.currentUser.name}!</span>
                <span style="font-size: 0.72rem; background: #dcfce7; color: #16a34a; padding: 2px 8px; border-radius: 9999px; font-weight: 800;">
                  ${roleNames[this.currentUser.role] || this.currentUser.role}
                </span>
                <span style="font-size: 0.72rem; background: ${tier.bg}; color: ${tier.color}; padding: 2px 8px; border-radius: 9999px; font-weight: 800;">
                  ${tier.display}
                </span>
              </div>
              <div style="font-size: 0.82rem; color: #64748b; margin-top: 2px;">
                Tài khoản: <strong>${this.currentUser.phone}</strong> • Đã kích hoạt đầy đủ quyền lợi thành viên chính thức.
              </div>
            </div>
          </div>
          <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <button class="btn btn-outline-primary btn-sm" onclick="app.navigateTo('ui-08')">
              <i class="fa-solid fa-id-card"></i> Hồ Sơ ELO
            </button>
            <button class="btn btn-primary btn-sm" onclick="app.navigateTo('ui-05')">
              <i class="fa-solid fa-ticket"></i> Vé QR Của Tôi
            </button>
          </div>
        </div>
      `;
    }
  }

  renderUserProfilePage() {
    const container = document.getElementById('user-profile-view-container');
    if (!container) return;

    const lang = localStorage.getItem('badminton_app_language') || this.currentLanguage || 'vi';
    const isEn = lang === 'en';

    if (!this.currentUser) {
      container.innerHTML = `
        <div class="page-header" style="margin-bottom: 1.5rem; text-align: center;">
          <h1 class="page-title" style="justify-content: center;">
            <i class="fa-solid fa-user-gear text-primary"></i> ${isEn ? 'Account & Profile Management' : 'Hồ Sơ Cá Nhân & Quản Lý Tài Khoản'}
          </h1>
          <p class="page-subtitle">
            ${isEn ? 'Manage your bookings, promotional vouchers, notification preferences and security settings' : 'Quản lý lịch đặt sân, kho ưu đãi, thông báo và bảo mật tài khoản cá nhân'}
          </p>
        </div>

        <div class="guest-locked-card">
          <div style="width: 72px; height: 72px; border-radius: 50%; background: #f0fdf4; display: flex; align-items: center; justify-content: center; margin: 0 auto 1.25rem; font-size: 2rem; color: #167946; border: 2px dashed #86efac;">
            <i class="fa-solid fa-id-card"></i>
          </div>
          <h2 style="font-size: 1.4rem; color: #0f172a; margin-bottom: 0.5rem; font-weight: 800;">
            ${isEn ? 'Guest Mode (Not Logged In)' : 'Chế Độ Khách Vãng Lai'}
          </h2>
          <p style="font-size: 0.92rem; color: #64748b; max-width: 460px; margin: 0 auto 1.5rem; line-height: 1.6;">
            ${isEn ? 'Please log in to your account to view your bookings, active discount vouchers, notification preferences and security settings.' : 'Bạn hiện đang truy cập ở chế độ chưa đăng nhập. Vui lòng <strong>Đăng Nhập</strong> hoặc <strong>Đăng Ký</strong> để xem lịch đặt sân, kho voucher ưu đãi, cài đặt thông báo và quản lý tài khoản của bạn!'}
          </p>
          <div style="display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;">
            <button class="btn btn-primary" onclick="app.navigateTo('ui-01')" style="padding: 10px 24px; font-weight: 800;">
              <i class="fa-solid fa-right-to-bracket"></i> ${isEn ? 'Log In Now' : 'Đăng Nhập Ngay'}
            </button>
            <button class="btn btn-outline-primary" onclick="app.navigateTo('ui-01'); app.switchAuthTab('register')" style="padding: 10px 24px; font-weight: 800;">
              <i class="fa-solid fa-user-plus"></i> ${isEn ? 'Create Account' : 'Đăng Ký Tài Khoản'}
            </button>
          </div>
        </div>
      `;
      return;
    }

    const user = this.currentUser;
    const roleNames = {
      'CUSTOMER': isEn ? 'Member Player' : 'Khách Hàng Hội Viên',
      'OWNER': isEn ? 'Facility Partner / Owner' : 'Chủ Cụm Sân',
      'STAFF': isEn ? 'Staff / Cashier' : 'Thu Ngân Vận Hành',
      'ADMIN': isEn ? 'System Administrator' : 'Quản Trị Viên'
    };

    // Joined date & duration calculation
    const joinedDateStr = user.joined_date || "15/03/2025";
    const durationText = this.getMembershipDurationText(joinedDateStr, isEn);
    const membershipTier = user.membership_tier || (isEn ? "Gold Member ⭐" : "Hội viên Vàng ⭐");
    const skillTier = this.getSkillTierInfo(user.skill_tier_id || user.skill_tier || 5);
    const userPhoto = user.photo || user.avatar;
    const isPhotoUrl = userPhoto && (userPhoto.startsWith('data:image') || userPhoto.startsWith('http') || userPhoto.includes('/'));

    // Filter user booking orders
    const allOrders = MockData.booking_orders || [];
    const userOrders = allOrders.filter(o => 
      o.user_name === user.name || o.user_phone === user.phone || (user.id === 6 && o.user_name === "Vũ Nhất Phong") || (user.id === 1 && o.user_name === "Nguyễn Văn Hùng")
    );

    // Active tab
    const activeTab = this.currentProfileTab || 'bookings';

    container.innerHTML = `
      <div class="page-header" style="margin-bottom: 1.25rem;">
        <div>
          <h1 class="page-title"><i class="fa-solid fa-user-gear text-primary"></i> ${isEn ? 'My Profile & Account Settings' : 'Hồ Sơ Cá Nhân & Quản Lý Tài Khoản'}</h1>
          <p class="page-subtitle">${isEn ? 'Manage your bookings, promotional vouchers, notification preferences and security settings' : 'Quản lý lịch đặt sân, kho ưu đãi, thông báo và bảo mật tài khoản cá nhân'}</p>
        </div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          <button class="btn btn-secondary btn-sm" onclick="app.switchProfileTab('security')" title="${isEn ? 'Change Password' : 'Đổi Mật Khẩu'}">
            <i class="fa-solid fa-key"></i> ${isEn ? 'Change Password' : 'Đổi Mật Khẩu'}
          </button>
          <button class="btn btn-danger btn-sm" onclick="app.logout()" style="background: #ef4444; border: none; color: #fff;">
            <i class="fa-solid fa-right-from-bracket"></i> ${isEn ? 'Log Out' : 'Đăng Xuất'}
          </button>
        </div>
      </div>

      <!-- User Identity Hero Card -->
      <div class="glass-card" style="margin-bottom: 1.5rem; padding: 1.5rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1.25rem; background: linear-gradient(135deg, #ffffff 0%, #f0fdf4 100%); border: 1.5px solid #86efac; border-radius: 16px; box-shadow: 0 4px 16px rgba(0,0,0,0.04);">
        <div style="display: flex; align-items: center; gap: 1.25rem; flex-wrap: wrap;">
          <!-- Avatar with Camera Button -->
          <div style="position: relative; cursor: pointer;" onclick="app.triggerPlayerPhotoUpload()" title="${isEn ? 'Click to change avatar photo from device' : 'Bấm để tải ảnh khuôn mặt từ thiết bị'}">
            ${isPhotoUrl ? `
              <img src="${userPhoto}" alt="${user.name}" style="width: 76px; height: 76px; border-radius: 50%; object-fit: cover; border: 3px solid #167946; box-shadow: 0 4px 14px rgba(22, 121, 70, 0.25);">
            ` : `
              <div style="width: 76px; height: 76px; border-radius: 50%; background: linear-gradient(135deg, #167946 0%, #059669 100%); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 2rem; font-weight: 800; box-shadow: 0 4px 14px rgba(22, 121, 70, 0.25);">
                ${user.avatar || user.name.charAt(0)}
              </div>
            `}
            <span style="position: absolute; bottom: 0; right: 0; background: #0284c7; color: #fff; width: 26px; height: 26px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; border: 2px solid #fff; box-shadow: 0 2px 6px rgba(0,0,0,0.2);">
              <i class="fa-solid fa-camera"></i>
            </span>
          </div>

          <!-- User Details -->
          <div>
            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
              <h2 style="margin: 0; font-size: 1.35rem; font-weight: 800; color: #0f172a;">${user.name}</h2>
              <span style="background: #fef3c7; color: #b45309; font-size: 0.75rem; font-weight: 800; padding: 3px 9px; border-radius: 9999px; border: 1px solid #fde68a;">
                ${membershipTier}
              </span>
              <span class="tier-badge-pill" style="background: ${skillTier.bg}; color: ${skillTier.color}; border: 1px solid ${skillTier.borderColor || '#cbd5e1'};">
                ${skillTier.display}
              </span>
            </div>

            <div style="font-size: 0.85rem; color: #475569; margin-top: 6px; line-height: 1.5;">
              <div>
                <i class="fa-solid fa-phone text-primary" style="width: 16px;"></i> <strong>${user.phone}</strong> • 
                <i class="fa-solid fa-envelope text-primary" style="width: 16px;"></i> <strong>${user.email || (user.phone + '@badminton.ai')}</strong> • 
                <span style="color: #167946; font-weight: 700;">${roleNames[user.role] || user.role}</span>
              </div>
              <div style="margin-top: 4px; color: #166534; font-weight: 700; display: flex; align-items: center; gap: 6px;">
                <i class="fa-solid fa-calendar-days text-primary"></i> 
                <span>${isEn ? 'Member since:' : 'Tham gia từ:'} <strong>${joinedDateStr}</strong> (${durationText})</span>
              </div>
            </div>
          </div>
        </div>

        <div style="display: flex; gap: 8px; align-items: center;">
          <button class="btn btn-outline-primary btn-sm" onclick="app.triggerPlayerPhotoUpload()" style="font-weight: 700;">
            <i class="fa-solid fa-camera"></i> ${isEn ? 'Upload Photo' : 'Đổi Ảnh Diện Mạo'}
          </button>
        </div>
      </div>

      <!-- Profile Sub-Navigation Tabs Bar -->
      <div class="profile-tabs-nav">
        <button class="profile-tab-btn ${activeTab === 'bookings' ? 'active' : ''}" onclick="app.switchProfileTab('bookings')">
          <i class="fa-solid fa-calendar-check"></i> ${isEn ? 'My Bookings' : 'Lịch Đã Đặt'}
          <span class="badge-pill">${userOrders.length}</span>
        </button>
        <button class="profile-tab-btn ${activeTab === 'vouchers' ? 'active' : ''}" onclick="app.switchProfileTab('vouchers')">
          <i class="fa-solid fa-ticket-simple"></i> ${isEn ? 'Offers & Vouchers' : 'Kho Ưu Đãi'}
          <span class="badge-pill" style="background: #ea580c; color: #fff;">4</span>
        </button>
        <button class="profile-tab-btn ${activeTab === 'notifications' ? 'active' : ''}" onclick="app.switchProfileTab('notifications')">
          <i class="fa-solid fa-bell"></i> ${isEn ? 'Notifications' : 'Thông Báo'}
        </button>
        <button class="profile-tab-btn ${activeTab === 'language' ? 'active' : ''}" onclick="app.switchProfileTab('language')">
          <i class="fa-solid fa-globe"></i> ${isEn ? 'Language: English' : 'Ngôn Ngữ: Tiếng Việt'}
        </button>
        <button class="profile-tab-btn ${activeTab === 'security' ? 'active' : ''}" onclick="app.switchProfileTab('security')">
          <i class="fa-solid fa-shield-halved"></i> ${isEn ? 'Security & Account' : 'Bảo Mật & Mật Khẩu'}
        </button>
      </div>

      <!-- Tab Content Area -->
      <div id="profile-tab-content-container">
        ${activeTab === 'bookings' ? this.renderProfileBookingsTab(userOrders, isEn) : ''}
        ${activeTab === 'vouchers' ? this.renderProfileVouchersTab(isEn) : ''}
        ${activeTab === 'notifications' ? this.renderProfileNotificationsTab(isEn) : ''}
        ${activeTab === 'language' ? this.renderProfileLanguageTab(isEn) : ''}
        ${activeTab === 'security' ? this.renderProfileSecurityTab(isEn) : ''}
      </div>
    `;
  }

  switchProfileTab(tabName) {
    this.currentProfileTab = tabName;
    this.renderUserProfilePage();
  }

  getMembershipDurationText(joinedDateStr, isEn) {
    // Expected format: DD/MM/YYYY
    const parts = joinedDateStr.split('/');
    if (parts.length === 3) {
      const joinYear = parseInt(parts[2], 10);
      const joinMonth = parseInt(parts[1], 10);
      const nowYear = 2026;
      const nowMonth = 10;
      const totalMonths = (nowYear - joinYear) * 12 + (nowMonth - joinMonth);
      if (totalMonths <= 0) {
        return isEn ? "Newly joined member" : "Thành viên mới gia nhập";
      }
      const years = Math.floor(totalMonths / 12);
      const months = totalMonths % 12;
      if (years > 0 && months > 0) {
        return isEn ? `${years} yr ${months} mos with us` : `${years} năm ${months} tháng gắn bó`;
      } else if (years > 0) {
        return isEn ? `${years} years with us` : `${years} năm gắn bó`;
      }
      return isEn ? `${months} months with us` : `${months} tháng gắn bó`;
    }
    return isEn ? "Active member" : "Hội viên tích cực";
  }

  renderProfileBookingsTab(userOrders, isEn) {
    if (!userOrders || userOrders.length === 0) {
      return `
        <div class="glass-card" style="text-align: center; padding: 3rem 1.5rem; background: #ffffff;">
          <div style="width: 64px; height: 64px; border-radius: 50%; background: #f0fdf4; color: #167946; display: flex; align-items: center; justify-content: center; font-size: 1.8rem; margin: 0 auto 1rem;">
            <i class="fa-solid fa-calendar-xmark"></i>
          </div>
          <h3 style="margin: 0 0 6px; font-size: 1.15rem; color: #0f172a;">${isEn ? 'No bookings found' : 'Bạn chưa có lịch đặt sân nào'}</h3>
          <p style="color: #64748b; font-size: 0.88rem; max-width: 420px; margin: 0 auto 1.5rem;">
            ${isEn ? 'Book badminton courts quickly with real-time slot booking and AI matchmaking!' : 'Đặt sân cầu lông thông minh, giữ chỗ ngay lập tức và tham gia ghép kèo cùng đối thủ!'}
          </p>
          <button class="btn btn-primary" onclick="app.navigateTo('ui-02')" style="padding: 10px 24px; font-weight: 700;">
            <i class="fa-solid fa-calendar-plus"></i> ${isEn ? 'Book a Court Now' : 'Đặt Sân Giữ Chỗ Ngay'}
          </button>
        </div>
      `;
    }

    let itemsHtml = '';
    userOrders.forEach(o => {
      const isConfirmed = o.order_status === "Đã Xác Nhận";
      itemsHtml += `
        <div class="profile-booking-item">
          <div style="display: flex; gap: 14px; align-items: center;">
            <div style="width: 50px; height: 50px; border-radius: 12px; background: #f0fdf4; color: #167946; display: flex; align-items: center; justify-content: center; font-size: 1.4rem; border: 1.5px solid #86efac; flex-shrink: 0;">
              🏸
            </div>
            <div>
              <div style="display: flex; align-items: center; gap: 8px;">
                <strong style="color: #0f172a; font-size: 1rem;">${o.booking_code}</strong>
                <span class="badge ${isConfirmed ? 'badge-success' : 'badge-warning'}" style="font-size: 0.72rem; padding: 2px 8px;">
                  ${o.order_status}
                </span>
                <span style="font-size: 0.75rem; background: #e0f2fe; color: #0369a1; padding: 2px 8px; border-radius: 6px; font-weight: 700;">
                  ${o.deposit_status || 'Đã Cọc 50K'}
                </span>
              </div>
              <div style="font-size: 0.85rem; color: #475569; margin-top: 4px;">
                <strong>${o.facility_name}</strong> • ${o.court_name}
              </div>
              <div style="font-size: 0.8rem; color: #64748b; margin-top: 2px;">
                <i class="fa-solid fa-clock text-amber"></i> ${o.slot_time} | 
                <i class="fa-solid fa-calendar text-primary"></i> ${o.booking_date} | 
                <i class="fa-solid fa-money-bill-wave text-emerald"></i> <strong>${o.total_amount.toLocaleString('vi-VN')}đ</strong>
              </div>
            </div>
          </div>

          <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <button class="btn btn-primary btn-sm" onclick="app.openBookingTicketModal('${o.booking_code}')" style="font-size: 0.8rem; padding: 6px 12px; background: #167946; font-weight: 700;">
              <i class="fa-solid fa-qrcode"></i> ${isEn ? 'View QR Ticket' : 'Xem Vé QR'}
            </button>
            <button class="btn btn-secondary btn-sm" onclick="app.navigateTo('ui-02'); app.showToast('${isEn ? 'Selected facility: ' : 'Đã chọn cụm sân: '} ${o.facility_name}')" style="font-size: 0.8rem; padding: 6px 12px;">
              <i class="fa-solid fa-rotate-right"></i> ${isEn ? 'Book Again' : 'Đặt Lại'}
            </button>
          </div>
        </div>
      `;
    });

    return `
      <div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
          <h3 style="margin: 0; font-size: 1.1rem; color: #0f172a;">
            <i class="fa-solid fa-list-check text-primary"></i> ${isEn ? 'Your Court Booking History' : 'Danh Sách Lịch Đã Đặt Sân Của Bạn'}
          </h3>
          <button class="btn btn-primary btn-sm" onclick="app.navigateTo('ui-02')">
            <i class="fa-solid fa-plus"></i> ${isEn ? 'New Booking' : 'Đặt Sân Mới'}
          </button>
        </div>
        ${itemsHtml}
      </div>
    `;
  }

  renderProfileVouchersTab(isEn) {
    const vouchers = [
      {
        code: "BADMINTONAI20",
        discount: isEn ? "20% OFF Prime Hours" : "Giảm 20% Đặt Sân Giờ Vàng",
        desc: isEn ? "Applicable for slots from 18:00 to 20:00 every weekday" : "Áp dụng cho khung giờ vàng 18:00 - 20:00 các ngày trong tuần",
        expiry: "30/11/2026",
        badge: isEn ? "HOT DISCOUNT" : "GIỜ VÀNG",
        color: "#16a34a",
        bg: "#f0fdf4"
      },
      {
        code: "WELCOME30K",
        discount: isEn ? "30,000 VND OFF First Booking" : "Giảm 30.000đ Đơn Đầu Tiên",
        desc: isEn ? "Applicable for orders with minimum value of 100,000 VND" : "Áp dụng cho mọi đơn đặt sân có giá trị từ 100.000đ",
        expiry: "31/12/2026",
        badge: isEn ? "NEW MEMBER" : "CHÀO BẠN MỚI",
        color: "#0284c7",
        bg: "#f0f9ff"
      },
      {
        code: "FREEWATER",
        discount: isEn ? "Free 02 Revive Drinks" : "Tặng 02 Chai Nước Revive",
        desc: isEn ? "Receive 2 bottles of cold Revive drink upon successful Matchmaking check-in" : "Nhận ngay 2 chai nước khoáng thể thao Revive khi ghép kèo thành công",
        expiry: isEn ? "Permanent" : "Vĩnh viễn",
        badge: isEn ? "MATCHMAKING" : "GHÉP KÈO",
        color: "#9333ea",
        bg: "#faf5ff"
      },
      {
        code: "VIPYONEX15",
        discount: isEn ? "15% OFF Racket & Shuttlecocks" : "Giảm 15% Thuê Vợt & Mua Cầu",
        desc: isEn ? "Discount on court-side pro gear rental and Yonex shuttles" : "Ưu đãi trực tiếp khi thuê vợt thi đấu Yonex hoặc mua ống cầu tại quầy lễ tân",
        expiry: "30/10/2026",
        badge: isEn ? "PRO GEAR" : "PHỤ KIỆN",
        color: "#ea580c",
        bg: "#fff7ed"
      }
    ];

    let vHtml = '';
    vouchers.forEach(v => {
      vHtml += `
        <div class="profile-voucher-card" style="background: ${v.bg};">
          <span class="profile-voucher-badge">${v.badge}</span>
          <div>
            <div style="font-size: 0.78rem; font-weight: 800; color: ${v.color}; text-transform: uppercase;">
              ${isEn ? 'VOUCHER BADMINTON.AI' : 'ƯU ĐÃI ĐỘC QUYỀN'}
            </div>
            <h4 style="margin: 4px 0 6px; font-size: 1.15rem; color: #0f172a; font-weight: 800;">${v.discount}</h4>
            <p style="margin: 0; font-size: 0.82rem; color: #475569; line-height: 1.5;">${v.desc}</p>
          </div>

          <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px dashed #cbd5e1; padding-top: 10px; margin-top: 6px;">
            <div>
              <div style="font-size: 0.72rem; color: #64748b;">${isEn ? 'Expiry date:' : 'Hạn sử dụng:'} <strong>${v.expiry}</strong></div>
              <code style="font-size: 0.95rem; font-weight: 900; color: ${v.color}; letter-spacing: 0.8px;">${v.code}</code>
            </div>
            <div style="display: flex; gap: 6px;">
              <button class="btn btn-sm btn-outline-primary" onclick="app.copyVoucherCode('${v.code}')" style="font-size: 0.78rem; padding: 4px 10px; font-weight: 700;">
                <i class="fa-solid fa-copy"></i> ${isEn ? 'Copy' : 'Sao Chép'}
              </button>
              <button class="btn btn-sm btn-primary" onclick="app.navigateTo('ui-02'); app.showToast('${isEn ? 'Applied code: ' : 'Đã áp dụng mã: '} ${v.code}')" style="font-size: 0.78rem; padding: 4px 10px; background: ${v.color}; border: none; font-weight: 700;">
                ${isEn ? 'Use Now' : 'Dùng Ngay'}
              </button>
            </div>
          </div>
        </div>
      `;
    });

    return `
      <div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
          <div>
            <h3 style="margin: 0; font-size: 1.1rem; color: #0f172a;">
              <i class="fa-solid fa-gift text-primary"></i> ${isEn ? 'Your Active Discounts & Vouchers' : 'Kho Mã Khuyến Mãi & Voucher Ưu Đãi Của Bạn'}
            </h3>
            <p style="margin: 2px 0 0; font-size: 0.82rem; color: #64748b;">
              ${isEn ? 'Copy voucher code and apply during court checkout to save money' : 'Sao chép mã ưu đãi và áp dụng khi thanh toán đặt sân để tiết kiệm chi phí'}
            </p>
          </div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 14px;">
          ${vHtml}
        </div>
      </div>
    `;
  }

  renderProfileNotificationsTab(isEn) {
    const user = this.currentUser;
    const notis = user.notifications || { reminder: true, matchmaking: true, promos: true, system: true };

    return `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px;">
        <!-- Notification Preferences -->
        <div class="glass-card" style="padding: 1.25rem; background: #ffffff;">
          <h3 style="margin: 0 0 1rem; font-size: 1.1rem; color: #0f172a; display: flex; align-items: center; gap: 8px;">
            <i class="fa-solid fa-sliders text-primary"></i> ${isEn ? 'Notification Settings' : 'Cài Đặt Nhận Thông Báo'}
          </h3>

          <div style="display: flex; flex-direction: column; gap: 14px;">
            <!-- Switch 1: Booking reminder -->
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <div>
                <strong style="font-size: 0.9rem; color: #0f172a;">${isEn ? '⏰ Court Booking Reminder' : '⏰ Nhắc Lịch Ra Sân Trước 60 Phút'}</strong>
                <div style="font-size: 0.78rem; color: #64748b;">${isEn ? 'Receive automated alerts 1 hour before scheduled match time' : 'Hệ thống tự động nhắc nhở giờ thi đấu trước khi bóng lăn'}</div>
              </div>
              <label class="profile-toggle-switch">
                <input type="checkbox" ${notis.reminder ? 'checked' : ''} onchange="app.toggleNotificationPref('reminder')">
                <span class="profile-toggle-slider"></span>
              </label>
            </div>

            <!-- Switch 2: Matchmaking alerts -->
            <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #f1f5f9; padding-top: 12px;">
              <div>
                <strong style="font-size: 0.9rem; color: #0f172a;">${isEn ? '🏸 AI Matchmaking Invitations' : '🏸 Lời Mời Ghép Kèo & Đối Thủ Mới'}</strong>
                <div style="font-size: 0.78rem; color: #64748b;">${isEn ? 'Alerts when players with balanced skill challenge or join your room' : 'Thông báo khi có bạn chơi cùng cấp bậc mời giao lưu hoặc vào phòng'}</div>
              </div>
              <label class="profile-toggle-switch">
                <input type="checkbox" ${notis.matchmaking ? 'checked' : ''} onchange="app.toggleNotificationPref('matchmaking')">
                <span class="profile-toggle-slider"></span>
              </label>
            </div>

            <!-- Switch 3: Promotions -->
            <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #f1f5f9; padding-top: 12px;">
              <div>
                <strong style="font-size: 0.9rem; color: #0f172a;">${isEn ? '🎁 Exclusive Discounts & Golden Hours' : '🎁 Khuyến Mãi & Giờ Vàng Giảm Giá'}</strong>
                <div style="font-size: 0.78rem; color: #64748b;">${isEn ? 'Get notified when new promo vouchers or discounted slots drop' : 'Nhận thông báo mã voucher mới và các khung giờ giảm giá đặc biệt'}</div>
              </div>
              <label class="profile-toggle-switch">
                <input type="checkbox" ${notis.promos ? 'checked' : ''} onchange="app.toggleNotificationPref('promos')">
                <span class="profile-toggle-slider"></span>
              </label>
            </div>

            <!-- Switch 4: System updates -->
            <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #f1f5f9; padding-top: 12px;">
              <div>
                <strong style="font-size: 0.9rem; color: #0f172a;">${isEn ? '📋 Order & Refund Confirmations' : '📋 Xác Nhận Đặt Sân & Hoàn Cọc'}</strong>
                <div style="font-size: 0.78rem; color: #64748b;">${isEn ? 'Real-time billing, VietQR payment confirmation and refund updates' : 'Thông báo trạng thái thanh toán VietQR và cập nhật biên lai điện tử'}</div>
              </div>
              <label class="profile-toggle-switch">
                <input type="checkbox" ${notis.system ? 'checked' : ''} onchange="app.toggleNotificationPref('system')">
                <span class="profile-toggle-slider"></span>
              </label>
            </div>
          </div>
        </div>

        <!-- Recent Notification Feed -->
        <div class="glass-card" style="padding: 1.25rem; background: #ffffff;">
          <h3 style="margin: 0 0 1rem; font-size: 1.1rem; color: #0f172a; display: flex; align-items: center; gap: 8px;">
            <i class="fa-solid fa-inbox text-primary"></i> ${isEn ? 'Recent Messages' : 'Hộp Thư Thông Báo Gần Nhất'}
          </h3>

          <div style="display: flex; flex-direction: column; gap: 10px;">
            <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 10px; padding: 10px 12px;">
              <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #166534; font-weight: 700;">
                <span><i class="fa-solid fa-circle-check"></i> ${isEn ? 'Booking Confirmed' : 'Đặt Sân Thành Công'}</span>
                <span>${isEn ? '10 mins ago' : '10 phút trước'}</span>
              </div>
              <div style="font-size: 0.82rem; color: #0f172a; margin-top: 2px;">
                ${isEn ? 'Your slot at Catchy Badminton Arena (Court 02, 18:00 - 19:30) is confirmed! QR check-in ready.' : 'Đơn đặt sân BK-20261005-088 tại Catchy Badminton Arena đã được xác nhận. Mã QR check-in đã sẵn sàng.'}
              </div>
            </div>

            <div style="background: #eff6ff; border: 1px solid #93c5fd; border-radius: 10px; padding: 10px 12px;">
              <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #1d4ed8; font-weight: 700;">
                <span><i class="fa-solid fa-users"></i> ${isEn ? 'AI Matchmaking Alert' : 'Ghép Kèo Cân Bậc'}</span>
                <span>${isEn ? '1 hour ago' : '1 giờ trước'}</span>
              </div>
              <div style="font-size: 0.82rem; color: #0f172a; margin-top: 2px;">
                ${isEn ? 'Found 3 players of your exact skill rank looking for doubles partners nearby!' : 'AI đã quét thấy 3 tay vợt cùng cấp bậc [Khá] đang mở phòng giao lưu tại khu vực Hoàng Mai!'}
              </div>
            </div>

            <div style="background: #fdf4ff; border: 1px solid #f0abfc; border-radius: 10px; padding: 10px 12px;">
              <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #a21caf; font-weight: 700;">
                <span><i class="fa-solid fa-gift"></i> ${isEn ? 'New Voucher Received' : 'Quà Tặng Hội Viên'}</span>
                <span>${isEn ? 'Yesterday' : 'Hôm qua'}</span>
              </div>
              <div style="font-size: 0.82rem; color: #0f172a; margin-top: 2px;">
                ${isEn ? 'You received code BADMINTONAI20 offering 20% discount on prime-hour bookings!' : 'Bạn nhận được mã ưu đãi BADMINTONAI20 giảm 20% cho các lượt đặt sân giờ vàng!'}
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  renderProfileLanguageTab(isEn) {
    return `
      <div class="glass-card" style="padding: 1.5rem; background: #ffffff; max-width: 600px; margin: 0 auto;">
        <h3 style="margin: 0 0 6px; font-size: 1.15rem; color: #0f172a; display: flex; align-items: center; gap: 8px;">
          <i class="fa-solid fa-language text-primary"></i> ${isEn ? 'Display Language Settings' : 'Cài Đặt Ngôn Ngữ Hiển Thị'}
        </h3>
        <p style="color: #64748b; font-size: 0.84rem; margin-bottom: 1.5rem;">
          ${isEn ? 'Choose your preferred language for the badminton booking platform' : 'Chọn ngôn ngữ giao diện ưa thích của bạn cho ứng dụng đặt sân cầu lông'}
        </p>

        <div style="display: flex; flex-direction: column; gap: 12px; margin-bottom: 1.5rem;">
          <!-- Option 1: Vietnamese -->
          <div class="profile-lang-card ${!isEn ? 'active' : ''}" onclick="app.setAppLanguage('vi')">
            <div style="display: flex; align-items: center; gap: 12px;">
              <span style="font-size: 1.8rem;">🇻🇳</span>
              <div>
                <strong style="color: #0f172a; font-size: 0.95rem;">Tiếng Việt (Vietnamese)</strong>
                <div style="font-size: 0.78rem; color: #64748b;">Ngôn ngữ mặc định cho toàn bộ cụm sân tại Việt Nam</div>
              </div>
            </div>
            ${!isEn ? `<span style="color: #167946; font-size: 1.2rem;"><i class="fa-solid fa-circle-check"></i></span>` : `<span style="color: #cbd5e1; font-size: 1.2rem;"><i class="fa-regular fa-circle"></i></span>`}
          </div>

          <!-- Option 2: English -->
          <div class="profile-lang-card ${isEn ? 'active' : ''}" onclick="app.setAppLanguage('en')">
            <div style="display: flex; align-items: center; gap: 12px;">
              <span style="font-size: 1.8rem;">🇬🇧</span>
              <div>
                <strong style="color: #0f172a; font-size: 0.95rem;">English (Tiếng Anh)</strong>
                <div style="font-size: 0.78rem; color: #64748b;">International language support for foreign players</div>
              </div>
            </div>
            ${isEn ? `<span style="color: #167946; font-size: 1.2rem;"><i class="fa-solid fa-circle-check"></i></span>` : `<span style="color: #cbd5e1; font-size: 1.2rem;"><i class="fa-regular fa-circle"></i></span>`}
          </div>
        </div>

        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px; font-size: 0.8rem; color: #475569;">
          💡 <strong>${isEn ? 'Note:' : 'Ghi chú:'}</strong> ${isEn ? 'Language preference is automatically synced and stored in your device storage.' : 'Lựa chọn ngôn ngữ được lưu tự động trên thiết bị của bạn và giữ nguyên cho các lần truy cập tiếp theo.'}
        </div>
      </div>
    `;
  }

  renderProfileSecurityTab(isEn) {
    return `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px;">
        <!-- Change Password Form -->
        <div class="glass-card" style="padding: 1.5rem; background: #ffffff;">
          <h3 style="margin: 0 0 6px; font-size: 1.15rem; color: #0f172a; display: flex; align-items: center; gap: 8px;">
            <i class="fa-solid fa-key text-primary"></i> ${isEn ? 'Change Password' : 'Đổi Mật Khẩu Tài Khoản'}
          </h3>
          <p style="color: #64748b; font-size: 0.82rem; margin-bottom: 1.25rem;">
            ${isEn ? 'Ensure your account stays secure by using a strong password' : 'Bảo vệ tài khoản và lịch đặt sân bằng mật khẩu bảo mật'}
          </p>

          <form onsubmit="app.handleChangePassword(event)">
            <div class="form-group">
              <label class="form-label">${isEn ? 'Current Password' : 'Mật Khẩu Hiện Tại'}</label>
              <input type="password" id="profile-current-password" class="form-control" placeholder="••••••••" required>
            </div>

            <div class="form-group">
              <label class="form-label">${isEn ? 'New Password (min 6 characters)' : 'Mật Khẩu Mới (Tối thiểu 6 ký tự)'}</label>
              <input type="password" id="profile-new-password" class="form-control" placeholder="••••••••" minlength="6" required>
            </div>

            <div class="form-group">
              <label class="form-label">${isEn ? 'Confirm New Password' : 'Xác Nhận Mật Khẩu Mới'}</label>
              <input type="password" id="profile-confirm-password" class="form-control" placeholder="••••••••" minlength="6" required>
            </div>

            <button type="submit" class="btn btn-primary" style="width: 100%; margin-top: 0.5rem; font-weight: 700;">
              <i class="fa-solid fa-circle-check"></i> ${isEn ? 'Save New Password' : 'Cập Nhật Mật Khẩu Mới'}
            </button>
          </form>
        </div>

        <!-- Account Actions & Danger Zone -->
        <div class="glass-card" style="padding: 1.5rem; background: #ffffff;">
          <h3 style="margin: 0 0 6px; font-size: 1.15rem; color: #0f172a; display: flex; align-items: center; gap: 8px;">
            <i class="fa-solid fa-user-shield text-primary"></i> ${isEn ? 'Account Actions' : 'Thao Tác Tài Khoản'}
          </h3>
          <p style="color: #64748b; font-size: 0.82rem; margin-bottom: 1.25rem;">
            ${isEn ? 'Quick log out or account management options' : 'Các tùy chọn đăng xuất hoặc xóa dữ liệu tài khoản cá nhân'}
          </p>

          <!-- Log Out Card -->
          <div style="background: #f8fafc; border: 1.5px solid #e2e8f0; border-radius: 12px; padding: 14px; margin-bottom: 1.25rem; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <strong style="color: #0f172a; font-size: 0.95rem;">${isEn ? 'Log Out of Account' : 'Đăng Xuất Khỏi Tài Khoản'}</strong>
              <div style="font-size: 0.78rem; color: #64748b;">${isEn ? 'Sign out from this device safely' : 'Đăng xuất an toàn trên thiết bị này'}</div>
            </div>
            <button class="btn btn-danger btn-sm" onclick="app.logout()" style="background: #ef4444; border: none; font-weight: 700;">
              <i class="fa-solid fa-right-from-bracket"></i> ${isEn ? 'Log Out' : 'Đăng Xuất'}
            </button>
          </div>

          <!-- Danger Zone: Delete Account -->
          <div class="profile-danger-zone">
            <div style="display: flex; gap: 10px; align-items: flex-start; margin-bottom: 10px;">
              <div style="color: #dc2626; font-size: 1.3rem; line-height: 1;">
                <i class="fa-solid fa-triangle-exclamation"></i>
              </div>
              <div>
                <strong style="color: #991b1b; font-size: 0.95rem;">${isEn ? 'Danger Zone: Delete Account' : 'Vùng Nguy Hiểm: Xóa Tài Khoản'}</strong>
                <p style="margin: 4px 0 0; font-size: 0.8rem; color: #b91c1c; line-height: 1.5;">
                  ${isEn ? 'Permanently delete your account, booking records, and vouchers. This action cannot be reversed!' : 'Xóa vĩnh viễn tài khoản của bạn cùng lịch sử đặt sân và ưu đãi tích lũy. Hành động này không thể hoàn tác!'}
                </p>
              </div>
            </div>
            <div style="text-align: right;">
              <button class="btn btn-danger btn-sm" onclick="app.confirmDeleteAccount()" style="background: #dc2626; font-weight: 800; border: none;">
                <i class="fa-solid fa-trash-can"></i> ${isEn ? 'Delete My Account' : 'Xóa Tài Khoản Của Tôi'}
              </button>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  copyVoucherCode(code) {
    if (navigator && navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(code).catch(() => {});
    }
    const isEn = (localStorage.getItem('badminton_app_language') || this.currentLanguage) === 'en';
    this.showToast(isEn ? `📋 Copied voucher code [${code}] to clipboard!` : `📋 Đã sao chép mã ưu đãi [${code}] vào bộ nhớ tạm! Dán mã khi đặt sân để được giảm giá.`);
  }

  toggleNotificationPref(type) {
    if (!this.currentUser) return;
    if (!this.currentUser.notifications) {
      this.currentUser.notifications = { reminder: true, matchmaking: true, promos: true, system: true };
    }
    this.currentUser.notifications[type] = !this.currentUser.notifications[type];

    const u = (MockData.users || []).find(x => x.id === this.currentUser.id || x.phone === this.currentUser.phone);
    if (u) {
      if (!u.notifications) u.notifications = { reminder: true, matchmaking: true, promos: true, system: true };
      u.notifications[type] = this.currentUser.notifications[type];
    }

    if (typeof saveMockDataToLocalStorage === 'function') {
      saveMockDataToLocalStorage();
    }

    const isEn = (localStorage.getItem('badminton_app_language') || this.currentLanguage) === 'en';
    const statusText = this.currentUser.notifications[type] ? (isEn ? "Enabled" : "Đã bật") : (isEn ? "Disabled" : "Đã tắt");
    this.showToast(`🔔 ${statusText} ${isEn ? 'notification successfully!' : 'thông báo thành công!'}`);
  }

  setAppLanguage(lang) {
    this.currentLanguage = lang;
    localStorage.setItem('badminton_app_language', lang);
    if (this.currentUser) {
      this.currentUser.language = lang;
      const u = (MockData.users || []).find(x => x.id === this.currentUser.id || x.phone === this.currentUser.phone);
      if (u) u.language = lang;
    }
    if (typeof saveMockDataToLocalStorage === 'function') {
      saveMockDataToLocalStorage();
    }
    this.renderUserProfilePage();
    if (lang === 'en') {
      this.showToast("🇬🇧 Language changed to English successfully!");
    } else {
      this.showToast("🇻🇳 Đã chuyển ngôn ngữ sang Tiếng Việt thành công!");
    }
  }

  handleChangePassword(e) {
    if (e && e.preventDefault) e.preventDefault();
    if (!this.currentUser) return;

    const isEn = (localStorage.getItem('badminton_app_language') || this.currentLanguage) === 'en';
    const currentPass = document.getElementById('profile-current-password')?.value.trim();
    const newPass = document.getElementById('profile-new-password')?.value.trim();
    const confirmPass = document.getElementById('profile-confirm-password')?.value.trim();

    if (!currentPass || !newPass || !confirmPass) {
      this.showToast(isEn ? "⚠️ Please fill in all password fields!" : "⚠️ Vui lòng nhập đầy đủ thông tin mật khẩu!", "error");
      return;
    }

    if (currentPass !== this.currentUser.password) {
      this.showToast(isEn ? "❌ Current password is incorrect!" : "❌ Mật khẩu hiện tại không chính xác! Vui lòng thử lại.", "error");
      return;
    }

    if (newPass.length < 6) {
      this.showToast(isEn ? "⚠️ New password must be at least 6 characters!" : "⚠️ Mật khẩu mới phải có tối thiểu 6 ký tự!", "error");
      return;
    }

    if (newPass !== confirmPass) {
      this.showToast(isEn ? "❌ New password and confirmation do not match!" : "❌ Mật khẩu mới và xác nhận mật khẩu không trùng khớp!", "error");
      return;
    }

    this.currentUser.password = newPass;
    const u = (MockData.users || []).find(x => x.id === this.currentUser.id || x.phone === this.currentUser.phone);
    if (u) u.password = newPass;

    if (typeof saveMockDataToLocalStorage === 'function') {
      saveMockDataToLocalStorage();
    }

    this.showToast(isEn ? "🎉 Password updated successfully! Please remember your new password." : "🎉 Đổi mật khẩu tài khoản thành công! Hãy ghi nhớ mật khẩu mới của bạn.");
    this.renderUserProfilePage();
  }

  confirmDeleteAccount() {
    if (!this.currentUser) return;
    const modalBody = document.getElementById('modal-body');
    if (!modalBody) return;

    const isEn = (localStorage.getItem('badminton_app_language') || this.currentLanguage) === 'en';

    modalBody.innerHTML = `
      <div style="padding: 1rem 0; text-align: center;">
        <div style="width: 68px; height: 68px; border-radius: 50%; background: #fee2e2; color: #dc2626; display: flex; align-items: center; justify-content: center; font-size: 2rem; margin: 0 auto 1rem; border: 2px dashed #fca5a5;">
          <i class="fa-solid fa-triangle-exclamation"></i>
        </div>
        <h3 style="margin: 0 0 8px; color: #991b1b; font-size: 1.25rem; font-weight: 800;">
          ${isEn ? 'Permanently Delete Account?' : 'Xác Nhận Xóa Vĩnh Viễn Tài Khoản?'}
        </h3>
        <p style="color: #64748b; font-size: 0.88rem; line-height: 1.6; max-width: 420px; margin: 0 auto 1.25rem;">
          ${isEn ? `Warning: This action <strong>CANNOT BE UNDONE</strong>. All account details for <strong>${this.currentUser.name}</strong> (${this.currentUser.phone}), booking history, and active vouchers will be permanently removed!` : `Cảnh báo: Hành động này <strong>KHÔNG THỂ HOÀN TÁC</strong>. Toàn bộ thông tin tài khoản của <strong>${this.currentUser.name}</strong> (${this.currentUser.phone}), lịch sử đặt sân và voucher ưu đãi sẽ bị xóa vĩnh viễn khỏi hệ thống!`}
        </p>

        <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 10px; padding: 12px; margin-bottom: 1.25rem; text-align: left; font-size: 0.82rem; color: #991b1b;">
          <div>• ${isEn ? 'All active bookings will be cancelled.' : 'Các lượt đặt sân hiện tại sẽ bị hủy bỏ.'}</div>
          <div>• ${isEn ? 'All membership rewards and vouchers will be forfeited.' : 'Toàn bộ điểm tích lũy và voucher ưu đãi sẽ mất hiệu lực.'}</div>
        </div>

        <div style="display: flex; gap: 10px; justify-content: center;">
          <button class="btn btn-secondary" onclick="app.closeModal()">${isEn ? 'Cancel (Keep Account)' : 'Hủy Bỏ (Giữ Tài Khoản)'}</button>
          <button class="btn btn-danger" onclick="app.executeDeleteAccount()" style="background: #dc2626; font-weight: 800;">
            <i class="fa-solid fa-trash-can"></i> ${isEn ? 'Confirm Delete' : 'Xác Nhận Xóa Vĩnh Viễn'}
          </button>
        </div>
      </div>
    `;
    this.openModal();
  }

  executeDeleteAccount() {
    if (!this.currentUser) return;
    const deletedName = this.currentUser.name;
    const deletedId = this.currentUser.id;

    // Remove from MockData.users
    MockData.users = (MockData.users || []).filter(u => u.id !== deletedId && u.phone !== this.currentUser.phone);

    if (typeof saveMockDataToLocalStorage === 'function') {
      saveMockDataToLocalStorage();
    }

    this.closeModal();
    this.logout();
    this.showToast(`🗑️ Đã xóa vĩnh viễn tài khoản của "${deletedName}" khỏi hệ thống thành công!`, 'info');
  }

  openBookingTicketModal(bookingCode) {
    const order = (MockData.booking_orders || []).find(o => o.booking_code === bookingCode);
    if (!order) {
      this.navigateTo('ui-05');
      return;
    }
    const modalBody = document.getElementById('modal-body');
    if (!modalBody) return;

    modalBody.innerHTML = `
      <div style="padding: 0.5rem 0; text-align: center;">
        <h3 style="margin: 0 0 6px; color: #0f172a; font-size: 1.25rem; display: flex; align-items: center; justify-content: center; gap: 8px;">
          <i class="fa-solid fa-ticket text-primary"></i> Vé Điện Tử Check-in Quầy Sân
        </h3>
        <p style="color: #64748b; font-size: 0.84rem; margin-bottom: 1.25rem;">Xuất trình mã QR này cho nhân viên lễ tân khi đến sân để vào sân đúng giờ</p>

        <div style="background: #ffffff; border: 2px dashed #167946; border-radius: 16px; padding: 1.5rem; max-width: 360px; margin: 0 auto; box-shadow: 0 8px 24px rgba(0,0,0,0.06);">
          <div style="width: 170px; height: 170px; margin: 0 auto 1rem; border-radius: 12px; overflow: hidden; border: 2px solid #86efac; padding: 6px; background: #fff;">
            <img src="https://api.qrserver.com/v1/create-qr-code/?size=170x170&data=${order.qr_ticket_code}" alt="QR Ticket" style="width: 100%; height: 100%; object-fit: contain;">
          </div>
          
          <div style="font-size: 1.1rem; font-weight: 900; color: #167946; margin-bottom: 6px;">
            ${order.booking_code}
          </div>
          <div style="font-size: 0.85rem; color: #0f172a; font-weight: 700; margin-bottom: 4px;">
            ${order.facility_name}
          </div>
          <div style="font-size: 0.82rem; color: #475569;">
            ${order.court_name} • <strong style="color: #0284c7;">${order.slot_time}</strong>
          </div>
          <div style="font-size: 0.82rem; color: #64748b; margin-top: 2px;">
            Ngày chơi: <strong>${order.booking_date}</strong>
          </div>
          <div style="margin-top: 10px; padding: 6px 12px; background: #f0fdf4; border-radius: 8px; font-size: 0.8rem; color: #166534; font-weight: 700;">
            Trạng thái: ${order.order_status} (${order.deposit_status || 'Đã Cọc 50K'})
          </div>
        </div>

        <div style="margin-top: 1.25rem; display: flex; gap: 8px; justify-content: center;">
          <button class="btn btn-secondary btn-sm" onclick="app.closeModal()">Đóng Cửa Sổ</button>
          <button class="btn btn-primary btn-sm" onclick="window.print()" style="background: #167946;">
            <i class="fa-solid fa-print"></i> In / Lưu Vé
          </button>
        </div>
      </div>
    `;
    this.openModal();
  }

  handleHeaderProfileClick() {
    if (this.currentUser) {
      this.navigateTo('ui-08');
    } else {
      this.navigateTo('ui-01');
      this.showToast('ℹ️ Vui lòng Đăng Nhập hoặc Đăng Ký tài khoản để xem thông tin cá nhân!', 'info');
    }
  }

  initSplashScreen() {
    const splash = document.getElementById('app-splash-screen');
    if (splash) {
      setTimeout(() => {
        splash.classList.add('fade-out');
        setTimeout(() => {
          splash.style.display = 'none';
        }, 500);
      }, 1200);
    }
  }

  /* ------------------------------------------------------------------------
     1. NAVIGATION & ROLE SWITCHING
     ------------------------------------------------------------------------ */
  switchRole(role, targetUserObject = null) {
    // If a target user object is explicitly passed (e.g. from handleLogin or handleRegister)
    if (targetUserObject) {
      this.currentUser = targetUserObject;
      this.currentRole = role;
    } else {
      // If user is currently logged in, enforce that their user role matches the target role!
      if (this.currentUser && this.currentUser.role !== role) {
        const roleNames = {
          'CUSTOMER': 'Khách Hàng',
          'OWNER': 'Chủ Sân',
          'STAFF': 'Thu Ngân',
          'ADMIN': 'Quản Trị Viên'
        };
        const currentRoleName = roleNames[this.currentUser.role] || this.currentUser.role;
        const targetRoleName = roleNames[role] || role;

        this.showToast(`⛔ Quyền truy cập bị từ chối! Tài khoản "${this.currentUser.name}" hiện tại có vai trò [${currentRoleName}], không thể truy cập phân hệ [${targetRoleName}]. Vui lòng Đăng Xuất trước!`, 'error');
        return false;
      }

      // If no user is logged in and tries to switch to non-CUSTOMER role:
      // Require real login instead of silently assigning a demo account!
      if (!this.currentUser && role !== 'CUSTOMER') {
        const roleNames = {
          'OWNER': 'Chủ Sân',
          'STAFF': 'Thu Ngân',
          'ADMIN': 'Quản Trị Viên'
        };
        const targetRoleName = roleNames[role] || role;
        this.showToast(`🔒 Phân hệ [${targetRoleName}] yêu cầu đăng nhập tài khoản có thẩm quyền!`, 'info');
        if (typeof this.selectLoginRole === 'function') {
          this.selectLoginRole(role, false);
        }
        this.navigateTo('ui-01');
        return false;
      }
      this.currentRole = role;
    }

    if (this.currentUser && this.currentUser.is_approved === false) {
      if (role === 'STAFF') {
        this.showToast(`⛔ Đăng nhập thất bại: Tài khoản Thu Ngân (${this.currentUser.name}) đang CHỜ CHỦ SÂN PHÊ DUYỆT!`, 'error');
        return false;
      }
      if (role === 'OWNER') {
        this.showToast(`⛔ Đăng nhập thất bại: Tài khoản Chủ Sân (${this.currentUser.name}) đang CHỜ QUẢN TRỊ VIÊN (ADMIN) PHÊ DUYỆT!`, 'error');
        return false;
      }
    }
    
    // Update Role Switcher Buttons UI
    document.querySelectorAll('.role-btn').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.getElementById(`role-btn-${role.toLowerCase()}`);
    if (activeBtn) activeBtn.classList.add('active');

    // Update Header Avatar, Name & Auth Buttons
    this.updateHeaderUserUI();

    // Update Sidebar Navigation according to Role & Auth state
    this.renderSidebarNav();

    // Default view routing per role
    const defaultRoleViewMap = {
      'CUSTOMER': 'ui-02',
      'OWNER': 'ui-09',
      'STAFF': 'ui-15',
      'ADMIN': 'ui-17'
    };
    this.navigateTo(defaultRoleViewMap[role]);
    return true;
  }

  logout() {
    this.currentUser = null;
    this.currentRole = 'CUSTOMER';
    this.updateHeaderUserUI();

    document.querySelectorAll('.role-btn').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.getElementById('role-btn-customer');
    if (activeBtn) activeBtn.classList.add('active');

    this.renderSidebarNav();
    this.navigateTo('ui-02');
    this.showToast('👋 Đã đăng xuất khỏi hệ thống! Giao diện đã chuyển về chế độ Khách vãng lai.');
  }

  renderSidebarNav() {
    const navList = document.getElementById('sidebar-nav-list');
    const titleEl = document.getElementById('sidebar-role-title');

    const navMenus = {
      'CUSTOMER': {
        title: 'PHÂN HỆ KHÁCH HÀNG',
        items: [
          { id: 'ui-02', icon: 'fa-compass', text: 'Tìm Kiếm Sân AI' },
          { id: 'ui-map', icon: 'fa-map-location-dot', text: 'Bản Đồ Thể Thao GPS' },
          { id: 'ui-trending', icon: 'fa-fire', text: 'Sự Kiện & Nổi Bật' },
          { id: 'ui-03', icon: 'fa-calendar-days', text: 'Đặt Sân & Thuê Đồ' },
          { id: 'ui-04', icon: 'fa-qrcode', text: 'Thanh Toán Cọc QR' },
          { id: 'ui-05', icon: 'fa-ticket', text: 'Vé QR Điện Tử', requiresAuth: true },
          { id: 'ui-06', icon: 'fa-users-viewfinder', text: 'AI Matchmaking ELO' },
          { id: 'ui-07', icon: 'fa-comments', text: 'Chat Nhóm Giao Lưu' },
          { id: 'ui-08', icon: 'fa-id-card', text: 'Hồ Sơ & Điểm ELO', requiresAuth: true }
        ]
      },
      'OWNER': {
        title: 'PHÂN HỆ CHỦ SÂN',
        items: [
          { id: 'ui-09', icon: 'fa-chart-line', text: 'Dashboard Tổng Quan' },
          { id: 'ui-10', icon: 'fa-map-location-dot', text: 'Quản Lý Sân & GPS' },
          { id: 'ui-11', icon: 'fa-bolt', text: 'Cấu Hình AI Dynamic Price' },
          { id: 'ui-12', icon: 'fa-boxes-stacked', text: 'Quản Lý Thiết Bị Kho' },
          { id: 'ui-13', icon: 'fa-user-gear', text: 'Quản Lý Ca Trực POS' },
          { id: 'ui-14', icon: 'fa-chart-pie', text: 'Heatmap Tải Lấp Đầy' }
        ]
      },
      'STAFF': {
        title: 'PHÂN HỆ NHÂN VIÊN POS',
        items: [
          { id: 'ui-15', icon: 'fa-qrcode', text: 'Check-in Sân POS' },
          { id: 'ui-16', icon: 'fa-file-invoice-dollar', text: 'Lập Hóa Đơn & Check-out' }
        ]
      },
      'ADMIN': {
        title: 'PHÂN HỆ QUẢN TRỊ ADMIN',
        items: [
          { id: 'ui-17', icon: 'fa-user-shield', text: 'Tổng Quan Hệ Thống Admin' },
          { id: 'ui-18', icon: 'fa-clipboard-check', text: 'Duyệt Cơ Sở Sân Mới' },
          { id: 'ui-19', icon: 'fa-users-gear', text: 'Quản Lý User & Phân Quyền' },
          { id: 'ui-20', icon: 'fa-database', text: 'Trình Xem CSDL 9 Bảng' }
        ]
      }
    };

    // Toggle Header CSDL Web Button (Only visible for ADMIN)
    const csdlBtn = document.getElementById('header-csdl-btn');
    if (csdlBtn) {
      csdlBtn.style.display = this.currentRole === 'ADMIN' ? 'inline-flex' : 'none';
    }

    const currentConfig = navMenus[this.currentRole];
    titleEl.textContent = currentConfig.title;

    let html = '';

    // Render Distinct Top Card in Sidebar: Guest vs Logged-in Member
    if (!this.currentUser) {
      html += `
        <div class="sidebar-auth-card guest">
          <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
            <div class="sidebar-auth-avatar guest-avatar"><i class="fa-solid fa-user"></i></div>
            <div style="overflow: hidden;">
              <div style="font-weight: 800; font-size: 0.88rem; color: #0f172a;">Khách Vãng Lai</div>
              <div style="font-size: 0.72rem; color: #64748b;">Chưa đăng nhập</div>
            </div>
          </div>
          <div style="display: flex; gap: 6px;">
            <button class="btn btn-xs btn-primary" style="flex: 1; font-weight: 700; padding: 5px;" onclick="app.navigateTo('ui-01')">
              <i class="fa-solid fa-right-to-bracket"></i> Đăng Nhập
            </button>
            <button class="btn btn-xs btn-outline-primary" style="flex: 1; font-weight: 700; padding: 5px;" onclick="app.navigateTo('ui-01'); app.switchAuthTab('register')">
              <i class="fa-solid fa-user-plus"></i> Đăng Ký
            </button>
          </div>
        </div>
      `;
    } else {
      const roleNames = {
        'CUSTOMER': 'Khách Hàng',
        'OWNER': 'Chủ Sân',
        'STAFF': 'Thu Ngân',
        'ADMIN': 'Quản Trị'
      };
      html += `
        <div class="sidebar-auth-card member">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div class="sidebar-auth-avatar member-avatar">${this.currentUser.avatar || '👤'}</div>
            <div style="overflow: hidden; flex: 1;">
              <div style="font-weight: 800; font-size: 0.88rem; color: #0f172a; white-space: nowrap; text-overflow: ellipsis; overflow: hidden;">${this.currentUser.name}</div>
              <div style="font-size: 0.72rem; color: #167946; font-weight: 700;">${roleNames[this.currentUser.role] || this.currentUser.role} • ELO ${this.currentUser.elo_rating || 1200}</div>
            </div>
          </div>
        </div>
      `;
    }

    currentConfig.items.forEach(item => {
      const isLocked = !this.currentUser && item.requiresAuth;
      html += `
        <a class="nav-item ${this.currentView === item.id ? 'active' : ''}" onclick="app.navigateTo('${item.id}')">
          <i class="fa-solid ${item.icon} icon"></i>
          <span>${item.text}</span>
          ${isLocked ? `<span style="margin-left: auto; font-size: 0.72rem; color: #94a3b8;" title="Yêu cầu đăng nhập"><i class="fa-solid fa-lock"></i></span>` : ''}
        </a>
      `;
    });

    if (this.currentUser) {
      html += `
        <hr style="border-color: var(--border-color); margin: 0.5rem 0;">
        <a class="nav-item" onclick="app.logout()" style="color: #ef4444;">
          <i class="fa-solid fa-right-from-bracket icon" style="color: #ef4444;"></i>
          <span>Đăng Xuất (${this.currentUser.name.split(' ').pop() || 'Tài khoản'})</span>
        </a>
      `;
    }

    navList.innerHTML = html;
  }

  navigateTo(screenId) {
    if (screenId === 'ui-20' && this.currentRole !== 'ADMIN') {
      this.showToast("Quyền truy cập bị từ chối! Chỉ tài khoản Quản Trị Viên (ADMIN) mới được quyền truy cập CSDL Web!", "error");
      return;
    }

    this.currentView = screenId;

    document.querySelectorAll('.screen-view').forEach(view => view.classList.remove('active'));
    const targetView = document.getElementById(`view-${screenId}`);
    if (targetView) targetView.classList.add('active');

    document.querySelectorAll('.nav-item').forEach(item => {
      if (item.getAttribute('onclick') && item.getAttribute('onclick').includes(screenId)) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });

    if (screenId === 'ui-02') this.updateBottomNavActive('home');
    else if (screenId === 'ui-map') this.updateBottomNavActive('map');
    else if (screenId === 'ui-trending') this.updateBottomNavActive('trending');
    else if (screenId === 'ui-01' || screenId === 'ui-08') this.updateBottomNavActive('account');
    else this.updateBottomNavActive('');

    if (screenId === 'ui-02') this.renderHomeAuthBanner();
    if (screenId === 'ui-05') this.renderBookingOrdersList();
    if (screenId === 'ui-06') this.updatePendingMatchesUI();
    if (screenId === 'ui-08') this.renderUserProfilePage();
    if (screenId === 'ui-map') this.initGoogleSportsMap();
    if (screenId === 'ui-09') this.renderOwnerDashboardOrders();
    if (screenId === 'ui-10') this.initLeafletMap();
    if (screenId === 'ui-13') this.renderOwnerStaff();
    if (screenId === 'ui-15') this.renderPOSTodayBookingsTable();
    if (screenId === 'ui-17') this.renderAdminOverviewFacilities();
    if (screenId === 'ui-18') this.renderAdminApprovals();
    if (screenId === 'ui-19') this.renderAdminUsers();
    if (screenId === 'ui-20') this.renderDatabaseInspector();

    // Auto close mobile sidebar after navigation
    this.toggleMobileSidebar(false);

    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  toggleMobileSidebar(forceState = null) {
    const sidebar = document.getElementById('main-sidebar');
    const backdrop = document.getElementById('sidebar-backdrop');
    if (!sidebar) return;

    const shouldOpen = forceState !== null ? forceState : !sidebar.classList.contains('mobile-open');
    if (shouldOpen) {
      sidebar.classList.add('mobile-open');
      if (backdrop) backdrop.classList.add('active');
    } else {
      sidebar.classList.remove('mobile-open');
      if (backdrop) backdrop.classList.remove('active');
    }
  }

  /* ------------------------------------------------------------------------
     2. UI 02: CUSTOMER SEARCH & SPORTS FACILITIES (ALOBO STYLE)
     ------------------------------------------------------------------------ */
  renderCustomerFacilities(filteredList = null) {
    const container = document.getElementById('facilities-grid-container');
    if (!container) return;

    let list = filteredList !== null ? filteredList : MockData.facilities.filter(f => f.is_approved);

    if (this.isFavoritesFilterActive) {
      list = list.filter(f => this.favorites.has(f.id));
    }

    let html = '';

    list.forEach(fac => {
      const isFav = this.favorites.has(fac.id);
      const distance = fac.distance || '5.2km';
      const hours = fac.open_hours || `${fac.open_time} - ${fac.close_time}`;
      const logoText = fac.club_logo || fac.name.split(' ').slice(0, 2).map(w => w[0]).join('');
      const logoBg = fac.club_avatar_bg || '#fef3c7';
      const logoColor = fac.club_avatar_color || '#d97706';

      html += `
        <div class="sports-court-card" onclick="app.selectFacilityForBooking(${fac.id})">
          <!-- Card Media Header -->
          <div class="court-card-media">
            <img src="${fac.img}" alt="${fac.name}" class="court-card-img" onerror="this.src='images/court1.jpg'">
            
            <!-- Badges Top Left -->
            <div class="court-card-badges-left">
              <span class="badge-pill badge-rating"><i class="fa-solid fa-star"></i> ${fac.rating}</span>
              ${fac.ai_score ? `<span class="badge-pill" style="background: linear-gradient(135deg, #10b981, #06b6d4); color: #fff; font-weight: 800; border: none; box-shadow: 0 2px 6px rgba(16,185,129,0.4);"><i class="fa-solid fa-wand-magic-sparkles"></i> AI: ${fac.ai_score}% Match</span>` : ''}
              ${fac.ai_reason ? `<span class="badge-pill" style="background: rgba(22,121,70,0.85); color: #fff; font-size: 0.65rem;">${fac.ai_reason}</span>` : ''}
              <span class="badge-pill badge-single-day">Đơn ngày</span>
              <span class="badge-pill badge-event">Sự kiện</span>
            </div>

            <!-- Action Icons Top Right -->
            <div class="court-card-actions-right">
              <button type="button" class="circle-action-btn ${isFav ? 'active' : ''}" onclick="event.stopPropagation(); app.toggleFavoriteFacility(${fac.id})" title="${isFav ? 'Bỏ yêu thích' : 'Thêm vào yêu thích'}">
                <i class="${isFav ? 'fa-solid' : 'fa-regular'} fa-heart"></i>
              </button>
              <button type="button" class="circle-action-btn" onclick="event.stopPropagation(); app.openGoogleMapsDirections(${fac.id})" title="Chỉ đường Google Maps">
                <i class="fa-solid fa-route"></i>
              </button>
            </div>
          </div>

          <!-- Card Body Section -->
          <div class="court-card-body">
            <div class="court-club-logo" style="background: ${logoBg}; color: ${logoColor};">
              <span>${logoText}</span>
            </div>

            <div class="court-info-main">
              <h3 class="court-card-name" title="${fac.name}">${fac.name}</h3>
              <div class="court-card-address">
                <span class="court-dist-highlight">[${distance}]</span>
                <span class="court-addr-text" title="${fac.address}">${fac.address}</span>
              </div>
              <div class="court-card-hours">
                <i class="fa-regular fa-clock"></i> ${hours}
              </div>
            </div>

            <button type="button" class="btn-booking-amber" onclick="event.stopPropagation(); app.selectFacilityForBooking(${fac.id})">
              ĐẶT LỊCH
            </button>
          </div>
        </div>
      `;
    });

    if (list.length === 0) {
      html = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 3rem 1.5rem; background: #ffffff; border-radius: 12px; border: 1.5px dashed #cbd5e1;">
          <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">🏸</div>
          <h4 style="color: #0f172a; font-weight: 800; font-size: 1.1rem; margin-bottom: 4px;">Không tìm thấy sân phù hợp</h4>
          <p style="color: #64748b; font-size: 0.85rem; margin-bottom: 1rem;">Vui lòng thử từ khóa khác hoặc tắt chế độ lọc danh sách yêu thích</p>
          <button class="btn btn-primary btn-sm" onclick="app.resetFacilitiesFilter()">
            <i class="fa-solid fa-rotate-left"></i> Xem Tất Cả Sân
          </button>
        </div>
      `;
    }

    container.innerHTML = html;
  }

  toggleFavoriteFacility(facilityId) {
    if (this.favorites.has(facilityId)) {
      this.favorites.delete(facilityId);
      this.showToast('Đã xóa khỏi danh sách Yêu thích');
    } else {
      this.favorites.add(facilityId);
      this.showToast('❤️ Đã thêm sân vào danh sách Yêu thích!');
    }
    this.renderCustomerFacilities();
  }

  toggleFilterFavorites() {
    this.isFavoritesFilterActive = !this.isFavoritesFilterActive;
    const tabEl = document.getElementById('quick-tab-fav');
    if (tabEl) {
      if (this.isFavoritesFilterActive) {
        tabEl.style.background = 'rgba(22, 121, 70, 0.15)';
        tabEl.style.fontWeight = '700';
        this.showToast('Đang lọc danh sách sân Yêu thích của bạn');
      } else {
        tabEl.style.background = 'transparent';
        tabEl.style.fontWeight = '600';
      }
    }
    this.renderCustomerFacilities();
  }

  toggleSearchFilterDropdown() {
    const panel = document.getElementById('advanced-filters-panel');
    if (panel) {
      const isHidden = panel.style.display === 'none';
      panel.style.display = isHidden ? 'block' : 'none';
    }
  }

  resetFacilitiesFilter() {
    this.isFavoritesFilterActive = false;
    const searchInput = document.getElementById('search-keyword');
    const districtSelect = document.getElementById('search-district');
    const favTab = document.getElementById('quick-tab-fav');
    if (searchInput) searchInput.value = '';
    if (districtSelect) districtSelect.value = '';
    if (favTab) favTab.style.background = 'transparent';
    this.renderCustomerFacilities();
  }

  openFacilitiesMap() {
    this.navigateTo('ui-02');
    this.showToast('🗺️ Mở chế độ xem vị trí bản đồ các cụm sân');
    // Scroll or open map modal if exists
    const mapSection = document.getElementById('facility-map');
    if (mapSection) {
      mapSection.scrollIntoView({ behavior: 'smooth' });
    }
  }

  updateBottomNavActive(tabKey) {
    document.querySelectorAll('.bottom-bar-item').forEach(item => item.classList.remove('active'));
    const tabMap = {
      'home': 'bottom-tab-home',
      'map': 'bottom-tab-map',
      'trending': 'bottom-tab-trending',
      'account': 'bottom-tab-account'
    };
    if (tabMap[tabKey]) {
      const el = document.getElementById(tabMap[tabKey]);
      if (el) el.classList.add('active');
    }
  }

  openGoogleMapsDirections(facilityId) {
    const fac = MockData.facilities.find(f => f.id === facilityId) || this.selectedFacility;
    if (!fac) return;
    const query = encodeURIComponent(`${fac.name}, ${fac.address}`);
    const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${query}`;
    window.open(mapsUrl, '_blank');
  }

  openCurrentGoogleMaps() {
    if (this.selectedFacility) {
      this.openGoogleMapsDirections(this.selectedFacility.id);
    } else {
      window.open('https://www.google.com/maps/search/?api=1&query=S%C3%A2n+C%E1%BA%A7u+L%C3%B4ng+H%C3%A0+N%E1%BB%99i', '_blank');
    }
  }

  filterFacilities() {
    const keyword = (document.getElementById('search-keyword')?.value || '').toLowerCase();
    const district = document.getElementById('search-district')?.value || '';
    const sortBy = document.getElementById('search-sort')?.value || 'distance';

    let result = MockData.facilities.filter(f => f.is_approved);
    if (keyword) {
      result = result.filter(f => f.name.toLowerCase().includes(keyword) || f.address.toLowerCase().includes(keyword));
    }
    if (district) {
      result = result.filter(f => f.address.includes(district));
    }

    if (sortBy === 'distance') {
      result.sort((a, b) => parseFloat(a.distance || 99) - parseFloat(b.distance || 99));
    } else if (sortBy === 'rating') {
      result.sort((a, b) => b.rating - a.rating);
    }

    this.renderCustomerFacilities(result);
  }

  requestGPSLocation() {
    this.showToast("Đang kết nối GPS định vị tọa độ hiện tại (10.8456 N, 106.7925 E)...");
    setTimeout(() => {
      this.showToast("AI đã dùng thuật toán Haversine sắp xếp Top sân gần bạn nhất!");
      this.renderCustomerFacilities();
    }, 600);
  }

  selectFacilityForBooking(facilityId) {
    this.selectedFacility = MockData.facilities.find(f => f.id === facilityId);
    document.getElementById('facility-detail-name').textContent = this.selectedFacility.name;
    document.getElementById('facility-detail-address').textContent = this.selectedFacility.address;
    this.renderSlotMatrix();
    this.navigateTo('ui-03');
  }

  /* ------------------------------------------------------------------------
     3. UI 03: SLOT MATRIX & MULTI-HOUR BOOKING (HỖ TRỢ CHỌN NHIỀU GIỜ)
     ------------------------------------------------------------------------ */
  renderSlotMatrix() {
    const matrixGrid = document.getElementById('slot-matrix-grid');
    const ownerMatrix = document.getElementById('owner-ai-slot-matrix');
    let html = '';
    let ownerHtml = '';

    if (!this.selectedSlots) this.selectedSlots = [];
    const selectedIds = new Set(this.selectedSlots.map(s => s.id));

    MockData.time_slots.forEach(slot => {
      const isSelected = selectedIds.has(slot.id);
      const statusClass = isSelected ? 'selected' : slot.status.toLowerCase();

      let aiTag = '';
      if (slot.is_ai_dynamic && this.isAIDynamicPriceActive) {
        aiTag = `<span class="slot-price-ai ${slot.price_type}"><i class="fa-solid fa-robot"></i> ${slot.adjustment}</span>`;
      }

      html += `
        <div class="slot-btn ${statusClass}" onclick="app.toggleSlotSelection(${slot.id})">
          <div style="display: flex; align-items: center; justify-content: center; gap: 4px; width: 100%;">
            ${isSelected ? '<i class="fa-solid fa-circle-check" style="color: #ffffff; font-size: 0.85rem;"></i>' : ''}
            <span class="slot-time">${slot.start_time} - ${slot.end_time}</span>
          </div>
          <span class="slot-price">${slot.price.toLocaleString('vi-VN')} đ</span>
          ${aiTag}
        </div>
      `;

      ownerHtml += `
        <div class="slot-btn ${slot.status.toLowerCase()}" style="border-color: var(--border-color);">
          <span class="slot-time">${slot.start_time} - ${slot.end_time}</span>
          <span class="slot-price">${slot.price.toLocaleString('vi-VN')} đ</span>
          ${aiTag}
          <span style="font-size: 0.7rem; margin-top: 2px;">Trạng thái: <strong>${slot.status === 'AVAILABLE' ? 'Còn Trống' : (slot.status === 'BOOKED' ? 'Đã Đặt' : 'Tạm Giữ')}</strong></span>
        </div>
      `;
    });

    if (matrixGrid) matrixGrid.innerHTML = html;
    if (ownerMatrix) ownerMatrix.innerHTML = ownerHtml;
  }

  // Toggle selection for multiple slots (1 hour, 2 hours, 3+ hours)
  toggleSlotSelection(slotId) {
    const slot = MockData.time_slots.find(s => s.id === slotId);
    if (!slot) return;

    if (slot.status !== 'AVAILABLE') {
      this.showToast(`Khung giờ ${slot.start_time} - ${slot.end_time} đang ở trạng thái: ${slot.status === 'BOOKED' ? 'Đã được đặt' : 'Đang tạm giữ 10p'}!`, 'error');
      return;
    }

    if (!this.selectedSlots) this.selectedSlots = [];
    const index = this.selectedSlots.findIndex(s => s.id === slotId);

    if (index >= 0) {
      // Bỏ chọn slot này
      this.selectedSlots.splice(index, 1);
    } else {
      // Thêm slot mới vào danh sách đã chọn
      this.selectedSlots.push(slot);
    }

    // Sắp xếp lại danh sách slot đã chọn theo thứ tự thời gian
    this.selectedSlots.sort((a, b) => a.start_time.localeCompare(b.start_time));
    this.selectedSlot = this.selectedSlots.length > 0 ? this.selectedSlots[0] : null;

    this.renderSlotMatrix();
    this.updateBookingSummary();
  }

  // Quick select duration preset (1h, 2h, 3h consecutive available slots)
  quickSelectDuration(hours) {
    const availableSlots = MockData.time_slots.filter(s => s.status === 'AVAILABLE');
    if (availableSlots.length === 0) {
      this.showToast("Hiện không còn khung giờ trống trong ngày!", "error");
      return;
    }

    // Ưu tiên chọn các slot giờ đẹp buổi chiều tối (17h - 21h) hoặc các slot liên tiếp đầu tiên
    let chosenSlots = [];
    const eveningSlots = availableSlots.filter(s => parseInt(s.start_time.split(':')[0], 10) >= 17);
    const candidateList = eveningSlots.length >= hours ? eveningSlots : availableSlots;

    // Tìm các slot liên tiếp
    for (let i = 0; i <= candidateList.length - hours; i++) {
      const sub = candidateList.slice(i, i + hours);
      let isConsecutive = true;
      for (let j = 0; j < sub.length - 1; j++) {
        if (sub[j].end_time !== sub[j + 1].start_time) {
          isConsecutive = false;
          break;
        }
      }
      if (isConsecutive) {
        chosenSlots = sub;
        break;
      }
    }

    // Nếu không có liên tiếp hoàn hảo thì lấy N slot đầu tiên khả dụng
    if (chosenSlots.length === 0) {
      chosenSlots = candidateList.slice(0, hours);
    }

    this.selectedSlots = chosenSlots;
    this.selectedSlot = this.selectedSlots[0] || null;
    this.renderSlotMatrix();
    this.updateBookingSummary();
    this.showToast(`✨ Đã chọn nhanh ${hours} giờ thuê sân (${this.selectedSlots.map(s => s.start_time).join(', ')}...)!`);
  }

  clearSelectedSlots() {
    this.selectedSlots = [];
    this.selectedSlot = null;
    this.renderSlotMatrix();
    this.updateBookingSummary();
  }

  selectSlot(slotId) {
    this.toggleSlotSelection(slotId);
  }

  renderEquipmentRentalList() {
    const container = document.getElementById('equipment-rent-container');
    let html = '';

    MockData.equipments.forEach(eq => {
      const qty = this.selectedEquipments[eq.id] || 0;
      const styleTag = eq.style ? `<div style="font-size: 0.72rem; color: var(--accent-cyan); font-weight: 600; margin-top: 1px;">${eq.style}</div>` : '';
      html += `
        <div class="equip-item-card">
          <div>
            <div style="font-weight: 600; font-size: 0.85rem;">${eq.name}</div>
            ${styleTag}
            <div style="font-size: 0.75rem; color: var(--text-muted);">${eq.price.toLocaleString('vi-VN')}đ / ${eq.unit}</div>
          </div>
          <div class="qty-counter">
            <button class="qty-btn" onclick="app.changeEquipQty(${eq.id}, -1)">-</button>
            <span style="font-weight: 700; width: 20px; text-align: center;">${qty}</span>
            <button class="qty-btn" onclick="app.changeEquipQty(${eq.id}, 1)">+</button>
          </div>
        </div>
      `;
    });

    if (container) container.innerHTML = html;
  }

  changeEquipQty(equipId, delta) {
    const currentQty = this.selectedEquipments[equipId] || 0;
    const newQty = Math.max(0, currentQty + delta);
    this.selectedEquipments[equipId] = newQty;
    this.renderEquipmentRentalList();
    this.updateBookingSummary();
  }

  updateBookingSummary() {
    const summarySlot = document.getElementById('selected-slot-summary');
    const summaryTotal = document.getElementById('selected-total-summary');
    const btnProceed = document.getElementById('btn-proceed-checkout');

    if (!this.selectedSlots || this.selectedSlots.length === 0) {
      if (summarySlot) summarySlot.textContent = "Chưa chọn khung giờ nào";
      if (summaryTotal) summaryTotal.textContent = "0 VNĐ";
      if (btnProceed) btnProceed.disabled = true;
      return;
    }

    const totalHours = this.selectedSlots.length;
    let slotPriceTotal = 0;
    this.selectedSlots.forEach(s => {
      slotPriceTotal += s.price;
    });

    let equipPriceTotal = 0;
    MockData.equipments.forEach(eq => {
      const qty = this.selectedEquipments[eq.id] || 0;
      equipPriceTotal += qty * eq.price;
    });

    const totalAmount = slotPriceTotal + equipPriceTotal;
    const depositAmount = 50000;

    // Check if slots are consecutive
    let isConsecutive = true;
    for (let i = 0; i < this.selectedSlots.length - 1; i++) {
      if (this.selectedSlots[i].end_time !== this.selectedSlots[i + 1].start_time) {
        isConsecutive = false;
        break;
      }
    }

    let timeRangeText = '';
    if (isConsecutive && totalHours > 1) {
      timeRangeText = `${this.selectedSlots[0].start_time} - ${this.selectedSlots[this.selectedSlots.length - 1].end_time} (${totalHours} tiếng liên tục)`;
    } else {
      timeRangeText = this.selectedSlots.map(s => `${s.start_time}-${s.end_time}`).join(', ') + ` (${totalHours} giờ)`;
    }

    if (summarySlot) {
      summarySlot.innerHTML = `
        <span style="color: #0f172a; font-weight: 800;">Sân 01</span> | 
        <span style="color: var(--primary); font-weight: 700;">${timeRangeText}</span>
      `;
    }

    if (summaryTotal) {
      summaryTotal.innerHTML = `
        <span style="color: #0f172a;">${totalAmount.toLocaleString('vi-VN')} VNĐ</span> 
        <span style="font-size: 0.85rem; color: #16a34a; font-weight: 700;">(Cọc giữ chỗ: ${depositAmount.toLocaleString('vi-VN')}đ)</span>
      `;
    }

    if (btnProceed) btnProceed.disabled = false;
  }

  proceedToCheckout() {
    if (!this.currentUser) {
      this.showToast("⚠️ Vui lòng Đăng Nhập hoặc Đăng Ký tài khoản trước khi thực hiện Đặt Sân & Thanh Toán!", "error");
      this.navigateTo('ui-01');
      return;
    }

    if (!this.selectedSlots || this.selectedSlots.length === 0) {
      this.showToast("⚠️ Vui lòng chọn ít nhất 1 khung giờ đặt sân!", "error");
      return;
    }

    // Update Checkout UI with selected slots detail
    this.updateCheckoutViewDetails();
    this.navigateTo('ui-04');
    this.startHoldTimer();
    this.showToast(`Hệ thống đã kích hoạt Redis Atomic Lock giữ ${this.selectedSlots.length} khung giờ trong 10:00 phút!`);
  }

  updateCheckoutViewDetails() {
    const totalHours = this.selectedSlots ? this.selectedSlots.length : 1;
    let slotPriceTotal = 0;
    (this.selectedSlots || []).forEach(s => slotPriceTotal += s.price);

    let equipPriceTotal = 0;
    MockData.equipments.forEach(eq => {
      const qty = this.selectedEquipments[eq.id] || 0;
      equipPriceTotal += qty * eq.price;
    });

    const totalAmount = slotPriceTotal + equipPriceTotal;
    const depositAmount = Math.round((totalAmount * 0.5) / 1000) * 1000;
    this.currentPendingTotalAmount = totalAmount;
    this.currentPendingDepositAmount = depositAmount;

    const timeSlotsStr = (this.selectedSlots && this.selectedSlots.length > 0)
      ? this.selectedSlots.map(s => `${s.start_time} - ${s.end_time}`).join(', ')
      : '17:30 - 18:30';

    const datePicker = document.getElementById('booking-date-picker');
    const bookingDate = datePicker ? datePicker.value : new Date().toISOString().slice(0, 10);

    const bookingCode = `BK-${bookingDate.replace(/-/g, '')}-${Math.floor(100 + Math.random() * 900)}`;
    this.currentPendingBookingCode = bookingCode;

    // Chuẩn hóa VietQR tiêu chuẩn liên ngân hàng 24/7
    const vietQrUrl = `https://img.vietqr.io/image/MB-0983582321-compact2.png?amount=${depositAmount}&addInfo=${encodeURIComponent(bookingCode)}&accountName=BADMINTON%20AI%20VIETNAM`;
    const qrImg = document.getElementById('payment-qr-img');
    if (qrImg) qrImg.src = vietQrUrl;

    const payDepositEl = document.getElementById('pay-deposit-text');
    if (payDepositEl) payDepositEl.textContent = `${depositAmount.toLocaleString('vi-VN')} VNĐ`;

    const payMemoEl = document.getElementById('pay-memo-text');
    if (payMemoEl) payMemoEl.textContent = bookingCode;

    const courtName = (this.selectedCourt && this.selectedCourt.name)
      ? this.selectedCourt.name
      : ((MockData.courts && MockData.courts[0]) ? MockData.courts[0].name : "Sân 01 - Thảm Yonex Pro");
    const facName = this.selectedFacility ? this.selectedFacility.name : "CLB Cầu Lông Catchy Badminton Arena";

    const summaryBox = document.getElementById('checkout-order-summary-box');
    if (summaryBox) {
      summaryBox.innerHTML = `
        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
          <span style="color: var(--text-muted);">Mã đơn đặt sân:</span>
          <strong style="color: #38bdf8; font-family: monospace;">${bookingCode}</strong>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
          <span style="color: var(--text-muted);">Cơ sở thể thao:</span>
          <strong style="text-align: right; max-width: 260px;">${facName}</strong>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
          <span style="color: var(--text-muted);">Sân thi đấu & Giờ chơi:</span>
          <strong style="color: #22c55e;">${courtName} (${timeSlotsStr})</strong>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
          <span style="color: var(--text-muted);">Ngày thi đấu:</span>
          <span>${bookingDate}</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
          <span style="color: var(--text-muted);">Tổng giá trị đơn:</span>
          <strong>${totalAmount.toLocaleString('vi-VN')} VNĐ</strong>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
          <span style="color: var(--text-muted);">Tiền cọc giữ chỗ (50%):</span>
          <strong style="color: #22c55e; font-size: 1.05rem;">${depositAmount.toLocaleString('vi-VN')} VNĐ</strong>
        </div>
        <div style="display: flex; justify-content: space-between; border-top: 1px dashed rgba(255,255,255,0.12); padding-top: 5px; margin-top: 4px;">
          <span style="color: var(--text-muted);">Còn lại trả tại quầy POS:</span>
          <span style="color: #f59e0b; font-weight: 700;">${(totalAmount - depositAmount).toLocaleString('vi-VN')} VNĐ</span>
        </div>
      `;
    }
  }

  /* ------------------------------------------------------------------------
     4. UI 04: COUNTDOWN TIMER & VIETQR PAYMENT
     ------------------------------------------------------------------------ */
  startHoldTimer() {
    clearInterval(this.holdTimer);
    this.holdTimerSeconds = 600;

    const timerDisplay = document.getElementById('hold-timer-display');
    this.holdTimer = setInterval(() => {
      this.holdTimerSeconds--;
      const mins = Math.floor(this.holdTimerSeconds / 60).toString().padStart(2, '0');
      const secs = (this.holdTimerSeconds % 60).toString().padStart(2, '0');
      if (timerDisplay) timerDisplay.textContent = `${mins}:${secs}`;

      if (this.holdTimerSeconds <= 0) {
        clearInterval(this.holdTimer);
        this.showToast("Hết thời gian giữ chỗ! Các slot giờ đã được tự động giải phóng.", 'error');
        this.navigateTo('ui-03');
      }
    }, 1000);
  }

  processPaymentConfirmation() {
    clearInterval(this.holdTimer);

    const datePicker = document.getElementById('booking-date-picker');
    const bookingDate = datePicker ? datePicker.value : new Date().toISOString().slice(0, 10);
    const totalHours = this.selectedSlots ? this.selectedSlots.length : 1;

    let slotPriceTotal = 0;
    (this.selectedSlots || []).forEach(s => slotPriceTotal += s.price);

    let equipPriceTotal = 0;
    MockData.equipments.forEach(eq => {
      const qty = this.selectedEquipments[eq.id] || 0;
      equipPriceTotal += qty * eq.price;
    });

    const totalAmount = slotPriceTotal + equipPriceTotal;
    const depositAmount = Math.round((totalAmount * 0.5) / 1000) * 1000;
    const timeSlotsStr = (this.selectedSlots && this.selectedSlots.length > 0)
      ? this.selectedSlots.map(s => `${s.start_time} - ${s.end_time}`).join(', ')
      : '18:00 - 20:00';

    const bookingCode = this.currentPendingBookingCode || `BK-${bookingDate.replace(/-/g, '')}-${Math.floor(100 + Math.random() * 900)}`;
    const ticketCode = `TICKET-ALB-${Math.floor(100000 + Math.random() * 900000)}`;

    const courtName = (this.selectedCourt && this.selectedCourt.name)
      ? this.selectedCourt.name
      : ((MockData.courts && MockData.courts[0]) ? MockData.courts[0].name : "Sân 01 - Thảm Yonex Pro");

    const newOrder = {
      id: Date.now(),
      booking_code: bookingCode,
      user_name: (this.currentUser && this.currentUser.name) ? this.currentUser.name : 'Nguyễn Văn Hùng',
      user_phone: (this.currentUser && this.currentUser.phone) ? this.currentUser.phone : '0901234567',
      facility_name: this.selectedFacility ? this.selectedFacility.name : "CLB Cầu Lông Catchy Badminton Arena",
      court_name: courtName,
      slot_time: `${timeSlotsStr} (${totalHours} giờ)`,
      booking_date: bookingDate,
      total_amount: totalAmount,
      deposit_amount: depositAmount,
      deposit_status: `Đã Cọc 50% (${depositAmount.toLocaleString('vi-VN')}đ)`,
      order_status: "ĐÃ XÁC NHẬN (CHỜ CHECK-IN)",
      created_at: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      qr_ticket_code: ticketCode
    };

    MockData.booking_orders.unshift(newOrder);

    // Cập nhật trạng thái các slot vừa đặt thành BOOKED
    if (this.selectedSlots) {
      this.selectedSlots.forEach(s => {
        const found = MockData.time_slots.find(item => item.id === s.id);
        if (found) found.status = 'BOOKED';
      });
    }

    if (typeof saveMockDataToLocalStorage === 'function') {
      saveMockDataToLocalStorage();
    }

    // Âm thanh xác nhận giao dịch thành công (Web Audio API)
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.type = "sine";
      osc.frequency.setValueAtTime(587.33, audioCtx.currentTime); // D5
      osc.frequency.setValueAtTime(880, audioCtx.currentTime + 0.12); // A5
      gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.45);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.45);
    } catch (e) {}

    this.renderBookingOrdersList();
    this.renderSlotMatrix();

    this.showToast(`🎉 Xác thực thanh toán VietQR thành công! Vé QR điện tử ${ticketCode} đã sẵn sàng.`);
    this.navigateTo('ui-05');
  }

  simulatePaymentSuccess() {
    this.processPaymentConfirmation();
  }

  /* ------------------------------------------------------------------------
     5. UI 05: ELECTRONIC TICKET QR & ORDER HISTORY
     ------------------------------------------------------------------------ */
  renderBookingOrdersList() {
    const container = document.getElementById('booking-orders-list-container');
    if (!container) return;

    if (!this.currentUser) {
      container.innerHTML = `
        <div class="guest-locked-card" style="margin-top: 1rem;">
          <div style="width: 72px; height: 72px; border-radius: 50%; background: #f0fdf4; display: flex; align-items: center; justify-content: center; margin: 0 auto 1.25rem; font-size: 2rem; color: #16a34a; border: 2px dashed #86efac;">
            <i class="fa-solid fa-ticket"></i>
          </div>
          <h2 style="font-size: 1.35rem; color: #0f172a; margin-bottom: 0.5rem; font-weight: 800;">Tra Cứu Vé QR & Đơn Đặt Sân</h2>
          <p style="font-size: 0.9rem; color: #64748b; max-width: 440px; margin: 0 auto 1.5rem; line-height: 1.6;">
            Bạn đang truy cập ở chế độ <strong>Khách Vãng Lai</strong>. Vui lòng đăng nhập vào tài khoản để xem danh sách vé QR điện tử dùng check-in tại quầy sân và quản lý các lượt đặt sân của bạn!
          </p>
          <div style="display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;">
            <button class="btn btn-primary" onclick="app.navigateTo('ui-01')" style="padding: 10px 24px; font-weight: 800;">
              <i class="fa-solid fa-right-to-bracket"></i> Đăng Nhập Để Xem Vé
            </button>
            <button class="btn btn-outline-primary" onclick="app.navigateTo('ui-01'); app.switchAuthTab('register')" style="padding: 10px 24px; font-weight: 800;">
              <i class="fa-solid fa-user-plus"></i> Đăng Ký Tài Khoản
            </button>
          </div>
        </div>
      `;
      return;
    }

    const orders = MockData.booking_orders || [];
    if (orders.length === 0) {
      container.innerHTML = `
        <div class="glass-card" style="text-align: center; padding: 2.5rem; background: #fff;">
          <p style="color: #64748b; margin-bottom: 1rem;">Tài khoản của bạn hiện chưa có đơn đặt sân nào.</p>
          <button class="btn btn-primary btn-sm" onclick="app.navigateTo('ui-02')">
            <i class="fa-solid fa-calendar-plus"></i> Đặt Sân Giữ Chỗ Ngay
          </button>
        </div>
      `;
      return;
    }

    let html = '';
    orders.forEach(order => {
      html += `
        <div class="glass-card" style="margin-bottom: 1rem;">
          <div class="ticket-card">
            <div class="ticket-qr">
              <img src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${order.qr_ticket_code}" alt="QR Ticket" style="width: 100%; height: 100%;">
            </div>
            <div style="flex: 1;">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <h3 style="color: var(--primary);">${order.booking_code}</h3>
                <span class="tag-badge tag-ai">${order.order_status}</span>
              </div>
              <div style="font-size: 0.9rem; margin-top: 0.5rem;"><strong>Cụm Sân:</strong> ${order.facility_name}</div>
              <div style="font-size: 0.85rem; color: var(--text-muted);"><strong>Chi tiết:</strong> ${order.court_name} | Khung giờ: <strong style="color: #0369a1;">${order.slot_time}</strong> | Ngày: ${order.booking_date}</div>
              <div style="font-size: 0.85rem; margin-top: 0.25rem;"><strong>Mã Vé QR Check-in:</strong> <code style="color: var(--accent-cyan); font-weight: 700;">${order.qr_ticket_code}</code></div>
              <div style="margin-top: 0.75rem; font-size: 0.9rem;">Tổng đơn: <strong>${order.total_amount.toLocaleString('vi-VN')}đ</strong> | Đã cọc: <span style="color: var(--primary); font-weight: 700;">50,000đ</span></div>
            </div>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
  }

  /* ------------------------------------------------------------------------
     6. UI 06 & UI 07: AI MATCHMAKING & TACTICAL CHAT GROUP
     ------------------------------------------------------------------------ */
  filterMatchmakingCategory(cat) {
    this.currentMMFilter = cat;
    const chips = ['all', 'recommended', 'doubles', 'singles', 'handicap'];
    chips.forEach(c => {
      const el = document.getElementById(`mm-chip-${c}`);
      if (el) {
        if (c === cat) el.classList.add('active');
        else el.classList.remove('active');
      }
    });
    this.renderMatchmakingRooms();
  }

  searchMatchmakingRooms(query) {
    this.currentMMSearch = (query || '').trim().toLowerCase();
    this.renderMatchmakingRooms();
  }

  sortMatchmakingRooms(sortBy) {
    this.currentMMSort = sortBy;
    this.renderMatchmakingRooms();
  }

  // =========================================================================
  // 7-TIER SKILL RANKING & AI MATCHMAKING SYSTEM (UC006)
  // Standard 7-Tier Skill Hierarchy (7 Cấp Bậc Trình Độ Thi Đấu & Ghép Kèo AI):
  // 1 | Yếu - Tân thủ
  // 2 | Trung Bình Yếu - Cơ bản
  // 3 | Trung bình
  // 4 | Trung bình khá
  // 5 | Khá
  // 6 | Giỏi - Thành thạo
  // 7 | Tốt - Chuyên nghiệp
  // =========================================================================
  static SKILL_TIERS = [
    {
      tier: 1,
      id: 1,
      key: "yeu_tan_thu",
      name: "Yếu - Tân thủ",
      level: "Yếu",
      sub: "Tân thủ",
      display: "🟢 Cấp 1: Yếu - Tân thủ",
      badgeText: "Yếu - Tân thủ",
      color: "#16a34a",
      bg: "#dcfce7",
      borderColor: "#86efac",
      desc: "Mới tập chơi, nắm bắt kỹ thuật phát cầu & phản tạt cơ bản",
      minElo: 0,
      maxElo: 950,
      defaultElo: 800
    },
    {
      tier: 2,
      id: 2,
      key: "tb_yeu_co_ban",
      name: "Trung Bình Yếu - Cơ bản",
      level: "Trung Bình Yếu",
      sub: "Cơ bản",
      display: "🔵 Cấp 2: Trung Bình Yếu - Cơ bản",
      badgeText: "TB Yếu - Cơ bản",
      color: "#0284c7",
      bg: "#e0f2fe",
      borderColor: "#7dd3fc",
      desc: "Nắm vững luật thi đấu, phông cầu cơ bản, di chuyển bước đầu ổn định",
      minElo: 951,
      maxElo: 1150,
      defaultElo: 1050
    },
    {
      tier: 3,
      id: 3,
      key: "trung_binh",
      name: "Trung bình",
      level: "Trung bình",
      sub: "",
      display: "🟡 Cấp 3: Trung bình",
      badgeText: "Trung bình",
      color: "#ca8a04",
      bg: "#fef9c3",
      borderColor: "#fde047",
      desc: "Đánh cầu đều tay, di chuyển thanh thoát, phông cầu sâu và bỏ nhỏ ổn định",
      minElo: 1151,
      maxElo: 1350,
      defaultElo: 1250
    },
    {
      tier: 4,
      id: 4,
      key: "trung_binh_kha",
      name: "Trung bình khá",
      level: "Trung bình khá",
      sub: "",
      display: "🟠 Cấp 4: Trung bình khá",
      badgeText: "Trung bình khá",
      color: "#ea580c",
      bg: "#ffedd5",
      borderColor: "#fdba74",
      desc: "Thể lực tốt, chiến thuật bọc lót linh hoạt, smash cơ bản và tạt lưới sắc bén",
      minElo: 1351,
      maxElo: 1550,
      defaultElo: 1450
    },
    {
      tier: 5,
      id: 5,
      key: "kha",
      name: "Khá",
      level: "Khá",
      sub: "",
      display: "🔴 Cấp 5: Khá",
      badgeText: "Khá",
      color: "#dc2626",
      bg: "#fee2e2",
      borderColor: "#fca5a5",
      desc: "Kỹ thuật toàn diện, smash uy lực, điều tiết nhịp độ và kiểm soát thế trận vững vàng",
      minElo: 1551,
      maxElo: 1750,
      defaultElo: 1650
    },
    {
      tier: 6,
      id: 6,
      key: "gioi_thanh_thao",
      name: "Giỏi - Thành thạo",
      level: "Giỏi",
      sub: "Thành thạo",
      display: "🟣 Cấp 6: Giỏi - Thành thạo",
      badgeText: "Giỏi - Thành thạo",
      color: "#9333ea",
      bg: "#f3e8ff",
      borderColor: "#d8b4fe",
      desc: "Kỹ năng chuyên sâu, thi đấu giải phong trào nhiều năm, phản xạ cực nhạy",
      minElo: 1751,
      maxElo: 1950,
      defaultElo: 1850
    },
    {
      tier: 7,
      id: 7,
      key: "tot_chuyen_nghiep",
      name: "Tốt - Chuyên nghiệp",
      level: "Tốt",
      sub: "Chuyên nghiệp",
      display: "👑 Cấp 7: Tốt - Chuyên nghiệp",
      badgeText: "Tốt - Chuyên nghiệp",
      color: "#4f46e5",
      bg: "#e0e7ff",
      borderColor: "#a5b4fc",
      desc: "Đẳng cấp kiện tướng, vận động viên bán chuyên / chuyên nghiệp hoặc HLV đẳng cấp cao",
      minElo: 1951,
      maxElo: null,
      defaultElo: 2050
    }
  ];

  getSkillTierInfo(val) {
    const tiers = App.SKILL_TIERS || [
      { tier: 1, name: "Yếu - Tân thủ", display: "🟢 Cấp 1: Yếu - Tân thủ", color: "#16a34a", bg: "#dcfce7", desc: "Mới tập chơi" },
      { tier: 2, name: "Trung Bình Yếu - Cơ bản", display: "🔵 Cấp 2: Trung Bình Yếu - Cơ bản", color: "#0284c7", bg: "#e0f2fe", desc: "Cơ bản" },
      { tier: 3, name: "Trung bình", display: "🟡 Cấp 3: Trung bình", color: "#ca8a04", bg: "#fef9c3", desc: "Trung bình" },
      { tier: 4, name: "Trung bình khá", display: "🟠 Cấp 4: Trung bình khá", color: "#ea580c", bg: "#ffedd5", desc: "Trung bình khá" },
      { tier: 5, name: "Khá", display: "🔴 Cấp 5: Khá", color: "#dc2626", bg: "#fee2e2", desc: "Khá" },
      { tier: 6, name: "Giỏi - Thành thạo", display: "🟣 Cấp 6: Giỏi - Thành thạo", color: "#9333ea", bg: "#f3e8ff", desc: "Giỏi" },
      { tier: 7, name: "Tốt - Chuyên nghiệp", display: "👑 Cấp 7: Tốt - Chuyên nghiệp", color: "#4f46e5", bg: "#e0e7ff", desc: "Chuyên nghiệp" }
    ];

    if (typeof val === 'number') {
      if (val >= 1 && val <= 7) {
        return tiers[val - 1];
      }
      // If numeric ELO value passed from legacy:
      if (val <= 950) return tiers[0];
      if (val <= 1150) return tiers[1];
      if (val <= 1350) return tiers[2];
      if (val <= 1550) return tiers[3];
      if (val <= 1750) return tiers[4];
      if (val <= 1950) return tiers[5];
      return tiers[6];
    }

    if (typeof val === 'string') {
      const clean = val.trim().toLowerCase();
      // Match by number string '1'..'7'
      const num = parseInt(clean, 10);
      if (!isNaN(num) && num >= 1 && num <= 7) {
        return tiers[num - 1];
      }
      for (const t of tiers) {
        if (clean === t.key || clean === t.name.toLowerCase() || t.name.toLowerCase().includes(clean) || clean.includes(t.level.toLowerCase())) {
          return t;
        }
      }
    }

    return tiers[4]; // Default to Khá (Cấp 5)
  }

  // Alias for backward compatibility
  getEloTierInfo(elo) {
    return this.getSkillTierInfo(elo);
  }

  getRatingConfidenceInfo(gamesPlayed) {
    const games = gamesPlayed || 15;
    if (games < 10) {
      return { confidence: Math.min(0.45, 0.15 + games * 0.03), text: "Tân thủ (Thử việc)", kFactor: 48, badge: "Thử Việc (K=48)" };
    } else if (games < 30) {
      return { confidence: Math.min(0.85, 0.45 + (games - 10) * 0.02), text: "Đang hiệu chỉnh", kFactor: 32, badge: "Hiệu Chỉnh (K=32)" };
    }
    return { confidence: 0.95, text: "Xác thực (Độ tin cậy cao)", kFactor: 24, badge: "Xác Thực (K=24)" };
  }

  // =========================================================================
  // PHOTO UPLOAD & FACE RECOGNITION FOR AI MATCHMAKING
  // =========================================================================
  triggerPlayerPhotoUpload() {
    if (!this.currentUser) {
      this.showToast("⚠️ Bạn chưa đăng nhập! Vui lòng Đăng Nhập tài khoản để tải ảnh nhận diện.", "error");
      this.navigateTo('ui-01');
      return;
    }
    const input = document.getElementById('mm-player-photo-input');
    if (input) {
      input.click();
    }
  }

  handlePlayerPhotoUpload(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;

    if (!this.currentUser) {
      this.showToast("⚠️ Vui lòng Đăng Nhập để lưu ảnh nhận diện của bạn!", "error");
      this.navigateTo('ui-01');
      return;
    }

    if (!file.type.startsWith('image/')) {
      this.showToast("⚠️ Vui lòng chọn tệp định dạng hình ảnh hợp lệ (PNG, JPG, JPEG, WEBP)!", "error");
      return;
    }

    if (file.size > 12 * 1024 * 1024) {
      this.showToast("⚠️ Kích thước ảnh tối đa là 12MB. Vui lòng chọn ảnh nhỏ hơn!", "error");
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const dataUrl = e.target.result;

      // Update current user
      this.currentUser.avatar = dataUrl;
      this.currentUser.photo = dataUrl;

      // Update in MockData.users
      const u = (MockData.users || []).find(x => x.id === this.currentUser.id || x.name === this.currentUser.name);
      if (u) {
        u.avatar = dataUrl;
        u.photo = dataUrl;
      }

      // Update in MockData.player_profiles
      const prof = (MockData.player_profiles || []).find(p => p.user_id === this.currentUser.id || p.player_id === this.currentUser.id);
      if (prof) {
        prof.avatar = dataUrl;
        prof.photo = dataUrl;
      }

      // Update in active room if member/host
      if (this.activeRoom && this.activeRoom.players) {
        this.activeRoom.players.forEach(p => {
          if (p.name === this.currentUser.name || p.id === this.currentUser.id) {
            p.avatar = dataUrl;
            p.photo = dataUrl;
          }
        });
      }

      // Save to local storage
      if (typeof saveMockDataToLocalStorage === 'function') {
        saveMockDataToLocalStorage();
      }

      // Update visual avatars
      this.updateUserAvatarElements(dataUrl);
      this.executeMatchmakingEngine();
      if (this.activeRoom) {
        this.renderRoomDetailMembers();
        this.renderChatMessages();
      }

      this.showToast("📸 Đã cập nhật ảnh nhận diện thành công! Đối thủ ghép kèo giờ đây có thể nhận diện diện mạo của bạn.");
    };

    reader.readAsDataURL(file);
  }

  updateUserAvatarElements(photoUrl) {
    const avatarEl = document.getElementById('player-profile-avatar');
    if (avatarEl) {
      avatarEl.innerHTML = `<img src="${photoUrl}" alt="Avatar" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">`;
    }
    const faceStatusEl = document.getElementById('player-face-status');
    if (faceStatusEl) {
      faceStatusEl.innerHTML = `<i class="fa-solid fa-circle-check"></i> Đã có ảnh diện mạo`;
      faceStatusEl.style.color = "#16a34a";
    }
  }

  renderPlayerAvatarHtml(userOrPlayer, size = 36, extraStyle = "") {
    if (!userOrPlayer) return `<div class="avatar" style="width: ${size}px; height: ${size}px; border-radius: 50%; background: #64748b; color: #fff; display: inline-flex; align-items: center; justify-content: center;">👤</div>`;
    
    const photo = userOrPlayer.photo || userOrPlayer.avatar;
    const name = userOrPlayer.name || userOrPlayer.host_name || 'Đối thủ';
    const isPhotoUrl = photo && (photo.startsWith('data:image') || photo.startsWith('http') || photo.includes('/'));

    if (isPhotoUrl) {
      return `
        <div class="mm-avatar-container" style="display: inline-block; position: relative;">
          <img src="${photo}" alt="${name}" class="mm-avatar-img" style="width: ${size}px; height: ${size}px; border-radius: 50%; border: 2px solid #167946; box-shadow: 0 2px 6px rgba(0,0,0,0.12); ${extraStyle}" title="Bấm để xem ảnh nhận diện khuôn mặt của ${name}" onclick="event.stopPropagation(); app.showPlayerFaceModal('${name.replace(/'/g, "\\'")}', '${photo}')">
          <span class="mm-photo-badge" title="Đã có ảnh nhận diện"><i class="fa-solid fa-camera"></i></span>
        </div>
      `;
    }

    const initial = name.charAt(0).toUpperCase();
    return `
      <div class="avatar mm-avatar-fallback" style="width: ${size}px; height: ${size}px; font-size: ${Math.round(size * 0.42)}px; background: #167946; color: #fff; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-weight: 800; border: 2px solid #86efac; ${extraStyle}" title="${name}">
        ${initial}
      </div>
    `;
  }

  showPlayerFaceModal(playerName, photoUrl, tierName, notes) {
    const modalBody = document.getElementById('modal-body');
    if (!modalBody) return;

    const tier = this.getSkillTierInfo(tierName || 5);
    const hasPhoto = photoUrl && (photoUrl.startsWith('data:image') || photoUrl.startsWith('http') || photoUrl.includes('/'));
    const displayImg = hasPhoto ? photoUrl : 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=400&q=80';

    modalBody.innerHTML = `
      <div style="padding: 1rem 0; text-align: center;">
        <div style="margin-bottom: 1.25rem;">
          <h3 style="margin: 0 0 4px; color: #0f172a; font-size: 1.25rem; display: flex; align-items: center; justify-content: center; gap: 8px;">
            <i class="fa-solid fa-id-badge text-primary"></i> Nhận Diện Khuôn Mặt & Ngoại Hình Đối Thủ
          </h3>
          <p style="margin: 0; font-size: 0.84rem; color: #64748b;">
            Giúp bạn dễ dàng nhận diện đối thủ khi đến điểm hẹn tại sân cầu lông
          </p>
        </div>

        <div class="player-face-card-preview" style="max-width: 420px; margin: 0 auto; background: #ffffff; border: 2px solid #86efac; box-shadow: 0 10px 30px rgba(0,0,0,0.06);">
          <img src="${displayImg}" alt="${playerName}" class="player-face-modal-img" style="width: 170px; height: 170px; border-radius: 50%; object-fit: cover; border: 4px solid #167946; box-shadow: 0 8px 24px rgba(22, 121, 70, 0.25);">
          
          <h2 style="margin: 0 0 6px; font-size: 1.35rem; color: #0f172a; font-weight: 800;">${playerName}</h2>
          
          <div style="margin-bottom: 12px;">
            <span class="tier-badge-pill" style="background: ${tier.bg}; color: ${tier.color}; font-size: 0.85rem; padding: 4px 14px; font-weight: 800;">
              ${tier.display}
            </span>
          </div>

          <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 10px; padding: 12px 14px; text-align: left; font-size: 0.82rem; color: #166534; line-height: 1.5; margin-bottom: 12px; width: 100%;">
            <div style="font-weight: 700; margin-bottom: 4px;"><i class="fa-solid fa-circle-check"></i> Xác Thực Ngoại Hình Người Chơi:</div>
            <div>• Cấp bậc trình độ: <strong>${tier.name}</strong> (${tier.desc})</div>
            <div>• Trạng thái nhận diện: <strong style="color: #16a34a;">Đã xác nhận ảnh chụp thực tế</strong></div>
          </div>

          <div style="font-size: 0.8rem; color: #475569; line-height: 1.5; text-align: left; background: #f8fafc; padding: 10px 12px; border-radius: 8px; border: 1px solid #e2e8f0; width: 100%;">
            💡 <strong>Gợi ý nhận diện tại sân:</strong> Bạn hãy quan sát khuôn mặt này tại khu vực ghế chờ hoặc bảng số sân để chào hỏi và bắt đầu trận đấu giao lưu đúng giờ!
          </div>
        </div>

        <div style="margin-top: 1.5rem; display: flex; justify-content: center; gap: 10px;">
          <button class="btn btn-secondary" onclick="app.closeModal()">Đóng Cửa Sổ</button>
          ${this.currentUser && this.currentUser.name === playerName ? `
            <button class="btn btn-primary" onclick="app.closeModal(); app.triggerPlayerPhotoUpload();" style="background: #167946;">
              <i class="fa-solid fa-camera"></i> Đổi Ảnh Nhận Diện Khác
            </button>
          ` : ''}
        </div>
      </div>
    `;

    this.openModal();
  }

  // =========================================================================
  // 7 SKILL TIERS GUIDE & SELECTION MODAL
  // =========================================================================
  showEloTiersGuideModal() {
    const modalBody = document.getElementById('modal-body');
    if (!modalBody) return;

    const currentTierVal = (this.currentUser && (this.currentUser.skill_tier_id || this.currentUser.skill_tier || this.currentUser.elo_rating)) || 5;
    const currentTier = this.getSkillTierInfo(currentTierVal);
    const tiers = App.SKILL_TIERS;

    let rowsHtml = '';
    tiers.forEach(t => {
      const isSelected = currentTier.tier === t.tier;
      rowsHtml += `
        <tr style="border-bottom: 1px solid #e2e8f0; background: ${isSelected ? '#f0fdf4' : 'transparent'}; transition: background 0.2s ease;">
          <td style="padding: 12px 10px; font-weight: 800;">
            <span style="background: ${t.bg}; color: ${t.color}; font-size: 0.82rem; padding: 3px 9px; border-radius: 6px; border: 1px solid ${t.borderColor || '#cbd5e1'};">
              Cấp ${t.tier}
            </span>
          </td>
          <td style="padding: 12px 10px; font-weight: 800; color: ${t.color}; font-size: 0.95rem;">
            ${t.name}
          </td>
          <td style="padding: 12px 10px; font-size: 0.83rem; color: #475569; line-height: 1.4;">
            ${t.desc}
          </td>
          <td style="padding: 12px 10px; text-align: center;">
            <span class="badge" style="background: ${t.bg}; color: ${t.color}; font-weight: 700; font-size: 0.75rem;">
              Cân kèo Cấp ${t.tier}
            </span>
          </td>
          <td style="padding: 12px 10px; text-align: right;">
            ${isSelected ? `
              <span style="color: #16a34a; font-weight: 800; font-size: 0.82rem; display: inline-flex; align-items: center; gap: 4px;">
                <i class="fa-solid fa-circle-check"></i> Đang Chọn
              </span>
            ` : `
              <button class="btn btn-xs btn-outline-primary" onclick="app.applyCustomPlayerSkillTier(${t.tier}); app.closeModal();" style="font-weight: 700; padding: 4px 10px;">
                Chọn Cấp Này
              </button>
            `}
          </td>
        </tr>
      `;
    });

    const userPhoto = (this.currentUser && (this.currentUser.photo || this.currentUser.avatar)) || '';
    const hasPhoto = userPhoto && (userPhoto.startsWith('data:image') || userPhoto.startsWith('http') || userPhoto.includes('/'));

    modalBody.innerHTML = `
      <div style="padding: 0.5rem 0;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 8px;">
          <div>
            <h3 style="margin: 0; color: #0f172a; font-size: 1.25rem; display: flex; align-items: center; gap: 8px;">
              <i class="fa-solid fa-layer-group text-primary"></i> Bảng 7 Cấp Bậc Trình Độ Ghép Kèo AI
            </h3>
            <p style="margin: 4px 0 0; font-size: 0.82rem; color: #64748b;">
              Hệ thống tự động xét kèo cân đối cùng hạng mức trình độ - Không áp dụng điểm số phức tạp
            </p>
          </div>
          <span style="background: ${currentTier.bg}; color: ${currentTier.color}; font-size: 0.82rem; font-weight: 800; padding: 5px 12px; border-radius: 9999px; border: 1.5px solid ${currentTier.color};">
            Cấp bậc của bạn: ${currentTier.name}
          </span>
        </div>

        <div style="overflow-x: auto; margin-bottom: 1.25rem; border: 1px solid #e2e8f0; border-radius: 12px;">
          <table class="table" style="width: 100%; border-collapse: collapse; font-size: 0.85rem; margin: 0;">
            <thead>
              <tr style="background: #f8fafc; border-bottom: 2px solid #cbd5e1; text-align: left;">
                <th style="padding: 10px;">Hạng</th>
                <th style="padding: 10px;">Cấp Bậc Trình Độ</th>
                <th style="padding: 10px;">Đặc Điểm & Kỹ Năng Thi Đấu</th>
                <th style="padding: 10px; text-align: center;">Quy Chuẩn AI</th>
                <th style="padding: 10px; text-align: right;">Hành Động</th>
              </tr>
            </thead>
            <tbody>
              ${rowsHtml}
            </tbody>
          </table>
        </div>

        <!-- Section: Personal Photo Upload for Opponent Recognition -->
        <div style="background: linear-gradient(135deg, #f0fdf4 0%, #eff6ff 100%); border: 1.5px solid #86efac; border-radius: 12px; padding: 14px; margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
          <div style="display: flex; align-items: center; gap: 12px;">
            ${hasPhoto ? `
              <img src="${userPhoto}" alt="Avatar" style="width: 48px; height: 48px; border-radius: 50%; object-fit: cover; border: 2.5px solid #167946; box-shadow: 0 4px 10px rgba(0,0,0,0.12);">
            ` : `
              <div style="width: 48px; height: 48px; border-radius: 50%; background: #167946; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; font-weight: 800;">
                ${this.currentUser ? this.currentUser.name.charAt(0) : '👤'}
              </div>
            `}
            <div>
              <strong style="color: #0f172a; font-size: 0.9rem; display: flex; align-items: center; gap: 6px;">
                <i class="fa-solid fa-camera text-primary"></i> Ảnh Nhận Diện Ngoại Hình Của Bạn
              </strong>
              <div style="font-size: 0.78rem; color: #475569; margin-top: 2px;">
                Tải ảnh khuôn mặt từ thiết bị để đối thủ nhận diện và tìm thấy bạn dễ dàng khi đến sân.
              </div>
            </div>
          </div>
          <div>
            <button class="btn btn-primary btn-sm" onclick="app.closeModal(); app.triggerPlayerPhotoUpload();" style="background: #0284c7; font-weight: 700;">
              <i class="fa-solid fa-arrow-up-from-bracket"></i> ${hasPhoto ? 'Đổi Ảnh Từ Thiết Bị' : 'Tải Ảnh Lên Ngay'}
            </button>
          </div>
        </div>

        <div style="display: flex; gap: 8px; justify-content: flex-end;">
          <button class="btn btn-secondary btn-sm" onclick="app.closeModal()">Đóng Bảng</button>
        </div>
      </div>
    `;

    this.openModal();
  }

  applyCustomPlayerSkillTier(tierId) {
    if (!this.currentUser) {
      this.showToast("⚠️ Bạn chưa đăng nhập! Vui lòng Đăng Nhập hoặc Đăng Ký tài khoản để chọn cấp bậc trình độ.", "error");
      this.navigateTo('ui-01');
      return;
    }

    const tier = this.getSkillTierInfo(tierId);
    this.currentUser.skill_tier_id = tier.tier;
    this.currentUser.skill_tier = tier.name;
    this.currentUser.elo_rating = tier.defaultElo || 1650;

    // Update in MockData.users and MockData.player_profiles
    const u = (MockData.users || []).find(x => x.id === this.currentUser.id || x.name === this.currentUser.name);
    if (u) {
      u.skill_tier = tier.name;
      u.skill_tier_id = tier.tier;
      u.elo_rating = tier.defaultElo || 1650;
    }
    const prof = (MockData.player_profiles || []).find(p => p.user_id === this.currentUser.id || p.player_id === this.currentUser.id);
    if (prof) {
      prof.skill_level = tier.name;
      prof.current_elo = tier.defaultElo || 1650;
    }

    // Update visual badge in UI-06
    const tierBadge = document.getElementById('player-profile-tier');
    if (tierBadge) {
      tierBadge.textContent = tier.display;
      tierBadge.style.color = tier.color;
      tierBadge.style.background = tier.bg;
    }

    if (typeof saveMockDataToLocalStorage === 'function') {
      saveMockDataToLocalStorage();
    }

    this.showToast(`🎯 Bạn đã chọn trình độ: ${tier.display}! AI đang tự động lọc các kèo đấu cùng hạng mức...`);
    this.executeMatchmakingEngine();
  }

  // Legacy fallback proxy
  applyCustomPlayerElo(newElo) {
    const tier = this.getSkillTierInfo(newElo);
    this.applyCustomPlayerSkillTier(tier.tier);
  }

  promptCustomPlayerElo() {
    this.showEloTiersGuideModal();
  }

  switchDemoPlayerElo(newElo) {
    const tier = this.getSkillTierInfo(newElo);
    this.applyCustomPlayerSkillTier(tier.tier);
  }

  handleMatchTypeChange(val) {
    this.currentMatchType = val;
    this.executeMatchmakingEngine();
  }

  expandRadarRangeStep() {
    this.currentWaitTimer = (this.currentWaitTimer || 0) + 30;
    if (this.currentWaitTimer > 90) this.currentWaitTimer = 0;

    const rangeBadge = document.getElementById('dynamic-range-badge');
    const waitTimerEl = document.getElementById('dynamic-wait-timer');
    const matchingSelect = document.getElementById('finder-skill-matching');

    if (this.currentWaitTimer === 0) {
      if (rangeBadge) rangeBadge.textContent = "Hạng mức: Cùng cấp bậc";
      if (matchingSelect) matchingSelect.value = "same";
      this.showToast("🎯 Radar AI: Đang quét người chơi cùng hạng mức tuyệt đối (100% cân kèo)!");
    } else if (this.currentWaitTimer <= 30) {
      if (rangeBadge) rangeBadge.textContent = "Hạng mức: Lệch tối đa 1 cấp (+Chấp điểm)";
      if (matchingSelect) matchingSelect.value = "adjacent";
      this.showToast("⚖️ Radar AI mở rộng: Quét người chơi cùng hạng mức hoặc chênh lệch tối đa 1 cấp (+3 điểm chấp)!");
    } else {
      if (rangeBadge) rangeBadge.textContent = "Hạng mức: Mở rộng giao lưu mọi cấp";
      if (matchingSelect) matchingSelect.value = "all";
      this.showToast("🌐 Radar AI mở rộng tối đa: Giao lưu với mọi cấp bậc trình độ!");
    }

    if (waitTimerEl) waitTimerEl.textContent = `(Chờ: ${this.currentWaitTimer}s)`;
    this.executeMatchmakingEngine();
  }

  // =========================================================================
  // CORE AI MATCHMAKING ENGINE: 7 SKILL TIERS AUTO-BALANCING
  // =========================================================================
  executeMatchmakingEngine() {
    const container = document.getElementById('matchmaking-rooms-grid');
    if (!container) return;

    const isGuest = !this.currentUser;
    const userTierVal = (!isGuest && (this.currentUser.skill_tier_id || this.currentUser.skill_tier || this.currentUser.elo_rating)) || 5;
    const userTier = this.getSkillTierInfo(userTierVal);
    const userName = !isGuest ? this.currentUser.name : "Khách (Chưa đăng nhập)";

    // Sync UI-06 profile card with actual logged-in user or guest state
    const profileNameEl = document.getElementById('player-profile-name');
    const profileAvatarContainer = document.getElementById('player-profile-avatar-container');
    const profileTierEl = document.getElementById('player-profile-tier');
    const faceStatusEl = document.getElementById('player-face-status');

    if (profileNameEl) {
      if (isGuest) {
        profileNameEl.innerHTML = `<span style="color: #64748b;">Khách (Chưa đăng nhập)</span> <button class="btn btn-xs btn-primary" onclick="app.navigateTo('ui-01')" style="margin-left: 8px; font-size: 0.75rem; padding: 2px 8px; background: #167946;"><i class="fa-solid fa-right-to-bracket"></i> Đăng Nhập</button>`;
      } else {
        profileNameEl.textContent = this.currentUser.name;
      }
    }

    if (profileAvatarContainer && !isGuest) {
      const photo = this.currentUser.photo || this.currentUser.avatar;
      const isPhotoUrl = photo && (photo.startsWith('data:image') || photo.startsWith('http') || photo.includes('/'));
      if (isPhotoUrl) {
        profileAvatarContainer.innerHTML = `
          <img src="${photo}" alt="Avatar" class="mm-avatar-img" style="width: 36px; height: 36px; border-radius: 50%; object-fit: cover; border: 2px solid #167946; box-shadow: 0 2px 6px rgba(0,0,0,0.12);">
          <span class="mm-photo-badge" title="Tải ảnh nhận diện"><i class="fa-solid fa-camera"></i></span>
        `;
      } else {
        profileAvatarContainer.innerHTML = `
          <div class="avatar" id="player-profile-avatar" style="width: 36px; height: 36px; font-size: 0.95rem; background: #167946; color: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 800; border: 2px solid #86efac;">
            ${this.currentUser.name ? this.currentUser.name.charAt(0) : 'H'}
          </div>
          <span class="mm-photo-badge" title="Tải ảnh nhận diện"><i class="fa-solid fa-camera"></i></span>
        `;
      }
    }

    if (profileTierEl) {
      profileTierEl.textContent = userTier.display;
      profileTierEl.style.color = userTier.color;
      profileTierEl.style.background = userTier.bg;
      profileTierEl.style.borderColor = userTier.borderColor || '#cbd5e1';
    }

    if (faceStatusEl) {
      const hasPhoto = this.currentUser && (this.currentUser.photo || (this.currentUser.avatar && (this.currentUser.avatar.startsWith('data:image') || this.currentUser.avatar.startsWith('http'))));
      if (hasPhoto) {
        faceStatusEl.innerHTML = `<i class="fa-solid fa-circle-check"></i> Đã tải ảnh diện mạo`;
        faceStatusEl.style.color = "#16a34a";
      } else {
        faceStatusEl.innerHTML = `<i class="fa-solid fa-circle-exclamation text-amber"></i> Chưa có ảnh khuôn mặt`;
        faceStatusEl.style.color = "#d97706";
      }
    }

    const skillMatchingFilter = document.getElementById('finder-skill-matching')?.value || 'same';
    const matchTypeEl = document.getElementById('finder-match-type');
    const matchType = matchTypeEl ? matchTypeEl.value : 'DOUBLES';
    const preferredArea = document.getElementById('finder-area')?.value || 'Hoàng Mai';
    const preferredTime = document.getElementById('finder-time')?.value || '18:00 - 20:00';

    let candidatePool = [];

    // 1. Gather other players
    (MockData.users || []).forEach(u => {
      if (u.role === 'CUSTOMER' && u.name !== userName) {
        const uTier = this.getSkillTierInfo(u.skill_tier_id || u.skill_tier || u.elo_rating || 5);
        const tierDiff = Math.abs(userTier.tier - uTier.tier);

        let isMatchAllowed = false;
        if (skillMatchingFilter === 'same') {
          isMatchAllowed = (tierDiff === 0);
        } else if (skillMatchingFilter === 'adjacent') {
          isMatchAllowed = (tierDiff <= 1);
        } else {
          isMatchAllowed = true;
        }

        if (isMatchAllowed) {
          // Calculate MatchScore: Tier (50%), Time (25%), Location (25%)
          const sSkill = tierDiff === 0 ? 100.0 : (tierDiff === 1 ? 85.0 : Math.max(30, 70 - tierDiff * 15));
          const sTime = 95.0;
          const sLoc = 90.0;
          const matchScore = Math.round(sSkill * 0.50 + sTime * 0.25 + sLoc * 0.25);

          // Win rate estimation based on skill rank
          let winRateA = 50;
          let winRateB = 50;
          if (tierDiff === 1) {
            if (userTier.tier > uTier.tier) { winRateA = 58; winRateB = 42; }
            else { winRateA = 42; winRateB = 58; }
          } else if (tierDiff >= 2) {
            if (userTier.tier > uTier.tier) { winRateA = 70; winRateB = 30; }
            else { winRateA = 30; winRateB = 70; }
          }

          candidatePool.push({
            id: u.id,
            name: u.name,
            photo: u.photo || u.avatar,
            avatar: u.avatar,
            tier: uTier,
            tierDiff: tierDiff,
            matchScore: matchScore,
            subScores: {
              tier: tierDiff === 0 ? "Cùng cấp" : `Lệch ${tierDiff} cấp`,
              time: "95%",
              loc: "90%",
              balance: tierDiff === 0 ? "100% Cân kèo" : (tierDiff === 1 ? "Kèo lệch 1 cấp" : "Kèo thách đấu")
            },
            winRateA: winRateA,
            winRateB: winRateB,
            matchType: matchType,
            facility: preferredArea === 'Hoàng Mai' ? 'CLB Catchy Badminton Arena' : 'CLB Cầu Giấy Pro Center',
            time: preferredTime,
            isRoom: false
          });
        }
      }
    });

    // 2. Gather Matchmaking Rooms
    (MockData.matchmaking_rooms || []).forEach(r => {
      const rTier = this.getSkillTierInfo(r.required_tier_id || r.required_tier || r.host_tier || r.required_elo_min || 5);
      const tierDiff = Math.abs(userTier.tier - rTier.tier);

      let isMatchAllowed = false;
      if (skillMatchingFilter === 'same') {
        isMatchAllowed = (tierDiff === 0);
      } else if (skillMatchingFilter === 'adjacent') {
        isMatchAllowed = (tierDiff <= 1);
      } else {
        isMatchAllowed = true;
      }

      if (isMatchAllowed) {
        const sSkill = tierDiff === 0 ? 100.0 : (tierDiff === 1 ? 88.0 : Math.max(35, 75 - tierDiff * 15));
        const sTime = 95.0;
        const sLoc = (r.district && r.district.includes(preferredArea)) ? 100.0 : 85.0;
        const matchScore = Math.round(sSkill * 0.50 + sTime * 0.25 + sLoc * 0.25);

        let winRateA = 50;
        let winRateB = 50;
        if (tierDiff === 1) {
          if (userTier.tier > rTier.tier) { winRateA = 56; winRateB = 44; }
          else { winRateA = 44; winRateB = 56; }
        } else if (tierDiff >= 2) {
          if (userTier.tier > rTier.tier) { winRateA = 68; winRateB = 32; }
          else { winRateA = 32; winRateB = 68; }
        }

        candidatePool.push({
          id: r.id,
          roomId: r.id,
          name: r.room_name,
          hostName: r.host_name,
          photo: r.host_photo || (r.players && r.players[0] && r.players[0].photo) || null,
          avatar: (r.players && r.players[0] && r.players[0].avatar) || 'R',
          tier: rTier,
          tierDiff: tierDiff,
          matchScore: matchScore,
          subScores: {
            tier: tierDiff === 0 ? "Cùng cấp" : `Lệch ${tierDiff} cấp`,
            time: "95%",
            loc: "100%",
            balance: tierDiff === 0 ? "100% Cân kèo" : (tierDiff === 1 ? "Kèo chấp điểm" : "Kèo thách đấu")
          },
          winRateA: winRateA,
          winRateB: winRateB,
          matchType: r.match_type,
          facility: r.facility_name,
          time: `${r.match_date} (${r.match_time})`,
          isRoom: true,
          roomObj: r
        });
      }
    });

    // Apply sorting
    const sortBy = this.currentMMSort || 'ai-match';
    if (sortBy === 'tier-asc') {
      candidatePool.sort((a, b) => a.tier.tier - b.tier.tier);
    } else if (sortBy === 'tier-desc') {
      candidatePool.sort((a, b) => b.tier.tier - a.tier.tier);
    } else {
      candidatePool.sort((a, b) => b.matchScore - a.matchScore);
    }

    // Update total count
    const countEl = document.getElementById('mm-total-count');
    if (countEl) countEl.textContent = candidatePool.length;

    // Narrative Insight
    const narrativeEl = document.getElementById('ai-recom-narrative');
    const matchBadge = document.getElementById('ai-recom-match-badge');

    if (candidatePool.length > 0) {
      const best = candidatePool[0];
      if (matchBadge) matchBadge.textContent = `🎯 Khớp ${best.matchScore}% (${best.tierDiff === 0 ? 'Cùng cấp bậc hoàn hảo' : 'Lệch ' + best.tierDiff + ' cấp'})`;
      if (narrativeEl) {
        narrativeEl.innerHTML = `
          <strong>AI Recommendation:</strong> Bạn thuộc cấp <strong>[${userTier.name}]</strong>. 
          Hệ thống đề xuất tốt nhất với <strong>${best.name} (${best.tier.display})</strong> đạt độ phù hợp 
          <strong style="color: #16a34a;">${best.matchScore}%</strong>. 
          ${best.tierDiff === 0 ? 'Hai bên cùng hạng mức trình độ, tỉ lệ cân bằng 50% - 50%.' : `Chênh lệch ${best.tierDiff} cấp, AI đề xuất cơ chế chấp điểm công bằng.`}
          Cả hai đều có ảnh nhận diện để gặp nhau tại <strong>${best.facility}</strong>.
        `;
      }
    } else {
      if (narrativeEl) narrativeEl.innerHTML = `Chưa tìm thấy phòng ghép cùng cấp <strong>[${userTier.name}]</strong>. Hãy nhấn <strong>"Nới Rộng Cấp Bậc"</strong> hoặc chọn mục <strong>"Cho phép lệch tối đa 1 cấp"</strong> để tìm bạn chơi nhanh chóng!`;
    }

    // Render Cards in Grid
    let html = '';
    candidatePool.forEach(cand => {
      let badgeBg = '#16a34a';
      if (cand.matchScore < 85) badgeBg = '#ca8a04';
      if (cand.matchScore < 75) badgeBg = '#dc2626';

      const hasPhoto = cand.photo && (cand.photo.startsWith('data:image') || cand.photo.startsWith('http') || cand.photo.includes('/'));

      html += `
        <div class="mm-room-card">
          <div class="mm-card-header" style="background: ${cand.matchScore >= 90 ? 'linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%)' : '#f8fafc'};">
            <span style="background: ${badgeBg}; color: #fff; font-weight: 800; font-size: 0.78rem; padding: 4px 10px; border-radius: 9999px; display: inline-flex; align-items: center; gap: 5px;">
              <i class="fa-solid fa-wand-magic-sparkles"></i> Khớp ${cand.matchScore}%
            </span>
            <div style="display: flex; gap: 6px; align-items: center;">
              <span class="badge ${cand.matchType.includes('Đôi') ? 'badge-info' : 'badge-warning'}" style="font-size: 0.72rem; padding: 3px 8px;">
                ${cand.matchType.includes('Đôi') ? '🏸 Đôi 2v2' : '⚡ Đơn 1v1'}
              </span>
              <span class="tier-badge-pill" style="background: ${cand.tier.bg}; color: ${cand.tier.color}; border: 1px solid ${cand.tier.borderColor || '#cbd5e1'};">
                ${cand.tier.badgeText || cand.tier.name}
              </span>
            </div>
          </div>

          <div class="mm-card-body">
            <div style="display: flex; gap: 12px; align-items: flex-start;">
              <!-- Player/Host Photo -->
              <div style="position: relative; flex-shrink: 0; cursor: pointer;" onclick="app.showPlayerFaceModal('${(cand.hostName || cand.name).replace(/'/g, "\\'")}', '${hasPhoto ? cand.photo : ''}', '${cand.tier.name}')">
                ${hasPhoto ? `
                  <img src="${cand.photo}" alt="${cand.hostName || cand.name}" class="mm-avatar-img" style="width: 52px; height: 52px; border-radius: 50%; object-fit: cover; border: 2.5px solid #167946; box-shadow: 0 4px 10px rgba(0,0,0,0.12);">
                  <span class="mm-photo-badge" title="Đã có ảnh nhận diện"><i class="fa-solid fa-camera"></i></span>
                ` : `
                  <div class="avatar" style="width: 52px; height: 52px; font-size: 1.25rem; background: #167946; color: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 800; border: 2.5px solid #86efac;">
                    ${(cand.hostName || cand.name).charAt(0)}
                  </div>
                `}
              </div>

              <!-- Information -->
              <div style="flex: 1; min-width: 0;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 6px; margin-bottom: 4px;">
                  <h3 style="margin: 0; font-size: 1.05rem; font-weight: 800; color: #0f172a; line-height: 1.3;">${cand.name}</h3>
                </div>
                <div style="font-size: 0.78rem; color: #64748b; margin-bottom: 4px;">
                  ${cand.isRoom ? `Chủ phòng: <strong style="color: #0f172a;">${cand.hostName}</strong>` : `Đấu thủ: <strong style="color: #0f172a;">${cand.name}</strong>`}
                  • <span style="color: ${cand.tier.color}; font-weight: 700;">${cand.tier.display}</span>
                </div>
                <div style="font-size: 0.8rem; color: #64748b; line-height: 1.4;">
                  <div><i class="fa-solid fa-location-dot text-rose" style="width: 14px;"></i> ${cand.facility}</div>
                  <div><i class="fa-solid fa-clock text-amber" style="width: 14px;"></i> ${cand.time}</div>
                </div>
              </div>
            </div>

            <!-- Multi-Criteria Breakdown -->
            <div class="mm-match-breakdown-row" style="margin-top: 8px;">
              <div class="mm-match-metric-box">
                <div class="mm-match-metric-label">Hạng Mức</div>
                <div class="mm-match-metric-value" style="color: ${cand.tierDiff === 0 ? '#166534' : '#ea580c'}; font-size: 0.76rem;">${cand.subScores.tier}</div>
              </div>
              <div class="mm-match-metric-box">
                <div class="mm-match-metric-label">Khung Giờ</div>
                <div class="mm-match-metric-value" style="color: #0284c7;">${cand.subScores.time}</div>
              </div>
              <div class="mm-match-metric-box">
                <div class="mm-match-metric-label">Cụm Sân</div>
                <div class="mm-match-metric-value" style="color: #e11d48;">${cand.subScores.loc}</div>
              </div>
              <div class="mm-match-metric-box">
                <div class="mm-match-metric-label">Cân Đối</div>
                <div class="mm-match-metric-value" style="color: #7c3aed; font-size: 0.76rem;">${cand.subScores.balance}</div>
              </div>
            </div>

            <!-- Predicted Win Rate Bar -->
            <div class="mm-winrate-container">
              <div class="mm-winrate-labels">
                <span style="color: #166534;"><i class="fa-solid fa-shield-halved"></i> Bạn: ${cand.winRateA}%</span>
                <span style="color: #1e40af;">Đối thủ: ${cand.winRateB}% <i class="fa-solid fa-bolt"></i></span>
              </div>
              <div class="mm-winrate-bar-track">
                <div style="width: ${cand.winRateA}%; height: 100%; background: linear-gradient(90deg, #10b981, #059669);"></div>
                <div style="width: ${cand.winRateB}%; height: 100%; background: linear-gradient(90deg, #3b82f6, #1d4ed8);"></div>
              </div>
            </div>
          </div>

          <div class="mm-card-footer">
            <span style="font-size: 0.8rem; font-weight: 700; color: ${cand.tierDiff === 0 ? '#166534' : '#b45309'}; display: flex; align-items: center; gap: 4px;">
              ${cand.tierDiff === 0 ? '<i class="fa-solid fa-circle-check"></i> Cùng hạng mức (Chuẩn 100%)' : `<i class="fa-solid fa-scale-balanced"></i> Lệch ${cand.tierDiff} cấp (Có chấp điểm)`}
            </span>
            <div style="display: flex; gap: 6px;">
              <button class="btn btn-secondary btn-sm" onclick="app.showPlayerFaceModal('${(cand.hostName || cand.name).replace(/'/g, "\\'")}', '${hasPhoto ? cand.photo : ''}', '${cand.tier.name}')" style="font-size: 0.78rem; padding: 4px 9px;" title="Xem ảnh khuôn mặt nhận diện đối thủ">
                <i class="fa-solid fa-camera"></i> Xem Diện Mạo
              </button>
              ${cand.isRoom ? `
                <button class="btn btn-primary btn-sm" onclick="app.openRoomChat(${cand.roomId})" style="background: #167946; font-size: 0.78rem; padding: 4px 12px; font-weight: 700;">
                  <i class="fa-solid fa-users"></i> Vào Phòng
                </button>
              ` : (isGuest ? `
                <button class="btn btn-primary btn-sm" onclick="app.navigateTo('ui-01')" style="background: #d97706; font-size: 0.78rem; padding: 4px 12px; font-weight: 700;">
                  <i class="fa-solid fa-right-to-bracket"></i> Đăng Nhập
                </button>
              ` : `
                <button class="btn btn-primary btn-sm" onclick="app.challengeOpponentPrompt('${cand.name}', '${cand.tier.name}')" style="background: linear-gradient(135deg, #167946, #059669); font-size: 0.78rem; padding: 4px 12px; font-weight: 700;">
                  <i class="fa-solid fa-bolt"></i> Ghép Kèo Ngay
                </button>
              `)}
            </div>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
  }

  challengeOpponentPrompt(opponentName, tierName) {
    if (!this.currentUser) {
      this.showToast("⚠️ Bạn chưa đăng nhập! Vui lòng Đăng Nhập để gửi yêu cầu ghép kèo.", "error");
      this.navigateTo('ui-01');
      return;
    }
    this.showToast(`🏸 Đã gửi lời mời ghép kèo giao lưu cùng hạng tới ${opponentName} (Cấp [${tierName}])!`);
  }

  renderMatchmakingRooms() {
    this.executeMatchmakingEngine();
  }

  // =========================================================================
  // 8. TWO-WAY RESULT CONFIRMATION & DISPUTE MODAL (Component 8 & 9)
  // =========================================================================
  getPendingMatches() {
    if (!MockData.matches || !Array.isArray(MockData.matches)) return [];
    return MockData.matches.filter(m => m.status === 'PENDING_CONFIRMATION');
  }

  updatePendingMatchesUI() {
    const pending = this.getPendingMatches();
    const count = pending.length;

    // Cập nhật số lượng trên các badge hiển thị
    document.querySelectorAll('.pending-match-count-badge').forEach(el => {
      el.textContent = count;
    });

    const statusTextEl = document.getElementById('anti-cheat-status-text');
    const openBtn = document.getElementById('btn-open-match-result');

    if (count > 0) {
      if (statusTextEl) {
        statusTextEl.innerHTML = `<span style="color: #b45309; font-weight: 700;">⚠️ Có ${count} trận đấu</span> đang chờ bạn đối soát & xác nhận kết quả 2 chiều để cộng/trừ ELO.`;
      }
      if (openBtn) {
        openBtn.className = "btn btn-secondary btn-sm";
        openBtn.style.border = "1.5px solid #dc2626";
        openBtn.style.color = "#dc2626";
        openBtn.style.background = "#fff1f2";
        openBtn.style.fontWeight = "700";
        openBtn.innerHTML = `<i class="fa-solid fa-clock-rotate-left"></i> Xem Trận Chờ Xác Nhận (<span class="pending-match-count-badge">${count}</span>)`;
      }
    } else {
      if (statusTextEl) {
        statusTextEl.innerHTML = `<span style="color: #16a34a; font-weight: 700;">✅ Không còn trận chờ:</span> Tất cả trận đấu đã đối soát hoàn tất hoặc đã gửi khiếu nại. ELO an toàn.`;
      }
      if (openBtn) {
        openBtn.className = "btn btn-secondary btn-sm";
        openBtn.style.border = "1.5px solid #10b981";
        openBtn.style.color = "#166534";
        openBtn.style.background = "#f0fdf4";
        openBtn.style.fontWeight = "700";
        openBtn.innerHTML = `<i class="fa-solid fa-circle-check text-success"></i> Đã Đối Soát Xong (0)`;
      }
    }
  }

  openMatchResultModal() {
    if (!this.currentUser) {
      this.showToast("⚠️ Bạn chưa đăng nhập! Vui lòng Đăng Nhập tài khoản để xem & xác nhận kết quả kèo đấu.", "error");
      this.navigateTo('ui-01');
      return;
    }
    const modalBody = document.getElementById('modal-body');
    if (!modalBody) return;

    const pending = this.getPendingMatches();
    if (!pending || pending.length === 0) {
      modalBody.innerHTML = `
        <div style="text-align: center; padding: 2rem 1rem;">
          <div style="width: 58px; height: 58px; border-radius: 50%; background: #dcfce7; color: #16a34a; font-size: 1.6rem; display: flex; align-items: center; justify-content: center; margin: 0 auto 12px; border: 2px solid #86efac;">
            <i class="fa-solid fa-circle-check"></i>
          </div>
          <h3 style="margin: 0 0 6px; font-size: 1.2rem; color: #0f172a; font-weight: 800;">Không Còn Trận Nào Chờ Xác Nhận</h3>
          <p style="font-size: 0.88rem; color: #64748b; max-width: 380px; margin: 0 auto 1.25rem; line-height: 1.5;">
            Tất cả các trận đấu của bạn đã được đối soát 2 chiều hoàn tất hoặc đã gửi khiếu nại tới ban trọng tài!
          </p>
          <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 10px 14px; font-size: 0.82rem; color: #334155; margin-bottom: 1.25rem; display: flex; align-items: center; justify-content: center; gap: 8px;">
            <i class="fa-solid fa-shield-check" style="color: #16a34a; font-size: 1.1rem;"></i>
            <span>Hệ thống Anti-Cheat ELO đang hoạt động bình thường, điểm ELO của bạn đã được bảo vệ.</span>
          </div>
          <button class="btn btn-primary" onclick="app.closeModal()" style="min-width: 140px; font-weight: 700; background: #167946;">
            <i class="fa-solid fa-check"></i> Đã Hiểu & Đóng
          </button>
        </div>
      `;
      this.openModal();
      return;
    }

    const match = pending[0];
    const matchId = match.id;
    const playerA = match.player_a_name || "Nguyễn Văn Hùng";
    const playerAElo = match.player_a_elo || 1450;
    const playerAGain = match.player_a_gain || 16;
    const playerB = match.player_b_name || "Đỗ Minh Đức";
    const playerBElo = match.player_b_elo || 1520;
    const playerBGain = match.player_b_gain || -16;
    const finalScore = match.final_score || "21-18, 19-21, 21-19";
    const matchDate = match.match_date || "29/09/2026 (18:30 - 19:30)";
    const reporter = match.reporter_name || playerA;
    const summary = match.summary || `${playerA} thắng chung cuộc 2 - 1`;

    modalBody.innerHTML = `
      <div style="padding: 0.5rem 0;">
        <div style="text-align: center; margin-bottom: 1.25rem;">
          <div style="width: 52px; height: 52px; border-radius: 50%; background: #f0fdf4; color: #16a34a; font-size: 1.4rem; display: flex; align-items: center; justify-content: center; margin: 0 auto 8px; border: 2px solid #86efac;">
            <i class="fa-solid fa-trophy"></i>
          </div>
          <h3 style="margin: 0; font-size: 1.2rem; color: #0f172a; font-weight: 800;">Xác Nhận Kết Quả Trận Đấu & Cập Nhật ELO</h3>
          <p style="font-size: 0.84rem; color: #64748b; margin: 4px 0 0;">Quy trình 2 bên đối soát: Không cho phép tự ý cộng ELO nếu đối thủ chưa thống nhất</p>
        </div>

        <!-- Pending Match Banner -->
        <div style="background: #fffbeb; border: 1.5px solid #fde68a; border-radius: 12px; padding: 12px; margin-bottom: 1.25rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <span style="background: #fef3c7; color: #b45309; font-weight: 800; font-size: 0.75rem; padding: 2px 8px; border-radius: 6px;">
              Trận #${matchId} • Chờ Xác Nhận
            </span>
            <span style="font-size: 0.78rem; color: #78350f;">${matchDate}</span>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.92rem; font-weight: 800; color: #0f172a; margin-bottom: 6px;">
            <span>${playerA} (ELO ${playerAElo})</span>
            <span style="color: #ea580c; font-size: 1.1rem;">VS</span>
            <span>${playerB} (ELO ${playerBElo})</span>
          </div>
          <div style="background: #ffffff; border-radius: 8px; padding: 8px 12px; border: 1px solid #fcd34d; font-size: 0.84rem; color: #92400e;">
            📝 <strong>Kết quả do ${reporter} khai báo:</strong> Tỷ số <strong>${finalScore}</strong> (${summary}).
          </div>
        </div>

        <!-- Simulated Potential ELO changes -->
        <div style="background: #f8fafc; border-radius: 12px; padding: 12px; border: 1px solid #e2e8f0; margin-bottom: 1.25rem; font-size: 0.84rem;">
          <div style="font-weight: 700; color: #334155; margin-bottom: 6px;"><i class="fa-solid fa-chart-line text-primary"></i> Dự kiến biến động ELO (K=24):</div>
          <div style="display: flex; justify-content: space-between; line-height: 1.6;">
            <div>• ${playerA}: <strong style="color: #16a34a;">+${playerAGain} ELO</strong> (${playerAElo} ➔ ${playerAElo + playerAGain})</div>
            <div>• ${playerB}: <strong style="color: #ef4444;">${playerBGain} ELO</strong> (${playerBElo} ➔ ${playerBElo + playerBGain})</div>
          </div>
        </div>

        <!-- Anti-cheat Shield Tag -->
        <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 8px 12px; margin-bottom: 1.5rem; font-size: 0.8rem; color: #166534; display: flex; align-items: center; gap: 8px;">
          <i class="fa-solid fa-shield-check" style="font-size: 1.1rem; color: #16a34a;"></i>
          <span><strong>Anti-Cheat Guard:</strong> Không phát hiện cày điểm lặp lại (Win-Trading) hoặc tỷ lệ thắng dị thường.</span>
        </div>

        <!-- 2 Actions: Agree or Dispute -->
        <div style="display: flex; gap: 10px;">
          <button class="btn btn-primary" style="flex: 1; background: #167946; font-weight: 700;" onclick="app.confirmMatchResultAction(${matchId}, true)">
            <i class="fa-solid fa-circle-check"></i> Xác Nhận & Cập Nhật ELO
          </button>
          <button class="btn btn-secondary" style="border: 1.5px solid #ef4444; color: #dc2626; font-weight: 700;" onclick="app.confirmMatchResultAction(${matchId}, false)">
            <i class="fa-solid fa-triangle-exclamation"></i> Khiếu Nại Tranh Chấp
          </button>
        </div>
      </div>
    `;

    this.openModal();
  }

  confirmMatchResultAction(matchId, isAgreed) {
    this.closeModal();

    if (!this.currentUser) {
      this.showToast("⚠️ Bạn chưa đăng nhập! Vui lòng Đăng Nhập để xác nhận kết quả kèo đấu.", "error");
      this.navigateTo('ui-01');
      return;
    }

    if (!MockData.matches) MockData.matches = [];
    const targetMatch = MockData.matches.find(m => m.id === matchId);

    if (isAgreed) {
      if (targetMatch) {
        targetMatch.status = 'CONFIRMED';
        targetMatch.confirmed_at = new Date().toISOString().replace('T', ' ').substring(0, 19);
      }

      if (MockData.match_players) {
        MockData.match_players.filter(mp => mp.match_id === matchId).forEach(mp => {
          mp.confirmation_status = 'CONFIRMED';
        });
      }

      const oldElo = this.currentUser.elo_rating || 1200;
      const eloGain = (targetMatch && targetMatch.player_a_gain) ? targetMatch.player_a_gain : 16;
      const newElo = oldElo + eloGain;
      this.currentUser.elo_rating = newElo;

      // Cập nhật bảng users
      const u = (MockData.users || []).find(user => user.id === this.currentUser.id || user.phone === this.currentUser.phone);
      if (u) u.elo_rating = newElo;

      // Cập nhật bảng player_profiles
      if (!MockData.player_profiles) MockData.player_profiles = [];
      let prof = MockData.player_profiles.find(p => p.user_id === this.currentUser.id);
      if (prof) {
        prof.current_elo = newElo;
        prof.games_played = (prof.games_played || 0) + 1;
        prof.wins = (prof.wins || 0) + 1;
        prof.streak = "+1W";
      }

      // Thêm vào bảng elo_histories
      if (!MockData.elo_histories) MockData.elo_histories = [];
      MockData.elo_histories.unshift({
        id: Date.now(),
        player_id: this.currentUser.id || 1,
        match_id: matchId || 103,
        old_elo: oldElo,
        new_elo: newElo,
        elo_change: eloGain,
        reason: targetMatch ? `Thắng trận Đơn vs ${targetMatch.player_b_name} (${targetMatch.final_score})` : "Thắng trận Đơn vs Đỗ Minh Đức (21-18, 19-21, 21-19)",
        opponent_info: targetMatch ? `${targetMatch.player_b_name} (ELO ${targetMatch.player_b_elo})` : "Đỗ Minh Đức (ELO 1520)",
        created_at: new Date().toISOString().replace('T', ' ').substring(0, 19)
      });

      this.switchDemoPlayerElo(newElo);
      this.updatePendingMatchesUI();
      if (typeof saveMockDataToLocalStorage === 'function') saveMockDataToLocalStorage();

      this.showToast(`🎉 Hai bên đã thống nhất kết quả trận #${matchId}! Điểm ELO của bạn đã cập nhật lên ${newElo} (+${eloGain} ELO) và trận đấu đã hoàn tất!`);
    } else {
      if (targetMatch) {
        targetMatch.status = 'DISPUTED';
        targetMatch.disputed_at = new Date().toISOString().replace('T', ' ').substring(0, 19);
      }

      if (MockData.match_players) {
        MockData.match_players.filter(mp => mp.match_id === matchId).forEach(mp => {
          mp.confirmation_status = 'DISPUTED';
        });
      }

      this.updatePendingMatchesUI();
      if (typeof saveMockDataToLocalStorage === 'function') saveMockDataToLocalStorage();

      this.showToast(`⚠️ Đã ghi nhận khiếu nại tranh chấp trận #${matchId}! Trận đấu đã được gỡ khỏi danh sách chờ, điểm ELO bị đóng băng chuyển ban trọng tài xem xét.`);
    }
  }

  runAntiCheatAudit() {
    const modalBody = document.getElementById('modal-body');
    if (!modalBody) return;

    modalBody.innerHTML = `
      <div style="padding: 0.5rem 0;">
        <div style="text-align: center; margin-bottom: 1.25rem;">
          <div style="width: 52px; height: 52px; border-radius: 50%; background: #eff6ff; color: #2563eb; font-size: 1.4rem; display: flex; align-items: center; justify-content: center; margin: 0 auto 8px; border: 2px solid #93c5fd;">
            <i class="fa-solid fa-shield-virus"></i>
          </div>
          <h3 style="margin: 0; font-size: 1.2rem; color: #0f172a;">Kiểm Tra & Giám Sát Chống Gian Lận ELO (Anti-Cheat)</h3>
          <p style="font-size: 0.82rem; color: #64748b; margin: 4px 0 0;">Thuật toán quét bất thường trong lịch sử 30 trận gần nhất</p>
        </div>

        <div style="display: grid; gap: 10px; margin-bottom: 1.5rem;">
          <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 10px; padding: 12px; display: flex; align-items: flex-start; gap: 10px;">
            <i class="fa-solid fa-circle-check text-success" style="font-size: 1.2rem; margin-top: 2px;"></i>
            <div>
              <strong style="color: #166534; font-size: 0.88rem;">1. Kiểm tra Win-Trading (Cày Điểm Đối Tác):</strong>
              <div style="font-size: 0.8rem; color: #334155; margin-top: 2px;">✅ HỢP LỆ: Không có nhóm đấu thủ nào thi đấu lặp lại quá 2 lần trong 48 giờ.</div>
            </div>
          </div>

          <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 10px; padding: 12px; display: flex; align-items: flex-start; gap: 10px;">
            <i class="fa-solid fa-circle-check text-success" style="font-size: 1.2rem; margin-top: 2px;"></i>
            <div>
              <strong style="color: #166534; font-size: 0.88rem;">2. Kiểm tra Tăng ELO Đột Biến (Rapid Surge):</strong>
              <div style="font-size: 0.8rem; color: #334155; margin-top: 2px;">✅ HỢP LỆ: Tốc độ tăng ELO đạt +64 điểm / 5 trận (ngưỡng an toàn < +180 điểm).</div>
            </div>
          </div>

          <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 10px; padding: 12px; display: flex; align-items: flex-start; gap: 10px;">
            <i class="fa-solid fa-circle-check text-success" style="font-size: 1.2rem; margin-top: 2px;"></i>
            <div>
              <strong style="color: #166534; font-size: 0.88rem;">3. Kiểm tra Tài Khoản Mới Thắng Cao Thủ (Smurf Suspect):</strong>
              <div style="font-size: 0.8rem; color: #334155; margin-top: 2px;">✅ HỢP LỆ: Tài khoản đã có 28 trận thi đấu, độ tin cậy xếp hạng đạt 82%.</div>
            </div>
          </div>
        </div>

        <button class="btn btn-secondary" style="width: 100%;" onclick="app.closeModal()">Đóng Báo Cáo</button>
      </div>
    `;

    this.openModal();
  }

  showEloHistoryModal() {
    const modalBody = document.getElementById('modal-body');
    if (!modalBody) return;

    const list = MockData.elo_histories || [
      { id: 1, reason: "Thắng trận Đơn vs Bùi Đình Trọng", elo_change: 24, old_elo: 1426, new_elo: 1450, created_at: "2026-09-27 19:45" },
      { id: 2, reason: "Thắng trận Đôi vs Team Mỹ Đình", elo_change: 18, old_elo: 1408, new_elo: 1426, created_at: "2026-09-25 20:30" },
      { id: 3, reason: "Thua trận Đơn vs Hoàng Văn Nam", elo_change: -14, old_elo: 1422, new_elo: 1408, created_at: "2026-09-22 21:00" }
    ];

    let rowsHtml = '';
    list.forEach(h => {
      rowsHtml += `
        <tr>
          <td style="font-size: 0.8rem; color: #64748b;">${h.created_at || 'Vừa xong'}</td>
          <td style="font-weight: 700; font-size: 0.85rem;">${h.reason}</td>
          <td><span class="badge ${h.elo_change >= 0 ? 'badge-success' : 'badge-danger'}" style="font-size: 0.8rem; font-weight: 800;">${h.elo_change >= 0 ? '+' : ''}${h.elo_change} ELO</span></td>
          <td style="font-size: 0.85rem;"><strong>${h.new_elo}</strong> <span style="color: #94a3b8; font-size: 0.75rem;">(từ ${h.old_elo})</span></td>
          <td><span style="background: #f0fdf4; color: #166534; font-size: 0.75rem; font-weight: 700; padding: 2px 6px; border-radius: 4px;">Đã Xác Nhận</span></td>
        </tr>
      `;
    });

    modalBody.innerHTML = `
      <div style="padding: 0.5rem 0;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
          <h3 style="margin: 0; font-size: 1.15rem; color: #0f172a;"><i class="fa-solid fa-clock-rotate-left text-primary"></i> Sổ Cái Lịch Sử Biến Động ELO & Trận Đấu</h3>
          <span style="font-size: 0.78rem; background: #e0f2fe; color: #0284c7; padding: 2px 8px; border-radius: 6px; font-weight: 700;">Audit Trail</span>
        </div>
        <table class="custom-table" style="margin-bottom: 1.25rem;">
          <thead>
            <tr>
              <th>Thời Gian</th>
              <th>Trận Đấu & Đối Thủ</th>
              <th>Biến Động</th>
              <th>ELO Mới</th>
              <th>Trạng Thái</th>
            </tr>
          </thead>
          <tbody>
            ${rowsHtml}
          </tbody>
        </table>
        <button class="btn btn-secondary" style="width: 100%;" onclick="app.closeModal()">Đóng</button>
      </div>
    `;

    this.openModal();
  }


  openRoomChat(roomId) {
    this.activeRoom = MockData.matchmaking_rooms.find(r => r.id === roomId) || MockData.matchmaking_rooms[0];
    
    const titleEl = document.getElementById('room-detail-title');
    const metaEl = document.getElementById('room-detail-meta');
    const statusBadge = document.getElementById('room-detail-status-badge');

    if (titleEl) titleEl.textContent = this.activeRoom.room_name;
    if (metaEl) {
      metaEl.innerHTML = `
        <i class="fa-solid fa-map-pin text-rose"></i> ${this.activeRoom.facility_name} | 
        <i class="fa-solid fa-clock text-amber"></i> ${this.activeRoom.match_date} (${this.activeRoom.match_time}) | 
        <i class="fa-solid fa-tag text-primary"></i> ${this.activeRoom.price_per_slot || '45.000đ/người'}
      `;
    }

    if (statusBadge) {
      const isFull = (this.activeRoom.current_players || 0) >= (this.activeRoom.max_players || 4);
      if (isFull) {
        statusBadge.className = "badge badge-danger";
        statusBadge.innerHTML = `<i class="fa-solid fa-users"></i> Phòng đã đủ thành viên`;
      } else {
        statusBadge.className = "badge badge-success";
        statusBadge.innerHTML = `<i class="fa-solid fa-circle-check"></i> Đang mở ghép kèo (${this.activeRoom.current_players || 1}/${this.activeRoom.max_players || 4})`;
      }
    }

    const joinBtn = document.getElementById('btn-join-room-action');
    if (joinBtn) {
      if (!this.currentUser) {
        joinBtn.innerHTML = `<i class="fa-solid fa-right-to-bracket"></i> Đăng Nhập Để Chấp Nhận Kèo`;
        joinBtn.style.background = "#d97706";
      } else {
        const isMember = this.activeRoom.players && this.activeRoom.players.some(p => p.name === this.currentUser.name || p.id === this.currentUser.id);
        const isFull = (this.activeRoom.current_players || 0) >= (this.activeRoom.max_players || 4);
        if (isMember) {
          joinBtn.innerHTML = `<i class="fa-solid fa-circle-check"></i> Bạn Đã Trong Kèo Này`;
          joinBtn.style.background = "#059669";
        } else if (isFull) {
          joinBtn.innerHTML = `<i class="fa-solid fa-ban"></i> Phòng Đã Đủ Thành Viên`;
          joinBtn.style.background = "#64748b";
        } else {
          joinBtn.innerHTML = `<i class="fa-solid fa-user-plus"></i> Chấp Nhận & Tham Gia Kèo Này`;
          joinBtn.style.background = "#167946";
        }
      }
    }

    this.renderRoomDetailMembers();
    this.renderChatMessages();
    this.renderAIRoomTactics();
    this.navigateTo('ui-07');
  }

  renderRoomDetailMembers() {
    const container = document.getElementById('room-detail-members-grid');
    if (!container || !this.activeRoom) return;

    const room = this.activeRoom;
    const players = room.players || [];
    const maxPlayers = room.max_players || 4;
    let html = '';

    players.forEach((p) => {
      const pTier = this.getSkillTierInfo(p.tier_id || p.tier || p.elo || 5);
      const photo = p.photo || p.avatar;
      const isPhotoUrl = photo && (photo.startsWith('data:image') || photo.startsWith('http') || photo.includes('/'));
      const isHost = p.role === 'Host' || p.name === room.host_name;
      const isMe = this.currentUser && (p.name === this.currentUser.name || p.id === this.currentUser.id);

      html += `
        <div style="background: #ffffff; border: 1.5px solid ${isHost ? '#10b981' : '#cbd5e1'}; border-radius: 12px; padding: 10px; display: flex; align-items: center; gap: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); position: relative;">
          <div style="position: relative; cursor: pointer; flex-shrink: 0;" onclick="app.showPlayerFaceModal('${p.name.replace(/'/g, "\\'")}', '${isPhotoUrl ? photo : ''}', '${pTier.name}')">
            ${isPhotoUrl ? `
              <img src="${photo}" alt="${p.name}" class="mm-avatar-img" style="width: 48px; height: 48px; border-radius: 50%; object-fit: cover; border: 2.5px solid #167946; box-shadow: 0 2px 8px rgba(0,0,0,0.15);">
              <span class="mm-photo-badge" title="Đã có ảnh nhận diện khuôn mặt"><i class="fa-solid fa-camera"></i></span>
            ` : `
              <div class="avatar" style="width: 48px; height: 48px; border-radius: 50%; background: #167946; color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1.1rem; border: 2px solid #86efac;">
                ${p.name.charAt(0)}
              </div>
            `}
          </div>
          <div style="flex: 1; min-width: 0;">
            <div style="display: flex; align-items: center; gap: 6px; justify-content: space-between;">
              <span style="font-weight: 800; font-size: 0.88rem; color: #0f172a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                ${p.name} ${isMe ? '<span style="color: #167946; font-size: 0.72rem;">(Bạn)</span>' : ''}
              </span>
              ${isHost ? `<span style="background: #dcfce7; color: #16a34a; font-size: 0.68rem; font-weight: 800; padding: 1px 6px; border-radius: 4px;">Host</span>` : ''}
            </div>
            <div style="margin-top: 3px;">
              <span class="tier-badge-pill" style="background: ${pTier.bg}; color: ${pTier.color}; font-size: 0.72rem; padding: 2px 8px; border: 1px solid ${pTier.borderColor || '#cbd5e1'};">
                ${pTier.badgeText || pTier.name}
              </span>
            </div>
            <div style="margin-top: 4px; display: flex; gap: 6px;">
              <button class="btn btn-xs btn-outline-secondary" onclick="app.showPlayerFaceModal('${p.name.replace(/'/g, "\\'")}', '${isPhotoUrl ? photo : ''}', '${pTier.name}')" style="font-size: 0.7rem; padding: 2px 6px;">
                <i class="fa-solid fa-expand"></i> Diện Mạo
              </button>
              ${isMe ? `
                <button class="btn btn-xs btn-primary" onclick="app.triggerPlayerPhotoUpload()" style="font-size: 0.7rem; padding: 2px 6px; background: #0284c7;">
                  <i class="fa-solid fa-camera"></i> Đổi Ảnh
                </button>
              ` : ''}
            </div>
          </div>
        </div>
      `;
    });

    // Render empty slots
    const emptySlots = maxPlayers - players.length;
    for (let i = 0; i < emptySlots; i++) {
      html += `
        <div style="background: #f8fafc; border: 1.5px dashed #cbd5e1; border-radius: 12px; padding: 10px; display: flex; align-items: center; gap: 10px; opacity: 0.8;">
          <div style="width: 48px; height: 48px; border-radius: 50%; background: #e2e8f0; color: #94a3b8; display: flex; align-items: center; justify-content: center; font-size: 1.2rem;">
            <i class="fa-solid fa-user-plus"></i>
          </div>
          <div>
            <div style="font-weight: 700; font-size: 0.82rem; color: #64748b;">Chờ thành viên thứ ${players.length + i + 1}...</div>
            <div style="font-size: 0.72rem; color: #94a3b8;">AI đang tìm kiếm tay vợt cùng cấp bậc</div>
          </div>
        </div>
      `;
    }

    container.innerHTML = html;
  }

  renderAIRoomTactics() {
    const body = document.getElementById('ai-room-tactics-body');
    if (!body || !this.activeRoom) return;

    const room = this.activeRoom;
    const isDoubles = room.match_type && room.match_type.includes('Đôi');
    const roomTier = this.getSkillTierInfo(room.required_tier_id || room.required_tier || 5);

    body.innerHTML = `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; margin-bottom: 10px;">
        <div style="background: #ffffff; padding: 10px 14px; border-radius: 10px; border: 1px solid #bae6fd;">
          <div style="font-weight: 700; color: #0369a1; font-size: 0.85rem; margin-bottom: 4px;">
            <i class="fa-solid fa-users text-primary"></i> TỔNG QUAN CẶP ĐẤU & ĐỘ CÂN BẰNG:
          </div>
          <div style="font-size: 0.8rem; color: #475569;">
            • Thể thức: <strong>${room.match_type || 'Đôi Nam/Nữ'}</strong> | Khung giờ: <strong>${room.match_time}</strong><br>
            • Cấp bậc yêu cầu: <span class="tier-badge-pill" style="background: ${roomTier.bg}; color: ${roomTier.color}; border: 1px solid ${roomTier.borderColor || '#cbd5e1'}; font-size: 0.75rem; padding: 1px 7px;">${roomTier.display}</span><br>
            • Đánh giá AI: <strong>${room.ai_prediction || 'Kèo cùng cấp bậc vô cùng cân đối, kịch tính.'}</strong>
          </div>
        </div>

        <div style="background: #ffffff; padding: 10px 14px; border-radius: 10px; border: 1px solid #bae6fd;">
          <div style="font-weight: 700; color: #166534; font-size: 0.85rem; margin-bottom: 4px;">
            <i class="fa-solid fa-shield-halved text-primary"></i> CHIẾN THUẬT GỢI Ý TỪ AI COACH:
          </div>
          <div style="font-size: 0.8rem; color: #475569;">
            ${isDoubles 
              ? '• Chủ động khống chế lưới và ép cầu dọc dây để tạo cơ hội cho đồng đội phía sau smash dứt điểm.<br>• Phân chia vị trí tấn công trước - sau linh hoạt khi chuyển đổi phòng thủ.'
              : '• Điều cầu liên tục 4 góc sân để tiêu hao thể lực đối phương, tung cú chém cầu so le khi đối thủ lùi sâu.'}
          </div>
        </div>
      </div>
    `;
  }

  requestAICoachTactics() {
    if (!this.activeRoom) return;

    this.showToast("🤖 AI Coach đang phân tích dữ liệu trận đấu và đưa ra chiến thuật...");

    setTimeout(() => {
      const coachTips = [
        "💡 [Chiến Thuật AI]: Nhận thấy đối thủ có lối chơi đập cầu uy lực nhưng di chuyển đuôi sân chậm. Đề xuất: Kéo cầu 2 góc biên và chủ động bỏ nhỏ sát lưới!",
        "🏸 [Chiến Thuật AI]: Đội bạn nên tập trung khai thác khoảng trống giữa 2 tay vợt khi họ chuyển đổi công sang thủ. Sử dụng các quả tạt cầu ngang thắt lưng!",
        "⚡ [Chiến Thuật AI]: Tỉ lệ thắng của kèo này là 50% - 50%. Khuyên bạn nên khởi động kỹ khớp cổ chân và cổ tay trước trận 10 phút để tối ưu tốc độ phản xạ!",
        "🎯 [Chiến Thuật AI]: Đối thủ có xu hướng giao cầu bổng về cuối sân. Hãy sẵn sàng lùi đón cầu sớm để thực hiện cú smash chéo sân dứt điểm!"
      ];
      const randomTip = coachTips[Math.floor(Math.random() * coachTips.length)];

      this.activeRoom.chat_messages.push({
        sender: "🤖 AI Virtual Coach",
        text: randomTip,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isAI: true
      });

      this.renderChatMessages();
      this.showToast("✅ AI Coach đã gửi lời khuyên chiến thuật vào phòng chat!");
    }, 600);
  }

  sendQuickChatMessage(text) {
    if (!this.currentUser) {
      this.showToast("⚠️ Bạn chưa đăng nhập! Vui lòng Đăng Nhập để gửi tin nhắn trong phòng kèo đấu.", "error");
      this.navigateTo('ui-01');
      return;
    }
    if (!this.activeRoom) return;
    const input = document.getElementById('chat-input-text');
    if (input) input.value = text;
    this.sendChatMessage(new Event('submit'));
  }

  loadRoomIntoEloSimulator(roomId) {
    const room = MockData.matchmaking_rooms.find(r => r.id === roomId);
    if (!room) return;

    const p1Name = document.getElementById('matchup-p1-name');
    const p1TierSelect = document.getElementById('matchup-p1-tier');
    const p2Name = document.getElementById('matchup-p2-name');
    const p2TierSelect = document.getElementById('matchup-p2-tier');

    const userTierVal = (this.currentUser && (this.currentUser.skill_tier_id || this.currentUser.skill_tier)) || 5;
    const userTier = this.getSkillTierInfo(userTierVal);
    const roomTier = this.getSkillTierInfo(room.required_tier_id || room.required_tier || room.host_tier || 5);

    if (p1Name) p1Name.value = (this.currentUser && this.currentUser.name) ? this.currentUser.name : 'Bạn (Chưa đăng nhập)';
    if (p1TierSelect) p1TierSelect.value = String(userTier.tier);
    if (p2Name) p2Name.value = room.host_name || 'Đối thủ Host';
    if (p2TierSelect) p2TierSelect.value = String(roomTier.tier);

    const card = document.getElementById('ai-elo-predictor-card');
    if (card) {
      card.style.display = 'block';
      this.runAIMatchupCalculation();
      card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      this.showToast(`🧠 Đã tải dữ liệu phòng "${room.room_name}" vào bộ so sánh AI!`);
    }
  }

  loadActiveRoomToPredictor() {
    if (this.activeRoom) {
      this.navigateTo('ui-06');
      this.loadRoomIntoEloSimulator(this.activeRoom.id);
    }
  }

  joinActiveRoomChat() {
    if (!this.currentUser) {
      this.showToast("⚠️ Bạn chưa đăng nhập! Vui lòng Đăng Nhập hoặc Đăng Ký tài khoản để chấp nhận & tham gia kèo đấu này.", "error");
      this.navigateTo('ui-01');
      return;
    }

    if (!this.activeRoom) return;

    const user = this.currentUser;
    const alreadyIn = this.activeRoom.players && this.activeRoom.players.some(p => p.name === user.name || p.id === user.id);

    if (alreadyIn) {
      this.showToast("ℹ️ Bạn đã là thành viên trong phòng ghép này!");
      return;
    }

    if ((this.activeRoom.current_players || 0) >= (this.activeRoom.max_players || 4)) {
      this.showToast("⚠️ Phòng ghép đã đủ số lượng thành viên!");
      return;
    }

    const userTier = this.getSkillTierInfo(user.skill_tier_id || user.skill_tier || 5);

    if (!this.activeRoom.players) this.activeRoom.players = [];
    this.activeRoom.players.push({
      id: user.id,
      name: user.name,
      tier: userTier.name,
      tier_id: userTier.tier,
      elo: user.elo_rating || userTier.defaultElo || 1650,
      avatar: user.avatar || user.name.charAt(0),
      photo: user.photo || user.avatar || null,
      role: 'Member',
      style: 'Công thủ linh hoạt',
      team: 'B'
    });

    this.activeRoom.current_players = this.activeRoom.players.length;

    this.activeRoom.chat_messages.push({
      sender: "🤖 AI Match Referee",
      text: `🎉 Chào mừng ${user.name} (Cấp [${userTier.name}]) đã chấp nhận kèo và tham gia phòng! Kèo đấu hiện có ${this.activeRoom.current_players}/${this.activeRoom.max_players} thành viên.`,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    });

    this.renderRoomDetailMembers();
    this.renderChatMessages();
    this.renderAIRoomTactics();
    this.renderMatchmakingRooms();
    if (typeof saveMockDataToLocalStorage === 'function') {
      saveMockDataToLocalStorage();
    }
    this.showToast(`🎉 Bạn đã chấp nhận và tham gia kèo đấu "${this.activeRoom.room_name}" thành công!`);
  }

  renderChatMessages() {
    const container = document.getElementById('chat-messages-list');
    if (!container || !this.activeRoom) return;
    let html = '';

    const currentUserName = (this.currentUser && this.currentUser.name) ? this.currentUser.name : '';

    (this.activeRoom.chat_messages || []).forEach(msg => {
      const isSent = currentUserName && msg.sender === currentUserName;
      const isReferee = msg.sender.includes('AI') || msg.sender.includes('Referee') || msg.isAI;

      let msgClass = 'chat-msg received';
      if (isSent) msgClass = 'chat-msg sent';
      else if (isReferee) msgClass = 'chat-msg referee';

      html += `
        <div class="${msgClass}">
          <div style="font-size: 0.72rem; font-weight: 800; opacity: 0.85; margin-bottom: 2px;">
            ${msg.sender} • <span style="font-weight: 500;">${msg.time || 'vừa xong'}</span>
          </div>
          <div>${msg.text}</div>
        </div>
      `;
    });

    container.innerHTML = html;
    container.scrollTop = container.scrollHeight;
  }

  sendChatMessage(e) {
    if (e && e.preventDefault) e.preventDefault();
    if (!this.currentUser) {
      this.showToast("⚠️ Bạn chưa đăng nhập! Vui lòng Đăng Nhập để gửi tin nhắn trong phòng kèo đấu.", "error");
      this.navigateTo('ui-01');
      return;
    }

    const input = document.getElementById('chat-input-text');
    if (!input) return;
    const text = input.value.trim();
    if (!text || !this.activeRoom) return;

    const currentUserName = this.currentUser.name;
    const nowTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    this.activeRoom.chat_messages.push({
      sender: currentUserName,
      text: text,
      time: nowTime
    });

    input.value = '';
    this.renderChatMessages();

    // If user asks @AI or mentions tactics, auto reply with AI coach advice
    if (text.toLowerCase().includes('@ai') || text.toLowerCase().includes('chiến thuật') || text.toLowerCase().includes('kèo')) {
      setTimeout(() => {
        this.activeRoom.chat_messages.push({
          sender: "🤖 AI Virtual Coach",
          text: `🎯 Trả lời bạn @${currentUserName}: Dựa trên phân tích ELO trận đấu này, đề xuất chiến thuật tối ưu nhất là tập trung kiểm soát nhịp độ, phát cầu ngắn sát lưới và bọc lót chéo góc!`,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          isAI: true
        });
        this.renderChatMessages();
      }, 700);
    }

    if (typeof saveMockDataToLocalStorage === 'function') {
      saveMockDataToLocalStorage();
    }
  }

  openCreateRoomModal() {
    if (!this.currentUser) {
      this.showToast("⚠️ Bạn chưa đăng nhập! Vui lòng Đăng Nhập hoặc Đăng Ký tài khoản để khởi tạo phòng ghép kèo.", "error");
      this.navigateTo('ui-01');
      return;
    }

    const modalBody = document.getElementById('modal-body');
    if (!modalBody) return;

    let facOptions = '';
    (MockData.facilities || []).forEach(f => {
      facOptions += `<option value="${f.id}">${f.name} (${f.address || ''})</option>`;
    });

    const userTierVal = (this.currentUser && (this.currentUser.skill_tier_id || this.currentUser.skill_tier)) || 5;
    const userTier = this.getSkillTierInfo(userTierVal);
    const userPhoto = (this.currentUser && (this.currentUser.photo || this.currentUser.avatar)) || '';
    const hasPhoto = userPhoto && (userPhoto.startsWith('data:image') || userPhoto.startsWith('http') || userPhoto.includes('/'));

    modalBody.innerHTML = `
      <div style="padding: 0.5rem 0;">
        <h3 style="margin: 0 0 6px; color: #0f172a; font-size: 1.2rem; display: flex; align-items: center; gap: 8px;">
          <i class="fa-solid fa-users-viewfinder text-primary"></i> Khởi Tạo Phòng Ghép Kèo AI Cân Bằng Cấp Bậc
        </h3>
        <p style="color: #64748b; font-size: 0.82rem; margin-bottom: 1rem;">
          Hệ thống AI tự động xét kèo cùng hạng mức trình độ (7 cấp bậc chuẩn) để ghép các tay vợt cân sức vào thi đấu.
        </p>

        <form onsubmit="app.handleCreateRoom(event)">
          <div class="form-group">
            <label class="form-label">Tên Phòng Ghép / Tiêu Đề</label>
            <input type="text" id="modal-room-name" class="form-control" value="Giao lưu Săn Kèo Cân Kèo Cùng Cấp" required>
          </div>

          <div class="form-group">
            <label class="form-label">Chọn Cụm Cơ Sở Sân Cầu Lông</label>
            <select id="modal-room-facility" class="form-control" required>
              ${facOptions}
            </select>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
            <div class="form-group">
              <label class="form-label">Thể Thức Thi Đấu</label>
              <select id="modal-room-type" class="form-control">
                <option value="Đôi Nam/Nữ">🏸 Đôi Nam/Nữ (4 người)</option>
                <option value="Đôi Nam">🏸 Đôi Nam (4 người)</option>
                <option value="Đơn Nam">⚡ Đơn Nam (2 người)</option>
                <option value="Đơn Nữ">⚡ Đơn Nữ (2 người)</option>
                <option value="Giao Lưu Tự Do">🎯 Giao Lưu Tự Do</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Khung Giờ Dự Kiến</label>
              <input type="text" id="modal-room-time" class="form-control" value="18:00 - 20:00 (Hôm nay)">
            </div>
          </div>

          <!-- Phân Khúc Ghép Trình Tiêu Chuẩn 7 Cấp Bậc (Không dùng điểm số ELO) -->
          <div class="form-group" style="background: #f8fafc; border: 1.5px solid #cbd5e1; border-radius: 12px; padding: 12px; margin-bottom: 1rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <label class="form-label" style="margin: 0; font-weight: 800; color: #0f172a; display: flex; align-items: center; gap: 6px;">
                <i class="fa-solid fa-layer-group text-primary"></i> Cấp Bậc Trình Độ Yêu Cầu Ghép Kèo
              </label>
              <span id="tier-selection-badge" style="font-size: 0.72rem; font-weight: 800; background: ${userTier.bg}; color: ${userTier.color}; padding: 3px 8px; border-radius: 6px;">
                ${userTier.display}
              </span>
            </div>

            <!-- Dropdown chọn cấp bậc 1-7 -->
            <select id="modal-tier-select" class="form-control" style="font-weight: 700; margin-bottom: 8px; font-size: 0.88rem;" onchange="app.onModalSkillTierChange(this.value)">
              <option value="1">🟢 1 | Yếu - Tân thủ</option>
              <option value="2">🔵 2 | Trung Bình Yếu - Cơ bản</option>
              <option value="3">🟡 3 | Trung bình</option>
              <option value="4">🟠 4 | Trung bình khá</option>
              <option value="5" ${userTier.tier === 5 ? 'selected' : ''}>🔴 5 | Khá</option>
              <option value="6">🟣 6 | Giỏi - Thành thạo</option>
              <option value="7">👑 7 | Tốt - Chuyên nghiệp</option>
            </select>

            <!-- 1-Click Fast Tier Buttons (Pills) -->
            <div style="display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 10px;">
              <button type="button" class="btn btn-xs" onclick="app.selectModalSkillTier(1)" style="font-size: 0.72rem; padding: 3px 7px; border-radius: 6px; background: #dcfce7; color: #16a34a; border: 1px solid #86efac; font-weight: 700;">1: Yếu</button>
              <button type="button" class="btn btn-xs" onclick="app.selectModalSkillTier(2)" style="font-size: 0.72rem; padding: 3px 7px; border-radius: 6px; background: #e0f2fe; color: #0284c7; border: 1px solid #7dd3fc; font-weight: 700;">2: TB Yếu</button>
              <button type="button" class="btn btn-xs" onclick="app.selectModalSkillTier(3)" style="font-size: 0.72rem; padding: 3px 7px; border-radius: 6px; background: #fef9c3; color: #ca8a04; border: 1px solid #fde047; font-weight: 700;">3: Trung bình</button>
              <button type="button" class="btn btn-xs" onclick="app.selectModalSkillTier(4)" style="font-size: 0.72rem; padding: 3px 7px; border-radius: 6px; background: #ffedd5; color: #ea580c; border: 1px solid #fdba74; font-weight: 700;">4: TB Khá</button>
              <button type="button" class="btn btn-xs" onclick="app.selectModalSkillTier(5)" style="font-size: 0.72rem; padding: 3px 7px; border-radius: 6px; background: #fee2e2; color: #dc2626; border: 1px solid #fca5a5; font-weight: 700;">5: Khá</button>
              <button type="button" class="btn btn-xs" onclick="app.selectModalSkillTier(6)" style="font-size: 0.72rem; padding: 3px 7px; border-radius: 6px; background: #f3e8ff; color: #9333ea; border: 1px solid #d8b4fe; font-weight: 700;">6: Giỏi</button>
              <button type="button" class="btn btn-xs" onclick="app.selectModalSkillTier(7)" style="font-size: 0.72rem; padding: 3px 7px; border-radius: 6px; background: #e0e7ff; color: #4f46e5; border: 1px solid #a5b4fc; font-weight: 700;">7: Chuyên nghiệp</button>
            </div>

            <!-- Cơ chế AI Cân Kèo -->
            <label class="form-label" style="font-size: 0.78rem; font-weight: 700; color: #475569; margin-bottom: 4px;">
              Tiêu chuẩn cân kèo của AI:
            </label>
            <select id="modal-room-tolerance" class="form-control" style="font-size: 0.82rem;">
              <option value="same" selected>🎯 Chỉ ghép tay vợt cùng cấp bậc chính xác (100% Cân Kèo Tuyệt Đối)</option>
              <option value="adjacent">⚖️ Cho phép ghép lệch tối đa 1 cấp (AI tự động tính toán điểm chấp công bằng)</option>
              <option value="all">🌐 Mở rộng ghép mọi cấp bậc giao lưu</option>
            </select>
          </div>

          <!-- Trình Độ & Ảnh Nhận Diện Của Bạn (Host) -->
          <div class="form-group" style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 12px; padding: 10px 12px; margin-bottom: 1rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <span style="font-size: 0.8rem; font-weight: 700; color: #166534;">
                <i class="fa-solid fa-user-check"></i> Cấp Bậc & Ảnh Diện Mạo Của Bạn (Host):
              </span>
              <span id="modal-host-tier-preview" style="font-size: 0.75rem; font-weight: 800; background: ${userTier.bg}; color: ${userTier.color}; padding: 2px 8px; border-radius: 6px;">
                ${userTier.display}
              </span>
            </div>
            
            <div style="display: grid; grid-template-columns: auto 1fr; gap: 12px; align-items: center;">
              <!-- Host Face Photo Upload Preview -->
              <div style="text-align: center;">
                <div style="position: relative; display: inline-block; cursor: pointer;" onclick="app.triggerPlayerPhotoUpload()">
                  ${hasPhoto ? `
                    <img src="${userPhoto}" alt="${this.currentUser.name}" class="mm-avatar-img" style="width: 52px; height: 52px; border-radius: 50%; object-fit: cover; border: 2.5px solid #167946; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">
                    <span class="mm-photo-badge" title="Tải ảnh nhận diện từ thiết bị"><i class="fa-solid fa-camera"></i></span>
                  ` : `
                    <div class="avatar" style="width: 52px; height: 52px; border-radius: 50%; background: #167946; color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1.2rem; border: 2px solid #86efac;">
                      ${this.currentUser.name.charAt(0)}
                    </div>
                    <span class="mm-photo-badge" title="Tải ảnh nhận diện từ thiết bị"><i class="fa-solid fa-camera"></i></span>
                  `}
                </div>
                <div style="margin-top: 3px;">
                  <button type="button" class="btn btn-xs btn-outline-primary" onclick="app.triggerPlayerPhotoUpload()" style="font-size: 0.68rem; padding: 2px 6px;">
                    <i class="fa-solid fa-camera"></i> ${hasPhoto ? 'Đổi ảnh' : 'Tải ảnh'}
                  </button>
                </div>
              </div>

              <!-- Host Skill Tier Selection -->
              <div>
                <label style="font-size: 0.75rem; font-weight: 700; color: #475569; display: block; margin-bottom: 4px;">Cấp bậc của bạn:</label>
                <select id="modal-host-tier-select" class="form-control" style="font-size: 0.82rem; font-weight: 700;" onchange="app.onModalHostSkillTierChange(this.value)">
                  <option value="1" ${userTier.tier === 1 ? 'selected' : ''}>🟢 Cấp 1: Yếu - Tân thủ</option>
                  <option value="2" ${userTier.tier === 2 ? 'selected' : ''}>🔵 Cấp 2: Trung Bình Yếu - Cơ bản</option>
                  <option value="3" ${userTier.tier === 3 ? 'selected' : ''}>🟡 Cấp 3: Trung bình</option>
                  <option value="4" ${userTier.tier === 4 ? 'selected' : ''}>🟠 Cấp 4: Trung bình khá</option>
                  <option value="5" ${userTier.tier === 5 ? 'selected' : ''}>🔴 Cấp 5: Khá</option>
                  <option value="6" ${userTier.tier === 6 ? 'selected' : ''}>🟣 Cấp 6: Giỏi - Thành thạo</option>
                  <option value="7" ${userTier.tier === 7 ? 'selected' : ''}>👑 Cấp 7: Tốt - Chuyên nghiệp</option>
                </select>
                <span style="font-size: 0.72rem; color: #64748b; margin-top: 2px; display: block;">
                  📸 Ảnh diện mạo sẽ giúp đối thủ nhận ra bạn ngay khi tới sân.
                </span>
              </div>
            </div>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
            <div class="form-group">
              <label class="form-label">Sân Số</label>
              <input type="text" id="modal-room-court" class="form-control" value="Sân số 03 (Thảm Pro)">
            </div>
            <div class="form-group">
              <label class="form-label">Phí Chia Sân / Người</label>
              <input type="text" id="modal-room-price" class="form-control" value="45.000đ">
            </div>
          </div>

          <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 10px; padding: 10px; margin: 10px 0; font-size: 0.8rem; color: #166534;">
            <i class="fa-solid fa-wand-magic-sparkles"></i> <strong>AI Auto-Balance:</strong> Tự động xét kèo cùng hạng mức và tính toán điểm chấp nếu có thành viên chênh lệch 1 cấp bậc tham gia.
          </div>

          <button type="submit" class="btn btn-primary" style="width: 100%; margin-top: 0.5rem; background: linear-gradient(135deg, #167946 0%, #059669 100%); font-weight: 700;">
            <i class="fa-solid fa-circle-check"></i> Khởi Tạo Phòng Ghép & Mở Radar AI
          </button>
        </form>
      </div>
    `;

    this.openModal();
  }

  onModalSkillTierChange(tierVal) {
    const tier = this.getSkillTierInfo(parseInt(tierVal, 10));
    const badge = document.getElementById('tier-selection-badge');
    if (badge) {
      badge.textContent = tier.display;
      badge.style.background = tier.bg;
      badge.style.color = tier.color;
    }
  }

  selectModalSkillTier(tier) {
    const select = document.getElementById('modal-tier-select');
    if (select) {
      select.value = String(tier);
      this.onModalSkillTierChange(String(tier));
    }
  }

  onModalHostSkillTierChange(val) {
    const tier = this.getSkillTierInfo(parseInt(val, 10));
    const preview = document.getElementById('modal-host-tier-preview');
    if (preview) {
      preview.textContent = tier.display;
      preview.style.color = tier.color;
      preview.style.background = tier.bg;
    }
  }

  handleCreateRoom(e) {
    if (e && e.preventDefault) e.preventDefault();
    if (!this.currentUser) {
      this.showToast("⚠️ Bạn chưa đăng nhập! Vui lòng Đăng Nhập tài khoản để tạo phòng ghép kèo.", "error");
      this.navigateTo('ui-01');
      return;
    }

    const name = document.getElementById('modal-room-name')?.value || 'Phòng Giao Lưu Mới';
    const facId = parseInt(document.getElementById('modal-room-facility')?.value || '101', 10);
    const matchType = document.getElementById('modal-room-type')?.value || 'Đôi Nam/Nữ';
    const matchTime = document.getElementById('modal-room-time')?.value || '18:00 - 20:00 (Hôm nay)';
    const requiredTierVal = parseInt(document.getElementById('modal-tier-select')?.value || '5', 10);
    const hostTierVal = parseInt(document.getElementById('modal-host-tier-select')?.value || '5', 10);
    const tolerance = document.getElementById('modal-room-tolerance')?.value || 'same';
    const court = document.getElementById('modal-room-court')?.value || 'Sân số 03';
    const price = document.getElementById('modal-room-price')?.value || '45.000đ';

    const requiredTier = this.getSkillTierInfo(requiredTierVal);
    const hostTier = this.getSkillTierInfo(hostTierVal);
    const fac = MockData.facilities.find(f => f.id === facId) || MockData.facilities[0];
    const isDoubles = matchType.includes('Đôi');
    const maxPlayers = isDoubles ? 4 : 2;
    const currentUserName = this.currentUser.name;

    // Update currentUser skill tier
    this.currentUser.skill_tier_id = hostTier.tier;
    this.currentUser.skill_tier = hostTier.name;
    this.currentUser.elo_rating = hostTier.defaultElo || 1650;
    const u = (MockData.users || []).find(x => x.id === this.currentUser.id || x.name === this.currentUser.name);
    if (u) {
      u.skill_tier = hostTier.name;
      u.skill_tier_id = hostTier.tier;
      u.elo_rating = hostTier.defaultElo || 1650;
    }

    const hostPhoto = this.currentUser.photo || (this.currentUser.avatar && (this.currentUser.avatar.startsWith('data:image') || this.currentUser.avatar.startsWith('http')) ? this.currentUser.avatar : null);

    const newRoom = {
      id: Date.now(),
      room_name: name,
      facility_id: fac.id,
      facility_name: fac.name,
      district: fac.address || 'Hà Nội',
      match_date: "Hôm nay, 22/09/2026",
      match_time: matchTime,
      required_tier: requiredTier.name,
      required_tier_id: requiredTier.tier,
      host_tier: hostTier.name,
      host_tier_id: hostTier.tier,
      host_photo: hostPhoto,
      match_tolerance: tolerance,
      match_type: matchType,
      court_number: court,
      price_per_slot: price,
      current_players: 1,
      max_players: maxPlayers,
      status: "OPEN",
      host_name: currentUserName,
      ai_compatibility: 98,
      ai_prediction: `Phòng mới tạo. Trình độ yêu cầu [${requiredTier.name}], AI đang mời các tay vợt cùng hạng mức phù hợp.`,
      ai_handicap: "Cùng cấp bậc - Đồng banh (0 điểm)",
      category: isDoubles ? 'doubles' : 'singles',
      is_ai_recommended: true,
      players: [
        {
          name: currentUserName,
          tier: hostTier.name,
          tier_id: hostTier.tier,
          elo: hostTier.defaultElo || 1650,
          avatar: currentUserName.charAt(0),
          photo: hostPhoto,
          role: 'Host',
          style: 'Công thủ toàn diện',
          team: 'A'
        }
      ],
      chat_messages: [
        {
          sender: "🤖 AI Match Referee",
          text: `Phòng ghép "${name}" đã khởi tạo thành công! Radar AI đang tự động gửi thông báo đến các tay vợt thuộc cấp [${requiredTier.name}].`,
          time: "vừa xong"
        },
        {
          sender: currentUserName,
          text: `Chào mọi người, phòng đã sẵn sàng cho kèo giao lưu trình độ [${requiredTier.name}], mời anh em vào đánh cùng!`,
          time: "vừa xong"
        }
      ]
    };

    MockData.matchmaking_rooms.unshift(newRoom);

    this.closeModal();
    this.renderMatchmakingRooms();
    if (typeof saveMockDataToLocalStorage === 'function') {
      saveMockDataToLocalStorage();
    }
    this.showToast(`🎉 Đã khởi tạo phòng ghép thành công (Cấp [${requiredTier.name}]) và kích hoạt Radar AI!`);
  }

  /* ------------------------------------------------------------------------
     7. FIELD OWNER PORTAL (UI 09 - UI 14)
     ------------------------------------------------------------------------ */
  renderOwnerDashboardOrders() {
    const tbody = document.getElementById('owner-dashboard-orders-tbody');
    if (!tbody) return;

    let html = '';
    MockData.booking_orders.forEach(order => {
      const isDepositPaid = order.deposit_status.includes('50K') || order.deposit_status.includes('Đã');
      html += `
        <tr>
          <td><strong>${order.booking_code}</strong></td>
          <td>
            <strong>${order.user_name}</strong>
            <div style="font-size: 0.75rem; color: var(--text-muted);">${order.user_phone}</div>
          </td>
          <td>
            <div style="font-size: 0.85rem;"><strong>${order.facility_name}</strong></div>
            <div style="font-size: 0.75rem; color: var(--accent-cyan);">${order.court_name}</div>
          </td>
          <td><span class="tag-badge tag-pos">${order.slot_time}</span></td>
          <td><strong>${order.total_amount.toLocaleString('vi-VN')}đ</strong></td>
          <td>
            <span class="tag-badge ${isDepositPaid ? 'tag-ai' : 'tag-pos'}">
              <i class="fa-solid ${isDepositPaid ? 'fa-circle-check' : 'fa-clock'}"></i> ${order.deposit_status}
            </span>
          </td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick="app.showBookingTicketModal('${order.qr_ticket_code}')" title="Xem Chi Tiết Vé QR">
              <i class="fa-solid fa-qrcode"></i> Vé QR
            </button>
          </td>
        </tr>
      `;
    });

    tbody.innerHTML = html;
  }

  showOwnerRevenueModal() {
    const modalBody = document.getElementById('modal-body');
    modalBody.innerHTML = `
      <h3>📊 Phân Tích Doanh Thu Hôm Nay (4.850.000 VNĐ)</h3>
      <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px;">Chi tiết nguồn thu từ tiền thuê sân, phụ thu AI Dynamic Price và thuê mua thiết bị tại quầy</p>

      <div style="display: flex; flex-direction: column; gap: 0.75rem; margin-top: 1.25rem;">
        <div style="display: flex; justify-content: space-between; padding: 0.75rem; background: rgba(16,185,129,0.1); border-radius: 8px; border-left: 4px solid var(--primary);">
          <span><strong>1. Tiền Thuê Sân Cố Định (32 Lượt):</strong></span>
          <strong style="color: var(--primary);">3.520.000đ</strong>
        </div>
        <div style="display: flex; justify-content: space-between; padding: 0.75rem; background: rgba(6,182,212,0.1); border-radius: 8px; border-left: 4px solid var(--accent-cyan);">
          <span><strong>2. Phụ Thu AI Dynamic Price (Giờ Vàng +15%):</strong></span>
          <strong style="color: var(--accent-cyan);">+530.000đ</strong>
        </div>
        <div style="display: flex; justify-content: space-between; padding: 0.75rem; background: rgba(245,158,11,0.1); border-radius: 8px; border-left: 4px solid var(--accent-amber);">
          <span><strong>3. Dịch Vụ Cho Thuê Vợt & Bán Cầu/Pocari:</strong></span>
          <strong style="color: var(--accent-amber);">+800.000đ</strong>
        </div>
        <div style="display: flex; justify-content: space-between; padding: 0.75rem; background: rgba(255,255,255,0.05); border-radius: 8px; font-size: 1rem; border-top: 1px solid var(--border-color);">
          <span><strong>TỔNG DOANH THU THỰC NHẬN:</strong></span>
          <strong style="color: var(--primary); font-size: 1.15rem;">4.850.000đ</strong>
        </div>
      </div>

      <div style="margin-top: 1.25rem; display: flex; gap: 0.5rem; justify-content: flex-end;">
        <button class="btn btn-secondary btn-sm" onclick="app.closeModal()">Đóng</button>
        <button class="btn btn-primary btn-sm" onclick="app.closeModal(); app.exportExcelReport();">
          <i class="fa-solid fa-file-excel"></i> Tải Báo Cáo Chi Tiết
        </button>
      </div>
    `;
    this.openModal();
  }

  openAddFacilityModal() {
    const modalBody = document.getElementById('modal-body');
    modalBody.innerHTML = `
      <h3>🏟️ Đăng Ký Cơ Sở Sân Cầu Lông Mới</h3>
      <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px;">Khai báo thông tin cơ sở sân mới để gửi yêu cầu kiểm duyệt tới Admin</p>
      
      <form onsubmit="app.saveNewFacility(event)" style="margin-top: 1rem; display: flex; flex-direction: column; gap: 0.75rem;">
        <div class="form-group">
          <label class="form-label">Tên Cụm Sân Cầu Lông</label>
          <input type="text" id="add-fac-name" class="form-control" placeholder="VD: Sân Cầu Lông Cầu Giấy Pro Arena" required>
        </div>
        <div class="form-group">
          <label class="form-label">Địa Chỉ Chi Nhánh (Số nhà, Đường, Phường, Quận)</label>
          <input type="text" id="add-fac-address" class="form-control" placeholder="VD: 102 Phố Láng Hạ, Phường Láng Hạ, Quận Đống Đa, Hà Nội" required>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
          <div class="form-group">
            <label class="form-label">Vĩ Độ (Latitude)</label>
            <input type="text" id="add-fac-lat" class="form-control" value="21.0153" required>
          </div>
          <div class="form-group">
            <label class="form-label">Kinh Độ (Longitude)</label>
            <input type="text" id="add-fac-lng" class="form-control" value="105.8152" required>
          </div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
          <div class="form-group">
            <label class="form-label">Giờ Mở Cửa</label>
            <input type="time" id="add-fac-open" class="form-control" value="06:00" required>
          </div>
          <div class="form-group">
            <label class="form-label">Giờ Đóng Cửa</label>
            <input type="time" id="add-fac-close" class="form-control" value="23:00" required>
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Số Lượng Sân Con Khởi Tạo</label>
          <input type="number" id="add-fac-courts" class="form-control" value="6" min="1" max="30" required>
        </div>
        
        <div style="display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 0.5rem;">
          <button type="button" class="btn btn-secondary btn-sm" onclick="app.closeModal()">Hủy</button>
          <button type="submit" class="btn btn-primary btn-sm"><i class="fa-solid fa-paper-plane"></i> Gửi Đăng Ký Kiểm Duyệt</button>
        </div>
      </form>
    `;
    this.openModal();
  }

  saveNewFacility(e) {
    e.preventDefault();
    const name = document.getElementById('add-fac-name').value.trim();
    const address = document.getElementById('add-fac-address').value.trim();
    const lat = parseFloat(document.getElementById('add-fac-lat').value) || 21.0153;
    const lng = parseFloat(document.getElementById('add-fac-lng').value) || 105.8152;
    const open_time = document.getElementById('add-fac-open').value;
    const close_time = document.getElementById('add-fac-close').value;
    const courts_count = parseInt(document.getElementById('add-fac-courts').value) || 6;

    const newFac = {
      id: Date.now(),
      name,
      address,
      latitude: lat,
      longitude: lng,
      open_time,
      close_time,
      is_approved: false,
      rating: 5.0,
      reviews_count: 1,
      img: "images/court1.jpg",
      courts_count
    };

    MockData.facilities.push(newFac);
    if (typeof saveMockDataToLocalStorage === 'function') {
      saveMockDataToLocalStorage();
    }
    this.closeModal();
    this.renderAdminApprovals();
    this.renderAdminOverviewFacilities();
    if (this.currentView === 'ui-20') this.renderDatabaseInspector();
    this.showToast("🎉 Đã gửi đăng ký cụm sân mới thành công! Hồ sơ đã được lưu và đẩy lên cho Admin phê duyệt.");
  }

  approveFacility(facId) {
    const fac = MockData.facilities.find(f => f.id === facId);
    if (fac) {
      fac.is_approved = true;
      if (typeof saveMockDataToLocalStorage === 'function') {
        saveMockDataToLocalStorage();
      }
    }
    this.renderAdminApprovals();
    this.renderCustomerFacilities();
    this.renderAdminOverviewFacilities();
    if (this.currentView === 'ui-20') this.renderDatabaseInspector();
    this.showToast("✅ Đã phê duyệt cụm sân thành công! Cụm sân đã được kích hoạt hiển thị công khai.");
  }

  rejectFacility(facId) {
    MockData.facilities = MockData.facilities.filter(f => f.id !== facId);
    if (typeof saveMockDataToLocalStorage === 'function') {
      saveMockDataToLocalStorage();
    }
    this.renderAdminApprovals();
    this.renderAdminOverviewFacilities();
    if (this.currentView === 'ui-20') this.renderDatabaseInspector();
    this.showToast("Đã gửi yêu cầu từ chối kèm lý do sửa đổi tới Chủ sân.", 'error');
  }

  openAddCourtModal() {
    const modalBody = document.getElementById('modal-body');
    modalBody.innerHTML = `
      <h3>🏸 Thêm Sân Con Mới</h3>
      <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px;">Khai báo tên sân con, loại thảm Yonex/Enlio và giá giờ cơ bản</p>

      <form onsubmit="app.saveNewCourt(event)" style="margin-top: 1rem; display: flex; flex-direction: column; gap: 0.75rem;">
        <div class="form-group">
          <label class="form-label">Tên Sân Con</label>
          <input type="text" id="add-court-name" class="form-control" placeholder="VD: Sân 05 - Thảm Yonex Pro" required>
        </div>
        <div class="form-group">
          <label class="form-label">Loại Thảm / Mặt Sân</label>
          <select id="add-court-type" class="form-control">
            <option value="Standard Matte">Standard Matte (Thảm Tiêu Chuẩn)</option>
            <option value="VIP Cushion">VIP Cushion (Thảm Giảm Chấn Cao Cấp)</option>
            <option value="Wooden Pro Flex">Wooden Pro Flex (Gỗ Sồi Thi Đấu)</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Giá Thuê Cơ Bản (VNĐ / Giờ)</label>
          <input type="number" id="add-court-price" class="form-control" value="120000" step="5000" required>
        </div>
        <div class="form-group">
          <label class="form-label">Trạng Thái Sân</label>
          <select id="add-court-status" class="form-control">
            <option value="Hoạt Động">Hoạt Động (Sẵn Sàng Mở Đặt)</option>
            <option value="Đang Bảo Trì">Đang Bảo Trì</option>
          </select>
        </div>

        <div style="display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 0.5rem;">
          <button type="button" class="btn btn-secondary btn-sm" onclick="app.closeModal()">Hủy</button>
          <button type="submit" class="btn btn-primary btn-sm"><i class="fa-solid fa-plus"></i> Thêm Sân Con</button>
        </div>
      </form>
    `;
    this.openModal();
  }

  saveNewCourt(e) {
    e.preventDefault();
    const name = document.getElementById('add-court-name').value.trim();
    const court_type = document.getElementById('add-court-type').value;
    const base_price = parseInt(document.getElementById('add-court-price').value) || 120000;
    const status = document.getElementById('add-court-status').value;

    const newCourt = {
      id: 200 + MockData.courts.length + 1,
      facility_id: 101,
      name,
      court_type,
      base_price,
      status
    };

    MockData.courts.push(newCourt);
    this.closeModal();
    this.renderOwnerCourts();
    this.showToast(`Đã thêm ${name} thành công!`);
  }

  openEditCourtModal(courtId) {
    const court = MockData.courts.find(c => c.id === courtId);
    if (!court) return;

    const modalBody = document.getElementById('modal-body');
    modalBody.innerHTML = `
      <h3>✏️ Chỉnh Sửa Thông Tin Sân #${court.id}</h3>
      <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px;">Cập nhật tên sân con, giá giờ niêm yết và trạng thái hoạt động</p>

      <form onsubmit="app.updateCourt(event, ${court.id})" style="margin-top: 1rem; display: flex; flex-direction: column; gap: 0.75rem;">
        <div class="form-group">
          <label class="form-label">Tên Sân Con</label>
          <input type="text" id="edit-court-name" class="form-control" value="${court.name}" required>
        </div>
        <div class="form-group">
          <label class="form-label">Loại Thảm / Mặt Sân</label>
          <select id="edit-court-type" class="form-control">
            <option value="Standard Matte" ${court.court_type === 'Standard Matte' ? 'selected' : ''}>Standard Matte (Thảm Tiêu Chuẩn)</option>
            <option value="VIP Cushion" ${court.court_type === 'VIP Cushion' ? 'selected' : ''}>VIP Cushion (Thảm Giảm Chấn Cao Cấp)</option>
            <option value="Wooden Pro Flex" ${court.court_type === 'Wooden Pro Flex' ? 'selected' : ''}>Wooden Pro Flex (Gỗ Sồi Thi Đấu)</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Giá Thuê Cơ Bản (VNĐ / Giờ)</label>
          <input type="number" id="edit-court-price" class="form-control" value="${court.base_price}" step="5000" required>
        </div>
        <div class="form-group">
          <label class="form-label">Trạng Thái Sân</label>
          <select id="edit-court-status" class="form-control">
            <option value="Hoạt Động" ${court.status === 'Hoạt Động' ? 'selected' : ''}>Hoạt Động (ACTIVE)</option>
            <option value="Đang Bảo Trì" ${court.status === 'Đang Bảo Trì' ? 'selected' : ''}>Đang Bảo Trì (MAINTENANCE)</option>
          </select>
        </div>

        <div style="display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 0.5rem;">
          <button type="button" class="btn btn-secondary btn-sm" onclick="app.closeModal()">Hủy</button>
          <button type="submit" class="btn btn-primary btn-sm"><i class="fa-solid fa-floppy-disk"></i> Lưu Thay Đổi</button>
        </div>
      </form>
    `;
    this.openModal();
  }

  updateCourt(e, courtId) {
    e.preventDefault();
    const court = MockData.courts.find(c => c.id === courtId);
    if (court) {
      court.name = document.getElementById('edit-court-name').value.trim();
      court.court_type = document.getElementById('edit-court-type').value;
      court.base_price = parseInt(document.getElementById('edit-court-price').value) || 120000;
      court.status = document.getElementById('edit-court-status').value;
    }

    this.closeModal();
    this.renderOwnerCourts();
    this.showToast(`Đã cập nhật sân #${courtId} thành công!`);
  }

  renderOwnerCourts() {
    const tbody = document.getElementById('owner-courts-table-body');
    let html = '';

    MockData.courts.forEach(court => {
      const isActive = court.status === 'Hoạt Động' || court.status === 'ACTIVE';
      html += `
        <tr>
          <td>#${court.id}</td>
          <td><strong>${court.name}</strong></td>
          <td>${court.court_type}</td>
          <td>${court.base_price.toLocaleString('vi-VN')}đ/h</td>
          <td><span class="tag-badge ${isActive ? 'tag-ai' : 'tag-pos'}">${court.status}</span></td>
          <td>
            <div style="display: flex; gap: 6px;">
              <button class="btn btn-secondary btn-sm" onclick="app.openEditCourtModal(${court.id})" title="Chỉnh Sửa Sân"><i class="fa-solid fa-pen"></i></button>
              <button class="btn btn-sm" style="background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3);" onclick="app.deleteCourt(${court.id})" title="Xóa Sân Thi Đấu"><i class="fa-solid fa-trash-can"></i> Xóa</button>
            </div>
          </td>
        </tr>
      `;
    });

    if (tbody) tbody.innerHTML = html;
  }

  deleteCourt(courtId) {
    const court = MockData.courts.find(c => c.id === courtId);
    if (!court) return;

    if (confirm(`⚠️ Bạn có chắc chắn muốn xóa "${court.name}" khỏi danh mục quản lý không?`)) {
      // Remove court from MockData
      MockData.courts = MockData.courts.filter(c => c.id !== courtId);
      // Also remove associated slots
      MockData.time_slots = MockData.time_slots.filter(s => s.court_id !== courtId);
      
      this.renderOwnerCourts();
      this.renderSlotMatrix();
      this.showToast(`🗑️ Đã xóa thành công sân "${court.name}"!`, "success");
    }
  }

  pickGPSLocation(e) {
    const box = document.getElementById('owner-gps-map-box');
    const pin = document.getElementById('owner-map-pin');
    const coordsText = document.getElementById('owner-gps-coords-text');

    if (!box || !pin) return;
    const rect = box.getBoundingClientRect();
    const scale = this.mapZoomScale || 1.0;

    // Tính toán vị trí click chính xác trong không gian tọa độ đã thu phóng (Zoom Space)
    const clickXFromCenter = (e.clientX - rect.left) - rect.width / 2;
    const clickYFromCenter = (e.clientY - rect.top) - rect.height / 2;

    const unscaledXFromCenter = clickXFromCenter / scale;
    const unscaledYFromCenter = clickYFromCenter / scale;

    const rawXPercent = ((rect.width / 2 + unscaledXFromCenter) / rect.width) * 100;
    const rawYPercent = ((rect.height / 2 + unscaledYFromCenter) / rect.height) * 100;

    const xPercent = Math.min(Math.max(Math.round(rawXPercent), 2), 98);
    const yPercent = Math.min(Math.max(Math.round(rawYPercent), 2), 98);

    pin.style.left = `${xPercent}%`;
    pin.style.top = `${yPercent}%`;
    
    this.pinnedXPercent = xPercent;
    this.pinnedYPercent = yPercent;

    this.updateMapZoomUI();

    const newLat = (10.7 + (100 - yPercent) * 0.003).toFixed(4);
    const newLng = (106.6 + xPercent * 0.003).toFixed(4);

    if (coordsText) {
      coordsText.textContent = `${newLat} N, ${newLng} E`;
    }

    this.showToast(`📍 Đã ghim vị trí GPS mới: ${newLat} N, ${newLng} E!`);
  }

  initLeafletMap() {
    this.initOwnerGoogleMap();
  }

  initOwnerGoogleMap() {
    const container = document.getElementById('owner-google-map-container');
    if (!container) return;

    if (this.ownerGoogleMap) {
      setTimeout(() => {
        this.ownerGoogleMap.invalidateSize();
      }, 200);
      return;
    }

    // Default center at central Hanoi badminton arena (102 Láng Hạ: 21.0153, 105.8152)
    const initialLat = 21.0153;
    const initialLng = 105.8152;

    this.ownerGoogleMap = L.map('owner-google-map-container', {
      center: [initialLat, initialLng],
      zoom: 13,
      zoomControl: false
    });

    // Zoom control bottom-right
    L.control.zoom({ position: 'bottomright' }).addTo(this.ownerGoogleMap);

    // Primary Google Roads Layer
    this.ownerGoogleRoadsLayer = L.tileLayer('https://{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', {
      maxZoom: 20,
      subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
      attribution: '&copy; Google Maps'
    });

    // Google Satellite Layer
    this.ownerGoogleSatelliteLayer = L.tileLayer('https://{s}.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', {
      maxZoom: 20,
      subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
      attribution: '&copy; Google Maps Satellite'
    });

    // Fallback OpenStreetMap
    this.ownerOsmFallbackLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap'
    });

    this.ownerMapTileType = 'roads';
    this.ownerGoogleRoadsLayer.addTo(this.ownerGoogleMap);

    let ownerTileFallback = false;
    this.ownerGoogleRoadsLayer.on('tileerror', () => {
      if (!ownerTileFallback && this.ownerGoogleMap) {
        ownerTileFallback = true;
        this.ownerGoogleMap.removeLayer(this.ownerGoogleRoadsLayer);
        this.ownerOsmFallbackLayer.addTo(this.ownerGoogleMap);
      }
    });

    // Marker Layer Group for surrounding sports facilities
    this.ownerSportsMarkerGroup = L.layerGroup().addTo(this.ownerGoogleMap);
    this.currentOwnerMapFilter = 'all';
    this.renderOwnerSportsMarkers();

    // Red Google Pin Marker for Court Location (Drag & Drop or Click to re-position)
    const customPin = L.divIcon({
      className: 'owner-google-pin',
      html: `
        <div style="display: flex; flex-direction: column; align-items: center; cursor: grab; z-index: 9999;">
          <div style="width: 44px; height: 44px; border-radius: 50% 50% 50% 0; background: linear-gradient(135deg, #ef4444, #dc2626); border: 3px solid #ffffff; box-shadow: 0 6px 18px rgba(220,38,38,0.45); transform: rotate(-45deg); display: flex; align-items: center; justify-content: center;">
            <span style="transform: rotate(45deg); font-size: 20px; color: #fff;">🏸</span>
          </div>
          <div style="width: 12px; height: 12px; border-radius: 50%; background: rgba(0,0,0,0.35); margin-top: -4px; filter: blur(1.5px);"></div>
        </div>
      `,
      iconSize: [44, 52],
      iconAnchor: [22, 52],
      popupAnchor: [0, -52]
    });

    this.ownerMarker = L.marker([initialLat, initialLng], {
      icon: customPin,
      draggable: true,
      zIndexOffset: 1000
    }).addTo(this.ownerGoogleMap);

    this.ownerMarker.bindPopup("🏸 <strong>Vị trí đón khách của Cơ Sở Sân Của Bạn</strong><br><small style='color: #64748b;'>Kéo hoặc bấm bất kỳ đâu trên bản đồ để đổi vị trí</small>").openPopup();

    this.ownerGoogleMap.on('click', (e) => {
      const { lat, lng } = e.latlng;
      this.ownerMarker.setLatLng([lat, lng]);
      this.updateGPSCoordsDisplay(lat, lng);
    });

    this.ownerMarker.on('dragend', (e) => {
      const { lat, lng } = e.target.getLatLng();
      this.updateGPSCoordsDisplay(lat, lng);
    });

    setTimeout(() => {
      if (this.ownerGoogleMap) this.ownerGoogleMap.invalidateSize();
    }, 250);
  }

  renderOwnerSportsMarkers() {
    if (!this.ownerGoogleMap || !this.ownerSportsMarkerGroup) return;

    this.ownerSportsMarkerGroup.clearLayers();

    const facilities = MockData.facilities.filter(f => f.is_approved !== false);
    const filter = this.currentOwnerMapFilter || 'all';

    let visibleCount = 0;
    const drawerListContainer = document.getElementById('owner-drawer-facilities-list');
    let drawerHtml = '';

    facilities.forEach(fac => {
      if (filter === 'standard') {
        const hasYonex = (fac.badges && fac.badges.some(b => b.toLowerCase().includes('yonex'))) || fac.name.toLowerCase().includes('yonex');
        if (!hasYonex) return;
      } else if (filter === 'vip') {
        const hasVip = (fac.badges && fac.badges.some(b => b.toLowerCase().includes('enlio') || b.toLowerCase().includes('vip'))) || fac.name.toLowerCase().includes('vip');
        if (!hasVip) return;
      } else if (filter === 'ac') {
        const hasAC = (fac.badges && fac.badges.some(b => b.toLowerCase().includes('máy lạnh') || b.toLowerCase().includes('ac'))) || fac.name.toLowerCase().includes('arena') || fac.name.toLowerCase().includes('hub');
        if (!hasAC) return;
      } else if (filter === 'near') {
        const distNum = parseFloat(fac.distance) || 5.0;
        if (distNum > 5.0) return;
      }

      visibleCount++;

      // Pure Badminton Pin Icon
      const pinHtml = `
        <div class="sports-map-marker badminton" title="${fac.name}">
          <span class="sports-map-marker-icon">🏸</span>
        </div>
      `;

      const customIcon = L.divIcon({
        className: 'custom-sports-pin',
        html: pinHtml,
        iconSize: [34, 34],
        iconAnchor: [17, 34],
        popupAnchor: [0, -34]
      });

      const marker = L.marker([fac.latitude, fac.longitude], { icon: customIcon });
      
      // Khi chủ sân bấm vào logo chiếc vợt 🏸
      marker.on('click', (e) => {
        L.DomEvent.stopPropagation(e);
        this.showOwnerFacilityDetail(fac);
        this.ownerGoogleMap.panTo([fac.latitude, fac.longitude], { animate: true });
      });

      this.ownerSportsMarkerGroup.addLayer(marker);

      drawerHtml += `
        <div class="drawer-facility-card" onclick="app.panToOwnerFacilityOnMap(${fac.id})">
          <img src="${fac.img}" alt="${fac.name}" style="width: 65px; height: 65px; object-fit: cover; border-radius: 8px; flex-shrink: 0;" onerror="this.src='images/court1.jpg'">
          <div style="flex: 1; min-width: 0;">
            <strong style="font-size: 0.88rem; color: #0f172a; display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${fac.name}</strong>
            <p style="font-size: 0.75rem; color: #64748b; margin: 2px 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">${fac.address}</p>
            <div style="display: flex; justify-content: space-between; font-size: 0.75rem;">
              <span style="color: #16a34a; font-weight: 700;">📍 ${fac.distance || 'Gần bạn'}</span>
              <span style="color: #f59e0b; font-weight: 700;">⭐ ${fac.rating}</span>
            </div>
          </div>
        </div>
      `;
    });

    const countEl = document.getElementById('owner-drawer-count');
    if (countEl) countEl.textContent = visibleCount;

    if (drawerListContainer) {
      drawerListContainer.innerHTML = drawerHtml || '<p style="text-align: center; color: #64748b; padding: 2rem;">Không tìm thấy sân cầu lông phù hợp bộ lọc.</p>';
    }
  }

  showOwnerFacilityDetail(fac) {
    // 1. Render popup nổi bên trong map
    const previewPopup = document.getElementById('owner-facility-preview-card');
    if (previewPopup) {
      previewPopup.innerHTML = `
        <div style="display: flex; gap: 12px; align-items: center;">
          <img src="${fac.img}" alt="${fac.name}" style="width: 76px; height: 76px; border-radius: 10px; object-fit: cover; border: 1.5px solid #e2e8f0; flex-shrink: 0;" onerror="this.src='images/court1.jpg'">
          <div style="flex: 1; min-width: 0;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
              <h4 style="margin: 0 0 4px; font-size: 0.95rem; font-weight: 800; color: #0f172a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${fac.name}</h4>
              <button onclick="app.hideOwnerFacilityDetail()" style="background: none; border: none; font-size: 1.1rem; color: #94a3b8; cursor: pointer; padding: 0 0 0 8px;">&times;</button>
            </div>
            <p style="font-size: 0.75rem; color: #64748b; margin: 0 0 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
              <i class="fa-solid fa-location-dot" style="color: #167946;"></i> ${fac.address}
            </p>
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 6px;">
              <span style="font-size: 0.78rem; font-weight: 700; color: #dc2626;">💰 ${fac.price_range || '120.000đ/giờ'}</span>
              <button class="btn btn-sm" onclick="app.confirmDeleteFacility(${fac.id}, '${fac.name.replace(/'/g, "\\'")}')" style="background: #fee2e2; color: #dc2626; border: 1px solid #fca5a5; font-size: 0.75rem; padding: 3px 10px; border-radius: 6px; font-weight: 700; cursor: pointer;">
                <i class="fa-solid fa-trash-can"></i> Xóa Sân Này
              </button>
            </div>
          </div>
        </div>
      `;
      previewPopup.style.display = 'block';
    }

    // 2. Render hộp thông tin chi tiết đầy đủ ở ngay bên dưới bản đồ
    const detailBox = document.getElementById('owner-selected-facility-detail-card');
    if (detailBox) {
      const badgesHtml = (fac.badges || []).map(b => `<span style="background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; font-size: 0.75rem; padding: 2px 8px; border-radius: 12px; font-weight: 600;">${b}</span>`).join(' ');

      detailBox.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
          <div>
            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
              <span style="background: #167946; color: #fff; padding: 3px 10px; border-radius: 6px; font-size: 0.78rem; font-weight: 700;">MÃ SÂN #${fac.id}</span>
              <h3 style="margin: 0; font-size: 1.15rem; color: #0f172a; font-weight: 800;">🏸 ${fac.name}</h3>
              <span style="color: #f59e0b; font-weight: 700; font-size: 0.88rem;">⭐ ${fac.rating} (${fac.reviews_count || 50}+ đánh giá)</span>
            </div>
            <p style="margin: 4px 0 0; font-size: 0.85rem; color: #64748b;">
              <i class="fa-solid fa-location-dot" style="color: #167946;"></i> <strong>Địa chỉ:</strong> ${fac.address}
            </p>
          </div>
          <div style="display: flex; gap: 8px; align-items: center;">
            <button class="btn btn-sm" onclick="app.focusMapToFacility(${fac.latitude}, ${fac.longitude})" style="background: #ecfdf5; color: #167946; border: 1px solid #bbf7d0;">
              <i class="fa-solid fa-crosshairs"></i> Phóng Tới Sân
            </button>
            <button class="btn btn-sm btn-danger" onclick="app.confirmDeleteFacility(${fac.id}, '${fac.name.replace(/'/g, "\\'")}')" style="background: #dc2626; color: #ffffff; border: none; font-weight: 700; padding: 6px 14px; border-radius: 8px; box-shadow: 0 4px 12px rgba(220,38,38,0.25);">
              <i class="fa-solid fa-trash-can"></i> XÓA SÂN NÀY KHỎI HỆ THỐNG
            </button>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; background: #f8fafc; padding: 12px 16px; border-radius: 10px; border: 1px solid #e2e8f0; font-size: 0.85rem;">
          <div><strong>⏱️ Giờ mở cửa:</strong> <span style="color: #0f172a; font-weight: 600;">${fac.open_hours || fac.open_time + ' - ' + fac.close_time}</span></div>
          <div><strong>🏸 Quy mô:</strong> <span style="color: #167946; font-weight: 700;">${fac.courts_count || 3} Sân con thi đấu</span></div>
          <div><strong>💵 Giá thuê niêm yết:</strong> <span style="color: #dc2626; font-weight: 700;">${fac.price_range || '120.000đ/giờ'}</span></div>
          <div><strong>📍 Tọa độ GPS:</strong> <span style="font-family: monospace; color: #0369a1; font-weight: 600;">${fac.latitude.toFixed(4)} N, ${fac.longitude.toFixed(4)} E</span></div>
        </div>

        <div style="margin-top: 10px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
          <span style="font-size: 0.82rem; color: #64748b; font-weight: 600;">Tiện ích & Thảm:</span>
          ${badgesHtml}
        </div>
      `;
      detailBox.style.display = 'block';
      detailBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    this.showToast(`🏸 Đã chọn sân: ${fac.name}`);
  }

  hideOwnerFacilityDetail() {
    const previewPopup = document.getElementById('owner-facility-preview-card');
    if (previewPopup) previewPopup.style.display = 'none';

    const detailBox = document.getElementById('owner-selected-facility-detail-card');
    if (detailBox) detailBox.style.display = 'none';
  }

  focusMapToFacility(lat, lng) {
    if (this.ownerGoogleMap) {
      this.ownerGoogleMap.setView([lat, lng], 16, { animate: true });
    }
  }

  confirmDeleteFacility(facId, facName) {
    const confirmed = confirm(`⚠️ BẠN CÓ CHẮC CHẮN MUỐN XÓA SÂN:\n\n"${facName}"\n\nSau khi xóa, cụm sân này sẽ được gỡ bỏ hoàn toàn khỏi bản đồ và hệ thống đặt sân của bạn!`);
    if (!confirmed) return;

    // Xóa khỏi MockData.facilities
    const idx = MockData.facilities.findIndex(f => f.id === facId);
    if (idx !== -1) {
      MockData.facilities.splice(idx, 1);
    }

    // Ẩn bảng chi tiết
    this.hideOwnerFacilityDetail();

    // Re-render lại các marker trên bản đồ
    this.renderOwnerSportsMarkers();
    if (this.googleSportsMap) {
      this.renderGoogleSportsMarkers();
    }
    this.renderCustomerFacilities();

    this.showToast(`🗑️ Đã xóa thành công sân "${facName}" khỏi hệ thống!`);
  }

  filterOwnerMapBadminton(category, btn) {
    this.currentOwnerMapFilter = category;

    document.querySelectorAll('[data-owner-filter]').forEach(c => c.classList.remove('active'));
    if (btn) btn.classList.add('active');

    this.renderOwnerSportsMarkers();
    const labelMap = {
      'all': 'Tất cả sân cầu',
      'standard': 'Thảm Yonex Pro',
      'vip': 'Thảm Enlio VIP',
      'ac': 'Có máy lạnh',
      'near': 'Gần tôi (< 5km)'
    };
    this.showToast(`🏸 Bộ lọc chủ sân: ${labelMap[category] || category}`);
  }

  toggleOwnerFacilitiesSidebar() {
    const drawer = document.getElementById('owner-map-facilities-drawer');
    if (!drawer) return;
    drawer.classList.toggle('open');
  }

  panToOwnerFacilityOnMap(facId) {
    const fac = MockData.facilities.find(f => f.id === facId);
    if (!fac || !this.ownerGoogleMap) return;

    this.ownerGoogleMap.setView([fac.latitude, fac.longitude], 16, { animate: true });
    this.toggleOwnerFacilitiesSidebar();
    this.showOwnerFacilityDetail(fac);
  }

  toggleOwnerMapTileLayer() {
    if (!this.ownerGoogleMap) return;

    if (this.ownerMapTileType === 'roads') {
      this.ownerGoogleMap.removeLayer(this.ownerGoogleRoadsLayer);
      if (this.ownerGoogleMap.hasLayer(this.ownerOsmFallbackLayer)) {
        this.ownerGoogleMap.removeLayer(this.ownerOsmFallbackLayer);
      }
      this.ownerGoogleSatelliteLayer.addTo(this.ownerGoogleMap);
      this.ownerMapTileType = 'satellite';
      this.showToast("🛰️ Đã đổi bản đồ quản lý sang Vệ Tinh Google!");
    } else {
      this.ownerGoogleMap.removeLayer(this.ownerGoogleSatelliteLayer);
      this.ownerGoogleRoadsLayer.addTo(this.ownerGoogleMap);
      this.ownerMapTileType = 'roads';
      this.showToast("🗺️ Đã đổi bản đồ quản lý sang Đường Phố Google!");
    }
  }

  locateOwnerGPS() {
    if (!this.ownerGoogleMap) return;

    if (navigator.geolocation) {
      this.showToast("📡 Đang lấy tọa độ GPS chính xác...");
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const lat = pos.coords.latitude;
          const lng = pos.coords.longitude;
          this.ownerGoogleMap.setView([lat, lng], 16, { animate: true });
          if (this.ownerMarker) {
            this.ownerMarker.setLatLng([lat, lng]);
          }
          this.updateGPSCoordsDisplay(lat, lng);
          this.showToast("🎯 Đã định vị chính xác cơ sở sân của bạn!");
        },
        () => {
          this.ownerGoogleMap.setView([21.0153, 105.8152], 16);
          this.showToast("📍 Vị trí trung tâm: Đống Đa, Hà Nội");
        }
      );
    } else {
      this.ownerGoogleMap.setView([21.0153, 105.8152], 16);
    }
  }

  // Dynamic Multi-Tier Geocoding Engine (Nominatim -> Progressive Cleaning -> Photon -> VN Geo Dictionary)
  async geocodeAddress(query) {
    if (!query || !query.trim()) return null;
    const rawQuery = query.trim();

    // 1. Prepare search variations
    // Remove micro-administrative prefixes like "Tổ 5", "TDP 12", "Số 123", "Ngõ 45/6", "Xóm 3", "Thôn 2", "Khu phố 1"
    const cleanedQuery = rawQuery
      .replace(/^(tổ|tdp|tổ dân phố|số nhà|số|ngõ|ngách|hẻm|xóm|thôn|khu phố|khu)\s+[\w\d\.\/\-]+\s*[,-\s]*/gi, '')
      .trim();

    const hasCountry = /vi[eệ]t\s*nam|vn/i.test(rawQuery);
    const queryTier1 = hasCountry ? rawQuery : `${rawQuery}, Việt Nam`;
    const queryTier2 = cleanedQuery && cleanedQuery.toLowerCase() !== rawQuery.toLowerCase() 
      ? (hasCountry ? cleanedQuery : `${cleanedQuery}, Việt Nam`) 
      : null;

    // Helper: Nominatim fetch
    const fetchNominatim = async (q) => {
      try {
        const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(q)}&addressdetails=1&limit=5`;
        const res = await fetch(url, { headers: { 'Accept-Language': 'vi,en' } });
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data) && data.length > 0) {
            return {
              lat: parseFloat(data[0].lat),
              lng: parseFloat(data[0].lon),
              displayName: data[0].display_name.split(',')[0] || data[0].display_name,
              source: 'Nominatim'
            };
          }
        }
      } catch (e) {
        console.warn('Nominatim error:', e);
      }
      return null;
    };

    // Helper: Photon API fetch
    const fetchPhoton = async (q) => {
      try {
        const url = `https://photon.komoot.io/api/?q=${encodeURIComponent(q)}&limit=5`;
        const res = await fetch(url);
        if (res.ok) {
          const data = await res.json();
          if (data && data.features && data.features.length > 0) {
            const vnFeature = data.features.find(f => f.properties && f.properties.countrycode === 'VN') || data.features[0];
            if (vnFeature && vnFeature.geometry && vnFeature.geometry.coordinates) {
              const coords = vnFeature.geometry.coordinates;
              return {
                lat: coords[1],
                lng: coords[0],
                displayName: vnFeature.properties.name || vnFeature.properties.city || rawQuery,
                source: 'Photon'
              };
            }
          }
        }
      } catch (e) {
        console.warn('Photon error:', e);
      }
      return null;
    };

    // Helper: Built-in Vietnamese Regional & District Geo Dictionary (Guarantees 100% offline & fallback match)
    const matchGeoDictionary = (q) => {
      const norm = q.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d");
      
      const geoDict = [
        // Thái Nguyên & wards / districts
        { keys: ['quan trieu', 'phuong quan trieu'], lat: 21.6247, lng: 105.8194, name: 'Phường Quan Triều, TP. Thái Nguyên' },
        { keys: ['tan thinh', 'phuong tan thinh'], lat: 21.5670, lng: 105.8234, name: 'Phường Tân Thịnh, TP. Thái Nguyên' },
        { keys: ['phan dinh phung'], lat: 21.5889, lng: 105.8398, name: 'Phường Phan Đình Phùng, TP. Thái Nguyên' },
        { keys: ['hoang van thu'], lat: 21.5954, lng: 105.8385, name: 'Phường Hoàng Văn Thụ, TP. Thái Nguyên' },
        { keys: ['linh son'], lat: 21.6050, lng: 105.8750, name: 'Xã Linh Sơn, TP. Thái Nguyên' },
        { keys: ['song cong'], lat: 21.4921, lng: 105.8166, name: 'TP. Sông Công, Thái Nguyên' },
        { keys: ['pho yen'], lat: 21.4172, lng: 105.8703, name: 'TP. Phổ Yên, Thái Nguyên' },
        { keys: ['dong hy'], lat: 21.6358, lng: 105.8825, name: 'Huyện Đồng Hỷ, Thái Nguyên' },
        { keys: ['thai nguyen', 'tp thai nguyen', 'tinh thai nguyen'], lat: 21.5928, lng: 105.8442, name: 'TP. Thái Nguyên, Tỉnh Thái Nguyên' },

        // Hà Nội & districts / landmarks
        { keys: ['dong da', 'lang ha', 'chua boc', 'thai ha', 'o cho dua'], lat: 21.0153, lng: 105.8152, name: 'Quận Đống Đa, Hà Nội' },
        { keys: ['cau giay', 'duy tan', 'xuan thuy', 'tran thai tong', 'trung hoa'], lat: 21.0362, lng: 105.7906, name: 'Quận Cầu Giấy, Hà Nội' },
        { keys: ['hoan kiem', 'ho guom', 'pho co', 'trang tien', 'hang bai'], lat: 21.0285, lng: 105.8542, name: 'Quận Hoàn Kiếm, Hà Nội' },
        { keys: ['ba dinh', 'kim ma', 'lieu giai', 'doi can', 'giang vo'], lat: 21.0341, lng: 105.8242, name: 'Quận Ba Đình, Hà Nội' },
        { keys: ['thanh xuan', 'nguyen trai', 'khuat duy tien', 'le van luong'], lat: 20.9980, lng: 105.8071, name: 'Quận Thanh Xuân, Hà Nội' },
        { keys: ['hai ba trung', 'ba trieu', 'pho hue', 'bach mai', 'dai co viet'], lat: 21.0068, lng: 105.8524, name: 'Quận Hai Bà Trưng, Hà Nội' },
        { keys: ['nam tu liem', 'my dinh', 'le duc tho', 'me tri'], lat: 21.0135, lng: 105.7656, name: 'Quận Nam Từ Liêm, Hà Nội' },
        { keys: ['bac tu liem', 'co nhue', 'xuan dinh'], lat: 21.0620, lng: 105.7602, name: 'Quận Bắc Từ Liêm, Hà Nội' },
        { keys: ['tay ho', 'ho tay', 'lac long quan', 'thuy khue', 'quang an'], lat: 21.0718, lng: 105.8245, name: 'Quận Tây Hồ, Hà Nội' },
        { keys: ['hoang mai', 'linh dam', 'dinh cong', 'giai phong'], lat: 20.9765, lng: 105.8521, name: 'Quận Hoàng Mai, Hà Nội' },
        { keys: ['long bien', 'viet hung', 'nguyen van cu'], lat: 21.0487, lng: 105.8885, name: 'Quận Long Biên, Hà Nội' },
        { keys: ['ha dong', 'quang trung', 'van quan', 'mo lao'], lat: 20.9634, lng: 105.7725, name: 'Quận Hà Đông, Hà Nội' },
        { keys: ['ha noi', 'tp ha noi', 'thanh pho ha noi', 'thu do'], lat: 21.0285, lng: 105.8542, name: 'Hà Nội' },

        // TP. Hồ Chí Minh
        { keys: ['quan 1', 'q1', 'ben nghe', 'ben thanh', 'nguyen hue', 'dong khoi'], lat: 10.7769, lng: 106.7009, name: 'Quận 1, TP. Hồ Chí Minh' },
        { keys: ['quan 3', 'q3', 'vo thi sau'], lat: 10.7844, lng: 106.6843, name: 'Quận 3, TP. Hồ Chí Minh' },
        { keys: ['quan 7', 'q7', 'phu my hung', 'tan phong'], lat: 10.7340, lng: 106.7218, name: 'Quận 7, TP. Hồ Chí Minh' },
        { keys: ['binh thanh', 'hang xanh', 'bach dang', 'xo viet nghe tinh'], lat: 10.8015, lng: 106.7114, name: 'Quận Bình Thạnh, TP. Hồ Chí Minh' },
        { keys: ['tan binh', 'cong hoa', 'truong chinh', 'san bay tan son nhat'], lat: 10.8014, lng: 106.6526, name: 'Quận Tân Bình, TP. Hồ Chí Minh' },
        { keys: ['thu duc', 'tp thu duc', 'thao dien', 'an phu'], lat: 10.8494, lng: 106.7537, name: 'TP. Thủ Đức, TP. Hồ Chí Minh' },
        { keys: ['go vap', 'quang trung go vap'], lat: 10.8387, lng: 106.6653, name: 'Quận Gò Vấp, TP. Hồ Chí Minh' },
        { keys: ['phu nhuan', 'phan xich long'], lat: 10.7992, lng: 106.6803, name: 'Quận Phú Nhuận, TP. Hồ Chí Minh' },
        { keys: ['quan 10', 'q10', 'su van hanh', '3 thang 2'], lat: 10.7716, lng: 106.6675, name: 'Quận 10, TP. Hồ Chí Minh' },
        { keys: ['quan 5', 'q5', 'cho lon', 'an dong'], lat: 10.7554, lng: 106.6669, name: 'Quận 5, TP. Hồ Chí Minh' },
        { keys: ['ho chi minh', 'tp hcm', 'tphcm', 'sai gon', 'tp ho chi minh'], lat: 10.7769, lng: 106.7009, name: 'TP. Hồ Chí Minh' },

        // Các tỉnh thành trọng điểm toàn quốc
        { keys: ['da nang', 'hai chau', 'son tra', 'ngu hanh son'], lat: 16.0544, lng: 108.2022, name: 'TP. Đà Nẵng' },
        { keys: ['hai phong', 'hong bang', 'ngo quyen', 'le chan', 'do son'], lat: 20.8449, lng: 106.6881, name: 'TP. Hải Phòng' },
        { keys: ['can tho', 'ninh kieu', 'cai rang'], lat: 10.0452, lng: 105.7469, name: 'TP. Cần Thơ' },
        { keys: ['bac ninh', 'tu son', 'yen phong'], lat: 21.1861, lng: 106.0763, name: 'Tỉnh Bắc Ninh' },
        { keys: ['bac giang', 'viet yen'], lat: 21.2731, lng: 106.1946, name: 'Tỉnh Bắc Giang' },
        { keys: ['vinh phuc', 'vinh yen', 'phuc yen'], lat: 21.3089, lng: 105.6049, name: 'Tỉnh Vĩnh Phúc' },
        { keys: ['phu tho', 'viet tri'], lat: 21.3228, lng: 105.4019, name: 'Tỉnh Phú Thọ' },
        { keys: ['quang ninh', 'ha long', 'cam pha', 'bai chay'], lat: 20.9505, lng: 107.0734, name: 'Tỉnh Quảng Ninh' },
        { keys: ['hai duong', 'chi linh'], lat: 20.9372, lng: 106.3146, name: 'Tỉnh Hải Dương' },
        { keys: ['hung yen', 'pho noi', 'van giang'], lat: 20.6464, lng: 106.0511, name: 'Tỉnh Hưng Yên' },
        { keys: ['nam dinh'], lat: 20.4347, lng: 106.1772, name: 'Tỉnh Nam Định' },
        { keys: ['ninh binh', 'tam diep'], lat: 20.2506, lng: 105.9745, name: 'Tỉnh Ninh Bình' },
        { keys: ['thanh hoa', 'sam son'], lat: 19.8067, lng: 105.7852, name: 'Tỉnh Thanh Hóa' },
        { keys: ['nghe an', 'tp vinh', 'cua lo'], lat: 18.6734, lng: 105.6813, name: 'Tỉnh Nghệ An' },
        { keys: ['ha tinh'], lat: 18.3435, lng: 105.9058, name: 'Tỉnh Hà Tĩnh' },
        { keys: ['quang binh', 'dong hoi'], lat: 17.4690, lng: 106.6225, name: 'Tỉnh Quảng Bình' },
        { keys: ['thua thien hue', 'hue', 'tp hue'], lat: 16.4637, lng: 107.5909, name: 'Thừa Thiên Huế' },
        { keys: ['quang nam', 'hoi an', 'tam ky'], lat: 15.5658, lng: 108.4795, name: 'Tỉnh Quảng Nam' },
        { keys: ['quang ngai'], lat: 15.1205, lng: 108.7923, name: 'Tỉnh Quảng Ngãi' },
        { keys: ['binh dinh', 'quy nhon'], lat: 13.7820, lng: 109.2197, name: 'Tỉnh Bình Định' },
        { keys: ['phu yen', 'tuy hoa'], lat: 13.0882, lng: 109.3075, name: 'Tỉnh Phú Yên' },
        { keys: ['khanh hoa', 'nha trang', 'cam ranh'], lat: 12.2388, lng: 109.1967, name: 'Tỉnh Khánh Hòa' },
        { keys: ['binh thuan', 'phan thiet', 'mui ne'], lat: 10.9289, lng: 108.1021, name: 'Tỉnh Bình Thuận' },
        { keys: ['dak lak', 'buon ma thuot', 'bmt'], lat: 12.6675, lng: 108.0383, name: 'Tỉnh Đắk Lắk' },
        { keys: ['gia lai', 'pleiku'], lat: 13.9833, lng: 108.0000, name: 'Tỉnh Gia Lai' },
        { keys: ['lam dong', 'da lat', 'bao loc'], lat: 11.9404, lng: 108.4583, name: 'Tỉnh Lâm Đồng' },
        { keys: ['binh duong', 'thu dau mot', 'di an', 'thuan an'], lat: 10.9805, lng: 106.6519, name: 'Tỉnh Bình Dương' },
        { keys: ['dong nai', 'bien hoa', 'long khanh'], lat: 10.9574, lng: 106.8427, name: 'Tỉnh Đồng Nai' },
        { keys: ['ba ria vung tau', 'vung tau', 'ba ria'], lat: 10.3460, lng: 107.0843, name: 'Bà Rịa - Vũng Tàu' },
        { keys: ['long an', 'tan an'], lat: 10.5361, lng: 106.4116, name: 'Tỉnh Long An' },
        { keys: ['tien giang', 'my tho'], lat: 10.3541, lng: 106.3653, name: 'Tỉnh Tiền Giang' },
        { keys: ['kien giang', 'rach gia', 'phu quoc'], lat: 10.0125, lng: 105.0809, name: 'Tỉnh Kiên Giang' },
        { keys: ['an giang', 'long xuyen', 'chau doc'], lat: 10.3759, lng: 105.4389, name: 'Tỉnh An Giang' },
        { keys: ['dong thap', 'cao lanh', 'sa dec'], lat: 10.4578, lng: 105.6322, name: 'Tỉnh Đồng Tháp' },
        { keys: ['ben tre'], lat: 10.2433, lng: 106.3759, name: 'Tỉnh Bến Tre' },
        { keys: ['vinh long'], lat: 10.2537, lng: 105.9722, name: 'Tỉnh Vĩnh Long' },
        { keys: ['ca mau'], lat: 9.1769, lng: 105.1501, name: 'Tỉnh Cà Mau' }
      ];

      for (const item of geoDict) {
        for (const k of item.keys) {
          if (norm.includes(k)) {
            return {
              lat: item.lat,
              lng: item.lng,
              displayName: item.name,
              source: 'GeoDictionary'
            };
          }
        }
      }
      return null;
    };

    // 1. Try Nominatim (Tier 1)
    let result = await fetchNominatim(queryTier1);
    if (result) return result;

    // 2. Try Nominatim simplified (Tier 2)
    if (queryTier2) {
      result = await fetchNominatim(queryTier2);
      if (result) return result;
    }

    // 3. Try Photon (Tier 3)
    result = await fetchPhoton(queryTier1);
    if (result) return result;

    if (queryTier2) {
      result = await fetchPhoton(queryTier2);
      if (result) return result;
    }

    // 4. Try Built-in Geo Dictionary (Tier 4)
    result = matchGeoDictionary(rawQuery);
    if (result) return result;

    return null;
  }

  async searchOwnerMapAddress(e) {
    if (e) e.preventDefault();
    const input = document.getElementById('owner-map-search-input') || document.getElementById('map-search-address-input');
    if (!input || !input.value.trim()) return;

    const query = input.value.trim();
    this.showToast(`🔍 Đang tìm địa chỉ: "${query}"...`);

    try {
      const result = await this.geocodeAddress(query);

      if (result) {
        const { lat, lng, displayName } = result;
        if (this.ownerGoogleMap) {
          this.ownerGoogleMap.setView([lat, lng], 16, { animate: true });
        }
        if (this.ownerMarker) {
          this.ownerMarker.setLatLng([lat, lng]);
        }
        this.updateGPSCoordsDisplay(lat, lng);
        this.showToast(`🎯 Đã ghim vị trí: ${displayName}!`);
      } else {
        this.showToast(`⚠️ Không tìm thấy địa chỉ "${query}". Hãy thử gõ thêm tên quận, huyện hoặc thành phố!`);
      }
    } catch (err) {
      console.warn("Geocoding error:", err);
      this.showToast(`⚠️ Lỗi tìm kiếm địa chỉ. Bạn có thể bấm trực tiếp lên bản đồ Google để ghim!`);
    }
  }

  updateGPSCoordsDisplay(lat, lng) {
    const coordsText = document.getElementById('owner-gps-coords-text');
    if (coordsText) {
      coordsText.textContent = `${lat.toFixed(4)} N, ${lng.toFixed(4)} E`;
    }
    this.showToast(`📍 Đã cập nhật tọa độ GPS mới: ${lat.toFixed(4)} N, ${lng.toFixed(4)} E!`);
  }

  /* ------------------------------------------------------------------------
     GOOGLE MAPS INTERACTIVE SPORTS EXPLORER ENGINE (Alobo Style)
     ------------------------------------------------------------------------ */
  openFacilitiesMap() {
    this.navigateTo('ui-map');
  }

  initGoogleSportsMap() {
    const mapContainer = document.getElementById('google-sports-map');
    if (!mapContainer) return;

    if (this.googleSportsMap) {
      setTimeout(() => {
        this.googleSportsMap.invalidateSize();
      }, 250);
      return;
    }

    // Initialize Map at central Hanoi (as seen in user screenshot: Hanoi sports clusters)
    this.googleSportsMap = L.map('google-sports-map', {
      center: [21.0285, 105.8150],
      zoom: 12,
      zoomControl: false // custom floating controls
    });

    // Add zoom control top-right
    L.control.zoom({ position: 'bottomright' }).addTo(this.googleSportsMap);

    // Primary Layer: Google Maps Roads / Clean Sports Tile Layer
    this.googleRoadsLayer = L.tileLayer('https://{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', {
      maxZoom: 20,
      subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
      attribution: '&copy; Google Maps'
    });

    // Satellite Layer: Google Maps Satellite + Labels
    this.googleSatelliteLayer = L.tileLayer('https://{s}.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', {
      maxZoom: 20,
      subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
      attribution: '&copy; Google Maps Satellite'
    });

    // Fallback OpenStreetMap if Google tiles are blocked or slow
    this.osmFallbackLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap'
    });

    this.currentMapTileType = 'roads';
    this.googleRoadsLayer.addTo(this.googleSportsMap);

    let googleTileErrorHandled = false;
    this.googleRoadsLayer.on('tileerror', () => {
      if (!googleTileErrorHandled && this.googleSportsMap) {
        googleTileErrorHandled = true;
        this.googleSportsMap.removeLayer(this.googleRoadsLayer);
        this.osmFallbackLayer.addTo(this.googleSportsMap);
        console.log("Switched to OSM fallback layer");
      }
    });

    // Marker Layer Group
    this.sportsMarkerGroup = L.layerGroup().addTo(this.googleSportsMap);

    // Current selected sport filter
    this.currentMapSportFilter = 'all';

    // Render Markers
    this.renderGoogleSportsMarkers();

    // Map Click Closes preview
    this.googleSportsMap.on('click', () => {
      this.hideFacilityPreviewCard();
    });

    setTimeout(() => {
      if (this.googleSportsMap) this.googleSportsMap.invalidateSize();
    }, 300);
  }

  toggleMapTileLayer() {
    if (!this.googleSportsMap) return;

    if (this.currentMapTileType === 'roads') {
      this.googleSportsMap.removeLayer(this.googleRoadsLayer);
      if (this.googleSportsMap.hasLayer(this.osmFallbackLayer)) {
        this.googleSportsMap.removeLayer(this.osmFallbackLayer);
      }
      this.googleSatelliteLayer.addTo(this.googleSportsMap);
      this.currentMapTileType = 'satellite';
      this.showToast("🛰️ Đã chuyển sang chế độ Bản đồ Vệ Tinh Google!");
    } else {
      this.googleSportsMap.removeLayer(this.googleSatelliteLayer);
      this.googleRoadsLayer.addTo(this.googleSportsMap);
      this.currentMapTileType = 'roads';
      this.showToast("🗺️ Đã chuyển sang chế độ Bản đồ Đường phố Google!");
    }
  }

  locateUserGPS() {
    if (!this.googleSportsMap) return;

    if (navigator.geolocation) {
      this.showToast("📡 Đang định vị GPS của bạn...");
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const lat = pos.coords.latitude;
          const lng = pos.coords.longitude;
          this.googleSportsMap.setView([lat, lng], 14, { animate: true });

          if (this.userGpsMarker) {
            this.googleSportsMap.removeLayer(this.userGpsMarker);
          }

          const userIcon = L.divIcon({
            className: 'user-gps-marker',
            html: '<div style="width: 20px; height: 20px; border-radius: 50%; background: #0284c7; border: 3px solid #ffffff; box-shadow: 0 0 0 6px rgba(2,132,199,0.3); animation: mapPinPulse 1.5s infinite;"></div>',
            iconSize: [20, 20],
            iconAnchor: [10, 10]
          });

          this.userGpsMarker = L.marker([lat, lng], { icon: userIcon }).addTo(this.googleSportsMap);
          this.userGpsMarker.bindPopup("📍 <strong>Vị trí của bạn</strong>").openPopup();
          this.showToast("🎯 Đã định vị thành công vị trí của bạn!");
        },
        (err) => {
          console.warn("GPS error:", err);
          // Fallback to central Hanoi
          this.googleSportsMap.setView([21.0285, 105.8150], 13, { animate: true });
          this.showToast("📍 Vị trí trung tâm: Ba Đình, Hà Nội");
        }
      );
    } else {
      this.googleSportsMap.setView([21.0285, 105.8150], 13, { animate: true });
      this.showToast("📍 Vị trí trung tâm: Ba Đình, Hà Nội");
    }
  }

  renderGoogleSportsMarkers() {
    if (!this.googleSportsMap || !this.sportsMarkerGroup) return;

    this.sportsMarkerGroup.clearLayers();

    const facilities = MockData.facilities.filter(f => f.is_approved !== false);
    const filter = this.currentMapBadmintonFilter || 'all';

    let visibleCount = 0;
    const drawerListContainer = document.getElementById('map-drawer-facilities-list');
    let drawerHtml = '';

    facilities.forEach(fac => {
      // Filter exclusively by badminton attributes
      if (filter === 'standard') {
        const hasYonex = (fac.badges && fac.badges.some(b => b.toLowerCase().includes('yonex'))) || fac.name.toLowerCase().includes('yonex');
        if (!hasYonex) return;
      } else if (filter === 'vip') {
        const hasVip = (fac.badges && fac.badges.some(b => b.toLowerCase().includes('enlio') || b.toLowerCase().includes('vip'))) || fac.name.toLowerCase().includes('vip');
        if (!hasVip) return;
      } else if (filter === 'ac') {
        const hasAC = (fac.badges && fac.badges.some(b => b.toLowerCase().includes('máy lạnh') || b.toLowerCase().includes('ac'))) || fac.name.toLowerCase().includes('arena') || fac.name.toLowerCase().includes('hub');
        if (!hasAC) return;
      } else if (filter === 'near') {
        const distNum = parseFloat(fac.distance) || 5.0;
        if (distNum > 5.0) return;
      }

      visibleCount++;

      // Pure Badminton Pin Icon
      const pinHtml = `
        <div class="sports-map-marker badminton" title="${fac.name}">
          <span class="sports-map-marker-icon">🏸</span>
        </div>
      `;

      const customIcon = L.divIcon({
        className: 'custom-sports-pin',
        html: pinHtml,
        iconSize: [34, 34],
        iconAnchor: [17, 34],
        popupAnchor: [0, -34]
      });

      const marker = L.marker([fac.latitude, fac.longitude], { icon: customIcon });

      // Click Marker opens preview card & popup
      marker.on('click', (e) => {
        L.DomEvent.stopPropagation(e);
        this.showFacilityPreviewCard(fac);
        this.googleSportsMap.panTo([fac.latitude, fac.longitude], { animate: true });
      });

      this.sportsMarkerGroup.addLayer(marker);

      // Add to drawer list
      drawerHtml += `
        <div class="drawer-facility-card" onclick="app.panToFacilityOnMap(${fac.id})">
          <img src="${fac.img}" alt="${fac.name}" style="width: 70px; height: 70px; object-fit: cover; border-radius: 8px; flex-shrink: 0;" onerror="this.src='images/court1.jpg'">
          <div style="flex: 1; min-width: 0;">
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 4px;">
              <strong style="font-size: 0.88rem; color: #0f172a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${fac.name}</strong>
            </div>
            <p style="font-size: 0.75rem; color: #64748b; margin: 2px 0 4px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">${fac.address}</p>
            <div style="display: flex; align-items: center; justify-content: space-between; font-size: 0.75rem;">
              <span style="color: #16a34a; font-weight: 700;">📍 ${fac.distance || 'Gần bạn'}</span>
              <span style="color: #f59e0b; font-weight: 700;">⭐ ${fac.rating} (🏸 Cầu lông)</span>
            </div>
          </div>
        </div>
      `;
    });

    const countEl = document.getElementById('map-drawer-count');
    if (countEl) countEl.textContent = visibleCount;

    if (drawerListContainer) {
      drawerListContainer.innerHTML = drawerHtml || '<p style="text-align: center; color: #64748b; padding: 2rem;">Không tìm thấy sân cầu lông phù hợp bộ lọc.</p>';
    }
  }

  filterMapBadminton(category, btn) {
    this.currentMapBadmintonFilter = category;

    document.querySelectorAll('.sport-chip').forEach(c => c.classList.remove('active'));
    if (btn) btn.classList.add('active');

    this.renderGoogleSportsMarkers();
    const labelMap = {
      'all': 'Tất cả sân cầu lông',
      'standard': 'Thảm Yonex Pro',
      'vip': 'Thảm Enlio VIP',
      'ac': 'Sân có điều hòa máy lạnh',
      'near': 'Sân gần tôi (< 5km)'
    };
    this.showToast(`🏸 Bộ lọc: ${labelMap[category] || category}`);
  }

  filterMapSport(sportType, btn) {
    this.filterMapBadminton(sportType, btn);
  }

  async handleMapSearch(e) {
    const rawVal = e && e.target ? e.target.value : '';
    const keyword = rawVal.toLowerCase().trim();
    if (!keyword) {
      this.currentMapSportFilter = 'all';
      this.renderGoogleSportsMarkers();
      return;
    }

    if (this.googleSportsMap && this.sportsMarkerGroup) {
      this.sportsMarkerGroup.clearLayers();
      const facilities = MockData.facilities.filter(f => 
        (f.name && f.name.toLowerCase().includes(keyword)) || 
        (f.address && f.address.toLowerCase().includes(keyword))
      );

      facilities.forEach(fac => {
        const pinHtml = `
          <div class="sports-map-marker ${fac.sport_type || 'badminton'}" title="${fac.name}">
            <span class="sports-map-marker-icon">${fac.sport_icon || '🏸'}</span>
          </div>
        `;

        const customIcon = L.divIcon({
          className: 'custom-sports-pin',
          html: pinHtml,
          iconSize: [32, 32],
          iconAnchor: [16, 32]
        });

        const marker = L.marker([fac.latitude, fac.longitude], { icon: customIcon });
        marker.on('click', () => {
          this.showFacilityPreviewCard(fac);
          this.googleSportsMap.panTo([fac.latitude, fac.longitude]);
        });
        this.sportsMarkerGroup.addLayer(marker);
      });

      if (facilities.length > 0) {
        this.googleSportsMap.panTo([facilities[0].latitude, facilities[0].longitude], { animate: true });
        this.showFacilityPreviewCard(facilities[0]);
      } else {
        // If no direct facility match, try geocoding the address/area
        const geoResult = await this.geocodeAddress(rawVal);
        if (geoResult && this.googleSportsMap) {
          this.googleSportsMap.setView([geoResult.lat, geoResult.lng], 14, { animate: true });
          this.showToast(`📍 Đã chuyển bản đồ đến khu vực: ${geoResult.displayName}!`);
        }
      }
    }
  }

  async executeMapSearch() {
    const input = document.getElementById('map-explore-search-input');
    if (input) {
      await this.handleMapSearch({ target: input });
    }
  }

  showFacilityPreviewCard(fac) {
    const card = document.getElementById('map-facility-preview-card');
    if (!card) return;

    card.innerHTML = `
      <div style="display: flex; gap: 12px; align-items: center;">
        <img src="${fac.img}" alt="${fac.name}" style="width: 80px; height: 80px; border-radius: 10px; object-fit: cover; border: 1.5px solid #e2e8f0; flex-shrink: 0;" onerror="this.src='images/court1.jpg'">
        <div style="flex: 1; min-width: 0;">
          <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <h4 style="margin: 0 0 4px; font-size: 0.95rem; font-weight: 800; color: #0f172a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${fac.name}</h4>
            <button onclick="app.hideFacilityPreviewCard()" style="background: none; border: none; font-size: 1rem; color: #94a3b8; cursor: pointer; padding: 0 0 0 8px;">&times;</button>
          </div>
          <p style="font-size: 0.75rem; color: #64748b; margin: 0 0 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
            <i class="fa-solid fa-location-dot" style="color: #167946;"></i> ${fac.address}
          </p>
          <div style="display: flex; align-items: center; justify-content: space-between;">
            <span style="font-size: 0.8rem; font-weight: 700; color: #167946;">
              <i class="fa-solid fa-clock"></i> ${fac.open_hours || '05:00 - 23:30'}
            </span>
            <div style="display: flex; gap: 6px;">
              <button class="btn btn-secondary btn-sm" style="padding: 4px 10px; font-size: 0.75rem;" onclick="app.openExternalGoogleMaps(${fac.latitude}, ${fac.longitude})">
                <i class="fa-solid fa-diamond-turn-right"></i> Chỉ Đường
              </button>
              <button class="btn btn-primary btn-sm" style="padding: 4px 12px; font-size: 0.75rem;" onclick="app.selectFacilityForBooking(${fac.id})">
                <i class="fa-solid fa-calendar-check"></i> Đặt Sân
              </button>
            </div>
          </div>
        </div>
      </div>
    `;
    card.style.display = 'block';
  }

  hideFacilityPreviewCard() {
    const card = document.getElementById('map-facility-preview-card');
    if (card) card.style.display = 'none';
  }

  toggleMapFacilitiesSidebar() {
    const drawer = document.getElementById('map-facilities-drawer');
    if (drawer) {
      drawer.classList.toggle('open');
    }
  }

  panToFacilityOnMap(facId) {
    const fac = MockData.facilities.find(f => f.id === facId);
    if (!fac || !this.googleSportsMap) return;

    this.googleSportsMap.setView([fac.latitude, fac.longitude], 15, { animate: true });
    this.showFacilityPreviewCard(fac);

    const drawer = document.getElementById('map-facilities-drawer');
    if (drawer) drawer.classList.remove('open');
  }

  openExternalGoogleMaps(lat, lng) {
    window.open(`https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`, '_blank');
  }


  toggleAIDynamicPricing() {
    this.isAIDynamicPriceActive = !this.isAIDynamicPriceActive;
    const btn = document.getElementById('btn-toggle-ai-price');
    if (this.isAIDynamicPriceActive) {
      btn.className = "btn btn-accent btn-sm";
      btn.innerHTML = `<i class="fa-solid fa-toggle-on"></i> Đang Bật AI Price`;
      this.showToast("Đã bật AI Dynamic Pricing Engine!");
    } else {
      btn.className = "btn btn-secondary btn-sm";
      btn.innerHTML = `<i class="fa-solid fa-toggle-off"></i> Giá Cố Định Thủ Công`;
      this.showToast("Đã chuyển về đặt giá thủ công.");
    }
    this.renderSlotMatrix();
  }

  renderOwnerEquipments() {
    const tbody = document.getElementById('owner-equipments-table-body');
    let html = '';

    MockData.equipments.forEach(eq => {
      html += `
        <tr>
          <td><strong>${eq.name}</strong></td>
          <td>${eq.price.toLocaleString('vi-VN')}đ</td>
          <td><strong style="color: var(--primary);">${eq.quantity}</strong> ${eq.unit}</td>
          <td>${eq.unit}</td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick="app.showToast('Cập nhật kho ${eq.name}')"><i class="fa-solid fa-boxes-packing"></i> Nhập Kho</button>
          </td>
        </tr>
      `;
    });

    if (tbody) tbody.innerHTML = html;
  }

  renderOwnerStaff() {
    const tbody = document.getElementById('owner-staff-table-body');
    if (!tbody) return;
    let html = '';

    const staffMembers = MockData.users.filter(u => u.role === 'STAFF' || u.role === 'STAFF_LEADER');
    if (staffMembers.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">Chưa có nhân viên nào. Bấm nút "Thêm Nhân Viên Ca Trực" để khởi tạo tài khoản!</td></tr>`;
      return;
    }

    staffMembers.forEach(staff => {
      const fac = MockData.facilities.find(f => f.id === staff.facility_id) || MockData.facilities[0];
      const facName = fac ? fac.name : 'Chưa phân công';
      const isApproved = staff.is_approved !== false;
      const statusBadge = isApproved 
        ? '<span class="tag-badge tag-ai"><i class="fa-solid fa-circle-check"></i> ĐÃ DUYỆT</span>'
        : '<span class="tag-badge" style="background: rgba(239,68,68,0.2); color: #ef4444; border: 1px solid rgba(239,68,68,0.3);"><i class="fa-solid fa-clock"></i> CHỜ CHỦ SÂN DUYỆT</span>';

      const approveActionBtn = isApproved 
        ? '' 
        : `<button class="btn btn-primary btn-sm" onclick="app.approveUserAccount(${staff.id})" title="Phê Duyệt Quyền Thu Ngân"><i class="fa-solid fa-user-check"></i> Phê Duyệt</button>`;

      html += `
        <tr>
          <td>#${staff.id}</td>
          <td>
            <div style="display: flex; align-items: center; gap: 0.5rem;">
              <div class="user-avatar-sm" style="width: 32px; height: 32px; border-radius: 50%; background: var(--primary); color: #fff; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 0.85rem;">${staff.avatar || staff.name.charAt(0)}</div>
              <div>
                <strong>${staff.name}</strong>
                <div style="font-size: 0.75rem; color: var(--text-muted);">Thu Ngân Quầy POS</div>
              </div>
            </div>
          </td>
          <td>${staff.phone}</td>
          <td><i class="fa-solid fa-store text-primary" style="margin-right: 4px;"></i> ${facName}</td>
          <td>${statusBadge}</td>
          <td>
            <div style="display: flex; gap: 0.35rem; flex-wrap: wrap;">
              ${approveActionBtn}
              <button class="btn btn-secondary btn-sm" onclick="app.editStaffShift(${staff.id})" title="Chỉnh Sửa Ca Trực & Thông Tin"><i class="fa-solid fa-user-pen"></i></button>
              <button class="btn btn-secondary btn-sm text-danger" onclick="app.deleteStaff(${staff.id})" title="Xóa Tài Khoản Nhân Viên"><i class="fa-solid fa-trash" style="color: #ef4444;"></i></button>
            </div>
          </td>
        </tr>
      `;
    });

    tbody.innerHTML = html;
  }

  openAddStaffModal() {
    const modalBody = document.getElementById('modal-body');
    if (!modalBody) return;

    let facilityOptions = MockData.facilities.map(f => `<option value="${f.id}">${f.name}</option>`).join('');

    modalBody.innerHTML = `
      <h3>👤 Thêm Nhân Viên Ca Trực & Phân Công Quầy POS</h3>
      <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px;">Khởi tạo tài khoản nhân viên thu ngân / quản lý ca trực quầy sân</p>
      
      <form onsubmit="app.saveNewStaff(event)" style="margin-top: 1rem; display: flex; flex-direction: column; gap: 0.75rem;">
        <div class="form-group">
          <label class="form-label">Họ và Tên Nhân Viên</label>
          <input type="text" id="add-staff-name" class="form-control" placeholder="VD: Nguyễn Văn An" required>
        </div>
        <div class="form-group">
          <label class="form-label">Số Điện Thoại Đăng Nhập</label>
          <input type="tel" id="add-staff-phone" class="form-control" placeholder="VD: 0988123456" pattern="[0-9]{10}" title="Nhập số điện thoại 10 chữ số" required>
        </div>
        <div class="form-group">
          <label class="form-label">Phân Công Cơ Sở Làm Việc</label>
          <select id="add-staff-facility" class="form-control" required>
            ${facilityOptions}
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Quyền Truy Cập / Vai Trò</label>
          <select id="add-staff-role" class="form-control" required>
            <option value="STAFF">ROLE_STAFF (Nhân Viên Thu Ngân Quầy POS)</option>
            <option value="STAFF_LEADER">ROLE_STAFF_LEADER (Trưởng Ca Quản Lý Cụm Sân)</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Mật Khẩu Đăng Nhập Ban Đầu</label>
          <input type="password" id="add-staff-password" class="form-control" value="123456" required>
        </div>

        <div style="margin-top: 1rem; display: flex; gap: 0.5rem; justify-content: flex-end;">
          <button type="button" class="btn btn-secondary btn-sm" onclick="app.closeModal()">Hủy</button>
          <button type="submit" class="btn btn-primary btn-sm">
            <i class="fa-solid fa-user-check"></i> Lưu & Phân Công Nhân Viên
          </button>
        </div>
      </form>
    `;

    this.openModal();
  }

  openAddOwnerModal() {
    if (this.currentRole !== 'ADMIN') {
      this.showToast('⛔ Chỉ Quản trị viên (ADMIN) mới có quyền tạo tài khoản Chủ Sân!', 'error');
      return;
    }

    const modalBody = document.getElementById('modal-body');
    if (!modalBody) return;

    modalBody.innerHTML = `
      <h3>🏢 ADMIN: Khởi Tạo Tài Khoản Chủ Sân Mới</h3>
      <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px;">Tạo tài khoản Chủ Sân phân cấp theo mô hình quản lý 4 tầng</p>
      
      <form onsubmit="app.saveNewOwner(event)" style="margin-top: 1rem; display: flex; flex-direction: column; gap: 0.75rem;">
        <div class="form-group">
          <label class="form-label"><i class="fa-solid fa-signature text-primary"></i> Họ và Tên Chủ Sân</label>
          <input type="text" id="add-owner-name" class="form-control" placeholder="VD: Lê Hoàng Nam" required>
        </div>
        <div class="form-group">
          <label class="form-label"><i class="fa-solid fa-phone text-primary"></i> Số Điện Thoại Đăng Nhập</label>
          <input type="tel" id="add-owner-phone" class="form-control" placeholder="VD: 0912345678" pattern="[0-9]{10}" title="Nhập số điện thoại 10 chữ số" required>
        </div>
        <div class="form-group">
          <label class="form-label"><i class="fa-solid fa-building text-primary"></i> Tên Cụm Sân Quản Lý</label>
          <input type="text" id="add-owner-facility-name" class="form-control" placeholder="VD: Sân Cầu Lông Cầu Giấy Sport" required>
        </div>
        <div class="form-group">
          <label class="form-label"><i class="fa-solid fa-location-dot text-primary"></i> Địa Chỉ Cụm Sân</label>
          <input type="text" id="add-owner-facility-address" class="form-control" value="102 Đường Cầu Giấy, Quận Cầu Giấy, Hà Nội" required>
        </div>
        <div class="form-group">
          <label class="form-label"><i class="fa-solid fa-lock text-primary"></i> Mật Khẩu Đăng Nhập Ban Đầu</label>
          <input type="password" id="add-owner-password" class="form-control" value="123456" required>
        </div>

        <div style="margin-top: 1rem; display: flex; gap: 0.5rem; justify-content: flex-end;">
          <button type="button" class="btn btn-secondary btn-sm" onclick="app.closeModal()">Hủy</button>
          <button type="submit" class="btn btn-primary btn-sm">
            <i class="fa-solid fa-building-circle-check"></i> Lưu & Khởi Tạo Tài Khoản Chủ Sân
          </button>
        </div>
      </form>
    `;

    this.openModal();
  }

  saveNewOwner(e) {
    if (e) e.preventDefault();
    const nameInput = document.getElementById('add-owner-name');
    const phoneInput = document.getElementById('add-owner-phone');
    const facNameInput = document.getElementById('add-owner-facility-name');
    const facAddrInput = document.getElementById('add-owner-facility-address');
    const passInput = document.getElementById('add-owner-password');

    if (!nameInput || !phoneInput || !facNameInput) return;

    const name = nameInput.value.trim();
    const phone = phoneInput.value.trim();
    const facName = facNameInput.value.trim();
    const facAddr = facAddrInput ? facAddrInput.value.trim() : 'Hà Nội';
    const password = passInput && passInput.value.trim() ? passInput.value.trim() : '123456';

    const newFacId = MockData.facilities.length > 0 ? Math.max(...MockData.facilities.map(f => f.id)) + 1 : 101;
    const newFacility = {
      id: newFacId,
      name: facName,
      address: facAddr,
      latitude: 21.0285,
      longitude: 105.8542,
      open_time: "06:00",
      close_time: "23:00",
      is_approved: true,
      rating: 5.0,
      reviews_count: 1,
      img: "images/court1.jpg",
      courts_count: 6
    };
    MockData.facilities.push(newFacility);

    const newUserId = MockData.users.length > 0 ? Math.max(...MockData.users.map(u => u.id)) + 1 : 1;
    const avatar = name.split(' ').pop().charAt(0).toUpperCase() || 'O';
    const newOwner = {
      id: newUserId,
      name: name + " (Chủ Sân)",
      phone: phone,
      password: password,
      role: 'OWNER',
      facility_id: newFacId,
      elo_rating: 'N/A',
      avatar: avatar,
      is_approved: true,
      created_at: new Date().toLocaleDateString('vi-VN')
    };

    MockData.users.push(newOwner);
    if (typeof saveMockDataToLocalStorage === 'function') saveMockDataToLocalStorage();

    this.closeModal();
    this.renderAdminUsers();
    if (typeof this.renderAdminOverviewFacilities === 'function') {
      this.renderAdminOverviewFacilities();
    }
    if (this.currentView === 'ui-20') this.renderDatabaseInspector();
    this.showToast(`🎉 ADMIN đã tạo thành công tài khoản Chủ Sân: ${name} (Mật khẩu: ${password})!`);
  }

  saveNewStaff(e) {
    if (e) e.preventDefault();
    const nameInput = document.getElementById('add-staff-name');
    const phoneInput = document.getElementById('add-staff-phone');
    const facInput = document.getElementById('add-staff-facility');
    const roleInput = document.getElementById('add-staff-role');
    const passInput = document.getElementById('add-staff-password');

    if (!nameInput || !phoneInput) return;

    const name = nameInput.value.trim();
    const phone = phoneInput.value.trim();
    const facility_id = parseInt(facInput ? facInput.value : 101);
    const role = roleInput ? roleInput.value : 'STAFF';
    const password = passInput && passInput.value.trim() ? passInput.value.trim() : '123456';

    const newId = MockData.users.length > 0 ? Math.max(...MockData.users.map(u => u.id)) + 1 : 1;
    const avatar = name.split(' ').pop().charAt(0).toUpperCase() || 'S';

    const newStaff = {
      id: newId,
      name: name + " (Thu Ngân)",
      phone: phone,
      password: password,
      role: role,
      facility_id: facility_id,
      elo_rating: 'N/A',
      avatar: avatar,
      is_approved: true,
      created_at: new Date().toLocaleDateString('vi-VN')
    };

    MockData.users.push(newStaff);
    if (typeof saveMockDataToLocalStorage === 'function') saveMockDataToLocalStorage();

    this.closeModal();
    this.renderOwnerStaff();
    if (this.currentView === 'ui-20') this.renderDatabaseInspector();
    this.showToast(`🎉 CHỦ SÂN đã tạo thành công tài khoản Thu Ngân: ${name} (Mật khẩu: ${password})!`);
  }

  deleteStaff(staffId) {
    const staffIndex = MockData.users.findIndex(u => u.id === staffId);
    if (staffIndex !== -1) {
      const staffName = MockData.users[staffIndex].name;
      if (confirm(`Bạn có chắc chắn muốn xóa tài khoản nhân viên "${staffName}" không?`)) {
        MockData.users.splice(staffIndex, 1);
        if (typeof saveMockDataToLocalStorage === 'function') saveMockDataToLocalStorage();
        this.renderOwnerStaff();
        this.showToast(`🗑️ Đã xóa nhân viên ${staffName} khỏi hệ thống!`);
      }
    }
  }

  editStaffShift(staffId) {
    const staff = MockData.users.find(u => u.id === staffId);
    if (!staff) return;

    const modalBody = document.getElementById('modal-body');
    if (!modalBody) return;

    let facilityOptions = MockData.facilities.map(f => 
      `<option value="${f.id}" ${f.id === staff.facility_id ? 'selected' : ''}>${f.name}</option>`
    ).join('');

    modalBody.innerHTML = `
      <h3>✏️ Chỉnh Sửa Thông Tin & Phân Ca Nhân Viên #${staff.id}</h3>
      
      <form onsubmit="app.updateStaff(event, ${staff.id})" style="margin-top: 1rem; display: flex; flex-direction: column; gap: 0.75rem;">
        <div class="form-group">
          <label class="form-label">Họ và Tên Nhân Viên</label>
          <input type="text" id="edit-staff-name" class="form-control" value="${staff.name}" required>
        </div>
        <div class="form-group">
          <label class="form-label">Số Điện Thoại</label>
          <input type="tel" id="edit-staff-phone" class="form-control" value="${staff.phone}" required>
        </div>
        <div class="form-group">
          <label class="form-label">Phân Công Cơ Sở Làm Việc</label>
          <select id="edit-staff-facility" class="form-control" required>
            ${facilityOptions}
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Quyền Truy Cập / Vai Trò</label>
          <select id="edit-staff-role" class="form-control" required>
            <option value="STAFF" ${staff.role === 'STAFF' ? 'selected' : ''}>ROLE_STAFF (Nhân Viên Thu Ngân Quầy POS)</option>
            <option value="STAFF_LEADER" ${staff.role === 'STAFF_LEADER' ? 'selected' : ''}>ROLE_STAFF_LEADER (Trưởng Ca Quản Lý Cụm Sân)</option>
          </select>
        </div>

        <div style="margin-top: 1rem; display: flex; gap: 0.5rem; justify-content: flex-end;">
          <button type="button" class="btn btn-secondary btn-sm" onclick="app.closeModal()">Hủy</button>
          <button type="submit" class="btn btn-primary btn-sm">
            <i class="fa-solid fa-floppy-disk"></i> Cập Nhật Thông Tin
          </button>
        </div>
      </form>
    `;

    this.openModal();
  }

  updateStaff(e, staffId) {
    if (e) e.preventDefault();
    const staff = MockData.users.find(u => u.id === staffId);
    if (!staff) return;

    const nameInput = document.getElementById('edit-staff-name');
    const phoneInput = document.getElementById('edit-staff-phone');
    const facInput = document.getElementById('edit-staff-facility');
    const roleInput = document.getElementById('edit-staff-role');

    if (nameInput) staff.name = nameInput.value.trim();
    if (phoneInput) staff.phone = phoneInput.value.trim();
    if (facInput) staff.facility_id = parseInt(facInput.value);
    if (roleInput) staff.role = roleInput.value;

    this.closeModal();
    this.renderOwnerStaff();
    this.showToast(`✅ Đã cập nhật thông tin nhân viên ${staff.name}!`);
  }

  renderHeatmap() {
    const tbody = document.getElementById('occupancy-heatmap-body');
    let html = '';

    MockData.occupancy_heatmap.forEach(row => {
      html += `
        <tr>
          <td><strong>${row.hour}</strong></td>
          <td><strong class="heat-cell heat-${row.status}" style="padding: 4px 12px;">${row.rate}%</strong></td>
          <td>${row.rate > 80 ? '🔥 Giờ Cao Điểm' : '🍃 Khung Giờ Thường'}</td>
        </tr>
      `;
    });

    if (tbody) tbody.innerHTML = html;
  }

  exportExcelReport() {
    this.showToast("Đã xuất báo cáo doanh thu & tải lấp đầy sân dạng Excel thành công!");
  }

  /* ------------------------------------------------------------------------
     8. STAFF POS PORTAL (UI 15 & UI 16)
     ------------------------------------------------------------------------ */
  searchPOSBooking(inputQuery = null) {
    const scanInput = document.getElementById('pos-scan-input');
    const code = inputQuery !== null ? inputQuery : (scanInput ? scanInput.value.trim() : '');
    if (scanInput && inputQuery !== null) {
      scanInput.value = inputQuery;
    }

    const container = document.getElementById('pos-booking-result-container');
    if (!code) {
      this.showToast("Vui lòng nhập mã QR Ticket hoặc số điện thoại khách!", 'error');
      return;
    }

    const qLower = code.toLowerCase();
    const order = MockData.booking_orders.find(o => 
      o.qr_ticket_code.toLowerCase() === qLower || 
      o.booking_code.toLowerCase() === qLower || 
      o.user_phone.includes(code)
    );

    if (!container) return;

    if (!order) {
      this.showToast(`⚠️ Không tìm thấy đơn đặt sân cho mã "${code}"!`, 'error');
      container.innerHTML = `
        <div class="glass-card" style="border-color: var(--accent-rose); text-align: center; padding: 1.5rem;">
          <i class="fa-solid fa-triangle-exclamation text-danger" style="font-size: 2rem; margin-bottom: 0.5rem; color: var(--accent-rose);"></i>
          <h4 style="color: var(--accent-rose);">Không Tìm Thấy Đơn Hàng Hoặc Mã QR Ticket</h4>
          <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px;">Mã <code>${code}</code> không có trong danh sách đơn. Hãy thử các nút gợi ý mã vé mẫu ở trên!</p>
        </div>
      `;
      return;
    }

    const isCheckedIn = order.order_status.includes('Check-in') || order.order_status === 'ĐÃ CHECK-IN (ĐANG CHƠI SÂN)';
    const remainingDue = Math.max(0, order.total_amount - order.deposit_amount);

    container.innerHTML = `
      <div class="glass-card" style="border-color: var(--primary); background: rgba(16,185,129,0.05); animation: fadeIn 0.3s ease-in-out;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
          <div>
            <h3 style="color: var(--primary);"><i class="fa-solid fa-circle-check"></i> Đơn Hàng: ${order.booking_code}</h3>
            <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 2px;">Mã QR Vé: <code style="color: var(--accent-cyan); font-weight: bold; font-size: 0.95rem;">${order.qr_ticket_code}</code></div>
          </div>
          <span class="tag-badge ${isCheckedIn ? 'tag-ai' : 'tag-pos'}" style="font-size: 0.85rem; padding: 6px 14px;">
            <i class="fa-solid ${isCheckedIn ? 'fa-square-check' : 'fa-clock'}"></i> ${order.order_status}
          </span>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-top: 1rem; padding: 1rem; background: rgba(0,0,0,0.3); border-radius: 8px; border: 1px solid var(--border-color);">
          <div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">Thông Tin Khách Hàng</div>
            <strong style="font-size: 1.05rem;">${order.user_name}</strong>
            <div style="font-size: 0.85rem; color: var(--primary); font-weight: bold; margin-top: 2px;"><i class="fa-solid fa-phone"></i> ${order.user_phone}</div>
          </div>
          <div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">Cụm Sân & Khung Giờ</div>
            <strong style="color: var(--accent-cyan);">${order.facility_name}</strong>
            <div style="font-size: 0.85rem;">${order.court_name}</div>
            <div style="font-size: 0.85rem; color: var(--primary); font-weight: 600;">Slot: ${order.slot_time} (${order.booking_date})</div>
          </div>
          <div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">Thanh Toán</div>
            <div>Tổng tiền: <strong>${order.total_amount.toLocaleString('vi-VN')}đ</strong></div>
            <div style="font-size: 0.85rem; color: var(--primary);">Đã nộp cọc: <strong>${order.deposit_amount.toLocaleString('vi-VN')}đ</strong></div>
            <div style="font-size: 0.9rem; color: #f59e0b; font-weight: bold; margin-top: 2px;">Còn nợ tại quầy: ${remainingDue.toLocaleString('vi-VN')}đ</div>
          </div>
        </div>

        <div style="margin-top: 1.25rem; display: flex; gap: 0.75rem; flex-wrap: wrap;">
          <button class="btn btn-primary" onclick="app.confirmPOSCheckin('${order.booking_code}')" ${isCheckedIn ? 'disabled style="opacity: 0.65; cursor: not-allowed;"' : ''}>
            <i class="fa-solid fa-circle-check"></i> ${isCheckedIn ? 'Đã Check-in Vào Sân' : 'Xác Nhận Check-in Cho Khách Vào Sân'}
          </button>
          <button class="btn btn-secondary" onclick="app.preparePOSCheckout('${order.booking_code}')">
            <i class="fa-solid fa-file-invoice-dollar text-primary"></i> Chuyển Sang Lập Hóa Đơn Check-out
          </button>
        </div>
      </div>
    `;

    this.showToast(`🎯 Đã tìm thấy đơn hàng của khách ${order.user_name}!`);
  }

  confirmPOSCheckin(bookingCode) {
    const order = MockData.booking_orders.find(o => o.booking_code === bookingCode);
    if (order) {
      order.order_status = "ĐÃ CHECK-IN (ĐANG CHƠI SÂN)";
      order.deposit_status = "Đã Check-in";
      this.searchPOSBooking(order.qr_ticket_code);
      this.renderPOSTodayBookingsTable();
      this.showToast(`🎉 Xác nhận Check-in thành công cho khách ${order.user_name}! Sân đã chuyển trạng thái ĐANG CHƠI SÂN.`);
    }
  }

  simulateCameraQRScan() {
    const pendingOrder = MockData.booking_orders.find(o => !o.order_status.includes('Check-in') && o.order_status !== 'ĐÃ CHECK-IN (ĐANG CHƠI SÂN)') || MockData.booking_orders[0];
    const targetTicketCode = pendingOrder ? pendingOrder.qr_ticket_code : "TICKET-ALB-108291";

    const modalBody = document.getElementById('modal-body');
    if (!modalBody) return;

    modalBody.innerHTML = `
      <div style="text-align: center;">
        <h3>📷 Quét Mã QR Vé Bằng Camera Quầy POS</h3>
        <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px;">Đưa mã QR trên ứng dụng điện thoại của khách hàng trước Camera</p>
        
        <div style="position: relative; width: 100%; max-width: 380px; height: 260px; margin: 1rem auto; background: #000; border-radius: 12px; overflow: hidden; border: 2px solid var(--primary); display: flex; align-items: center; justify-content: center;">
          <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(180deg, rgba(16,185,129,0.15) 0%, rgba(0,0,0,0.8) 100%);"></div>
          
          <!-- Animated Green Scanner Line -->
          <div style="position: absolute; width: 80%; height: 3px; background: var(--primary); box-shadow: 0 0 15px var(--primary); animation: qrScanLaser 1.5s infinite ease-in-out;"></div>
          
          <!-- QR Frame Overlay -->
          <div style="width: 180px; height: 180px; border: 2px dashed var(--primary); border-radius: 12px; z-index: 2; display: flex; align-items: center; justify-content: center;">
            <i class="fa-solid fa-qrcode text-primary" style="font-size: 4rem; opacity: 0.8; animation: pulse 1s infinite alternate;"></i>
          </div>
        </div>

        <div id="qr-scan-status-text" style="font-weight: bold; color: var(--accent-cyan);">🔍 Đang dò quét mã QR từ Camera quầy...</div>
        <div style="margin-top: 8px; font-size: 0.78rem; color: #64748b;">Mã vé đang quét: <code>${targetTicketCode}</code></div>
        <button class="btn btn-secondary btn-sm" style="margin-top: 1rem;" onclick="app.closeModal()">Đóng Camera</button>
      </div>
    `;

    this.openModal();

    setTimeout(() => {
      const statusEl = document.getElementById('qr-scan-status-text');
      if (statusEl) {
        statusEl.innerHTML = `<span style="color: var(--primary);">✅ Đã quét thành công mã QR: ${targetTicketCode}!</span>`;
      }
      setTimeout(() => {
        this.closeModal();
        this.searchPOSBooking(targetTicketCode);
      }, 700);
    }, 1300);
  }

  renderPOSTodayBookingsTable() {
    const tbody = document.getElementById('pos-today-bookings-tbody');
    if (!tbody) return;

    let html = '';
    MockData.booking_orders.forEach(order => {
      const isCheckedIn = order.order_status.includes('Check-in') || order.order_status === 'ĐÃ CHECK-IN (ĐANG CHƠI SÂN)';
      const due = Math.max(0, order.total_amount - order.deposit_amount);

      html += `
        <tr>
          <td><code style="color: var(--accent-cyan); font-weight: bold;">${order.qr_ticket_code}</code></td>
          <td>
            <strong>${order.user_name}</strong>
            <div style="font-size: 0.75rem; color: var(--text-muted);">${order.user_phone}</div>
          </td>
          <td>
            <div><strong>${order.facility_name}</strong></div>
            <div style="font-size: 0.75rem; color: var(--primary);">${order.court_name} (${order.slot_time})</div>
          </td>
          <td>
            <div>Đã cọc: <strong>${order.deposit_amount.toLocaleString('vi-VN')}đ</strong></div>
            <div style="font-size: 0.75rem; color: #f59e0b; font-weight: 600;">Còn nợ: ${due.toLocaleString('vi-VN')}đ</div>
          </td>
          <td>
            <span class="tag-badge ${isCheckedIn ? 'tag-ai' : 'tag-pos'}">${order.order_status}</span>
          </td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick="app.searchPOSBooking('${order.qr_ticket_code}')" title="Chọn Đơn Này">
              <i class="fa-solid fa-eye"></i> Kiểm Tra & Check-in
            </button>
          </td>
        </tr>
      `;
    });

    tbody.innerHTML = html;
  }

  preparePOSCheckout(bookingCode) {
    const order = MockData.booking_orders.find(o => o.booking_code === bookingCode) || MockData.booking_orders[0];
    this.activePOSOrder = order;
    this.navigateTo('ui-16');

    if (order) {
      const baseEl = document.getElementById('pos-calc-base');
      const depositEl = document.getElementById('pos-calc-deposit');
      const extraInput = document.getElementById('pos-extra-fee');
      const overtimeInput = document.getElementById('pos-overtime-mins');

      if (baseEl) baseEl.textContent = `${order.total_amount.toLocaleString('vi-VN')}đ`;
      if (depositEl) depositEl.textContent = `-${order.deposit_amount.toLocaleString('vi-VN')}đ`;
      if (extraInput) extraInput.value = 0;
      if (overtimeInput) overtimeInput.value = 0;

      this.calculatePOSFinalAmount();
      this.showToast(`🧾 Đã nạp thông tin đơn ${order.booking_code} của khách ${order.user_name} sang Lập Hóa Đơn Check-out!`);
    }
  }

  calculatePOSFinalAmount() {
    const order = this.activePOSOrder || MockData.booking_orders[0] || {
      booking_code: "BK-20261002-001",
      user_name: "Nguyễn Văn Hùng",
      slot_time: "17:30 - 18:30",
      total_amount: 120000,
      deposit_amount: 60000
    };

    const extraFeeInput = document.getElementById('pos-extra-fee');
    const overtimeMinsInput = document.getElementById('pos-overtime-mins');

    const extraFee = extraFeeInput ? (parseInt(extraFeeInput.value, 10) || 0) : 0;
    const overtimeMins = overtimeMinsInput ? (parseInt(overtimeMinsInput.value, 10) || 0) : 0;

    const overtimeBlocks = Math.ceil(overtimeMins / 15);
    const overtimeFee = overtimeBlocks * 25000;

    const extraEl = document.getElementById('pos-calc-extra');
    const overtimeEl = document.getElementById('pos-calc-overtime');
    const finalEl = document.getElementById('pos-calc-final');

    if (extraEl) extraEl.textContent = `${extraFee.toLocaleString('vi-VN')}đ`;
    if (overtimeEl) overtimeEl.textContent = `${overtimeFee.toLocaleString('vi-VN')}đ`;

    const finalAmount = Math.max(0, (order.total_amount + extraFee + overtimeFee) - order.deposit_amount);
    if (finalEl) finalEl.textContent = `${finalAmount.toLocaleString('vi-VN')}đ`;

    // Cập nhật real-time hóa đơn in xem trước
    const previewEl = document.getElementById('invoice-print-preview');
    if (previewEl) {
      const invCode = this.currentActiveInvoiceCode || `INV-${new Date().toISOString().slice(2, 10).replace(/-/g, '')}-${order.id ? String(order.id).slice(-3) : '001'}`;
      this.currentActiveInvoiceCode = invCode;

      previewEl.innerHTML = `
        <div class="invoice-header" style="text-align: center; margin-bottom: 12px; border-bottom: 1px dashed #000; padding-bottom: 8px;">
          <h3 style="margin: 0 0 2px; font-size: 1.1rem; text-transform: uppercase;">${order.facility_name || "BADMINTON.AI ARENA"}</h3>
          <div style="font-weight: 700; font-size: 0.9rem;">HÓA ĐƠN THANH TOÁN DỊCH VỤ POS</div>
          <div style="font-size: 0.75rem; color: #475569;">Mã HĐ: <strong>${invCode}</strong> | Mã Đơn: <strong>${order.booking_code}</strong></div>
        </div>
        <div class="invoice-line" style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 3px;"><span>Khách hàng:</span> <strong>${order.user_name} (${order.user_phone || "0901234567"})</strong></div>
        <div class="invoice-line" style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 3px;"><span>Sân & Khung giờ:</span> <span>${order.court_name || "Sân thi đấu"} (${order.slot_time})</span></div>
        <div class="invoice-line" style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 3px;"><span>Giờ vào sân:</span> <span>${order.created_at || "18:00:00"}</span></div>
        <div class="invoice-line" style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 3px;"><span>Giờ ra sân:</span> <span>${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span></div>
        <hr style="border: none; border-top: 1px dashed #000; margin: 0.5rem 0;">
        <div class="invoice-line" style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 3px;"><span>Tiền thuê sân:</span> <span>${order.total_amount.toLocaleString('vi-VN')}đ</span></div>
        <div class="invoice-line" style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 3px;"><span>Phụ phí dịch vụ:</span> <span>${extraFee.toLocaleString('vi-VN')}đ</span></div>
        <div class="invoice-line" style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 3px;"><span>Quá giờ (${overtimeMins}p):</span> <span>${overtimeFee.toLocaleString('vi-VN')}đ</span></div>
        <div class="invoice-line" style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 3px; color: #16a34a;"><span>Đã cọc trước (50%):</span> <span>-${order.deposit_amount.toLocaleString('vi-VN')}đ</span></div>
        <hr style="border: none; border-top: 1px dashed #000; margin: 0.5rem 0;">
        <div class="invoice-line" style="display: flex; justify-content: space-between; font-weight: 800; font-size: 1.05rem; margin-top: 4px;"><span>CẦN THANH TOÁN:</span> <span style="color: #dc2626;">${finalAmount.toLocaleString('vi-VN')}đ</span></div>
        <div style="text-align: center; margin-top: 1rem; font-size: 0.75rem; color: #475569;">
          <div>Thu ngân: <strong>${(this.currentUser && this.currentUser.name) ? this.currentUser.name : "Nhân viên trực quầy"}</strong></div>
          <div style="margin-top: 4px;">Cảm ơn quý khách & Hẹn gặp lại trên sân đấu! 🏸</div>
        </div>
      `;
    }
  }

  completePOSInvoice() {
    const order = this.activePOSOrder || MockData.booking_orders[0];
    if (!order) {
      this.showToast("Không tìm thấy đơn hàng cần thanh toán!", "error");
      return;
    }

    const extraFee = parseInt(document.getElementById('pos-extra-fee')?.value, 10) || 0;
    const overtimeMins = parseInt(document.getElementById('pos-overtime-mins')?.value, 10) || 0;
    const overtimeFee = Math.ceil(overtimeMins / 15) * 25000;
    const finalAmount = Math.max(0, (order.total_amount + extraFee + overtimeFee) - order.deposit_amount);

    const invCode = this.currentActiveInvoiceCode || `INV-${new Date().toISOString().slice(2, 10).replace(/-/g, '')}-${Math.floor(100 + Math.random() * 900)}`;

    const newInvoice = {
      id: Date.now(),
      invoice_code: invCode,
      booking_code: order.booking_code,
      customer_name: order.user_name,
      facility_name: order.facility_name,
      checkin_time: order.created_at || "18:00",
      checkout_time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      booking_fee: order.total_amount,
      deposit_deducted: order.deposit_amount,
      extra_fee: extraFee,
      overtime_fee: overtimeFee,
      final_amount: finalAmount,
      payment_method: "Tiền mặt / Chuyển khoản QR",
      staff_name: (this.currentUser && this.currentUser.name) ? this.currentUser.name : "Nhân viên trực quầy",
      created_at: new Date().toLocaleDateString('vi-VN') + " " + new Date().toLocaleTimeString('vi-VN')
    };

    if (!MockData.invoices) MockData.invoices = [];
    MockData.invoices.unshift(newInvoice);

    // Cập nhật trạng thái đơn hàng thành hoàn tất check-out
    order.order_status = "HOÀN TẤT & ĐÃ CHECK-OUT";
    order.deposit_status = "Đã Thanh Toán Xong";

    if (typeof saveMockDataToLocalStorage === 'function') {
      saveMockDataToLocalStorage();
    }

    this.renderPOSTodayBookingsTable();

    // Hiển thị modal in hóa đơn POS chuyên nghiệp
    const modalBody = document.getElementById('modal-body');
    if (modalBody) {
      modalBody.innerHTML = `
        <div style="padding: 0.5rem 0;">
          <div style="text-align: center; margin-bottom: 1rem;">
            <div style="width: 48px; height: 48px; border-radius: 50%; background: #dcfce7; color: #16a34a; font-size: 1.5rem; display: flex; align-items: center; justify-content: center; margin: 0 auto 8px;">
              <i class="fa-solid fa-receipt"></i>
            </div>
            <h3 style="margin: 0; font-size: 1.2rem; color: #0f172a;">Thanh Toán & Xuất Hóa Đơn Thành Công</h3>
            <p style="font-size: 0.85rem; color: #64748b; margin: 4px 0 0;">Mã hóa đơn: <strong>${invCode}</strong> | Số tiền đã thu: <strong style="color: #16a34a;">${finalAmount.toLocaleString('vi-VN')}đ</strong></p>
          </div>

          <div style="background: #fff; color: #000; border: 1.5px dashed #64748b; border-radius: 10px; padding: 1.25rem; font-family: 'Courier New', monospace; font-size: 0.85rem; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 1.25rem;">
            <div style="text-align: center; border-bottom: 1px dashed #000; padding-bottom: 8px; margin-bottom: 8px;">
              <strong style="font-size: 1rem; text-transform: uppercase;">${order.facility_name}</strong>
              <div style="font-size: 0.75rem;">HÓA ĐƠN TÀI CHÍNH BÁN LẺ POS</div>
              <div style="font-size: 0.75rem;">Số HĐ: ${invCode} - Ngày: ${newInvoice.created_at}</div>
            </div>
            <div style="margin-bottom: 3px;">Khách hàng: <strong>${order.user_name}</strong></div>
            <div style="margin-bottom: 3px;">Số ĐT: ${order.user_phone || "0901234567"}</div>
            <div style="margin-bottom: 3px;">Sân thi đấu: ${order.court_name} (${order.slot_time})</div>
            <div style="border-top: 1px dashed #000; margin: 6px 0;"></div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 3px;"><span>Tiền sân:</span> <span>${order.total_amount.toLocaleString('vi-VN')}đ</span></div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 3px;"><span>Dịch vụ phát sinh:</span> <span>${extraFee.toLocaleString('vi-VN')}đ</span></div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 3px;"><span>Phụ thu quá giờ:</span> <span>${overtimeFee.toLocaleString('vi-VN')}đ</span></div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 3px; color: #16a34a;"><span>Đã trừ tiền cọc:</span> <span>-${order.deposit_amount.toLocaleString('vi-VN')}đ</span></div>
            <div style="border-top: 1px dashed #000; margin: 6px 0;"></div>
            <div style="display: flex; justify-content: space-between; font-weight: bold; font-size: 1rem; margin-top: 4px;"><span>TỔNG ĐÃ THU:</span> <span>${finalAmount.toLocaleString('vi-VN')}đ</span></div>
            <div style="text-align: center; margin-top: 12px; font-size: 0.72rem; color: #475569;">
              <div>Thu ngân: ${newInvoice.staff_name}</div>
              <div style="margin-top: 2px;">Cảm ơn quý khách & Hẹn gặp lại trên sân đấu! 🏸</div>
            </div>
          </div>

          <div style="display: flex; gap: 8px;">
            <button class="btn btn-primary" style="flex: 1; padding: 10px; font-weight: 700;" onclick="window.print()">
              <i class="fa-solid fa-print"></i> In Hóa Đơn Quầy (Print)
            </button>
            <button class="btn btn-secondary" onclick="app.closeModal(); app.navigateTo('ui-15');">
              <i class="fa-solid fa-check"></i> Quay Về Danh Sách POS
            </button>
          </div>
        </div>
      `;
      this.openModal();
    }

    this.showToast(`🧾 Hoàn tất check-out đơn ${order.booking_code}! Đã lập hóa đơn #${invCode}`);
  }

  /* ------------------------------------------------------------------------
     9. ADMIN PORTAL (UI 17 - UI 19)
     ------------------------------------------------------------------------ */
  renderAdminOverviewFacilities() {
    const tbody = document.getElementById('admin-facilities-table-body');
    const approvedList = MockData.facilities.filter(f => f.is_approved);
    const pendingList = MockData.facilities.filter(f => !f.is_approved);

    const approvedCountEl = document.getElementById('admin-stat-approved-count');
    const pendingCountEl = document.getElementById('admin-stat-pending-count');
    if (approvedCountEl) approvedCountEl.textContent = `${approvedList.length} Cụm`;
    if (pendingCountEl) pendingCountEl.textContent = `${pendingList.length} Cơ Sở`;

    let html = '';
    approvedList.forEach(fac => {
      html += `
        <tr>
          <td>#${fac.id}</td>
          <td>
            <div style="display: flex; align-items: center; gap: 8px;">
              <img src="${fac.img}" style="width: 44px; height: 32px; border-radius: 6px; object-fit: cover;">
              <strong>${fac.name}</strong>
            </div>
          </td>
          <td style="font-size: 0.85rem; max-width: 260px; color: var(--text-muted);">${fac.address}</td>
          <td><strong style="color: var(--primary);">${fac.courts_count}</strong> Sân</td>
          <td>⭐ ${fac.rating} (${fac.reviews_count})</td>
          <td><span class="tag-badge tag-pos"><i class="fa-solid fa-check-circle"></i> ĐÃ DUYỆT</span></td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick="app.showFacilityDetailModal(${fac.id})">
              <i class="fa-solid fa-eye"></i> Xem Chi Tiết
            </button>
          </td>
        </tr>
      `;
    });

    if (tbody) tbody.innerHTML = html;
  }

  showFacilityDetailModal(facId) {
    const fac = MockData.facilities.find(f => f.id === facId);
    if (!fac) return;

    const modalBody = document.getElementById('modal-body');
    modalBody.innerHTML = `
      <div style="text-align: center; margin-bottom: 1rem;">
        <img src="${fac.img}" style="width: 100%; height: 220px; border-radius: 12px; object-fit: cover; border: 2px solid var(--primary);">
      </div>
      <h3>${fac.name}</h3>
      <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.75rem;"><i class="fa-solid fa-location-dot text-primary"></i> ${fac.address}</p>
      
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; background: rgba(0,0,0,0.2); padding: 0.75rem; border-radius: 8px; font-size: 0.85rem; margin-bottom: 1rem;">
        <div><strong>Giờ mở cửa:</strong> ${fac.open_time} - ${fac.close_time}</div>
        <div><strong>Số lượng sân con:</strong> ${fac.courts_count} sân Yonex Pro</div>
        <div><strong>Tọa độ GPS:</strong> ${fac.latitude}, ${fac.longitude}</div>
        <div><strong>Đánh giá hệ thống:</strong> ⭐ ${fac.rating}/5.0 (${fac.reviews_count} đánh giá)</div>
        <div><strong>Mức giá dao động:</strong> 99.000đ - 150.000đ/giờ</div>
        <div><strong>Trạng thái pháp lý:</strong> <span class="tag-badge tag-pos">${fac.is_approved ? 'Đã Phê Duyệt' : 'Chờ Kiểm Duyệt'}</span></div>
      </div>

      <div style="display: flex; gap: 0.5rem; justify-content: flex-end; flex-wrap: wrap;">
        <button class="btn btn-secondary btn-sm" onclick="app.closeModal()">Đóng</button>
        <button class="btn btn-secondary btn-sm" onclick="app.openGoogleMapsDirections(${fac.id})">
          <i class="fa-solid fa-map-location-dot text-primary"></i> 🗺️ Google Maps
        </button>
        <button class="btn btn-primary btn-sm" onclick="app.closeModal(); app.selectFacilityForBooking(${fac.id});">
          <i class="fa-solid fa-calendar-check"></i> Xem Lịch & Đặt Sân Cụm Này
        </button>
      </div>
    `;
    this.openModal();
  }

  renderAdminApprovals() {
    const container = document.getElementById('admin-facilities-approval-container');
    if (!container) return;

    let html = '';
    const pending = MockData.facilities.filter(f => !f.is_approved);

    if (pending.length === 0) {
      container.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 2.5rem 1.5rem; text-align: center; color: var(--text-muted); background: rgba(0,0,0,0.15); border-radius: var(--radius-md); border: 1px dashed var(--border-color);">
          <i class="fa-solid fa-circle-check" style="font-size: 2.5rem; color: var(--primary); margin-bottom: 0.75rem;"></i>
          <div style="font-size: 1.1rem; font-weight: 700; color: var(--text-main);">Tất cả cơ sở đã được phê duyệt!</div>
          <p style="font-size: 0.85rem; margin-top: 0.25rem;">Hiện không có cơ sở đăng ký mới nào đang chờ kiểm duyệt pháp lý và tọa độ GPS.</p>
        </div>
      `;
      return;
    }

    pending.forEach(fac => {
      html += `
        <div class="facility-card">
          <img src="${fac.img}" class="facility-img" alt="${fac.name}">
          <div class="facility-body">
            <div>
              <h3>${fac.name}</h3>
              <p style="font-size: 0.85rem; color: var(--text-muted);">${fac.address}</p>
              <div style="font-size: 0.75rem; color: var(--accent-cyan); margin-top: 4px;">GPS: ${fac.latitude}, ${fac.longitude}</div>
            </div>
            <div style="display: flex; gap: 0.5rem; margin-top: 1rem;">
              <button class="btn btn-primary btn-sm" style="flex: 1;" onclick="app.approveFacility(${fac.id})">
                <i class="fa-solid fa-check"></i> Phê Duyệt
              </button>
              <button class="btn btn-danger btn-sm" style="flex: 1;" onclick="app.rejectFacility(${fac.id})">
                <i class="fa-solid fa-xmark"></i> Từ Chối
              </button>
            </div>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
  }



  renderAdminUsers() {
    const tbody = document.getElementById('admin-users-table-body');
    if (!tbody) return;

    let html = '';

    MockData.users.forEach(u => {
      const isApproved = u.is_approved !== false;
      const statusBadge = isApproved 
        ? '<span class="tag-badge tag-pos"><i class="fa-solid fa-circle-check"></i> ĐÃ DUYỆT (ACTIVE)</span>'
        : (u.role === 'OWNER' 
            ? '<span class="tag-badge" style="background: rgba(245,158,11,0.2); color: #f59e0b; border: 1px solid rgba(245,158,11,0.3);"><i class="fa-solid fa-clock"></i> CHỜ ADMIN DUYỆT</span>'
            : '<span class="tag-badge" style="background: rgba(239,68,68,0.2); color: #ef4444; border: 1px solid rgba(239,68,68,0.3);"><i class="fa-solid fa-clock"></i> CHỜ CHỦ SÂN DUYỆT</span>');

      const approveBtn = isApproved 
        ? '' 
        : `<button class="btn btn-primary btn-sm" onclick="app.approveUserAccount(${u.id})" title="Admin Phê Duyệt Kích Hoạt Tài Khoản"><i class="fa-solid fa-user-check"></i> Duyệt Quyền</button>`;

      html += `
        <tr>
          <td>#${u.id}</td>
          <td><strong>${u.name}</strong></td>
          <td>${u.phone}</td>
          <td><span class="tag-badge tag-ai">${u.role}</span></td>
          <td>${u.elo_rating || 'N/A'}</td>
          <td>${statusBadge}</td>
          <td>
            <div style="display: flex; gap: 0.35rem; flex-wrap: wrap; align-items: center;">
              ${approveBtn}
              <button class="btn btn-secondary btn-sm" onclick="app.viewUserDetail(${u.id})" title="Xem thông tin chi tiết tài khoản"><i class="fa-solid fa-eye"></i> Xem</button>
              <button class="btn btn-sm" style="background: rgba(14, 165, 233, 0.2); color: #0ea5e9; border: 1px solid rgba(14, 165, 233, 0.35);" onclick="app.editUserAccount(${u.id})" title="Chỉnh sửa thông tin & Đổi mật khẩu"><i class="fa-solid fa-pen-to-square"></i> Sửa</button>
              <button class="btn btn-sm" style="background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.35);" onclick="app.deleteUserAccount(${u.id})" title="Xóa tài khoản này khỏi hệ thống"><i class="fa-solid fa-trash-can"></i> Xóa</button>
            </div>
          </td>
        </tr>
      `;
    });

    tbody.innerHTML = html;
  }

  viewUserDetail(userId) {
    const u = MockData.users.find(user => user.id === userId);
    if (!u) return;

    const modalBody = document.getElementById('modal-body');
    const isApproved = u.is_approved !== false;
    const pwdDisplay = u.password ? u.password : '123456';

    modalBody.innerHTML = `
      <div style="text-align: left;">
        <h3 style="color: var(--primary); display: flex; align-items: center; gap: 8px;">
          <i class="fa-solid fa-id-card"></i> Chi Tiết Tài Khoản #${u.id}
        </h3>
        <hr style="border-color: var(--border-color); margin: 0.75rem 0;">
        <div style="display: flex; flex-direction: column; gap: 0.6rem; font-size: 0.9rem;">
          <div><strong>Họ và tên:</strong> <span style="color: var(--text-main); font-weight: 700;">${u.name}</span></div>
          <div><strong>Số điện thoại / Login:</strong> <code style="color: var(--accent-cyan); font-weight: 700;">${u.phone}</code></div>
          <div><strong>Mật khẩu hiện tại:</strong> <code style="background: rgba(22,121,70,0.15); color: var(--primary); font-weight: 700; padding: 2px 8px; border-radius: 4px;">${pwdDisplay}</code></div>
          <div><strong>Phân hệ vai trò:</strong> <span class="tag-badge tag-ai">${u.role}</span></div>
          <div><strong>Trình độ ELO:</strong> <span style="color: #f59e0b; font-weight: 700;">${u.elo_rating || 'N/A'} ELO</span></div>
          <div><strong>Trạng thái phê duyệt:</strong> ${isApproved ? '<span style="color: var(--primary); font-weight: bold;">✅ Đã kích hoạt (Active)</span>' : '<span style="color: #ef4444; font-weight: bold;">⏳ Chờ duyệt</span>'}</div>
          <div><strong>Ngày khởi tạo:</strong> ${u.created_at || 'Khởi tạo hệ thống'}</div>
        </div>
        <div style="display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 1.5rem; border-top: 1px solid var(--border-color); padding-top: 1rem;">
          <button class="btn btn-secondary btn-sm" onclick="app.closeModal()">Đóng</button>
          <button class="btn btn-primary btn-sm" onclick="app.closeModal(); app.editUserAccount(${u.id});">
            <i class="fa-solid fa-pen-to-square"></i> Đổi Mật Khẩu / Sửa
          </button>
          <button class="btn btn-danger btn-sm" onclick="app.closeModal(); app.deleteUserAccount(${u.id});">
            <i class="fa-solid fa-trash-can"></i> Xóa Tài Khoản
          </button>
        </div>
      </div>
    `;
    this.openModal();
  }

  editUserAccount(userId) {
    const u = MockData.users.find(user => user.id === userId);
    if (!u) return;

    const modalBody = document.getElementById('modal-body');
    const pwdDisplay = u.password ? u.password : '123456';
    const isApproved = u.is_approved !== false;

    modalBody.innerHTML = `
      <div style="text-align: left;">
        <h3 style="color: var(--primary); display: flex; align-items: center; gap: 8px;">
          <i class="fa-solid fa-user-pen"></i> Chỉnh Sửa Tài Khoản #${u.id}
        </h3>
        <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px;">Cập nhật thông tin định danh và quản trị mật khẩu đăng nhập</p>
        
        <form onsubmit="app.saveEditUser(event, ${u.id})" style="margin-top: 1rem; display: flex; flex-direction: column; gap: 0.75rem;">
          <div class="form-group">
            <label class="form-label"><i class="fa-solid fa-signature text-primary"></i> Họ và Tên</label>
            <input type="text" id="edit-user-name" class="form-control" value="${u.name}" required>
          </div>
          <div class="form-group">
            <label class="form-label"><i class="fa-solid fa-phone text-primary"></i> Số Điện Thoại Đăng Nhập</label>
            <input type="tel" id="edit-user-phone" class="form-control" value="${u.phone}" pattern="[0-9]{10}" title="Nhập số điện thoại 10 chữ số" required>
          </div>
          <div class="form-group">
            <label class="form-label"><i class="fa-solid fa-lock text-primary"></i> Mật Khẩu Đăng Nhập</label>
            <div style="position: relative;">
              <input type="password" id="edit-user-password" class="form-control" value="${pwdDisplay}" required style="padding-right: 2.5rem;">
              <button type="button" onclick="app.togglePasswordVisibility('edit-user-password', this)" style="position: absolute; right: 0.75rem; top: 50%; transform: translateY(-50%); background: none; border: none; color: #64748b; cursor: pointer; font-size: 1rem;">
                <i class="fa-solid fa-eye"></i>
              </button>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label"><i class="fa-solid fa-shield-halved text-primary"></i> Phân Hệ Vai Trò</label>
            <select id="edit-user-role" class="form-control">
              <option value="CUSTOMER" ${u.role === 'CUSTOMER' ? 'selected' : ''}>Khách Hàng (CUSTOMER)</option>
              <option value="OWNER" ${u.role === 'OWNER' ? 'selected' : ''}>Chủ Sân (OWNER)</option>
              <option value="STAFF" ${u.role === 'STAFF' ? 'selected' : ''}>Thu Ngân Quầy (STAFF)</option>
              <option value="ADMIN" ${u.role === 'ADMIN' ? 'selected' : ''}>Quản Trị Viên (ADMIN)</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label"><i class="fa-solid fa-trophy text-primary"></i> Điểm ELO Trình Độ</label>
            <input type="number" id="edit-user-elo" class="form-control" value="${typeof u.elo_rating === 'number' ? u.elo_rating : 1200}">
          </div>
          <div class="form-group">
            <label class="form-label"><i class="fa-solid fa-circle-check text-primary"></i> Trạng Thái Duyệt</label>
            <select id="edit-user-status" class="form-control">
              <option value="true" ${isApproved ? 'selected' : ''}>Đã Phê Duyệt (Kích Hoạt Hoạt Động)</option>
              <option value="false" ${!isApproved ? 'selected' : ''}>Chờ Phê Duyệt (Khóa Tạm Thời)</option>
            </select>
          </div>

          <div style="margin-top: 1rem; display: flex; gap: 0.5rem; justify-content: flex-end;">
            <button type="button" class="btn btn-secondary btn-sm" onclick="app.closeModal()">Hủy</button>
            <button type="submit" class="btn btn-primary btn-sm">
              <i class="fa-solid fa-floppy-disk"></i> Lưu Thay Đổi
            </button>
          </div>
        </form>
      </div>
    `;
    this.openModal();
  }

  saveEditUser(e, userId) {
    if (e) e.preventDefault();
    const user = MockData.users.find(u => u.id === userId);
    if (!user) return;

    const nameInput = document.getElementById('edit-user-name');
    const phoneInput = document.getElementById('edit-user-phone');
    const passInput = document.getElementById('edit-user-password');
    const roleInput = document.getElementById('edit-user-role');
    const eloInput = document.getElementById('edit-user-elo');
    const statusInput = document.getElementById('edit-user-status');

    if (nameInput) user.name = nameInput.value.trim();
    if (phoneInput) user.phone = phoneInput.value.trim();
    if (passInput && passInput.value.trim()) user.password = passInput.value.trim();
    if (roleInput) user.role = roleInput.value;
    if (eloInput) user.elo_rating = parseInt(eloInput.value) || 1200;
    if (statusInput) user.is_approved = statusInput.value === 'true';

    if (typeof saveMockDataToLocalStorage === 'function') {
      saveMockDataToLocalStorage();
    }

    this.closeModal();
    this.renderAdminUsers();
    this.renderOwnerStaff();
    if (this.currentView === 'ui-20') this.renderDatabaseInspector();
    this.showToast(`🎉 Đã cập nhật thành công thông tin & mật khẩu cho tài khoản "${user.name}"!`);
  }

  deleteUserAccount(userId) {
    const user = MockData.users.find(u => u.id === userId);
    if (!user) {
      this.showToast("⛔ Không tìm thấy tài khoản để xóa!", "error");
      return;
    }

    if (this.currentUser && this.currentUser.id === userId) {
      this.showToast("⛔ Quyền Admin: Không thể tự xóa tài khoản đang đăng nhập hiện tại!", "error");
      return;
    }

    if (confirm(`⚠️ XÁC NHẬN XÓA TÀI KHOẢN:\n\n- Họ tên: ${user.name}\n- SĐT: ${user.phone}\n- Vai trò: ${user.role}\n- ID: #${user.id}\n\nBạn có chắc chắn muốn XÓA VĨNH VIỄN tài khoản này khỏi hệ thống? Hành động này sẽ được đồng bộ ngay lập tức vào CSDL!`)) {
      MockData.users = MockData.users.filter(u => u.id !== userId);
      if (typeof saveMockDataToLocalStorage === 'function') {
        saveMockDataToLocalStorage();
      }

      this.renderAdminUsers();
      this.renderOwnerStaff();
      if (this.currentView === 'ui-20') this.renderDatabaseInspector();
      this.showToast(`🗑️ Đã xóa vĩnh viễn tài khoản "${user.name}" (#${userId}) khỏi hệ thống!`);
    }
  }

  /* ------------------------------------------------------------------------
     11. UTILITIES & MODAL SYSTEM
     ------------------------------------------------------------------------ */
  openModal() {
    document.getElementById('global-modal').classList.add('active');
  }

  closeModal() {
    document.getElementById('global-modal').classList.remove('active');
  }

  toggleTheme() {
    document.body.classList.toggle('light-theme');
    const isLight = document.body.classList.contains('light-theme');
    const themeIcon = document.getElementById('theme-icon');
    if (themeIcon) {
      themeIcon.className = isLight ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
    }
    this.showToast(`Đã chuyển sang giao diện: ${isLight ? 'Sáng (Light Mode)' : 'Tối (Dark Mode)'}`);
  }

  showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.style.borderColor = type === 'error' ? 'var(--accent-rose)' : 'var(--primary)';
    toast.innerHTML = `<i class="fa-solid ${type === 'error' ? 'fa-circle-exclamation' : 'fa-circle-check'}" style="color: ${type === 'error' ? 'var(--accent-rose)' : 'var(--primary)'}"></i> ${message}`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.remove();
    }, 3500);
  }

  selectLoginRole(role, autoFillPhone = false) {
    const select = document.getElementById('login-role-select');
    if (select) select.value = role;

    document.querySelectorAll('.login-role-card').forEach(card => card.classList.remove('active'));
    const activeCard = document.getElementById(`login-card-${role.toLowerCase()}`);
    if (activeCard) activeCard.classList.add('active');

    const badge = document.getElementById('login-role-preview-badge');
    const roleTitleMap = {
      'CUSTOMER': '<i class="fa-solid fa-user"></i> VAI TRÒ: KHÁCH HÀNG',
      'OWNER': '<i class="fa-solid fa-building-user"></i> VAI TRÒ: CHỦ SÂN',
      'STAFF': '<i class="fa-solid fa-cash-register"></i> VAI TRÒ: THU NGÂN POS',
      'ADMIN': '<i class="fa-solid fa-user-shield"></i> VAI TRÒ: QUẢN TRỊ VIÊN'
    };
    if (badge) badge.innerHTML = roleTitleMap[role] || role;
  }

  syncRoleSelectToCard(role) {
    this.selectLoginRole(role, false);
  }

  quickLogin(role) {
    this.selectLoginRole(role, true);
    const sampleUser = MockData.users.find(u => u.role === role);
    this.switchRole(role, sampleUser);
    this.showToast(`⚡ Đã đăng nhập nhanh thành công phân hệ ${role}!`);
  }

  switchAuthTab(tab) {
    const loginForm = document.getElementById('form-auth-login');
    const registerForm = document.getElementById('form-auth-register');
    const loginBtn = document.getElementById('auth-tab-login');
    const registerBtn = document.getElementById('auth-tab-register');

    if (tab === 'login') {
      if (loginForm) loginForm.style.display = 'block';
      if (registerForm) registerForm.style.display = 'none';
      if (loginBtn) {
        loginBtn.className = 'auth-tab-btn active';
        loginBtn.style.cssText = '';
      }
      if (registerBtn) {
        registerBtn.className = 'auth-tab-btn';
        registerBtn.style.cssText = '';
      }
    } else {
      if (loginForm) loginForm.style.display = 'none';
      if (registerForm) registerForm.style.display = 'block';
      if (registerBtn) {
        registerBtn.className = 'auth-tab-btn active';
        registerBtn.style.cssText = '';
      }
      if (loginBtn) {
        loginBtn.className = 'auth-tab-btn';
        loginBtn.style.cssText = '';
      }
    }
  }

  togglePasswordVisibility(id, btn) {
    const input = document.getElementById(id);
    if (!input) return;
    if (input.type === 'password') {
      input.type = 'text';
      btn.innerHTML = '<i class="fa-solid fa-eye-slash"></i>';
    } else {
      input.type = 'password';
      btn.innerHTML = '<i class="fa-solid fa-eye"></i>';
    }
  }

  handleRegRoleChange(role) {
    const facGroup = document.getElementById('reg-facility-group');
    const hint = document.getElementById('reg-role-hint');

    if (role === 'STAFF') {
      if (facGroup) facGroup.style.display = 'block';
      if (hint) {
        hint.style.borderColor = 'rgba(59, 130, 246, 0.4)';
        hint.style.background = 'rgba(59, 130, 246, 0.08)';
        hint.style.color = '#3b82f6';
        hint.innerHTML = `<i class="fa-solid fa-clock"></i> <strong>Lưu ý:</strong> Tài khoản Thu Ngân quầy cần có sự <strong>PHÊ DUYỆT CỦA CHỦ SÂN</strong> trước khi đăng nhập.`;
      }
    } else if (role === 'OWNER') {
      if (facGroup) facGroup.style.display = 'none';
      if (hint) {
        hint.style.borderColor = 'rgba(245, 158, 11, 0.4)';
        hint.style.background = 'rgba(245, 158, 11, 0.08)';
        hint.style.color = '#f59e0b';
        hint.innerHTML = `<i class="fa-solid fa-clock"></i> <strong>Lưu ý:</strong> Tài khoản Chủ Sân cần có sự <strong>PHÊ DUYỆT CỦA QUẢN TRỊ VIÊN (ADMIN)</strong> trước khi quản lý cụm sân.`;
      }
    } else {
      if (facGroup) facGroup.style.display = 'none';
      if (hint) {
        hint.style.borderColor = 'rgba(0, 229, 255, 0.2)';
        hint.style.background = 'rgba(0, 229, 255, 0.08)';
        hint.style.color = 'var(--accent-cyan)';
        hint.innerHTML = `<i class="fa-solid fa-circle-info"></i> Tài khoản <strong>Khách Hàng</strong> có thể sử dụng ngay sau khi đăng ký.`;
      }
    }
  }

  handleLoginRoleSelectChange(role) {
    this.selectLoginRole(role, false);
  }

  handleLogin(e) {
    e.preventDefault();
    const phone = document.getElementById('login-phone').value.trim();
    const password = document.getElementById('login-password').value.trim();
    const selectedRole = document.getElementById('login-role-select').value;

    // 1. Tim kiem tai khoan nguoi dung theo dung so dien thoại/username nhap vao
    const user = MockData.users.find(u => u.phone === phone);

    if (!user) {
      this.showToast(`⛔ Đăng nhập thất bại: Số điện thoại/Username "${phone}" chưa được đăng ký trong hệ thống!`, 'error');
      return;
    }

    // 2. Kiem tra mat khau chinh xac (tu dong khoi phuc neu mat khau cu bi loi undefined)
    let expectedPassword = user.password;
    if (!expectedPassword || expectedPassword === 'undefined' || expectedPassword === 'null' || !expectedPassword.trim()) {
      expectedPassword = (user.phone === '0123456789' ? '02092006' : '123456');
      user.password = expectedPassword;
      if (typeof saveMockDataToLocalStorage === 'function') saveMockDataToLocalStorage();
    }
    if (password !== expectedPassword) {
      this.showToast(`⛔ Đăng nhập thất bại: Mật khẩu nhập vào không chính xác! Vui lòng thử lại.`, 'error');
      return;
    }

    // 3. Kiem tra nghiem ngat: Vai tro tai khoan phai khop voi vai tro dang chon
    if (user.role !== selectedRole) {
      const roleNames = {
        'CUSTOMER': 'Khách Hàng',
        'OWNER': 'Chủ Sân',
        'STAFF': 'Thu Ngân',
        'ADMIN': 'Quản Trị Viên'
      };
      const actualRole = roleNames[user.role] || user.role;
      const targetRole = roleNames[selectedRole] || selectedRole;

      this.showToast(`⛔ Quyền truy cập bị từ chối: Tài khoản "${user.name}" có vai trò [${actualRole}], không thể đăng nhập vào phân hệ [${targetRole}]!`, 'error');
      return;
    }

    // 4. Kiem tra trang thai phe duyyet (is_approved)
    if (user.is_approved === false) {
      if (selectedRole === 'STAFF') {
        this.showToast(`⛔ Đăng nhập thất bại: Tài khoản Thu Ngân (${user.name}) đang CHỜ CHỦ SÂN PHÊ DUYỆT!`, 'error');
        return;
      }
      if (selectedRole === 'OWNER') {
        this.showToast(`⛔ Đăng nhập thất bại: Tài khoản Chủ Sân (${user.name}) đang CHỜ QUẢN TRỊ VIÊN (ADMIN) PHÊ DUYỆT!`, 'error');
        return;
      }
    }

    // 5. Dang nhap thanh cong va truyen doi tuong user chinh xac vao switchRole
    const success = this.switchRole(selectedRole, user);
    if (success !== false) {
      const roleNames = {
        'CUSTOMER': 'Khách Hàng',
        'OWNER': 'Chủ Sân',
        'STAFF': 'Thu Ngân Quầy',
        'ADMIN': 'Quản Trị Viên'
      };
      this.showToast(`🎉 Đăng nhập thành công vai trò ${roleNames[selectedRole] || selectedRole}! Xin chào ${user.name}`);
    }
  }

  handleRegister(e) {
    e.preventDefault();
    const name = document.getElementById('reg-fullname').value.trim();
    const phone = document.getElementById('reg-phone').value.trim();
    const password = document.getElementById('reg-password').value.trim();

    if (!password || password.length < 6) {
      this.showToast('⛔ Đăng ký thất bại: Mật khẩu khởi tạo phải từ 6 ký tự trở lên!', 'error');
      return;
    }

    const existingUser = MockData.users.find(u => u.phone === phone);
    if (existingUser) {
      this.showToast(`⛔ Đăng ký thất bại: Số điện thoại "${phone}" đã được tạo tài khoản trong hệ thống!`, 'error');
      return;
    }

    const newId = MockData.users.length + 1;
    const newUser = {
      id: newId,
      name: name,
      phone: phone,
      password: password,
      role: 'CUSTOMER',
      facility_id: null,
      elo_rating: 1200,
      avatar: name.charAt(0).toUpperCase() || 'C',
      is_approved: true,
      created_at: new Date().toLocaleDateString('vi-VN')
    };

    MockData.users.push(newUser);
    if (typeof saveMockDataToLocalStorage === 'function') saveMockDataToLocalStorage();

    // Tu dong dang nhap voi tai khoan Khach Hang vua tao
    this.switchRole('CUSTOMER', newUser);
    this.showToast(`🎉 Đăng ký thành công! Đã lưu mật khẩu & tự động đăng nhập tài khoản Khách Hàng cho ${name}.`);

    this.renderAdminUsers();
  }

  /* ------------------------------------------------------------------------
     FORGOT PASSWORD & SMS OTP VERIFICATION FLOW
     ------------------------------------------------------------------------ */
  openForgotPasswordModal() {
    const modalBody = document.getElementById('modal-body');
    if (!modalBody) return;

    modalBody.innerHTML = `
      <div style="text-align: left;">
        <h3 style="color: var(--primary); display: flex; align-items: center; gap: 8px;">
          <i class="fa-solid fa-mobile-retro"></i> Khôi Phục Mật Khẩu Qua SMS OTP
        </h3>
        <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px;">
          Nhập số điện thoại đã đăng ký để nhận mã xác thực OTP gửi qua tin nhắn SMS.
        </p>
        <form onsubmit="app.handleSendForgotPasswordOTP(event)" style="margin-top: 1.25rem;">
          <div class="form-group">
            <label class="form-label"><i class="fa-solid fa-phone text-primary"></i> Số điện thoại đã đăng ký</label>
            <input type="tel" id="forgot-phone-input" class="form-control" placeholder="VD: 0901234567" required>
          </div>
          <div style="display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 1.25rem;">
            <button type="button" class="btn btn-secondary btn-sm" onclick="app.closeModal()">Hủy</button>
            <button type="submit" class="btn btn-primary btn-sm">
              <i class="fa-solid fa-paper-plane"></i> Gửi Mã OTP SMS
            </button>
          </div>
        </form>
      </div>
    `;
    this.openModal();
  }

  handleSendForgotPasswordOTP(e) {
    e.preventDefault();
    const phone = document.getElementById('forgot-phone-input').value.trim();
    const user = MockData.users.find(u => u.phone === phone);

    if (!user) {
      this.showToast(`⛔ Không tìm thấy tài khoản nào đăng ký với SĐT "${phone}"!`, 'error');
      return;
    }

    const generatedOTP = Math.floor(100000 + Math.random() * 900000).toString();
    this.forgotPasswordSession = {
      phone: phone,
      userId: user.id,
      otp: generatedOTP
    };

    // Mo phang gui SMS gia lap
    this.showToast(`💬 SMS OTP: Mã xác thực khôi phục mật khẩu của bạn là [ ${generatedOTP} ]`, 'info');

    const modalBody = document.getElementById('modal-body');
    modalBody.innerHTML = `
      <div style="text-align: left;">
        <h3 style="color: var(--accent-cyan); display: flex; align-items: center; gap: 8px;">
          <i class="fa-solid fa-shield-halved"></i> Xác Nhận Mã OTP & Đổi Mật Khẩu
        </h3>
        <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px; background: rgba(16,185,129,0.1); padding: 8px 12px; border-radius: 6px; border: 1px solid rgba(16,185,129,0.3);">
          📲 Mã OTP đã được gửi đến số: <strong>${phone}</strong> (Tài khoản: <strong>${user.name}</strong>).<br>
          <span style="color: var(--primary); font-weight: 700;">Mã OTP SMS thử nghiệm: [ ${generatedOTP} ]</span>
        </div>
        <form onsubmit="app.handleVerifyOTPAndResetPassword(event)" style="margin-top: 1.25rem;">
          <div class="form-group">
            <label class="form-label"><i class="fa-solid fa-key text-primary"></i> Nhập 6 số OTP từ SMS</label>
            <input type="text" id="forgot-otp-input" class="form-control" placeholder="VD: ${generatedOTP}" maxlength="6" required style="letter-spacing: 4px; font-weight: 800; text-align: center; font-size: 1.1rem;">
          </div>
          <div class="form-group">
            <label class="form-label"><i class="fa-solid fa-lock text-primary"></i> Mật khẩu mới</label>
            <input type="password" id="forgot-new-password" class="form-control" placeholder="Nhập mật khẩu mới từ 6 ký tự..." required>
          </div>
          <div style="display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 1.25rem;">
            <button type="button" class="btn btn-secondary btn-sm" onclick="app.closeModal()">Hủy</button>
            <button type="submit" class="btn btn-accent btn-sm">
              <i class="fa-solid fa-circle-check"></i> Xác Nhận & Cập Nhật Mật Khẩu
            </button>
          </div>
        </form>
      </div>
    `;
  }

  handleVerifyOTPAndResetPassword(e) {
    e.preventDefault();
    const otpInput = document.getElementById('forgot-otp-input').value.trim();
    const newPassword = document.getElementById('forgot-new-password').value.trim();

    if (!this.forgotPasswordSession || otpInput !== this.forgotPasswordSession.otp) {
      this.showToast('⛔ Mã OTP nhập vào không chính xác! Vui lòng kiểm tra lại tin nhắn SMS.', 'error');
      return;
    }

    if (!newPassword || newPassword.length < 6) {
      this.showToast('⛔ Mật khẩu mới phải chứa ít nhất 6 ký tự!', 'error');
      return;
    }

    const user = MockData.users.find(u => u.id === this.forgotPasswordSession.userId);
    if (user) {
      user.password = newPassword;
      if (typeof saveMockDataToLocalStorage === 'function') saveMockDataToLocalStorage();

      this.closeModal();
      this.showToast(`🎉 Đã khôi phục mật khẩu thành công cho tài khoản ${user.name}! Bạn có thể đăng nhập bằng mật khẩu mới.`);

      // Dien san SĐT va Mat khau moi vao form login
      const phoneInput = document.getElementById('login-phone');
      const passInput = document.getElementById('login-password');
      if (phoneInput) phoneInput.value = user.phone;
      if (passInput) passInput.value = newPassword;

      this.selectLoginRole(user.role, false);
      this.navigateTo('ui-01');
    }
  }

  approveUserAccount(userId) {
    const user = MockData.users.find(u => u.id === userId);
    if (!user) return;
    user.is_approved = true;
    if (typeof saveMockDataToLocalStorage === 'function') saveMockDataToLocalStorage();

    if (user.role === 'STAFF') {
      this.showToast(`✅ Chủ Sân đã phê duyệt tài khoản Thu Ngân: ${user.name}!`);
    } else if (user.role === 'OWNER') {
      this.showToast(`✅ Quản Trị Viên (Admin) đã phê duyệt tài khoản Chủ Sân: ${user.name}!`);
    } else {
      this.showToast(`✅ Đã phê duyệt kích hoạt tài khoản: ${user.name}!`);
    }

    this.renderOwnerStaff();
    this.renderAdminUsers();
  }

  /* ------------------------------------------------------------------------
     10. UI 20: WEB DATABASE INSPECTOR & 9 TABLES VISUALIZER (BẢNG CSDL TIẾNG VIỆT)
     ------------------------------------------------------------------------ */
  renderDatabaseInspector() {
    const tabsContainer = document.getElementById('db-table-tabs-container');
    if (!tabsContainer) return;

    const tableConfigs = [
      { key: 'users', label: '1. NGUỜI DÙNG (users)', icon: 'fa-users', desc: 'Bảng 1: Quản lý tài khoản người dùng (Khách hàng, Chủ sân, Nhân viên POS, Admin) & điểm trình độ ELO' },
      { key: 'facilities', label: '2. CỤM SÂN (facilities)', icon: 'fa-building-user', desc: 'Bảng 2: Danh sách các cụm cơ sở thể thao cầu lông tại Hà Nội & tọa độ GPS ghim vị trí' },
      { key: 'courts', label: '3. SÂN CON (courts)', icon: 'fa-layer-group', desc: 'Bảng 3: Danh sách từng sân con thi đấu (loại thảm Yonex Pro/VIP Cushion, giá niêm yết cơ bản)' },
      { key: 'time_slots', label: '4. KHUNG GIỜ (time_slots)', icon: 'fa-clock', desc: 'Bảng 4: Ma trận ô giờ đặt sân (Giờ bình thường 5h-17h: 120k/h, Giờ cao điểm 18h-22h: 160k/h)' },
      { key: 'equipments', label: '5. VỢT & DỤNG CỤ (equipments)', icon: 'fa-boxes-stacked', desc: 'Bảng 5: Danh mục 6 loại vợt (Yonex, Victor, Li-Ning, Kumpoo), Hộp cầu Thành Công, Nước Pocari & Khăn' },
      { key: 'booking_orders', label: '6. ĐƠN ĐẶT SÂN (booking_orders)', icon: 'fa-receipt', desc: 'Bảng 6: Quản lý đơn hàng đặt sân trực tuyến, mã cọc 50k VNPay QR & mã vé điện tử QR' },
      { key: 'invoices', label: '7. HÓA ĐƠN POS (invoices)', icon: 'fa-file-invoice-dollar', desc: 'Bảng 7: Hóa đơn tài chính thanh toán và check-out xuất tại quầy POS thu ngân' },
      { key: 'matchmaking_rooms', label: '8. PHÒNG GHÉP ELO (matchmaking_rooms)', icon: 'fa-users-viewfinder', desc: 'Bảng 8: Danh sách phòng giao lưu tìm đối thủ ghép kèo ELO tự động' },
      { key: 'occupancy_heatmap', label: '9. HEATMAP LẤP ĐẦY (occupancy_heatmap)', icon: 'fa-chart-pie', desc: 'Bảng 9: Biểu đồ nhiệt lấp đầy và tỷ lệ tải giữ sân theo từng khung giờ trong ngày' }
    ];

    let tabsHtml = '';
    tableConfigs.forEach(tbl => {
      const count = MockData[tbl.key] ? MockData[tbl.key].length : 0;
      const isActive = this.currentDBTable === tbl.key;
      const btnClass = isActive ? 'btn-primary' : 'btn-secondary';
      tabsHtml += `
        <button class="btn ${btnClass} btn-sm" onclick="app.switchDBTable('${tbl.key}')" style="display: flex; align-items: center; gap: 6px; font-size: 0.8rem;">
          <i class="fa-solid ${tbl.icon}"></i> ${tbl.label} <span class="tag-badge" style="background: rgba(255,255,255,0.25); font-size: 0.7rem;">${count} dòng</span>
        </button>
      `;
    });
    tabsContainer.innerHTML = tabsHtml;

    // Update active table title & desc
    const activeConfig = tableConfigs.find(t => t.key === this.currentDBTable) || tableConfigs[0];
    const activeCount = MockData[this.currentDBTable] ? MockData[this.currentDBTable].length : 0;
    document.getElementById('db-active-table-title').innerHTML = `<i class="fa-solid ${activeConfig.icon}"></i> Bảng CSDL: <code style="color: var(--accent-cyan); font-size: 1.1rem; font-weight: 800;">${activeConfig.key}</code> — <span style="color: var(--primary); font-weight: bold;">${activeConfig.label}</span> (${activeCount} bản ghi)`;
    document.getElementById('db-active-table-desc').textContent = activeConfig.desc;

    // Render content
    this.renderDatabaseTableContent();
  }

  switchDBTable(tableName) {
    this.currentDBTable = tableName;
    this.renderDatabaseInspector();
  }

  toggleDBViewMode() {
    this.isDBJSONView = !this.isDBJSONView;
    const btnIcon = document.getElementById('db-view-mode-icon');
    const btnText = document.getElementById('db-view-mode-text');

    if (this.isDBJSONView) {
      if (btnIcon) btnIcon.className = "fa-solid fa-table";
      if (btnText) btnText.textContent = "Xem Dạng Bảng Lưới Tiếng Việt";
    } else {
      if (btnIcon) btnIcon.className = "fa-solid fa-code";
      if (btnText) btnText.textContent = "Xem Dạng Mã JSON Raw";
    }
    this.renderDatabaseTableContent();
  }

  renderDatabaseTableContent() {
    const tableContainer = document.getElementById('db-table-view-container');
    const jsonContainer = document.getElementById('db-json-view-container');
    const rawRecords = MockData[this.currentDBTable] || [];

    // Filter out 'img' property from CSDL records view
    const records = rawRecords.map(item => {
      const copy = { ...item };
      delete copy.img;
      return copy;
    });

    if (this.isDBJSONView) {
      if (tableContainer) tableContainer.style.display = 'none';
      if (jsonContainer) {
        jsonContainer.style.display = 'block';
        jsonContainer.textContent = JSON.stringify(records, null, 2);
      }
      return;
    }

    if (tableContainer) tableContainer.style.display = 'block';
    if (jsonContainer) jsonContainer.style.display = 'none';

    if (!records || records.length === 0) {
      tableContainer.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 2rem;">Bảng dữ liệu này hiện đang trống.</div>`;
      return;
    }

    // Từ điển Tiếng Việt chuẩn dịch tất cả tên cột Database
    const columnTranslation = {
      'id': 'Mã ID',
      'name': 'Tên / Họ Và Tên',
      'phone': 'Số Điện Thoại',
      'role': 'Vai Trò Quyền Hạn',
      'elo_rating': 'Điểm ELO Trình Độ',
      'avatar': 'Ảnh Đại Diện',
      'facility_id': 'Mã Cụm Sân',
      'facility_name': 'Tên Cụm Cơ Sở Sân',
      'address': 'Địa Chỉ Chi Nhánh',
      'latitude': 'Tọa Độ Vĩ Độ GPS (Lat)',
      'longitude': 'Tọa Độ Kinh Độ GPS (Long)',
      'open_time': 'Giờ Mở Cửa',
      'close_time': 'Giờ Đóng Cửa',
      'is_approved': 'Trạng Thái Duyệt Admin',
      'rating': 'Đánh Giá (Số Sao)',
      'reviews_count': 'Lượt Đánh Giá',
      'courts_count': 'Số Lượng Sân Con',
      'court_type': 'Loại Thảm / Mặt Sân',
      'base_price': 'Giá Giờ Niêm Yết',
      'status': 'Trạng Thái Hoạt Động',
      'court_id': 'Mã Sân Con',
      'start_time': 'Giờ Bắt Đầu',
      'end_time': 'Giờ Kết Thúc',
      'price': 'Đơn Giá Khung Giờ',
      'is_ai_dynamic': 'Giá Biến Động AI',
      'price_type': 'Loại Khung Giờ',
      'adjustment': 'AI Điều Chỉnh Giá',
      'held_until': 'Hạn Giữ Chỗ Tạm Thời',
      'quantity': 'Số Lượng Tồn Kho',
      'unit': 'Đơn Vị Tính',
      'style': 'Đặc Tính Vợt / Đồ',
      'booking_code': 'Mã Đơn Đặt Sân',
      'user_name': 'Tên Khách Hàng',
      'user_phone': 'SĐT Khách Hàng',
      'court_name': 'Tên Sân Con Đặt',
      'slot_time': 'Khung Giờ Đánh Sân',
      'booking_date': 'Ngày Đặt Sân',
      'total_amount': 'Tổng Tiền Đơn Hàng',
      'deposit_amount': 'Số Tiền Đặt Cọc',
      'deposit_status': 'Trạng Thái Tiền Cọc',
      'order_status': 'Trạng Thái Đơn Hàng',
      'created_at': 'Thời Gian Khởi Tạo',
      'qr_ticket_code': 'Mã Vé QR Check-in',
      'invoice_code': 'Mã Hóa Đơn POS',
      'customer_name': 'Tên Khách Hàng',
      'checkin_time': 'Giờ Khách Vào Sân',
      'checkout_time': 'Giờ Khách Ra Sân',
      'booking_fee': 'Tiền Sân & Đồ Đặt',
      'deposit_deducted': 'Số Tiền Cọc Đã Trừ',
      'extra_fee': 'Phụ Phí Nước/Đồ',
      'overtime_fee': 'Phí Chơi Quá Giờ',
      'final_amount': 'Tổng Thanh Toán Cuối',
      'payment_method': 'Phương Thức Thanh Toán',
      'staff_name': 'Nhân Viên Thu Ngân POS',
      'room_name': 'Tên Phòng Ghép Kèo',
      'match_date': 'Ngày Thi Đấu',
      'match_time': 'Khung Giờ Thi Đấu',
      'required_elo_min': 'Yêu Cầu ELO Thấp Nhất',
      'required_elo_max': 'Yêu Cầu ELO Cao Nhất',
      'match_type': 'Thể Thức Đánh',
      'current_players': 'Số Tay Vợt Hiện Có',
      'max_players': 'Số Tay Vợt Tối Đa',
      'host_name': 'Chủ Phòng Tạo Kèo',
      'host_elo': 'Điểm ELO Chủ Phòng',
      'chat_messages': 'Lịch Sử Chat Phòng',
      'hour': 'Khung Giờ Trong Ngày',
      'rate': 'Tỷ Lệ Lấp Đầy (%)'
    };

    // Dynamic Headers mit Tiếng Việt
    const headers = Object.keys(records[0]);
    let html = `<table class="custom-table" id="db-records-table"><thead><tr>`;
    headers.forEach(h => {
      const viTitle = columnTranslation[h] || h.toUpperCase();
      html += `<th>${viTitle} <div style="font-size: 0.68rem; color: var(--accent-cyan); font-weight: normal; text-transform: none; margin-top: 2px;">(${h})</div></th>`;
    });
    html += `</tr></thead><tbody>`;

    records.forEach(row => {
      html += `<tr>`;
      headers.forEach(h => {
        let val = row[h];
        let displayVal = val;

        if (typeof val === 'boolean') {
          displayVal = val 
            ? `<span class="tag-badge tag-ai"><i class="fa-solid fa-circle-check"></i> ĐÃ DUYỆT (TRUE)</span>` 
            : `<span class="tag-badge" style="background: rgba(239,68,68,0.2); color: #ef4444;"><i class="fa-solid fa-circle-xmark"></i> CHƯA DUYỆT (FALSE)</span>`;
        } else if (typeof val === 'number') {
          if (h.includes('price') || h.includes('amount') || h.includes('fee')) {
            displayVal = `<strong style="color: var(--primary);">${val.toLocaleString('vi-VN')}đ</strong>`;
          } else {
            displayVal = `<code>${val}</code>`;
          }
        } else if (typeof val === 'object' && val !== null) {
          displayVal = `<code style="font-size: 0.75rem; color: var(--accent-cyan);">${JSON.stringify(val)}</code>`;
        } else if (typeof val === 'string' && (val.startsWith('http') || val.startsWith('images/'))) {
          displayVal = `<a href="${val}" target="_blank" style="color: var(--accent-cyan); text-decoration: underline;"><i class="fa-solid fa-image"></i> ${val}</a>`;
        } else if (h === 'role') {
          const roleMap = {
            'CUSTOMER': '<span class="tag-badge tag-ai">KHÁCH HÀNG</span>',
            'OWNER': '<span class="tag-badge" style="background: rgba(245,158,11,0.2); color: #f59e0b;">CHỦ SÂN</span>',
            'STAFF': '<span class="tag-badge tag-pos">NHÂN VIÊN POS</span>',
            'ADMIN': '<span class="tag-badge" style="background: rgba(168,85,247,0.2); color: #a855f7;">QUẢN TRỊ VIÊN</span>'
          };
          displayVal = roleMap[val] || val;
        } else if (h === 'price_type') {
          displayVal = val === 'peak' 
            ? '<span class="tag-badge" style="background: rgba(239,68,68,0.2); color: #ef4444;">GIỜ VÀNG (PEAK)</span>' 
            : '<span class="tag-badge tag-ai">GIỜ BÌNH THƯỜNG</span>';
        }
        html += `<td>${displayVal}</td>`;
      });
      html += `</tr>`;
    });
    html += `</tbody></table>`;

    tableContainer.innerHTML = html;
  }

  filterDatabaseRecords() {
    const query = document.getElementById('db-search-input').value.toLowerCase();
    const rows = document.querySelectorAll('#db-records-table tbody tr');
    rows.forEach(row => {
      const text = row.textContent.toLowerCase();
      row.style.display = text.includes(query) ? '' : 'none';
    });
  }

  exportDatabaseJSON() {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(MockData, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", "badminton_ai_database.json");
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
    this.showToast("Đã tải xuống thành công toàn bộ Tệp CSDL JSON (badminton_ai_database.json)!");
  }

  async exportSQLiteDatabase() {
    try {
      // 1. First attempt to download binary .db directly from server if available
      const response = await fetch('http://localhost:8085/api/sqlite/download');
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = "badminton.db";
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        this.showToast("💾 Đã tải xuống tệp nhị phân SQLite (badminton.db) trực tiếp từ máy chủ!");
        return;
      }
    } catch (e) {
      console.log("Central SQLite binary server not active, generating standard SQLite SQL dump...");
    }

    // 2. Client-side generate comprehensive SQLite SQL script (.sql)
    this.generateSQLiteSQLDump();
  }

  generateSQLiteSQLDump() {
    let sql = `-- ==========================================================================\n`;
    sql += `-- BADMINTON AI MANAGEMENT SYSTEM - SQLITE3 DATABASE DUMP\n`;
    sql += `-- Generated: ${new Date().toISOString()}\n`;
    sql += `-- Compatibility: SQLite 3.x / DB Browser for SQLite\n`;
    sql += `-- ==========================================================================\n\n`;
    sql += `PRAGMA foreign_keys = ON;\nBEGIN TRANSACTION;\n\n`;

    // 1. users
    sql += `-- 1. BẢNG users\n`;
    sql += `CREATE TABLE IF NOT EXISTS users (\n  id INTEGER PRIMARY KEY,\n  name TEXT NOT NULL,\n  phone TEXT UNIQUE NOT NULL,\n  password TEXT,\n  role TEXT DEFAULT 'CUSTOMER',\n  elo_rating INTEGER DEFAULT 1000,\n  avatar TEXT,\n  facility_id INTEGER,\n  is_approved INTEGER DEFAULT 1\n);\n`;
    (MockData.users || []).forEach(u => {
      const name = (u.name || '').replace(/'/g, "''");
      const phone = (u.phone || '').replace(/'/g, "''");
      const pwd = (u.password || '123456').replace(/'/g, "''");
      const role = (u.role || 'CUSTOMER').replace(/'/g, "''");
      const avatar = (u.avatar || 'U').replace(/'/g, "''");
      const facId = u.facility_id ? u.facility_id : 'NULL';
      const isApp = u.is_approved ? 1 : 0;
      sql += `INSERT OR REPLACE INTO users (id, name, phone, password, role, elo_rating, avatar, facility_id, is_approved) VALUES (${u.id}, '${name}', '${phone}', '${pwd}', '${role}', ${u.elo_rating || 1000}, '${avatar}', ${facId}, ${isApp});\n`;
    });
    sql += `\n`;

    // 2. facilities
    sql += `-- 2. BẢNG facilities\n`;
    sql += `CREATE TABLE IF NOT EXISTS facilities (\n  id INTEGER PRIMARY KEY,\n  name TEXT NOT NULL,\n  address TEXT NOT NULL,\n  distance TEXT,\n  latitude REAL,\n  longitude REAL,\n  open_time TEXT,\n  close_time TEXT,\n  rating REAL,\n  reviews_count INTEGER,\n  courts_count INTEGER,\n  is_approved INTEGER DEFAULT 1\n);\n`;
    (MockData.facilities || []).forEach(f => {
      const name = (f.name || '').replace(/'/g, "''");
      const addr = (f.address || '').replace(/'/g, "''");
      const dist = (f.distance || '').replace(/'/g, "''");
      const lat = f.latitude || 21.0285;
      const lng = f.longitude || 105.8542;
      const ot = (f.open_time || '05:00').replace(/'/g, "''");
      const ct = (f.close_time || '23:00').replace(/'/g, "''");
      const rating = f.rating || 5.0;
      const rev = f.reviews_count || 0;
      const cc = f.courts_count || 8;
      const isApp = f.is_approved ? 1 : 0;
      sql += `INSERT OR REPLACE INTO facilities (id, name, address, distance, latitude, longitude, open_time, close_time, rating, reviews_count, courts_count, is_approved) VALUES (${f.id}, '${name}', '${addr}', '${dist}', ${lat}, ${lng}, '${ot}', '${ct}', ${rating}, ${rev}, ${cc}, ${isApp});\n`;
    });
    sql += `\n`;

    // 3. courts
    sql += `-- 3. BẢNG courts\n`;
    sql += `CREATE TABLE IF NOT EXISTS courts (\n  id INTEGER PRIMARY KEY,\n  facility_id INTEGER,\n  name TEXT NOT NULL,\n  court_type TEXT,\n  base_price REAL,\n  status TEXT\n);\n`;
    (MockData.courts || []).forEach(c => {
      const name = (c.name || '').replace(/'/g, "''");
      const ct = (c.court_type || 'Thảm Yonex').replace(/'/g, "''");
      const bp = c.base_price || 120000;
      const st = (c.status || 'AVAILABLE').replace(/'/g, "''");
      sql += `INSERT OR REPLACE INTO courts (id, facility_id, name, court_type, base_price, status) VALUES (${c.id}, ${c.facility_id || 101}, '${name}', '${ct}', ${bp}, '${st}');\n`;
    });
    sql += `\n`;

    // 4. time_slots
    sql += `-- 4. BẢNG time_slots\n`;
    sql += `CREATE TABLE IF NOT EXISTS time_slots (\n  id INTEGER PRIMARY KEY,\n  court_id INTEGER,\n  start_time TEXT,\n  end_time TEXT,\n  price REAL,\n  is_ai_dynamic INTEGER,\n  price_type TEXT,\n  status TEXT\n);\n`;
    (MockData.time_slots || []).forEach(s => {
      const st = (s.start_time || '').replace(/'/g, "''");
      const et = (s.end_time || '').replace(/'/g, "''");
      const isAi = s.is_ai_dynamic ? 1 : 0;
      const pt = (s.price_type || 'Tiêu chuẩn').replace(/'/g, "''");
      const status = (s.status || 'AVAILABLE').replace(/'/g, "''");
      sql += `INSERT OR REPLACE INTO time_slots (id, court_id, start_time, end_time, price, is_ai_dynamic, price_type, status) VALUES (${s.id}, ${s.court_id || 1}, '${st}', '${et}', ${s.price || 120000}, ${isAi}, '${pt}', '${status}');\n`;
    });
    sql += `\n`;

    // 5. equipments
    sql += `-- 5. BẢNG equipments\n`;
    sql += `CREATE TABLE IF NOT EXISTS equipments (\n  id INTEGER PRIMARY KEY,\n  name TEXT NOT NULL,\n  price REAL,\n  quantity INTEGER,\n  unit TEXT\n);\n`;
    (MockData.equipments || []).forEach(eq => {
      const name = (eq.name || '').replace(/'/g, "''");
      const unit = (eq.unit || 'cái').replace(/'/g, "''");
      sql += `INSERT OR REPLACE INTO equipments (id, name, price, quantity, unit) VALUES (${eq.id}, '${name}', ${eq.price || 0}, ${eq.quantity || 10}, '${unit}');\n`;
    });
    sql += `\n`;

    // 6. booking_orders
    sql += `-- 6. BẢNG booking_orders\n`;
    sql += `CREATE TABLE IF NOT EXISTS booking_orders (\n  id INTEGER PRIMARY KEY,\n  booking_code TEXT UNIQUE NOT NULL,\n  user_name TEXT,\n  user_phone TEXT,\n  facility_name TEXT,\n  court_name TEXT,\n  slot_time TEXT,\n  booking_date TEXT,\n  total_amount REAL,\n  deposit_amount REAL,\n  deposit_status TEXT,\n  order_status TEXT\n);\n`;
    (MockData.booking_orders || []).forEach(b => {
      const code = (b.booking_code || '').replace(/'/g, "''");
      const uName = (b.user_name || '').replace(/'/g, "''");
      const uPhone = (b.user_phone || '').replace(/'/g, "''");
      const facName = (b.facility_name || '').replace(/'/g, "''");
      const courtName = (b.court_name || '').replace(/'/g, "''");
      const slotTime = (b.slot_time || '').replace(/'/g, "''");
      const bDate = (b.booking_date || '').replace(/'/g, "''");
      const depSt = (b.deposit_status || '').replace(/'/g, "''");
      const ordSt = (b.order_status || '').replace(/'/g, "''");
      sql += `INSERT OR REPLACE INTO booking_orders (id, booking_code, user_name, user_phone, facility_name, court_name, slot_time, booking_date, total_amount, deposit_amount, deposit_status, order_status) VALUES (${b.id}, '${code}', '${uName}', '${uPhone}', '${facName}', '${courtName}', '${slotTime}', '${bDate}', ${b.total_amount || 0}, ${b.deposit_amount || 0}, '${depSt}', '${ordSt}');\n`;
    });
    sql += `\n`;

    // 7. invoices
    sql += `-- 7. BẢNG invoices\n`;
    sql += `CREATE TABLE IF NOT EXISTS invoices (\n  id INTEGER PRIMARY KEY,\n  invoice_code TEXT UNIQUE NOT NULL,\n  customer_name TEXT,\n  facility_name TEXT,\n  final_amount REAL,\n  payment_method TEXT,\n  created_at TEXT\n);\n`;
    (MockData.invoices || []).forEach(inv => {
      const invCode = (inv.invoice_code || '').replace(/'/g, "''");
      const cName = (inv.customer_name || '').replace(/'/g, "''");
      const fName = (inv.facility_name || '').replace(/'/g, "''");
      const pm = (inv.payment_method || 'CASH').replace(/'/g, "''");
      const cat = (inv.created_at || '').replace(/'/g, "''");
      sql += `INSERT OR REPLACE INTO invoices (id, invoice_code, customer_name, facility_name, final_amount, payment_method, created_at) VALUES (${inv.id}, '${invCode}', '${cName}', '${fName}', ${inv.final_amount || 0}, '${pm}', '${cat}');\n`;
    });
    sql += `\n`;

    // 8. matchmaking_rooms
    sql += `-- 8. BẢNG matchmaking_rooms\n`;
    sql += `CREATE TABLE IF NOT EXISTS matchmaking_rooms (\n  id INTEGER PRIMARY KEY,\n  room_name TEXT,\n  facility_name TEXT,\n  required_elo_min INTEGER,\n  required_elo_max INTEGER,\n  match_type TEXT,\n  current_players INTEGER,\n  max_players INTEGER,\n  status TEXT,\n  host_name TEXT,\n  host_elo INTEGER\n);\n`;
    (MockData.matchmaking_rooms || []).forEach(r => {
      const rName = (r.room_name || '').replace(/'/g, "''");
      const fName = (r.facility_name || '').replace(/'/g, "''");
      const mt = (r.match_type || '').replace(/'/g, "''");
      const st = (r.status || 'OPEN').replace(/'/g, "''");
      const hName = (r.host_name || '').replace(/'/g, "''");
      sql += `INSERT OR REPLACE INTO matchmaking_rooms (id, room_name, facility_name, required_elo_min, required_elo_max, match_type, current_players, max_players, status, host_name, host_elo) VALUES (${r.id}, '${rName}', '${fName}', ${r.required_elo_min || 1000}, ${r.required_elo_max || 2000}, '${mt}', ${r.current_players || 1}, ${r.max_players || 4}, '${st}', '${hName}', ${r.host_elo || 1200});\n`;
    });
    sql += `\n`;

    // 9. occupancy_heatmap
    sql += `-- 9. BẢNG occupancy_heatmap\n`;
    sql += `CREATE TABLE IF NOT EXISTS occupancy_heatmap (\n  hour TEXT PRIMARY KEY,\n  rate INTEGER,\n  status TEXT\n);\n`;
    (MockData.occupancy_heatmap || []).forEach(h => {
      const hr = (h.hour || '').replace(/'/g, "''");
      const st = (h.status || '').replace(/'/g, "''");
      sql += `INSERT OR REPLACE INTO occupancy_heatmap (hour, rate, status) VALUES ('${hr}', ${h.rate || 0}, '${st}');\n`;
    });

    sql += `\nCOMMIT;\n`;

    const blob = new Blob([sql], { type: 'text/sql;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = "badminton_database_sqlite.sql";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
    this.showToast("📄 Đã xuất thành công kịch bản CSDL SQLite chuẩn (.sql)!");
  }

  openImportDatabaseModal() {
    const modalBody = document.getElementById('modal-body');
    if (!modalBody) return;

    modalBody.innerHTML = `
      <div style="text-align: left;">
        <h3 style="color: var(--primary); display: flex; align-items: center; gap: 8px;">
          <i class="fa-solid fa-arrows-rotate"></i> Đồng Bộ & Nhập CSDL Đa Nền Tảng
        </h3>
        <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 6px; line-height: 1.5;">
          Khi bạn tạo tài khoản trên trình duyệt khác (hoặc tab ẩn danh), dữ liệu LocalStorage được lưu riêng theo từng trình duyệt. Bạn có thể dùng 1 trong 2 cách sau để đồng bộ tức thì sang tài khoản Admin:
        </p>

        <div style="margin-top: 1rem; display: flex; flex-direction: column; gap: 1rem;">
          <!-- Cách 1: Tải lên tệp JSON -->
          <div style="background: rgba(16, 185, 129, 0.08); border: 1px dashed var(--primary); border-radius: var(--radius-md); padding: 1rem;">
            <div style="font-weight: 700; color: var(--primary); font-size: 0.9rem; margin-bottom: 0.4rem;">
              <i class="fa-solid fa-file-arrow-up"></i> Cách 1: Tải lên file badminton_ai_database.json
            </div>
            <input type="file" id="db-import-file-input" accept=".json" class="form-control" style="font-size: 0.85rem;" onchange="app.handleImportDatabaseFile(event)">
          </div>

          <!-- Cách 2: Dán mã JSON trực tiếp -->
          <div style="background: rgba(6, 182, 212, 0.08); border: 1px solid rgba(6, 182, 212, 0.25); border-radius: var(--radius-md); padding: 1rem;">
            <div style="font-weight: 700; color: var(--accent-cyan); font-size: 0.9rem; margin-bottom: 0.4rem;">
              <i class="fa-solid fa-paste"></i> Cách 2: Hoặc Dán chuỗi JSON dữ liệu vào đây
            </div>
            <textarea id="db-import-paste-text" class="form-control" rows="5" placeholder='Dán chuỗi JSON database vào đây... {"users": [...]}' style="font-family: monospace; font-size: 0.8rem;"></textarea>
            <div style="display: flex; justify-content: flex-end; margin-top: 0.5rem; gap: 0.5rem;">
              <button class="btn btn-secondary btn-sm" onclick="app.copyCurrentDatabaseJSON()">
                <i class="fa-solid fa-copy"></i> Sao Chép CSDL Hiện Tại
              </button>
              <button class="btn btn-primary btn-sm" onclick="app.applyPastedDatabaseJSON()">
                <i class="fa-solid fa-check"></i> Cập Nhật & Đồng Bộ Ngay
              </button>
            </div>
          </div>
        </div>

        <div style="display: flex; justify-content: flex-end; margin-top: 1.25rem;">
          <button class="btn btn-secondary btn-sm" onclick="app.closeModal()">Đóng</button>
        </div>
      </div>
    `;
    this.openModal();
  }

  handleImportDatabaseFile(e) {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const imported = JSON.parse(event.target.result);
        this.applyImportedDatabase(imported);
        this.closeModal();
      } catch (err) {
        this.showToast("⛔ Tệp JSON không hợp lệ hoặc bị lỗi cú pháp!", "error");
      }
    };
    reader.readAsText(file);
  }

  applyPastedDatabaseJSON() {
    const textarea = document.getElementById('db-import-paste-text');
    if (!textarea) return;
    const text = textarea.value.trim();
    if (!text) {
      this.showToast("⛔ Vui lòng dán chuỗi JSON CSDL trước khi đồng bộ!", "error");
      return;
    }

    try {
      const imported = JSON.parse(text);
      this.applyImportedDatabase(imported);
      this.closeModal();
    } catch (err) {
      this.showToast("⛔ Chuỗi JSON dán vào không hợp lệ: " + err.message, "error");
    }
  }

  applyImportedDatabase(imported) {
    const keys = ['users', 'facilities', 'courts', 'time_slots', 'equipments', 'booking_orders', 'invoices', 'matchmaking_rooms', 'occupancy_heatmap', 'bookings', 'orders'];
    let updatedCount = 0;

    keys.forEach(k => {
      if (imported[k] && Array.isArray(imported[k])) {
        MockData[k] = imported[k];
        updatedCount++;
      }
    });

    if (typeof saveMockDataToLocalStorage === 'function') {
      saveMockDataToLocalStorage();
    }

    this.renderAdminUsers();
    this.renderAdminOverviewFacilities();
    this.renderAdminApprovals();
    if (this.currentView === 'ui-20') {
      this.renderDatabaseInspector();
    }

    this.showToast(`✅ Đồng bộ thành công ${updatedCount} bảng CSDL! Đã cập nhật toàn bộ tài khoản mới.`);
  }

  copyCurrentDatabaseJSON() {
    const dataStr = JSON.stringify(MockData, null, 2);
    navigator.clipboard.writeText(dataStr).then(() => {
      this.showToast("📋 Đã sao chép toàn bộ chuỗi JSON CSDL vào Clipboard!");
    }).catch(() => {
      this.showToast("Không thể tự động sao chép. Vui lòng xuất tệp JSON.");
    });
  }

  /* ==========================================================================
     AI ADVANCED MODULES & ALGORITHMS (UC003, UC004, UC006)
     ========================================================================== */

  // 1. UC004: AI SMART COURT RECOMMENDER
  openAICourtRecommenderModal() {
    const panel = document.getElementById('ai-recommender-panel');
    const tabEl = document.getElementById('quick-tab-ai-recom');
    if (!panel) return;
    const isHidden = panel.style.display === 'none';
    panel.style.display = isHidden ? 'block' : 'none';
    if (tabEl) {
      tabEl.style.background = isHidden ? 'rgba(16, 185, 129, 0.35)' : 'linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(6, 182, 212, 0.25))';
    }
    if (isHidden) {
      panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  closeAICourtRecommenderModal() {
    const panel = document.getElementById('ai-recommender-panel');
    const tabEl = document.getElementById('quick-tab-ai-recom');
    if (panel) panel.style.display = 'none';
    if (tabEl) tabEl.style.background = 'linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(6, 182, 212, 0.25))';
  }

  runAICourtRecommendation() {
    const elo = parseInt(document.getElementById('ai-filter-elo')?.value || '1450', 10);
    const playStyle = document.getElementById('ai-filter-playstyle')?.value || 'attack';
    const maxBudget = parseInt(document.getElementById('ai-filter-budget')?.value || '999999', 10);

    this.showToast("🤖 AI Recommendation Engine đang phân tích 48+ cụm sân theo thuật toán tối ưu...");

    // Machine Learning style Scoring Algorithm:
    // Score = Distance_weight * d + Rating_weight * r + Style_fit * s + Budget_fit * b
    const scoredFacilities = MockData.facilities.filter(f => f.is_approved).map(fac => {
      let score = 70; // baseline
      let reasons = [];

      // 1. Rating contribution (max +15)
      const ratingBoost = (fac.rating - 4.5) * 30;
      score += Math.max(0, ratingBoost);

      // 2. Distance contribution (closer is better, max +15)
      const distNum = parseFloat(fac.distance || '5.0');
      if (distNum <= 3.0) {
        score += 15;
        reasons.push("Gần bạn (< 3km)");
      } else if (distNum <= 6.0) {
        score += 10;
        reasons.push("Cự ly hợp lý (< 6km)");
      } else {
        score += 4;
      }

      // 3. Playstyle fit (thảm Yonex/Enlio, quy mô sân)
      const isYonex = (fac.name + ' ' + (fac.badges || []).join(' ')).toLowerCase().includes('yonex');
      const isEnlio = (fac.name + ' ' + (fac.badges || []).join(' ')).toLowerCase().includes('enlio');
      
      if (playStyle === 'attack') {
        if (isYonex || isEnlio) {
          score += 12;
          reasons.push("Thảm bám đập cầu tốt");
        }
      } else if (playStyle === 'defense') {
        if (fac.courts_count >= 8) {
          score += 10;
          reasons.push("Không gian rộng, phản xạ tốt");
        }
      } else if (playStyle === 'casual') {
        score += 8;
        reasons.push("Không khí giao lưu thoải mái");
      }

      // 4. Budget fit
      const price = fac.base_price || 120000;
      if (price <= maxBudget) {
        score += 8;
        reasons.push("Đúng khung ngân sách");
      } else {
        score -= 15;
      }

      // 5. ELO compatibility boost
      if (elo >= 1700 && (isYonex || fac.rating >= 4.9)) {
        score += 6;
        reasons.push("Chuẩn sàn ELO cao");
      } else if (elo < 1400) {
        score += 5;
        reasons.push("Thân thiện người mới");
      }

      const finalScore = Math.min(99, Math.max(55, Math.round(score)));
      return {
        ...fac,
        ai_score: finalScore,
        ai_reason: reasons.slice(0, 2).join(' • ')
      };
    });

    // Sort descending by AI Match Score
    scoredFacilities.sort((a, b) => b.ai_score - a.ai_score);

    // Update Summary Box
    const summaryBox = document.getElementById('ai-recommendation-summary-box');
    if (summaryBox) {
      summaryBox.style.display = 'block';
      summaryBox.innerHTML = `
        <div style="font-weight: 700; margin-bottom: 2px;">
          <i class="fa-solid fa-circle-check text-primary"></i> Đã tính toán xong cho ELO <strong>${elo}</strong> • Phong cách: <strong>${playStyle === 'attack' ? 'Chuyên Công Đập Cầu' : (playStyle === 'defense' ? 'Phản Tạt Phòng Thủ' : 'Giao Lưu Rèn Luyện')}</strong>
        </div>
        <div>Top 1 đề xuất tốt nhất: <strong>${scoredFacilities[0]?.name}</strong> đạt độ tương thích <strong>${scoredFacilities[0]?.ai_score}%</strong>!</div>
      `;
    }

    this.renderCustomerFacilities(scoredFacilities);
    this.showToast(`✨ Đã lọc Top ${scoredFacilities.length} sân phù hợp nhất theo gợi ý AI!`);
  }

  // 2. UC006: AI MATCHMAKING & ELO PREDICTOR
  toggleAIEloPredictor() {
    const card = document.getElementById('ai-elo-predictor-card');
    if (!card) return;
    const isHidden = card.style.display === 'none';
    card.style.display = isHidden ? 'block' : 'none';
    if (isHidden) {
      this.runAIMatchupCalculation();
      card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  runAIMatchupCalculation() {
    const p1Name = document.getElementById('matchup-p1-name')?.value.trim() || 'Người chơi 1';
    const p2Name = document.getElementById('matchup-p2-name')?.value.trim() || 'Người chơi 2';
    
    // Tier resolution
    const p1TierInput = document.getElementById('matchup-p1-tier')?.value;
    const p2TierInput = document.getElementById('matchup-p2-tier')?.value;
    const tier1 = this.getSkillTierInfo(p1TierInput ? parseInt(p1TierInput, 10) : 5);
    const tier2 = this.getSkillTierInfo(p2TierInput ? parseInt(p2TierInput, 10) : 5);

    // AI Logistic probability based on skill tier differences (1 tier diff ~ 8-10% win rate shift)
    const tierDiff = tier1.tier - tier2.tier; // positive if p1 is higher
    let p1Percent = 50;
    let p2Percent = 50;
    let handicapRecommendation = "Đồng banh (0 điểm)";

    if (tierDiff === 0) {
      p1Percent = 50;
      p2Percent = 50;
      handicapRecommendation = "Đồng banh (0 điểm chấp - Cân bằng tuyệt đối)";
    } else if (tierDiff === 1) {
      p1Percent = 58;
      p2Percent = 42;
      handicapRecommendation = `${p1Name} chấp ${p2Name} 2 - 3 điểm / set`;
    } else if (tierDiff === -1) {
      p1Percent = 42;
      p2Percent = 58;
      handicapRecommendation = `${p2Name} chấp ${p1Name} 2 - 3 điểm / set`;
    } else if (tierDiff === 2) {
      p1Percent = 70;
      p2Percent = 30;
      handicapRecommendation = `${p1Name} chấp ${p2Name} 4 - 5 điểm / set`;
    } else if (tierDiff === -2) {
      p1Percent = 30;
      p2Percent = 70;
      handicapRecommendation = `${p2Name} chấp ${p1Name} 4 - 5 điểm / set`;
    } else if (tierDiff >= 3) {
      p1Percent = 82;
      p2Percent = 18;
      handicapRecommendation = `${p1Name} chấp ${p2Name} 6 - 8 điểm / set`;
    } else {
      p1Percent = 18;
      p2Percent = 82;
      handicapRecommendation = `${p2Name} chấp ${p1Name} 6 - 8 điểm / set`;
    }

    // Update UI elements
    const label1 = document.getElementById('matchup-p1-winrate-label');
    const label2 = document.getElementById('matchup-p2-winrate-label');
    const bar1 = document.getElementById('matchup-winrate-bar-p1');
    const bar2 = document.getElementById('matchup-winrate-bar-p2');
    const balanceBadge = document.getElementById('matchup-match-balance-badge');
    const analysisContent = document.getElementById('matchup-analysis-content');

    if (label1) label1.innerHTML = `<i class="fa-solid fa-shield-halved"></i> ${p1Name} (${tier1.badgeText || tier1.name}): <strong>${p1Percent}%</strong>`;
    if (label2) label2.innerHTML = `<strong>${p2Percent}%</strong> :${p2Name} (${tier2.badgeText || tier2.name}) <i class="fa-solid fa-bolt"></i>`;
    if (bar1) bar1.style.width = `${p1Percent}%`;
    if (bar2) bar2.style.width = `${p2Percent}%`;

    const absDiff = Math.abs(tierDiff);
    if (balanceBadge) {
      if (absDiff === 0) {
        balanceBadge.className = "tag-badge";
        balanceBadge.style.background = "#ecfdf5";
        balanceBadge.style.color = "#15803d";
        balanceBadge.textContent = `Cân bằng tuyệt đối (Cùng cấp ${tier1.name})`;
      } else if (absDiff === 1) {
        balanceBadge.className = "tag-badge";
        balanceBadge.style.background = "#eff6ff";
        balanceBadge.style.color = "#1d4ed8";
        balanceBadge.textContent = `Chênh lệch nhẹ (Lệch 1 cấp bậc)`;
      } else {
        balanceBadge.className = "tag-badge";
        balanceBadge.style.background = "#fffbeb";
        balanceBadge.style.color = "#b45309";
        balanceBadge.textContent = `Kèo lệch thách đấu (Lệch ${absDiff} cấp bậc)`;
      }
    }

    if (analysisContent) {
      analysisContent.innerHTML = `
        <div style="background: #ffffff; padding: 12px; border-radius: 10px; border: 1px solid #cbd5e1;">
          <strong style="color: #166534; font-size: 0.88rem;"><i class="fa-solid fa-award"></i> Trình Độ & Cơ Hội ${p1Name}:</strong>
          <div style="margin-top: 6px; font-size: 0.82rem; line-height: 1.5;">
            <div>• Cấp bậc: <span style="color: ${tier1.color}; font-weight: 800;">${tier1.display}</span></div>
            <div>• Khả năng thắng: <span style="color: #16a34a; font-weight: 800;">${p1Percent}%</span></div>
            <div style="margin-top: 4px; color: #475569;">• Dự đoán tỉ số set: <strong>${p1Percent >= p2Percent ? '21 - ' + Math.max(12, Math.round(21 * (p2Percent / p1Percent))) : Math.max(12, Math.round(21 * (p1Percent / p2Percent))) + ' - 21'}</strong></div>
          </div>
        </div>
        <div style="background: #ffffff; padding: 12px; border-radius: 10px; border: 1px solid #cbd5e1;">
          <strong style="color: #1e40af; font-size: 0.88rem;"><i class="fa-solid fa-award"></i> Trình Độ & Cơ Hội ${p2Name}:</strong>
          <div style="margin-top: 6px; font-size: 0.82rem; line-height: 1.5;">
            <div>• Cấp bậc: <span style="color: ${tier2.color}; font-weight: 800;">${tier2.display}</span></div>
            <div>• Khả năng thắng: <span style="color: #2563eb; font-weight: 800;">${p2Percent}%</span></div>
            <div style="margin-top: 4px; color: #475569;">• Đánh giá kỹ năng: <strong>${tier2.desc}</strong></div>
          </div>
        </div>
        <div style="background: #ffffff; padding: 12px; border-radius: 10px; border: 1px solid #cbd5e1;">
          <strong style="color: #6b21a8; font-size: 0.88rem;"><i class="fa-solid fa-brain"></i> Đề Xuất Cân Bằng & Chấp Điểm AI:</strong>
          <div style="margin-top: 6px; font-size: 0.82rem; color: #334155; line-height: 1.5;">
            ${absDiff === 0 
              ? '🎯 <strong>Kèo Cùng Cấp Cân Bằng Tuyệt Đối:</strong> Không cần chấp điểm. Trận đấu phụ thuộc vào sự ổn định trong các pha gài cầu sát lưới và thể lực set cuối.' 
              : absDiff === 1
              ? `⚡ <strong>Đề Xuất Chấp Điểm:</strong> Chênh lệch 1 cấp bậc (${tier1.name} vs ${tier2.name}). Khuyến nghị: <strong>${handicapRecommendation}</strong> để trận đấu đạt trạng thái cân bằng lý tưởng 50-50!`
              : `⚖️ <strong>Đề Xuất Kèo Thách Đấu:</strong> Chênh lệch ${absDiff} cấp bậc. AI khuyến nghị: <strong>${handicapRecommendation}</strong> để duy trì tính cạnh tranh và kịch tính.`}
          </div>
        </div>
      `;
    }
  }

  // 3. UC003: AI DYNAMIC PRICING SIMULATOR & LIVE RECALC
  simulateAIDynamicPricingRecalc() {
    this.showToast("⚡ AI Dynamic Engine đang quét tỷ lệ lấp đầy hôm nay và tính toán lại ma trận giá...");

    setTimeout(() => {
      // Simulate occupancy and recalculate peak / off-peak slots
      MockData.time_slots.forEach(slot => {
        const startHour = parseInt(slot.start_time.split(':')[0], 10);
        if (startHour >= 18 && startHour < 22) {
          slot.is_ai_dynamic = true;
          slot.price_type = "peak";
          slot.price = 160000;
          slot.adjustment = "+33% (Giờ Vàng AI Surge)";
        } else if (startHour >= 12 && startHour <= 14) {
          slot.is_ai_dynamic = true;
          slot.price_type = "offpeak";
          slot.price = 100000;
          slot.adjustment = "-17% (Giờ Trưa Flash Sale)";
        } else {
          slot.is_ai_dynamic = false;
          slot.price_type = "normal";
          slot.price = 120000;
        }
      });

      this.renderSlotMatrix();
      if (typeof saveMockDataToLocalStorage === 'function') {
        saveMockDataToLocalStorage();
      }
      this.showToast("✅ AI Engine đã cập nhật thành công ma trận giá động (+33% Giờ Vàng, -17% Giờ Trưa)!");
    }, 600);
  }
}

// Initialize Application when DOM ready
let app;
document.addEventListener('DOMContentLoaded', () => {
  app = new BadmintonAIApp();
  app.init();
});
