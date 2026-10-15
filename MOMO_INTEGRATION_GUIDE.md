# TÀI LIỆU HƯỚNG DẪN TÍCH HỢP MOMO PAYMENT GATEWAY (SANDBOX & LIVE READINESS)
## Hệ Thống Quản Lý & Cho Thuê Sân Cầu Lông Badminton.AI (Đề tài 36 - Phase 11.1)

---

### 1. KIẾN TRÚC TÍCH HỢP (PAYMENT ADAPTER, SERVICE & IPN ROUTE)

Hệ thống thanh toán MoMo trong Badminton.AI được thiết kế theo kiến trúc Adapter Pattern đảm bảo phân tách rõ ràng và bảo mật đa tầng:

```
+---------------------------------------------------------------------------------------+
|                                    TRÌNH DUYỆT KHÁCH HÀNG                              |
+---------------------------------------------------------------------------------------+
        |                                                                 ^
   1. Tạo đơn đặt sân & chọn MoMo                              5. Redirect về frontend
        v                                                                 |
+------------------------------+                                          |
| Python Web Server (Port 8085)|                                          |
| - index.html / js/app.js     |                                          |
| - Route: /payment/result     | -----------------------------------------+
+------------------------------+
        |
        | 2. Gọi API tạo giao dịch (Anti-IDOR / Cookie Auth)
        v
+---------------------------------------------------------------------------------------+
| FastAPI Backend Service (Port 8000)                                                   |
|                                                                                       |
|  [app.api.v1.payments.py]                                                             |
|       |                                                                               |
|       v                                                                               |
|  [PaymentService: create_payment_attempt()]                                           |
|       |                                                                               |
|       +---> MoMoPaymentAdapter (is_configured(), check_preflight(), is_production_blocked())
|       |          |                                                                    |
|       |          v                                                                    |
|       |     HMAC-SHA256 Canonical Request Signature                                  |
|       |     (accessKey, amount, extraData, ipnUrl, orderId, orderInfo,                |
|       |      partnerCode, redirectUrl, requestId, requestType)                        |
+-------+-------------------------------------------------------------------------------+
        |                                                                  ^
   3. POST /v2/gateway/api/create                                          |
   (Timeout >= 30s)                                                        | 6. Server-to-Server
        v                                                                  |    Instant Payment
+-------------------------------------------------------------+            |    Notification (IPN)
|              CỔNG THANH TOÁN MOMO GATEWAY                   |            |    POST /momo/ipn
|                  (SANDBOX / TEST)                           |            |
+-------------------------------------------------------------+            |
        |                                                                  |
        +-- 4. Trả về payUrl (Web / QR / App deeplink)                     |
        |                                                                  |
        +------------------------------------------------------------------+
```

* **MoMoPaymentAdapter** (`backend/app/services/payment_adapters/momo_adapter.py`):
  * Chịu trách nhiệm tạo chữ ký chuẩn canonical HMAC-SHA256 cho yêu cầu thanh toán (`payWithMethod`) và xác thực chữ ký callback IPN.
  * Đảm bảo fail-closed: chặn tuyệt đối môi trường production trong phase thử nghiệm.
  * Cung cấp cơ chế `check_preflight()` và `is_configured()` để kiểm tra biến môi trường trước khi gửi bất kỳ request mạng nào.
* **PaymentService** (`backend/app/services/payment_service.py`):
  * Xử lý logic nghiệp vụ: xác thực quyền sở hữu Booking (Anti-IDOR), kiểm tra số tiền hợp lệ [1.000đ - 50.000.000đ], ghi nhận Payment record với trạng thái `PENDING`.
  * Xử lý webhook `process_momo_ipn()`: đối soát `partnerCode`, `orderId`, `amount`, kiểm tra chống hạ cấp trạng thái (downgrade prevention), xử lý callback trễ đối với booking đã bị hủy (`REQUIRES_RECONCILIATION`), và giữ tính lũy thừa (idempotency).
* **FastAPI IPN Route** (`backend/app/api/v1/payments.py`):
  * Endpoint: `POST /api/v1/payments/momo/ipn`.
  * Trả về HTTP `204 No Content` theo đúng hợp đồng của MoMo khi xử lý thành công hoặc nhận callback lặp.

---

### 2. PHÂN BIỆT MOCK TESTS VÀ LIVE SANDBOX

