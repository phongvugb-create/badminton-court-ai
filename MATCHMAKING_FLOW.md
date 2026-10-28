# Phòng ghép kèo và thông báo

- Tạo phòng: máy chủ cấp số phòng ổn định. Số hiện ở thẻ phòng, tiêu đề chat,
  thông báo và thông báo tạo thành công. Số phòng khác số sân thi đấu.
- Mở lại phòng: nút **Phòng đã tham gia** trong AI Ghép Kèo, kể cả phòng đã đủ người.
  Không khôi phục khối “Phòng ghép của bạn” đã bỏ trước đó.
- Tham gia: danh sách, trang phòng và lời mời đều dùng API
  `POST /api/matchmaking/rooms/{id}/join`. Máy chủ xác minh đăng nhập,
  lời mời phòng riêng, cấp bậc, trạng thái và sức chứa theo bản ghi mới nhất.
  Tham gia lại không thêm người hay tạo thông báo trùng.
- Người mới vào: máy chủ lưu thông báo tên người và số phòng cho những thành viên
  hiện có, gồm chủ phòng. Không thông báo cho chính người vừa vào.
- Nhắn tin: máy chủ lấy danh tính người gửi từ tài khoản xác thực, lưu tin nhắn
  và thông báo cho các thành viên khác. Gửi lại cùng message ID không tạo bản sao.
- Người đang mở website ở màn hình khác nhận toast, âm báo và badge chuông qua
  đồng bộ máy chủ khoảng 3 giây/lần. Chat đang mở có thêm SSE để cập nhật tin nhắn.
  Bấm **Mở phòng** trong thông báo để đọc và đánh dấu thông báo phòng đã xem.
- Thông báo chưa đọc được lưu, có thể xem lại sau đăng nhập/tải lại. Đây là
  thông báo trong website; không có push tới hệ điều hành khi đóng trình duyệt.
- Tin chưa gửi được có nút gửi lại; bản nháp lỗi không bị tải lên trong bản lưu
  database thông thường và được giữ khi có bản đồng bộ mới.

## Kiểm thử

```powershell
python -m unittest test_room_notifications -q
node test_room_ui.cjs
node test_room_sync.cjs
```

Kiểm thử HTTP dùng JWT thật cho các tài khoản giả lập, máy chủ loopback và kho
dữ liệu trong RAM, không tạo tin nhắn/thông báo trong dữ liệu sử dụng thật.
Bao gồm cuộc đua giành chỗ cuối, gửi lại, quyền thành viên, cùng tên khác ID,
thông báo mọi thành viên còn lại, trạng thái đã đọc và số phòng ổn định.

Máy chủ `server.py` hiện chạy một tiến trình có nhiều luồng; khóa tham gia
và cấp số bảo vệ các yêu cầu đồng thời trong tiến trình đó. Nếu triển khai nhiều
tiến trình/instance, cần chuyển giao dịch/khóa sang cơ sở dữ liệu dùng chung và
SSE sang pub/sub dùng chung trước khi mở rộng.
