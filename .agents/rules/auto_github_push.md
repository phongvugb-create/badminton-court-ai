# Rule: Tự Động Push Lên GitHub Sau Mỗi Lần Chỉnh Sửa

Mỗi khi có thay đổi code, thêm tính năng, fix lỗi hoặc theo yêu cầu chỉnh sửa từ người dùng:
1. Luôn kiểm tra `git status`.
2. Tự động chạy lệnh `git add .` và tạo commit với thông điệp rõ ràng theo chuẩn Conventional Commits (feat, fix, refactor, style...).
3. Tự động thực hiện `git push origin main` mà không cần đợi người dùng nhắc nhở thêm.
