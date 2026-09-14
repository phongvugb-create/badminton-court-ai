# Sử dụng image Nginx Alpine siêu nhẹ
FROM nginx:alpine

# Copy toàn bộ mã nguồn web vào thư mục phục vụ của Nginx
COPY . /usr/share/nginx/html

# Mở cổng 80
EXPOSE 80

# Chạy Nginx ở chế độ foreground
CMD ["nginx", "-g", "daemon off;"]
