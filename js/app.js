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
    this.selectedEquipments = {}; // { equipId: qty }
    this.holdTimer = null;
    this.holdTimerSeconds = 600; // 10 minutes (600s)
    this.isAIDynamicPriceActive = true;
    
    // Favorites & Quick Filters
    this.favorites = new Set([101, 102]);
    this.isFavoritesFilterActive = false;

    // Chat & Active Room
    this.activeRoom = MockData.matchmaking_rooms[0];

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
    const logoutBtn = document.getElementById('header-logout-btn');
    const authPills = document.getElementById('header-auth-pills-group');

    if (this.currentUser) {
      if (avatarEl) avatarEl.textContent = this.currentUser.avatar || '👤';
      if (nameEl) nameEl.textContent = this.currentUser.name;
      if (logoutBtn) logoutBtn.style.display = 'inline-flex';
      if (authPills) authPills.style.display = 'none';
    } else {
      if (avatarEl) avatarEl.textContent = '👤';
      if (nameEl) nameEl.textContent = 'Khách';
      if (logoutBtn) logoutBtn.style.display = 'none';
      if (authPills) authPills.style.display = 'flex';
    }
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

      // If no user is logged in:
      // If switching to non-CUSTOMER role, auto load demo user for that role so testing is smooth
      if (!this.currentUser && role !== 'CUSTOMER') {
        const userRoleMap = {
          'OWNER': MockData.users.find(u => u.role === 'OWNER') || MockData.users[2],
          'STAFF': MockData.users.find(u => u.role === 'STAFF') || MockData.users[3],
          'ADMIN': MockData.users.find(u => u.role === 'ADMIN') || MockData.users[4]
        };
        this.currentUser = userRoleMap[role];
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

    // Update Header Avatar & Name
    this.updateHeaderUserUI();

    // Update Sidebar Navigation according to Role
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
    this.showToast('👋 Đã đăng xuất khỏi hệ thống!');
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
          { id: 'ui-03', icon: 'fa-calendar-days', text: 'Đặt Sân & Thuê Đồ' },
          { id: 'ui-04', icon: 'fa-qrcode', text: 'Thanh Toán Cọc QR' },
          { id: 'ui-05', icon: 'fa-ticket', text: 'Vé QR Điện Tử' },
          { id: 'ui-06', icon: 'fa-users-viewfinder', text: 'AI Matchmaking ELO' },
          { id: 'ui-07', icon: 'fa-comments', text: 'Chat Nhóm Giao Lưu' },
          { id: 'ui-08', icon: 'fa-id-card', text: 'Hồ Sơ & Điểm ELO' }
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

    let html = `
      <a class="nav-item ${this.currentView === 'ui-01' ? 'active' : ''}" onclick="app.navigateTo('ui-01')">
        <i class="fa-solid fa-right-to-bracket icon"></i>
        <span>Đăng Nhập / Xác Thực</span>
      </a>
      <hr style="border-color: var(--border-color); margin: 0.5rem 0;">
    `;

    currentConfig.items.forEach(item => {
      html += `
        <a class="nav-item ${this.currentView === item.id ? 'active' : ''}" onclick="app.navigateTo('${item.id}')">
          <i class="fa-solid ${item.icon} icon"></i>
          <span>${item.text}</span>
        </a>
      `;
    });

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
    else if (screenId === 'ui-03') this.updateBottomNavActive('explore');
    else if (screenId === 'ui-06') this.updateBottomNavActive('trending');
    else if (screenId === 'ui-01' || screenId === 'ui-08') this.updateBottomNavActive('account');

    if (screenId === 'ui-map') this.initGoogleSportsMap();
    if (screenId === 'ui-09') this.renderOwnerDashboardOrders();
    if (screenId === 'ui-10') this.initLeafletMap();
    if (screenId === 'ui-13') this.renderOwnerStaff();
    if (screenId === 'ui-15') this.renderPOSTodayBookingsTable();
    if (screenId === 'ui-17') this.renderAdminOverviewFacilities();
    if (screenId === 'ui-18') this.renderAdminApprovals();
    if (screenId === 'ui-19') this.renderAdminUsers();
    if (screenId === 'ui-20') this.renderDatabaseInspector();

    window.scrollTo({ top: 0, behavior: 'smooth' });
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
      window.open('https://www.google.com/maps/search/?api=1&query=S%C3%A2n+C%E1%BA%A7u+L%C3%B4ng+TP.HCM', '_blank');
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
     3. UI 03: SLOT MATRIX & EQUIPMENT RENTAL
     ------------------------------------------------------------------------ */
  renderSlotMatrix() {
    const matrixGrid = document.getElementById('slot-matrix-grid');
    const ownerMatrix = document.getElementById('owner-ai-slot-matrix');
    let html = '';
    let ownerHtml = '';

    MockData.time_slots.forEach(slot => {
      const isSelected = this.selectedSlot && this.selectedSlot.id === slot.id;
      const statusClass = isSelected ? 'selected' : slot.status.toLowerCase();

      let aiTag = '';
      if (slot.is_ai_dynamic && this.isAIDynamicPriceActive) {
        aiTag = `<span class="slot-price-ai ${slot.price_type}"><i class="fa-solid fa-robot"></i> ${slot.adjustment}</span>`;
      }

      html += `
        <div class="slot-btn ${statusClass}" onclick="app.selectSlot(${slot.id})">
          <span class="slot-time">${slot.start_time} - ${slot.end_time}</span>
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

  selectSlot(slotId) {
    const slot = MockData.time_slots.find(s => s.id === slotId);
    if (slot.status !== 'AVAILABLE') {
      this.showToast(`Khung giờ ${slot.start_time} - ${slot.end_time} đang ở trạng thái: ${slot.status}!`, 'error');
      return;
    }

    this.selectedSlot = slot;
    this.renderSlotMatrix();
    this.updateBookingSummary();
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

    if (!this.selectedSlot) {
      summarySlot.textContent = "Chưa chọn slot giờ";
      summaryTotal.textContent = "0 VNĐ";
      btnProceed.disabled = true;
      return;
    }

    let slotPrice = this.selectedSlot.price;
    let equipPriceTotal = 0;

    MockData.equipments.forEach(eq => {
      const qty = this.selectedEquipments[eq.id] || 0;
      equipPriceTotal += qty * eq.price;
    });

    const totalAmount = slotPrice + equipPriceTotal;

    summarySlot.textContent = `Sân 01 | ${this.selectedSlot.start_time} - ${this.selectedSlot.end_time}`;
    summaryTotal.textContent = `${totalAmount.toLocaleString('vi-VN')} VNĐ (Cọc: 50,000đ)`;
    btnProceed.disabled = false;
  }

  proceedToCheckout() {
    if (!this.currentUser) {
      this.showToast("⚠️ Vui lòng Đăng Nhập hoặc Đăng Ký tài khoản trước khi thực hiện Đặt Sân & Thanh Toán!", "error");
      this.navigateTo('ui-01');
      return;
    }
    this.navigateTo('ui-04');
    this.startHoldTimer();
    this.showToast("Hệ thống đã kích hoạt Redis Atomic Lock giữ chỗ slot giờ trong 10:00 phút!");
  }

  /* ------------------------------------------------------------------------
     4. UI 04: COUNTDOWN TIMER & VNPAY QR PAYMENT
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
        this.showToast("Hết thời gian giữ chỗ! Slot giờ đã giải phóng.", 'error');
        this.navigateTo('ui-03');
      }
    }, 1000);
  }

  simulatePaymentSuccess() {
    clearInterval(this.holdTimer);
    this.showToast("Cổng thanh toán VNPay đã gửi Webhook IPN! Xác nhận cọc 50,000đ thành công.");
    this.navigateTo('ui-05');
  }

  /* ------------------------------------------------------------------------
     5. UI 05: ELECTRONIC TICKET QR & ORDER HISTORY
     ------------------------------------------------------------------------ */
  renderBookingOrdersList() {
    const container = document.getElementById('booking-orders-list-container');
    let html = '';

    MockData.booking_orders.forEach(order => {
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
              <div style="font-size: 0.85rem; color: var(--text-muted);"><strong>Chi tiết:</strong> ${order.court_name} | Khung giờ: ${order.slot_time} | Ngày: ${order.booking_date}</div>
              <div style="font-size: 0.85rem; margin-top: 0.25rem;"><strong>Mã Vé QR Check-in:</strong> <code style="color: var(--accent-cyan); font-weight: 700;">${order.qr_ticket_code}</code></div>
              <div style="margin-top: 0.75rem; font-size: 0.9rem;">Tổng đơn: <strong>${order.total_amount.toLocaleString('vi-VN')}đ</strong> | Đã cọc: <span style="color: var(--primary); font-weight: 700;">50,000đ</span></div>
            </div>
          </div>
        </div>
      `;
    });

    if (container) container.innerHTML = html;
  }

  /* ------------------------------------------------------------------------
     6. UI 06 & UI 07: AI MATCHMAKING & CHAT GROUP
     ------------------------------------------------------------------------ */
  renderMatchmakingRooms() {
    const container = document.getElementById('matchmaking-rooms-grid');
    let html = '';

    MockData.matchmaking_rooms.forEach(room => {
      html += `
        <div class="facility-card">
          <div class="facility-body">
            <div>
              <span class="elo-badge">ELO ${room.required_elo_min} - ${room.required_elo_max}</span>
              <h3 style="margin-top: 0.5rem;">${room.room_name}</h3>
              <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px;">
                <i class="fa-solid fa-map-pin"></i> ${room.facility_name}<br>
                <i class="fa-solid fa-clock"></i> ${room.match_date} (${room.match_time})
              </p>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1rem; border-top: 1px solid var(--border-color); padding-top: 0.75rem;">
              <span style="font-size: 0.85rem;"><i class="fa-solid fa-users text-primary"></i> ${room.current_players}/${room.max_players} Thành viên</span>
              <button class="btn btn-accent btn-sm" onclick="app.openRoomChat(${room.id})">
                <i class="fa-solid fa-comments"></i> Vào Phòng Chat
              </button>
            </div>
          </div>
        </div>
      `;
    });

    if (container) container.innerHTML = html;
  }

  openRoomChat(roomId) {
    this.activeRoom = MockData.matchmaking_rooms.find(r => r.id === roomId);
    document.getElementById('room-detail-title').textContent = this.activeRoom.room_name;
    this.renderChatMessages();
    this.navigateTo('ui-07');
  }

  renderChatMessages() {
    const container = document.getElementById('chat-messages-list');
    let html = '';

    this.activeRoom.chat_messages.forEach(msg => {
      const isSent = msg.sender === this.currentUser.name;
      html += `
        <div class="chat-msg ${isSent ? 'sent' : 'received'}">
          <div style="font-size: 0.7rem; font-weight: 700; opacity: 0.8;">${msg.sender} • ${msg.time}</div>
          <div>${msg.text}</div>
        </div>
      `;
    });

    if (container) {
      container.innerHTML = html;
      container.scrollTop = container.scrollHeight;
    }
  }

  sendChatMessage(e) {
    e.preventDefault();
    const input = document.getElementById('chat-input-text');
    const text = input.value.trim();
    if (!text) return;

    this.activeRoom.chat_messages.push({
      sender: this.currentUser.name,
      text: text,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    });

    input.value = '';
    this.renderChatMessages();
  }

  openCreateRoomModal() {
    const modalBody = document.getElementById('modal-body');
    modalBody.innerHTML = `
      <h3>Tạo Phòng Ghép Matchmaking Mới</h3>
      <form onsubmit="app.handleCreateRoom(event)" style="margin-top: 1rem;">
        <div class="form-group">
          <label class="form-label">Tên Phòng Ghép</label>
          <input type="text" id="modal-room-name" class="form-control" value="Giao lưu Săn Kèo Đôi Nam/Nữ" required>
        </div>
        <div class="form-group">
          <label class="form-label">Dải ELO Yêu Cầu (Min - Max)</label>
          <div style="display: flex; gap: 0.5rem;">
            <input type="number" id="modal-elo-min" class="form-control" value="1400">
            <input type="number" id="modal-elo-max" class="form-control" value="1600">
          </div>
        </div>
        <button type="submit" class="btn btn-accent" style="width: 100%; margin-top: 1rem;">
          <i class="fa-solid fa-circle-check"></i> Khởi Tạo Phòng Ghép
        </button>
      </form>
    `;
    this.openModal();
  }

  handleCreateRoom(e) {
    e.preventDefault();
    const name = document.getElementById('modal-room-name').value;
    const minElo = parseInt(document.getElementById('modal-elo-min').value);
    const maxElo = parseInt(document.getElementById('modal-elo-max').value);

    MockData.matchmaking_rooms.push({
      id: Date.now(),
      room_name: name,
      facility_name: "Smashing Arena",
      match_date: "12/09/2026",
      match_time: "19:00 - 21:00",
      required_elo_min: minElo,
      required_elo_max: maxElo,
      match_type: "Đôi Nam/Nữ",
      current_players: 1,
      max_players: 4,
      status: "OPEN",
      host_name: this.currentUser.name,
      chat_messages: [{ sender: this.currentUser.name, text: "Phòng đã sẵn sàng, mời mọi người tham gia!", time: "vừa xong" }]
    });

    this.closeModal();
    this.renderMatchmakingRooms();
    this.showToast("Đã khởi tạo phòng ghép thành công!");
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
          <input type="text" id="add-fac-name" class="form-control" placeholder="VD: Sân Cầu Lông Tân Phú Cyber Arena" required>
        </div>
        <div class="form-group">
          <label class="form-label">Địa Chỉ Chi Nhánh (Số nhà, Đường, Phường, Quận)</label>
          <input type="text" id="add-fac-address" class="form-control" placeholder="VD: 55 Lê Trọng Tấn, Sơn Kỳ, Tân Phú, TP.HCM" required>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
          <div class="form-group">
            <label class="form-label">Vĩ Độ (Latitude)</label>
            <input type="text" id="add-fac-lat" class="form-control" value="10.8012" required>
          </div>
          <div class="form-group">
            <label class="form-label">Kinh Độ (Longitude)</label>
            <input type="text" id="add-fac-lng" class="form-control" value="106.6211" required>
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
    const lat = parseFloat(document.getElementById('add-fac-lat').value) || 10.8012;
    const lng = parseFloat(document.getElementById('add-fac-lng').value) || 106.6211;
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
    this.closeModal();
    this.renderAdminApprovals();
    this.renderAdminOverviewFacilities();
    this.showToast("Đã gửi đăng ký cụm sân mới thành công! Hồ sơ đang chờ Admin duyệt.");
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
            <button class="btn btn-secondary btn-sm" onclick="app.openEditCourtModal(${court.id})" title="Chỉnh Sửa Sân"><i class="fa-solid fa-pen"></i></button>
          </td>
        </tr>
      `;
    });

    if (tbody) tbody.innerHTML = html;
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
    const container = document.getElementById('leaflet-map-container');
    const fallbackBox = document.getElementById('owner-gps-map-box');

    if (typeof L === 'undefined') {
      if (container) container.style.display = 'none';
      if (fallbackBox) fallbackBox.style.display = 'block';
      return;
    }

    if (container) container.style.display = 'block';
    if (fallbackBox) fallbackBox.style.display = 'none';

    if (this.leafletMap) {
      setTimeout(() => this.leafletMap.invalidateSize(), 200);
      return;
    }

    // Khởi tạo bản đồ tương tác thực tế Leaflet (Sử dụng Esri World Street Map siêu nét, miễn phí 100%, không API key, không watermark)
    this.leafletMap = L.map('leaflet-map-container', {
      center: [10.8456, 106.7925],
      zoom: 15,
      zoomControl: true
    });

    const primaryTiles = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 19,
      attribution: '&copy; Esri, OpenStreetMap'
    });

    const fallbackTiles = L.tileLayer('https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png', {
      maxZoom: 19,
      subdomains: ['a', 'b', 'c'],
      attribution: '&copy; OpenStreetMap'
    });

    primaryTiles.addTo(this.leafletMap);

    let tileFallbackActivated = false;
    primaryTiles.on('tileerror', () => {
      if (!tileFallbackActivated && this.leafletMap) {
        tileFallbackActivated = true;
        this.leafletMap.removeLayer(primaryTiles);
        fallbackTiles.addTo(this.leafletMap);
      }
    });

    // Ghim đỏ tương tác dạng Marker Icon
    const customIcon = L.divIcon({
      className: 'leaflet-custom-marker',
      html: '<div style="width: 24px; height: 24px; background: #ef4444; border: 3px solid #ffffff; border-radius: 50%; box-shadow: 0 0 15px rgba(239, 68, 68, 0.9), 0 0 25px rgba(239, 68, 68, 0.6); transform: translate(-50%, -50%); animation: mapPinPulse 1.8s infinite;"></div>',
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    });

    this.leafletMarker = L.marker([10.8456, 106.7925], {
      icon: customIcon,
      draggable: true
    }).addTo(this.leafletMap);

    this.leafletMap.on('click', (e) => {
      const { lat, lng } = e.latlng;
      this.leafletMarker.setLatLng([lat, lng]);
      this.updateGPSCoordsDisplay(lat, lng);
    });

    this.leafletMarker.on('dragend', (e) => {
      const { lat, lng } = e.target.getLatLng();
      this.updateGPSCoordsDisplay(lat, lng);
    });

    setTimeout(() => this.leafletMap.invalidateSize(), 250);
  }

  moveMapToCoords(lat, lng, zoom = 16) {
    if (this.leafletMap) {
      this.leafletMap.setView([lat, lng], zoom);
      if (this.leafletMarker) {
        this.leafletMarker.setLatLng([lat, lng]);
      }
      this.updateGPSCoordsDisplay(lat, lng);
    }
  }

  async searchMapAddress(e) {
    if (e) e.preventDefault();
    const input = document.getElementById('map-search-address-input');
    if (!input || !input.value.trim()) return;

    const query = input.value.trim();
    this.showToast(`🔍 Đang tìm vị trí địa chỉ: "${query}"...`);

    // Các xã/phường & khu vực tại Thủ Đô Hà Nội
    const districtCoords = {
      'cầu giấy': { lat: 21.0333, lng: 105.7994, name: 'Phường Dịch Vọng (Cầu Giấy)' },
      'dịch vọng': { lat: 21.0333, lng: 105.7994, name: 'Phường Dịch Vọng (Cầu Giấy)' },
      'hoàn kiếm': { lat: 21.0285, lng: 105.8542, name: 'Quận Hoàn Kiếm' },
      'hàng bạc': { lat: 21.0338, lng: 105.8525, name: 'Phường Hàng Bạc (Hoàn Kiếm)' },
      'tràng tiền': { lat: 21.0252, lng: 105.8561, name: 'Phường Tràng Tiền' },
      'ba đình': { lat: 21.0341, lng: 105.8265, name: 'Quận Ba Đình' },
      'điện biên': { lat: 21.0315, lng: 105.8398, name: 'Phường Điện Biên (Ba Đình)' },
      'đống đa': { lat: 21.0125, lng: 105.8252, name: 'Quận Đống Đa' },
      'láng hạ': { lat: 21.0153, lng: 105.8152, name: 'Phường Láng Hạ (Đống Đa)' },
      'văn miếu': { lat: 21.0272, lng: 105.8356, name: 'Phường Văn Miếu' },
      'mỹ đình': { lat: 21.0285, lng: 105.7682, name: 'Phường Mỹ Đình (Nam Từ Liêm)' },
      'bách khoa': { lat: 21.0028, lng: 105.8475, name: 'Phường Bách Khoa (Hai Bà Trưng)' },
      'nhân chính': { lat: 21.0062, lng: 105.8085, name: 'Phường Nhân Chính (Thanh Xuân)' },
      'quảng an': { lat: 21.0645, lng: 105.8241, name: 'Phường Quảng An (Tây Hồ)' },
      'văn quán': { lat: 20.9812, lng: 105.7891, name: 'Phường Văn Quán (Hà Đông)' },
      'đông anh': { lat: 21.1412, lng: 105.8451, name: 'Xã Đông Anh' },
      'gia lâm': { lat: 21.0454, lng: 105.9125, name: 'Xã Gia Lâm' },
      'thanh trì': { lat: 20.9521, lng: 105.8412, name: 'Xã Thanh Trì' }
    };

    const qLower = query.toLowerCase();

    // Khớp nhanh tên quận/khu vực
    for (const key in districtCoords) {
      if (qLower === key || qLower.includes(key)) {
        const item = districtCoords[key];
        this.moveMapToCoords(item.lat, item.lng, 15);
        this.showToast(`🎯 Tìm thấy khu vực: ${item.name}!`);
        return;
      }
    }

    // Tra cứu qua OpenStreetMap Nominatim Geocoding API
    try {
      const searchUrl = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query + ', Hà Nội, Việt Nam')}`;
      const resp = await fetch(searchUrl);
      const data = await resp.json();

      if (data && data.length > 0) {
        const result = data[0];
        const lat = parseFloat(result.lat);
        const lng = parseFloat(result.lon);
        this.moveMapToCoords(lat, lng, 16);
        const displayName = result.display_name.split(',')[0];
        this.showToast(`🎯 Đã định vị: ${displayName}!`);
      } else {
        // Fallback: Tìm kiếm không đính kèm hậu tố
        const rawResp = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}`);
        const rawData = await rawResp.json();
        if (rawData && rawData.length > 0) {
          const lat = parseFloat(rawData[0].lat);
          const lng = parseFloat(rawData[0].lon);
          this.moveMapToCoords(lat, lng, 16);
          this.showToast(`🎯 Đã định vị: ${rawData[0].display_name.split(',')[0]}!`);
        } else {
          this.showToast(`⚠️ Không tìm thấy địa chỉ "${query}". Hãy thử gõ thêm tên quận hoặc đường!`);
        }
      }
    } catch (err) {
      console.warn("Lỗi tra cứu Nominatim:", err);
      this.showToast(`⚠️ Lỗi mạng tra cứu địa chỉ. Bạn vẫn có thể bấm/kéo nút ghim trên bản đồ!`);
    }
  }

  updateGPSCoordsDisplay(lat, lng) {
    const coordsText = document.getElementById('owner-gps-coords-text');
    if (coordsText) {
      coordsText.textContent = `${lat.toFixed(4)} N, ${lng.toFixed(4)} E`;
    }
    this.showToast(`📍 Đã ghim vị trí GPS mới: ${lat.toFixed(4)} N, ${lng.toFixed(4)} E!`);
  }

  zoomMapIn() {
    if (this.leafletMap) {
      this.leafletMap.zoomIn();
      return;
    }
    if (!this.mapZoomScale) this.mapZoomScale = 1.0;
    this.mapZoomScale = Math.min(this.mapZoomScale + 0.25, 3.0);
    this.updateMapZoomUI();
  }

  zoomMapOut() {
    if (this.leafletMap) {
      this.leafletMap.zoomOut();
      return;
    }
    if (!this.mapZoomScale) this.mapZoomScale = 1.0;
    this.mapZoomScale = Math.max(this.mapZoomScale - 0.25, 0.75);
    this.updateMapZoomUI();
  }

  resetMapZoom() {
    if (this.leafletMap) {
      this.leafletMap.setView([10.8456, 106.7925], 15);
      return;
    }
    this.mapZoomScale = 1.0;
    this.updateMapZoomUI();
  }

  handleMapWheel(e) {
    e.preventDefault();
    if (e.deltaY < 0) {
      this.zoomMapIn();
    } else {
      this.zoomMapOut();
    }
  }

  updateMapZoomUI() {
    const wrapper = document.getElementById('map-zoom-wrapper');
    const pin = document.getElementById('owner-map-pin');
    const text = document.getElementById('map-zoom-level-text');

    if (wrapper) {
      wrapper.style.transform = `scale(${this.mapZoomScale})`;
    }
    if (pin) {
      const counterScale = (1 / this.mapZoomScale).toFixed(3);
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
    const filter = this.currentMapSportFilter;

    let visibleCount = 0;
    const drawerListContainer = document.getElementById('map-drawer-facilities-list');
    let drawerHtml = '';

    facilities.forEach(fac => {
      const sport = fac.sport_type || 'badminton';
      if (filter !== 'all' && filter !== sport) return;

      visibleCount++;

      // Create Custom Pin Icon
      let iconEmoji = fac.sport_icon || '🏸';
      let pinClass = 'badminton';
      if (sport === 'pickleball') { pinClass = 'pickleball'; iconEmoji = '🎾'; }
      else if (sport === 'football') { pinClass = 'football'; iconEmoji = '⚽'; }
      else if (sport === 'basketball') { pinClass = 'basketball'; iconEmoji = '🏀'; }
      else if (sport === 'tennis') { pinClass = 'tennis'; iconEmoji = '🎾'; }
      else if (sport === 'multi') { pinClass = 'multi'; iconEmoji = '🏟️'; }

      const pinHtml = `
        <div class="sports-map-marker ${pinClass}" title="${fac.name}">
          <span class="sports-map-marker-icon">${iconEmoji}</span>
        </div>
      `;

      const customIcon = L.divIcon({
        className: 'custom-sports-pin',
        html: pinHtml,
        iconSize: [32, 32],
        iconAnchor: [16, 32],
        popupAnchor: [0, -32]
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
              <span style="color: #f59e0b; font-weight: 700;">⭐ ${fac.rating}</span>
            </div>
          </div>
        </div>
      `;
    });

    const countEl = document.getElementById('map-drawer-count');
    if (countEl) countEl.textContent = visibleCount;

    if (drawerListContainer) {
      drawerListContainer.innerHTML = drawerHtml || '<p style="text-align: center; color: #64748b; padding: 2rem;">Không tìm thấy sân phù hợp môn này.</p>';
    }
  }

  filterMapSport(sportType, btn) {
    this.currentMapSportFilter = sportType;

    document.querySelectorAll('.sport-chip').forEach(c => c.classList.remove('active'));
    if (btn) btn.classList.add('active');

    this.renderGoogleSportsMarkers();
    this.showToast(`Lọc bản đồ môn: ${sportType === 'all' ? 'Tất cả các môn' : sportType.toUpperCase()}`);
  }

  handleMapSearch(e) {
    const keyword = e.target.value.toLowerCase().trim();
    if (!keyword) {
      this.currentMapSportFilter = 'all';
      this.renderGoogleSportsMarkers();
      return;
    }

    if (this.googleSportsMap && this.sportsMarkerGroup) {
      this.sportsMarkerGroup.clearLayers();
      const facilities = MockData.facilities.filter(f => 
        f.name.toLowerCase().includes(keyword) || 
        f.address.toLowerCase().includes(keyword)
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
      }
    }
  }

  executeMapSearch() {
    const input = document.getElementById('map-explore-search-input');
    if (input) {
      this.handleMapSearch({ target: input });
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
          <input type="text" id="add-owner-facility-name" class="form-control" placeholder="VD: Sân Cầu Lông Tân Bình Sport" required>
        </div>
        <div class="form-group">
          <label class="form-label"><i class="fa-solid fa-location-dot text-primary"></i> Địa Chỉ Cụm Sân</label>
          <input type="text" id="add-owner-facility-address" class="form-control" value="102 Hoàng Văn Thụ, Phường 4, Quận Tân Bình, TP.HCM" required>
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

    if (!nameInput || !phoneInput || !facNameInput) return;

    const name = nameInput.value.trim();
    const phone = phoneInput.value.trim();
    const facName = facNameInput.value.trim();
    const facAddr = facAddrInput ? facAddrInput.value.trim() : 'TP. Hồ Chí Minh';

    const newFacId = MockData.facilities.length > 0 ? Math.max(...MockData.facilities.map(f => f.id)) + 1 : 101;
    const newFacility = {
      id: newFacId,
      name: facName,
      address: facAddr,
      latitude: 10.7900,
      longitude: 106.6600,
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
      role: 'OWNER',
      facility_id: newFacId,
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
    this.showToast(`🎉 ADMIN đã tạo thành công tài khoản Chủ Sân: ${name}!`);
  }

  saveNewStaff(e) {
    if (e) e.preventDefault();
    const nameInput = document.getElementById('add-staff-name');
    const phoneInput = document.getElementById('add-staff-phone');
    const facInput = document.getElementById('add-staff-facility');
    const roleInput = document.getElementById('add-staff-role');

    if (!nameInput || !phoneInput) return;

    const name = nameInput.value.trim();
    const phone = phoneInput.value.trim();
    const facility_id = parseInt(facInput ? facInput.value : 101);
    const role = roleInput ? roleInput.value : 'STAFF';

    const newId = MockData.users.length > 0 ? Math.max(...MockData.users.map(u => u.id)) + 1 : 1;
    const avatar = name.split(' ').pop().charAt(0).toUpperCase() || 'S';

    const newStaff = {
      id: newId,
      name: name + " (Thu Ngân)",
      phone: phone,
      role: role,
      facility_id: facility_id,
      avatar: avatar,
      is_approved: true,
      created_at: new Date().toLocaleDateString('vi-VN')
    };

    MockData.users.push(newStaff);
    if (typeof saveMockDataToLocalStorage === 'function') saveMockDataToLocalStorage();

    this.closeModal();
    this.renderOwnerStaff();
    this.showToast(`🎉 CHỦ SÂN đã tạo thành công tài khoản Thu Ngân: ${name}!`);
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
        <button class="btn btn-secondary btn-sm" style="margin-top: 1rem;" onclick="app.closeModal()">Đóng Camera</button>
      </div>
    `;

    this.openModal();

    setTimeout(() => {
      const statusEl = document.getElementById('qr-scan-status-text');
      if (statusEl) {
        statusEl.innerHTML = `<span style="color: var(--primary);">✅ Đã quét thành công mã QR: TICKET-BADMINTON-8899!</span>`;
      }
      setTimeout(() => {
        this.closeModal();
        this.searchPOSBooking("TICKET-BADMINTON-8899");
      }, 700);
    }, 1500);
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
    const order = MockData.booking_orders.find(o => o.booking_code === bookingCode);
    this.navigateTo('ui-16');

    if (order) {
      this.calculatePOSFinalAmount();
      this.showToast(`🧾 Đã chuyển thông tin đơn ${order.booking_code} sang màn hình Lập Hóa Đơn Check-out!`);
    }
  }

  calculatePOSFinalAmount() {
    const extraFee = parseInt(document.getElementById('pos-extra-fee').value) || 0;
    const overtimeMins = parseInt(document.getElementById('pos-overtime-mins').value) || 0;

    const overtimeBlocks = Math.ceil(overtimeMins / 15);
    const overtimeFee = overtimeBlocks * 23000;

    document.getElementById('pos-calc-extra').textContent = `${extraFee.toLocaleString('vi-VN')}đ`;
    document.getElementById('pos-calc-overtime').textContent = `${overtimeFee.toLocaleString('vi-VN')}đ`;

    const finalAmount = (122000 + extraFee + overtimeFee) - 50000;
    document.getElementById('pos-calc-final').textContent = `${finalAmount.toLocaleString('vi-VN')}đ`;
  }

  completePOSInvoice() {
    this.showToast("Đã lập hóa đơn POS & xuất file in hóa đơn thành công!");
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

  approveFacility(facId) {
    const fac = MockData.facilities.find(f => f.id === facId);
    if (fac) fac.is_approved = true;
    this.renderAdminApprovals();
    this.renderCustomerFacilities();
    this.renderAdminOverviewFacilities();
    this.showToast("Đã phê duyệt cụm sân thành công! Cụm sân đã hiển thị công khai.");
  }

  rejectFacility(facId) {
    MockData.facilities = MockData.facilities.filter(f => f.id !== facId);
    this.renderAdminApprovals();
    this.renderAdminOverviewFacilities();
    this.showToast("Đã gửi yêu cầu từ chối kèm lý do sửa đổi tới Chủ sân.", 'error');
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
    modalBody.innerHTML = `
      <div style="text-align: left;">
        <h3 style="color: var(--primary); display: flex; align-items: center; gap: 8px;">
          <i class="fa-solid fa-id-card"></i> Chi Tiết Tài Khoản #${u.id}
        </h3>
        <hr style="border-color: var(--border-color); margin: 0.75rem 0;">
        <div style="display: flex; flex-direction: column; gap: 0.5rem; font-size: 0.9rem;">
          <div><strong>Họ và tên:</strong> <span style="color: var(--text-main); font-weight: 700;">${u.name}</span></div>
          <div><strong>Số điện thoại / Login:</strong> <code style="color: var(--accent-cyan); font-weight: 700;">${u.phone}</code></div>
          <div><strong>Phân hệ vai trò:</strong> <span class="tag-badge tag-ai">${u.role}</span></div>
          <div><strong>Trình độ ELO:</strong> <span style="color: #f59e0b; font-weight: 700;">${u.elo_rating || 'N/A'} ELO</span></div>
          <div><strong>Trạng thái phê duyệt:</strong> ${isApproved ? '<span style="color: var(--primary); font-weight: bold;">✅ Đã kích hoạt (Active)</span>' : '<span style="color: #ef4444; font-weight: bold;">⏳ Chờ duyệt</span>'}</div>
          <div><strong>Ngày khởi tạo:</strong> ${u.created_at || 'Khởi tạo hệ thống'}</div>
        </div>
        <div style="display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 1.5rem; border-top: 1px solid var(--border-color); padding-top: 1rem;">
          <button class="btn btn-secondary btn-sm" onclick="app.closeModal()">Đóng</button>
          <button class="btn btn-danger btn-sm" onclick="app.closeModal(); app.deleteUserAccount(${u.id});">
            <i class="fa-solid fa-trash-can"></i> Xóa Tài Khoản Này
          </button>
        </div>
      </div>
    `;
    this.openModal();
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
     10. GEMINI AI ASSISTANT DRAWER INTEGRATION & RENDER
     ------------------------------------------------------------------------ */
  toggleGeminiDrawer() {
    const drawer = document.getElementById('gemini-chat-drawer');
    drawer.classList.toggle('active');
  }

  promptGeminiAPIKey() {
    const currentKey = geminiAI.getAPIKey();
    const modalBody = document.getElementById('modal-body');
    modalBody.innerHTML = `
      <h3>⚙️ Cấu Hình Gemini AI API Key</h3>
      <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px;">
        Nhập Google Gemini API Key của bạn để sử dụng mô hình AI <strong>Gemini 3.6 Flash</strong> chuẩn trực tiếp trên trình duyệt.
      </p>
      <form onsubmit="app.saveGeminiAPIKey(event)" style="margin-top: 1rem;">
        <div class="form-group">
          <label class="form-label">Gemini API Key</label>
          <input type="password" id="modal-gemini-key-input" class="form-control" value="${currentKey}" placeholder="AIzaSy..." required>
          <div style="font-size: 0.75rem; color: var(--text-dim); margin-top: 4px;">
            Chưa có key? <a href="https://aistudio.google.com/app/apikey" target="_blank" style="color: var(--accent-cyan);">Lấy API Key miễn phí tại Google AI Studio</a>
          </div>
        </div>
        <button type="submit" class="btn btn-accent" style="width: 100%; margin-top: 1rem;">
          <i class="fa-solid fa-floppy-disk"></i> Lưu API Key
        </button>
      </form>
    `;
    this.openModal();
  }

  saveGeminiAPIKey(e) {
    e.preventDefault();
    const key = document.getElementById('modal-gemini-key-input').value;
    geminiAI.setAPIKey(key);
    this.closeModal();
    this.showToast("Đã lưu Gemini API Key thành công!");
  }

  async handleGeminiSubmit(e) {
    e.preventDefault();
    const input = document.getElementById('gemini-input-text');
    const text = input.value.trim();
    if (!text) return;

    this.addGeminiChatMessage('user', text);
    input.value = '';

    // Hiển thị trạng thái đang suy nghĩ
    const typingId = this.addGeminiChatMessage('bot', '<i class="fa-solid fa-spinner fa-spin"></i> Smashing AI đang xử lý...');

    const reply = await geminiAI.generateResponse(text);
    this.renderFormattedGeminiMessage(typingId, reply);
  }

  renderFormattedGeminiMessage(msgId, fullText) {
    const msgDiv = document.getElementById(msgId);
    if (!msgDiv) return;

    const targetElement = msgDiv.children[1];
    
    // Parse LaTeX / Math ($> 295\text{ mm}$ -> > 295 mm) & Markdown Formatting
    let formatted = fullText
      // Xử lý các biểu thức toán LaTeX phổ biến
      .replace(/\$\s*\\?([><=]=?)\s*(\d+)\\text\{\s*(\w+)\}\s*\$/g, '$1 $2 $3')
      .replace(/\$([^\$]+)\$/g, (match, p1) => {
        return p1.replace(/\\text\{([^\}]+)\}/g, '$1').replace(/\\/g, '').trim();
      })
      // Chuyển đổi tiêu đề Markdown ###, ##, # thành khối tiêu đề đẹp mắt
      .replace(/^###\s*(.*$)/gim, '<div style="font-weight: 800; font-size: 0.95rem; margin-top: 0.6rem; margin-bottom: 0.25rem; color: var(--accent-cyan);">$1</div>')
      .replace(/^##\s*(.*$)/gim, '<div style="font-weight: 800; font-size: 1rem; margin-top: 0.6rem; margin-bottom: 0.25rem; color: var(--primary);">$1</div>')
      .replace(/^#\s*(.*$)/gim, '<div style="font-weight: 800; font-size: 1.1rem; margin-top: 0.6rem; margin-bottom: 0.25rem; color: var(--primary);">$1</div>')
      // Chuyển đổi **in đậm**
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      // Đổi dòng
      .replace(/\n/g, '<br>');

    targetElement.innerHTML = formatted;
    
    const container = document.getElementById('gemini-chat-messages');
    if (container) container.scrollTop = container.scrollHeight;
  }

  sendGeminiQuickPrompt(prompt) {
    const drawer = document.getElementById('gemini-chat-drawer');
    if (!drawer.classList.contains('active')) {
      drawer.classList.add('active');
    }
    const input = document.getElementById('gemini-input-text');
    input.value = prompt;
    
    // Tự động gửi prompt khi bấm nút gợi ý nhanh
    const form = document.getElementById('gemini-chat-form');
    if (form) {
      form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
    }
  }

  addGeminiChatMessage(sender, text) {
    const container = document.getElementById('gemini-chat-messages');
    const uniqueSuffix = Math.random().toString(36).substring(2, 8);
    const msgId = `gemini-msg-${Date.now()}-${uniqueSuffix}`;
    const isUser = sender === 'user';

    const msgDiv = document.createElement('div');
    msgDiv.className = `chat-msg ${isUser ? 'sent' : 'received'}`;
    msgDiv.id = msgId;
    msgDiv.innerHTML = `
      <div style="font-size: 0.7rem; font-weight: 700; color: ${isUser ? '#fff' : 'var(--accent-cyan)'}; margin-bottom: 2px;">${isUser ? 'Bạn' : 'Smashing Gemini AI'}</div>
      <div>${text}</div>
    `;

    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
    return msgId;
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
    document.getElementById('theme-icon').className = isLight ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
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

    // 2. Kiem tra mat khau chinh xac
    const expectedPassword = user.password || '123456';
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
      { key: 'facilities', label: '2. CỤM SÂN (facilities)', icon: 'fa-building-user', desc: 'Bảng 2: Danh sách 13 cụm cơ sở thể thao cầu lông tại TP.HCM & tọa độ GPS ghim vị trí' },
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
}

// Initialize Application when DOM ready
let app;
document.addEventListener('DOMContentLoaded', () => {
  app = new BadmintonAIApp();
  app.init();
});
