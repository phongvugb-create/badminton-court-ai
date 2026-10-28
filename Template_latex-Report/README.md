# BỘ TEMPLATE LATEX BÁO CÁO HỌC PHẦN: PHÁT TRIỂN ỨNG DỤNG AI
**Khoa Công nghệ Thông tin – Trường Đại học Công nghệ Thông tin và Truyền thông (ICTU)**

Bộ template LaTeX chuyên nghiệp, thiết kế theo kiến trúc module hóa (modular architecture), tuân thủ chặt chẽ tiêu chuẩn trình bày văn bản khoa học và chuẩn trích dẫn quốc tế IEEE. Template được xây dựng để sinh viên có thể tái sử dụng dễ dàng cho mọi đề tài thuộc học phần **"Phát triển ứng dụng AI"**.

---

## 1. Yêu cầu công cụ biên dịch

- **Compiler chính:** `XeLaTeX`
  - *Lý do:* Hỗ trợ xử lý tiếng Việt Unicode toàn diện, quản lý font chữ tự nhiên qua `fontspec`, không phát sinh lỗi mã hóa font như pdfLaTeX.
- **Trình quản lý trích dẫn:** `BibTeX` (kết hợp với `IEEEtran.bst`).
- **Môi trường khuyến nghị:**
  - **Overleaf:** Nền tảng soạn thảo trực tuyến nhanh chóng, tiện lợi, không cần cài đặt.
  - **Máy tính cá nhân:** MiKTeX hoặc TeX Live kết hợp với VS Code (extension LaTeX Workshop) hoặc TeXstudio.

---

## 2. Quy trình biên dịch tài liệu

Để văn bản cập nhật đầy đủ Mục lục, Danh mục hình, Danh mục bảng và Tài liệu tham khảo IEEE, quy trình biên dịch gồm các bước sau:

### Biên dịch bằng dòng lệnh (Command Line)
```bash
# Bước 1: Biên dịch lần 1 để tạo file phụ trợ (.aux, .toc, .lof, .lot)
xelatex main.tex

# Bước 2: Biên dịch tài liệu tham khảo với BibTeX
bibtex main

# Bước 3: Biên dịch lần 2 để liên kết các mã trích dẫn
xelatex main.tex

# Bước 4: Biên dịch lần 3 để hoàn thiện số trang và liên kết chéo
xelatex main.tex
```