* **Bộ Test Adapter & Mock E2E (`backend/tests/`):**
  * File test: `test_phase7_4b_momo_adapter.py` (32 tests) và `test_phase7_4b_1_sandbox_e2e.py` (13 tests).
  * Mục tiêu: Xác thực toàn bộ thuật toán ký số canonicalization, kiểm tra chống giả mạo chữ ký (tampered signature), kiểm tra tính lũy thừa khi nhận IPN lặp, xử lý timeout, xử lý bất đồng bộ trong database, ngăn chặn race condition và chống hạ cấp trạng thái.
  * Môi trường chạy: Mock HTTP calls (không gọi ra gateway MoMo thật), sử dụng Mock credentials cô lập trong test context.
* **Live Sandbox:**
  * Chỉ được phép chạy khi đã có **Merchant Test Credentials thật** và **Public HTTPS Tunnel/Domain** đang hoạt động.
  * Kiểm thử giao dịch thật trên hệ sinh thái Sandbox của MoMo (ứng dụng MoMo Test, quét mã QR thật, nhận callback IPN thật từ server MoMo về backend).
  * Bắt buộc phải qua bước Preflight Gate trước khi thực hiện.

---

### 3. QUY TRÌNH ĐĂNG KÝ VÀ LẤY CREDENTIALS TEST TỪ MOMO

Khi bắt đầu giai đoạn tích hợp Live Sandbox, người quản trị cần thực hiện các bước sau:
1. Truy cập cổng MoMo Developer: `https://developers.momo.vn` hoặc Merchant Portal Sandbox `https://business.momo.vn`.
2. Đăng ký/Đăng nhập tài khoản đối tác doanh nghiệp hoặc cá nhân phát triển.
3. Tạo ứng dụng mới với phương thức thanh toán **Cổng thanh toán (All-in-one / Pay with MoMo)**.
4. Lấy bộ thông tin kết nối Sandbox:
   * **Partner Code** (Mã đối tác, ví dụ: `MOMOBK...`)
   * **Access Key** (Khóa truy cập API)
   * **Secret Key** (Khóa bí mật dùng để sinh chữ ký số HMAC-SHA256)
5. Cài đặt ứng dụng **MoMo Test** trên thiết bị di động (Android APK hoặc iOS TestFlight do MoMo cung cấp) và sử dụng số điện thoại test có số dư tiền ảo Sandbox để quét mã QR / kiểm thử thanh toán.

---

### 4. HƯỚNG DẪN CẤU HÌNH BIẾN MÔI TRƯỜNG (.env)

Sau khi được cấp credentials, cập nhật các biến sau trong file `.env` tại thư mục gốc:

```bash
# MoMo Payment Gateway Configuration
MOMO_ENVIRONMENT=sandbox
MOMO_PARTNER_CODE=<partner_code_duoc_cap>
MOMO_ACCESS_KEY=<access_key_duoc_cap>
MOMO_SECRET_KEY=<secret_key_duoc_cap>
MOMO_ENDPOINT=https://test-payment.momo.vn
MOMO_REDIRECT_URL=https://<public-domain-cua-ban>/payment/result
MOMO_IPN_URL=https://<public-domain-cua-ban>/api/v1/payments/momo/ipn
MOMO_PARTNER_NAME=Badminton AI
MOMO_STORE_ID=BadmintonCourt01
MOMO_TIMEOUT_SECONDS=30.0
```

> **Lưu ý an toàn:**
> - Tuyệt đối không commit file `.env` chứa credentials thật lên Git.
> - Giữ `MOMO_ENVIRONMENT=sandbox` và `PAYMENT_PENDING_EXPIRY_ENABLED=False`.

---

### 5. CẤU HÌNH PUBLIC HTTPS TUNNEL / REVERSE PROXY

Cổng MoMo yêu cầu cả `redirectUrl` và `ipnUrl` phải là **Public HTTPS**. Khi chạy local thử nghiệm, có thể sử dụng Cloudflare Tunnel hoặc ngrok.

#### A. Sử dụng Cloudflare Tunnel (Khuyên dùng)
```bash
cloudflared tunnel --url http://localhost:8000
```
Sau đó lấy URL HTTPS được cấp (ví dụ: `https://badminton-api.yourdomain.com`).

#### B. Quy tắc Định Tuyến Reverse Proxy (Nginx / Caddy / Cloudflare)
Nếu sử dụng 1 domain duy nhất cho cả Frontend và API:
* **Mọi request tiền tố `/api/`**: Chuyển tiếp (proxy_pass) về Backend FastAPI (`http://localhost:8000`).
* **Các request còn lại**: Chuyển tiếp về Web Server (`http://localhost:8085`).
* **Đặc biệt lưu ý**: Webhook IPN tại `/api/v1/payments/momo/ipn` phải chuyển thẳng đến FastAPI, tuyệt đối không để Web Server trả về trang HTML 404 hoặc Single Page Application `index.html`.

---

### 6. MAPPING ROUTING & PORT HIỆN TẠI TRONG REPOSITORY

