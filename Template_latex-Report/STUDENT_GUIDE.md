# SỔ TAY THAO TÁC NHANH CHO SINH VIÊN (STUDENT GUIDE)
**Học phần: Phát triển ứng dụng AI – Khoa CNTT, Trường ĐH CNTT & TT (ICTU)**

Tài liệu hướng dẫn tra cứu nhanh các thao tác thường dùng khi làm báo cáo với Template LaTeX.

---

### 1. Bảng tra cứu tác vụ nhanh

| Mục đích muốn làm | Vị trí tệp cần chỉnh sửa | Ghi chú quan trọng |
| :--- | :--- | :--- |
| **Đổi tên đề tài, tên SV, GV, Mã SV, Lớp** | `config/metadata.tex` | Không sửa trong `cover.tex` |
| **Viết nội dung Chương 1 (Tổng quan)** | `chapters/chapter1.tex` | Xóa các gợi ý TODO và viết nội dung đề tài của bạn |
| **Viết nội dung Chương 2 (Cơ sở lý thuyết)** | `chapters/chapter2.tex` | Đưa công thức toán, thuật toán AI vào đây |
| **Viết nội dung Chương 3 (Thiết kế hệ thống)** | `chapters/chapter3.tex` | Vẽ sơ đồ kiến trúc, luồng xử lý và chèn hình |
| **Viết nội dung Chương 4 (Triển khai & Kết quả)** | `chapters/chapter4.tex` | Đưa code huấn luyện, bảng kết quả định lượng |
| **Viết nội dung Chương 5 (Kết luận)** | `chapters/chapter5.tex` | Đánh giá ưu nhược điểm, hướng mở rộng |
| **Thêm hình ảnh mới** | Đặt file vào `figures/` | Chèn bằng `\insertfigure` hoặc `\begin{figure}` |
| **Thêm bảng số liệu mới** | Viết trực tiếp hoặc đặt trong `tables/` | Dùng chuẩn `booktabs` (`\toprule`, `\midrule`, `\bottomrule`) |
| **Thêm tài liệu tham khảo mới** | `references.bib` | Copy định dạng BibTeX từ Google Scholar / IEEE Xplore |
| **Trích dẫn tài liệu trong bài viết** | Sử dụng lệnh `\cite{khoa_trich_dan}` | Tuyệt đối không gõ thủ công [1], [2] |
| **Thêm từ viết tắt** | `frontmatter/abbreviations.tex` | Thêm hàng vào bảng viết tắt |
| **Thêm thuật ngữ chuyên ngành** | `frontmatter/glossary.tex` | Thêm hàng vào bảng 4 cột: Thuật ngữ, Tiếng Anh, Viết tắt, Giải thích |
| **Viết mã nguồn / link GitHub** | `appendices/appendixA.tex` | Cung cấp link repo và sơ đồ thư mục |
| **Viết hướng dẫn cài đặt và chạy app** | `appendices/appendixB.tex` | Viết các lệnh bash / shell chi tiết |

---

### 2. Các cú pháp thường dùng nhất (Copy & Paste)

#### A. Chèn hình ảnh
```latex
\insertfigure[width=0.85\linewidth]{figures/chapter3/ten_anh.png}{Chú thích chi tiết cho hình}{fig:nhan_hinh}

% Trong văn bản, tham chiếu bằng:
Như thể hiện trong \cref{fig:nhan_hinh}, kiến trúc mô hình gồm...
```

#### B. Chèn bảng biểu học thuật
```latex
\begin{table}[htbp]
\centering
\caption{Đánh giá kết quả trên tập kiểm thử}
\label{tab:ket_qua}
\begin{tabular}{lccc}
    \toprule
    \textbf{Thuật toán} & \textbf{Precision} & \textbf{Recall} & \textbf{F1-Score} \\
    \midrule
    Mô hình A & 88.5\% & 87.2\% & 87.8\% \\
    Mô hình B & 92.1\% & 91.8\% & 91.9\% \\
    \bottomrule
\end{tabular}
\end{table}

% Trong văn bản, tham chiếu bằng:
Số liệu so sánh chi tiết được trình bày tại \cref{tab:ket_qua}.
```

#### C. Công thức toán học
```latex
\begin{equation}
    \text{Accuracy} = \frac{TP + TN}{TP + TN + FP + FN}
    \label{eq:accuracy}
\end{equation}

% Trong văn bản, tham chiếu bằng:
Độ chính xác được xác định theo \cref{eq:accuracy}.
```

#### D. Trích dẫn tài liệu IEEE
```latex
Theo nghiên cứu của He và các cộng sự \cite{he2016deep}, mạng nơ-ron...
Kiến trúc Transformer đã chứng minh hiệu quả vượt trội trong thị giác máy tính \cite{vaswani2017attention}.
```

#### E. Chèn đoạn mã Python
```latex
\begin{lstlisting}[language=Python, caption={Hàm chuẩn hóa ảnh}, label={lst:preprocess}]
def preprocess_image(image_path):
    img = Image.open(image_path).convert('RGB')
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
    ])
    return transform(img).unsqueeze(0)
\end{lstlisting}
```

---

### 3. Những lỗi cần tránh tuyệt đối
1. **KHÔNG** chỉnh sửa file `main.tex` trừ khi bạn muốn thêm chương mới.
2. **KHÔNG** sao chép hình ảnh chụp bảng từ Microsoft Word sang chèn vào LaTeX. Hãy dùng mã lệnh LaTeX table.
3. **KHÔNG** gõ số chương, số hình, số bảng bằng tay (ví dụ: gõ "xem Hình 3.1"). Hãy dùng `\cref{fig:...}` để LaTeX tự động quản lý số thứ tự.
4. **KHÔNG** quên chọn compiler là **XeLaTeX** trên Overleaf hoặc IDE máy tính cá nhân.
