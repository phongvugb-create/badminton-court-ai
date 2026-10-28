# DANH SÁCH KIỂM TRA TRƯỚC KHI NỘP BÁO CÁO (CHECKLIST)
**Học phần: Phát triển ứng dụng AI – Khoa CNTT, Trường ĐH CNTT & TT (ICTU)**

Sinh viên hãy in hoặc rà soát kỹ lưỡng từng mục dưới đây trước khi xuất bản file PDF cuối cùng để nộp cho Giảng viên hướng dẫn và Khoa.

---

### 1. Thông tin định danh và trang bìa (Metadata)
- [ ] Đúng tên đề tài (khớp chính xác với tên đề tài đã đăng ký).
- [ ] Đúng họ và tên sinh viên thực hiện.
- [ ] Đúng mã sinh viên (MSSV).
- [ ] Đúng tên lớp sinh hoạt/chuyên ngành.
- [ ] Đúng học hàm, học vị và họ tên Giảng viên hướng dẫn.
- [ ] Năm báo cáo chính xác (2026).
- [ ] Logo ICTU hiển thị sắc nét, không bị méo tỷ lệ.
- [ ] Trang bìa không xuất hiện số trang.

### 2. Bố cục và phần đầu báo cáo (Frontmatter)
- [ ] Đã ký và ghi rõ họ tên ở phần **Lời cam đoan**.
- [ ] Đã viết nội dung hoàn chỉnh cho **Lời cảm ơn**.
- [ ] Đã có phần **Tóm tắt báo cáo** kèm danh sách Từ khóa (Keywords).
- [ ] Đã cập nhật đầy đủ các từ viết tắt được sử dụng trong báo cáo tại **Danh mục từ viết tắt**.
- [ ] Đã giải thích các khái niệm quan trọng tại **Danh mục thuật ngữ**.
- [ ] Có **Mục lục** tự động hiển thị đầy đủ Chapter, Section, Subsection.
- [ ] Có **Danh mục hình ảnh** tự động cập nhật đúng số trang.
- [ ] Có **Danh mục bảng biểu** tự động cập nhật đúng số trang.
- [ ] Số trang phần đầu đánh số La Mã thường: i, ii, iii...

### 3. Nội dung chuyên môn và chất lượng học thuật
- [ ] Đã xóa toàn bộ các ghi chú hướng dẫn mẫu (`% TODO`) trong các chương.
- [ ] Nội dung các chương phân chia rành mạch từ Chương 1 đến Chương 5.
- [ ] Bố cục cân đối: không có chương quá ngắn (dưới 2 trang) hoặc quá dài lệch chuẩn.
- [ ] Các công thức toán học quan trọng đều nằm trong môi trường `equation` và được đánh số tự động.
- [ ] Đã loại bỏ các từ ngữ văn nói, sử dụng văn phong khoa học, khách quan, chính xác.

### 4. Quản lý hình ảnh và bảng biểu
- [ ] Tất cả các hình ảnh đều có `\caption` tiếng Việt đặt ở phía **DƯỚI** hình.
- [ ] Tất cả các bảng biểu đều có `\caption` tiếng Việt đặt ở phía **TRÊN** bảng.
- [ ] Mọi hình ảnh và bảng biểu đều được dẫn nhập/tham chiếu rõ ràng trong bài viết bằng lệnh `\cref{}` hoặc `\ref{}` (không để hình/bảng đứng trôi nổi mà không được phân tích).
- [ ] Bảng biểu tuân thủ chuẩn `booktabs` (`\toprule`, `\midrule`, `\bottomrule`), không có đường kẻ dọc.
- [ ] Không có hình ảnh nào bị méo tỷ lệ (aspect ratio).
- [ ] Không có hình ảnh hoặc bảng nào bị tràn lề giấy (Overfull \hbox).

### 5. Mã nguồn và Phụ lục
- [ ] Mã nguồn Python được đưa vào môi trường `lstlisting` có tô màu cú pháp rõ ràng, không bị tràn dòng.
- [ ] Đã cung cấp đường link kho mã nguồn (GitHub / GitLab) công khai và còn hoạt động tại Phụ lục A.
- [ ] Có hướng dẫn cài đặt môi trường và các bước chạy ứng dụng rõ ràng tại Phụ lục B.

### 6. Tài liệu tham khảo và trích dẫn IEEE
- [ ] Toàn bộ tài liệu tham khảo được xuất chuẩn theo định dạng **IEEE** (sử dụng `IEEEtran`).
- [ ] Tất cả các citation trong bài đều sử dụng lệnh `\cite{...}`, tuyệt đối không gõ thủ công [1], [2].
- [ ] Không có mã trích dẫn nào bị lỗi thiếu (`[?]`).
- [ ] Không có tài liệu tham khảo nào trong danh mục mà không được trích dẫn trong nội dung.
- [ ] Thông tin tài liệu tham khảo đầy đủ tác giả, tên bài báo/sách, tạp chí/hội nghị, năm xuất bản, DOI hoặc URL.

### 7. Kỹ thuật biên dịch và xuất bản PDF
- [ ] Biên dịch thành công bằng **XeLaTeX** và **BibTeX** không còn lỗi nghiêm trọng (0 Errors).
- [ ] Đã kiểm tra không còn lỗi font tiếng Việt (không bị vỡ chữ, thiếu dấu hoặc ký tự lạ).
- [ ] Các siêu liên kết (hyperlinks) trong mục lục, hình, bảng, trích dẫn hoạt động trơn tru.
- [ ] File PDF xuất bản đạt kích thước hợp lý, chữ và hình hiển thị sắc nét khi in trên khổ A4.