* **Web Frontend (Python Server / Next.js):**
  * Port Host: `8085` (Container port: `8085`)
  * Result Page: `/payment/result` (tự động load Single Page Application `view-ui-payment-result` và kiểm tra trạng thái đơn qua `/api/payment/status`).
* **FastAPI Backend:**
  * Port Host: `8000` (Container port: `8000`)
  * Endpoint IPN: `POST /api/v1/payments/momo/ipn` (nhận webhook server-to-server từ MoMo, không yêu cầu browser cookie auth, xác thực bằng HMAC-SHA256 signature).
* **PostgreSQL:** Port Host `5433` -> Container `5432`.
* **Redis Lock:** Port Host `6379` -> Container `6379`.

---

### 7. CHECKLIST CHẠY LIVE SANDBOX E2E

Trước khi thực hiện giao dịch thử nghiệm đầu tiên, kiểm tra các bước sau:

1. [ ] **Preflight Check:** Chạy lệnh kiểm tra cấu hình:
   ```bash
   python -c "from app.services.payment_adapters.momo_adapter import MoMoPaymentAdapter; print(MoMoPaymentAdapter().check_preflight())"
   ```
   Kết quả phải trả về `status: PASS`.
2. [ ] **Chạy toàn bộ unit/mock test:** Đảm bảo 45/45 test passed.
3. [ ] **Tạo giao dịch Sandbox có kiểm soát:**
   * Khách hàng đăng nhập trên giao diện web hoặc gọi endpoint `/api/v1/payments/create-attempt`.
   * Nhận `pay_url` từ MoMo Sandbox.
4. [ ] **Thực hiện thanh toán:**
   * Dùng app MoMo Sandbox quét QR Code hoặc đăng nhập web test.
   * Xác nhận thanh toán với số tiền thử nghiệm (ví dụ: 40.000 VNĐ).
5. [ ] **Xác minh IPN:**
   * Kiểm tra log backend: MoMo gửi POST tới `/api/v1/payments/momo/ipn`.
   * Chữ ký HMAC-SHA256 hợp lệ.
   * Database chuyển trạng thái Booking sang `CONFIRMED` và Payment sang `SUCCESS`.
   * Backend trả về `204 No Content` trong vòng dưới 15 giây.
6. [ ] **Kiểm tra tính Idempotent:**
   * Gửi lại payload IPN tương tự (hoặc MoMo retry), backend xác nhận `payment_processed` mà không nhân đôi số dư hay tạo bản ghi thừa.
7. [ ] **Xác minh Redirect Frontend:**
   * Trình duyệt chuyển hướng về `/payment/result?orderId=...&resultCode=0`.
   * Frontend hiển thị màn hình thanh toán thành công và vé QR Code điện tử cho khách hàng.

---

### 8. HƯỚNG XỬ LÝ TIMEOUT VÀ ĐỐI SOÁT (RECONCILIATION)

* **Không bao giờ tạo giao dịch mới mù quáng:** Khi một request tạo thanh toán gặp timeout từ gateway MoMo, hệ thống đánh dấu trạng thái `TIMEOUT` kèm `request_id` tương ứng. Không tự ý retry tạo mã `request_id` mới nếu người dùng chưa chủ động thao tác lại.
* **Đối soát bất đồng bộ (Reconciliation):**
  * Nếu MoMo IPN gửi sau khi booking đã bị hủy do timeout, hệ thống chuyển giao dịch sang trạng thái `REQUIRES_RECONCILIATION` và cảnh báo quản trị viên, không tự động khôi phục booking bị hủy để tránh xung đột slot sân.
  * Khi giao dịch đã `SUCCESS`, các callback thất bại đến sau sẽ bị từ chối chuyển trạng thái (Downgrade Prevention).

---

### 9. ĐIỀU KIỆN TIÊN QUYẾT TRƯỚC KHI LÊN PRODUCTION

Tuyệt đối không kích hoạt môi trường Production cho đến khi:
1. Ký hợp đồng thương mại điện tử chính thức với Công ty Cổ phần Dịch vụ Di động Trực tuyến (M_Service / MoMo).
2. Được cấp bộ Merchant Production Credentials (Partner Code, Access Key, Secret Key riêng biệt của Production).
3. Đăng ký Domain chính thức có chứng chỉ SSL/TLS hợp lệ (HTTPS đạt chuẩn).
4. Thực hiện đối soát tài khoản ngân hàng thụ hưởng thực tế.
5. Kiểm toán bảo mật toàn bộ hệ thống (Security & Penetration Audit).
6. Bật cờ cấu hình và bỏ chặn production theo lộ trình phát hành chính thức.
