# Chatbot RAG BADMINTON.AI

Chatbot website (`js/chatbot.js`) gọi `/api/chat` trên `server.py`, dùng chung
`ChatbotService` với FastAPI `/api/v1/ai/chat`.

- Chính sách và hướng dẫn: tìm kiếm vector trong `documents` và `document_chunks`,
  lọc quyền truy cập, kiểm tra bằng chứng, đưa nội dung vào Gemini và trả nguồn.
- Giá, lịch trống, đơn đặt sân: lấy qua business tools từ cơ sở dữ liệu.
- Giữ chỗ và đặt sân: yêu cầu đăng nhập và xác nhận theo luồng hiện có.

## Khởi chạy

Chạy lệnh từ thư mục gốc dự án, với Python đã cài `requirements.txt`:

```powershell
python -m pip install -r requirements.txt
python server.py
```

Thiết lập `GEMINI_API_KEY` trong `.env` ở thư mục gốc. Xem `.env.example`
cho cấu hình model, số chiều embedding và ngưỡng tìm kiếm. Model tạo câu trả lời
và model embedding là hai cấu hình riêng. Phải chọn model mà tài khoản API có quyền dùng.

SQLite mặc định và SQLite dự phòng luôn dùng `badminton.db` ở gốc dự án,
kể cả khi khởi động FastAPI từ thư mục `backend`. Đường dẫn SQLite tương đối
được tính từ gốc dự án; đường dẫn tuyệt đối và PostgreSQL vẫn theo cấu hình.

## Cập nhật SRS

```powershell
python prepare_rag.py
python prepare_rag.py "duong-dan-tai-lieu.docx"
```

Mặc định dùng `extracted_doc.txt`. Lệnh dùng đúng document ID trả về từ bước
nạp tài liệu, không phụ thuộc ID cố định. Nội dung trùng và embedding cùng model
được tái sử dụng. Dùng `--force` khi cần tạo lại embedding; có phát sinh lượt gọi API.
Lệnh trả mã lỗi nếu tạo embedding thất bại hoặc chỉ hoàn tất một phần.

Tài liệu nạp bằng lệnh này có quyền `public`: chỉ dùng SRS/chính sách đã được phép
công khai. Tài liệu mới có nội dung khác được nạp riêng; quản trị viên cần quản lý
phiên bản cũ qua API tài liệu hiện có để tránh các chính sách mâu thuẫn cùng được truy xuất.

## Kiểm tra

```powershell
python -m unittest test_phase6_rag -q
```

Bộ kiểm thử này dùng embedding và LLM giả lập trong cơ sở dữ liệu riêng.
Nó kiểm tra luồng xử lý, quyền truy cập và trích dẫn; chất lượng tìm kiếm tiếng Việt
và khả năng kết nối Gemini cần kiểm tra thêm bằng API thật.