### Thiết lập trên Overleaf
1. Nén toàn bộ thư mục template thành file `.zip`.
2. Truy cập [Overleaf](https://www.overleaf.com), chọn **New Project** $\rightarrow$ **Upload Project** và tải file `.zip` lên.
3. Chọn biểu tượng **Menu** ở góc trên bên trái màn hình.
4. Tại mục **Compiler**, chuyển từ *pdfLaTeX* sang **XeLaTeX**.
5. Nhấn **Recompile** để xuất file PDF hoàn chỉnh.

---

## 3. Cấu trúc thư mục của dự án

```text
Template_latex-Report/
├── main.tex                    # File điều phối trung tâm (KHÔNG sửa nếu không cần thiết)
├── references.bib              # Cơ sở dữ liệu tài liệu tham khảo chuẩn BibTeX/IEEE
├── README.md                   # Hướng dẫn chi tiết kỹ thuật
├── STUDENT_GUIDE.md            # Sổ tay tóm tắt thao tác nhanh cho sinh viên
├── CHECKLIST.md                # Bảng kiểm tra trước khi nộp báo cáo
│
├── config/                     # Cấu hình hệ thống LaTeX
│   ├── packages.tex            # Khai báo các thư viện LaTeX
│   ├── formatting.tex          # Cấu hình font chữ, lề, giãn dòng, header/footer
│   ├── commands.tex            # Các lệnh hỗ trợ chèn hình, công thức, bảng biểu
│   └── metadata.tex            # THÔNG TIN ĐỀ TÀI & SINH VIÊN (SỬA Ở ĐÂY)
│
├── frontmatter/                # Phần đầu báo cáo (Đánh số La Mã)
│   ├── cover.tex               # Bìa báo cáo với khung viền chuẩn ICTU
│   ├── declaration.tex         # Lời cam đoan liêm chính học thuật
│   ├── acknowledgement.tex     # Lời cảm ơn
│   ├── abstract.tex            # Tóm tắt báo cáo và từ khóa
│   ├── abbreviations.tex       # Danh mục từ viết tắt
│   ├── glossary.tex            # Danh mục thuật ngữ (4 cột)
│   ├── tableofcontents.tex     # Tự động sinh Mục lục
│   ├── listoffigures.tex       # Tự động sinh Danh mục hình ảnh
│   └── listoftables.tex        # Tự động sinh Danh mục bảng biểu
│
├── chapters/                   # Nội dung chính của các chương (Đánh số Ả Rập)
│   ├── chapter1.tex            # Chương 1: Tổng quan về đề tài
│   ├── chapter2.tex            # Chương 2: Cơ sở lý thuyết và công nghệ
│   ├── chapter3.tex            # Chương 3: Phân tích và thiết kế ứng dụng AI
│   ├── chapter4.tex            # Chương 4: Triển khai và thực nghiệm
│   └── chapter5.tex            # Chương 5: Đánh giá và kết luận
│
├── appendices/                 # Các phụ lục bổ sung
│   ├── appendixA.tex           # Phụ lục A: Mã nguồn và cấu trúc kho chứa
│   ├── appendixB.tex           # Phụ lục B: Hướng dẫn cài đặt và vận hành
│   └── appendixC.tex           # Phụ lục C: Bảng siêu tham số và kết quả chi tiết
│
├── figures/                    # Thư mục lưu trữ hình ảnh
│   ├── logo/
│   │   └── ictu_logo.png       # Logo chính thức Trường ĐH CNTT & TT (ICTU)
│   ├── chapter1/
│   ├── chapter2/
│   ├── chapter3/
│   ├── chapter4/
│   └── appendix/
│
└── tables/                     # Thư mục chứa các module bảng biểu tách rời
    └── sample_table.tex        # Bảng mẫu độc lập
```

---

## 4. Hướng dẫn từng bước cho sinh viên

> **NGUYÊN TẮC VÀNG:** **KHÔNG sửa `main.tex` nếu không có yêu cầu đặc biệt.** Toàn bộ nội dung và thông tin của bạn được quản lý độc lập tại các file thành phần.

1. **Cập nhật thông tin đề tài:**
   - Mở file `config/metadata.tex`.
   - Chỉnh sửa tên đề tài (`\reporttitle`), họ tên sinh viên (`\studentname`), mã sinh viên (`\studentid`), lớp (`\studentclass`), giảng viên hướng dẫn (`\supervisor`).
2. **Thêm hình ảnh:**
   - Đưa file ảnh (`.png`, `.jpg`, `.pdf`) vào các thư mục tương ứng trong `figures/`.
   - Sử dụng lệnh tùy biến tiện lợi:
     ```latex
     \insertfigure[width=0.85\linewidth]{figures/chapter3/ten_anh.png}{Chú thích hình ảnh}{fig:nhan_hinh}
     ```
   - Hoặc chèn theo môi trường chuẩn:
     ```latex
     \begin{figure}[htbp]
         \centering
         \includegraphics[width=0.8\linewidth]{figures/chapter3/ten_anh.png}
         \caption{Chú thích của hình}
         \label{fig:nhan_hinh}
     \end{figure}
     ```
   - Tham chiếu hình trong văn bản: `\cref{fig:nhan_hinh}` $\rightarrow$ Tự động sinh `Hình X.Y`.
3. **Thêm bảng biểu học thuật:**
   - Sử dụng gói `booktabs` với các đường kẻ ngang: `\toprule`, `\midrule`, `\bottomrule`.
   - Tuyệt đối không dùng đường kẻ dọc dày đặc theo thói quen Word.
   - Caption bảng đặt ở **TRÊN** bảng:
     ```latex
     \begin{table}[htbp]
         \centering
         \caption{Bảng so sánh độ chính xác}
         \label{tab:so_sanh}
         \begin{tabular}{llr}
             \toprule
             \textbf{Mô hình} & \textbf{Tập dữ liệu} & \textbf{Độ chính xác} \\
             \midrule
             Baseline & CIFAR-10 & 82.5\% \\
             Proposed & CIFAR-10 & 91.8\% \\
             \bottomrule
         \end{tabular}
     \end{table}
     ```
   - Tham chiếu bảng trong văn bản: `\cref{tab:so_sanh}` $\rightarrow$ Tự động sinh `Bảng X.Y`.
4. **Công thức toán học:**
   - Viết công thức trong môi trường `equation`:
     ```latex
     \begin{equation}
         y = \sigma(\vect{w}^T \vect{x} + b)
         \label{eq:sigmoid}
     \end{equation}
     ```
   - Tham chiếu công thức: `\cref{eq:sigmoid}` $\rightarrow$ Tự động sinh `Phương trình (X.Y)`.
5. **Trích dẫn tài liệu tham khảo IEEE:**
   - Thêm entry vào file `references.bib` (được phân loại rõ: `@article`, `@inproceedings`, `@book`, `@misc`, `@techreport`).
   - Trích dẫn trong bài bằng lệnh: `\cite{he2016deep}` hoặc `\cite{he2016deep,vaswani2017attention}`.
   - Hệ thống tự động đánh số dạng `[1]`, `[1], [2]` hoặc `[1]--[3]`. Tuyệt đối không gõ thủ công `[1]`.
6. **Mã nguồn chương trình:**
   - Sử dụng môi trường `lstlisting` có sẵn style `pythonstyle`:
     ```latex
     \begin{lstlisting}[language=Python, caption={Hàm suy luận dự đoán}, label={lst:predict}]
     def predict(image, model):
         tensor = preprocess(image)
         return model(tensor).argmax(dim=1)
     \end{lstlisting}
     ```
7. **Thêm / Bớt chương:**
   - Khi muốn tạo thêm `chapter6.tex`, chỉ cần tạo file trong `chapters/` và thêm 1 dòng `\input{chapters/chapter6}` vào `main.tex`.

---

## 5. Quy ước trình bày văn bản (Typography)

- **Cỡ chữ body:** `12pt`, phông chữ **Times New Roman**.
- **Giãn dòng:** `1.35` (`\setstretch{1.35}`).
- **Căn lề chuẩn văn bản học thuật:**
  - Lề trái (đóng gáy): $3.0\text{ cm}$.
  - Lề phải: $2.0\text{ cm}$.
  - Lề trên: $2.5\text{ cm}$.
  - Lề dưới: $2.5\text{ cm}$.
- **Khoảng cách thụt đầu dòng đoạn văn:** $1.0\text{ cm}$. Khoảng cách đoạn: $6\text{ pt}$.
- **Màu sắc trang trí:** Tone xanh đặc trưng ICTU trang nhã, nghiêm túc, không sử dụng màu sắc sặc sỡ.
