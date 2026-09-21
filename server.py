import http.server
import json
import os
import sys
import urllib.request
import urllib.error

PORT = 8085
DATA_FILE = os.path.join(os.path.dirname(__file__), "database.json")

SYSTEM_INSTRUCTION = """Bạn là Trợ lý AI Thông Minh (BADMINTON.AI Virtual Assistant) của nền tảng Quản Lý & Cho Thuê Sân Cầu Lông & Pickleball BADMINTON.AI.
Nhiệm vụ của bạn:
- Tư vấn nhiệt tình, ngắn gọn, thân thiện, lịch sự và giải đáp mọi thắc mắc về sản phẩm/dịch vụ của website.
- Nắm vững kiến thức hệ thống:
  + Danh sách 48+ cụm sân cầu lông tại Hà Nội (Cầu Giấy, Hoàng Mai, Đống Đa, Thanh Xuân, Nam Từ Liêm, Ba Đình, Long Biên, Tây Hồ...).
  + Bảng giá thuê sân: 70.000đ - 160.000đ/giờ.
  + Cơ chế AI Dynamic Pricing (UC003): Tự động giảm giá 15% giờ hành chính (8h-14h) để kích cầu, phụ thu 25% khung giờ vàng (17h-21h) tối ưu doanh thu.
  + Giữ chỗ 10 phút (UC005): Khóa nguyên tử chống xung đột đặt trùng, cọc 50% qua VNPay/Chuyển khoản.
  + AI Matchmaking & Điểm ELO (UC006): Ghép kèo đấu công bằng, tìm bạn chơi theo trình độ ELO 1000 - 2000+.
  + Tư vấn dụng cụ: Chọn vợt công (Smash - nặng đầu 3U/4U), thủ (phản tạt - nhẹ đầu 4U/5U), cân bằng, căng dây 10.5 - 11.5 kg.
  + Chính sách hoàn cọc: Hoàn 100% khi hủy trước 24 giờ thi đấu.
- Luôn trả lời bằng tiếng Việt, định dạng Markdown cơ bản (tiêu đề ###, in đậm, danh sách -) rõ ràng, dùng emoji thể thao sinh động."""

def get_gemini_api_key():
    key = os.environ.get("GEMINI_API_KEY", "")
    if key and not key.startswith("YOUR_"):
        return key.strip()
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val and not val.startswith("YOUR_"):
                            return val
        except Exception:
            pass
    return ""

def get_smart_fallback(question: str) -> str:
    q = (question or "").lower()
    if "giá" in q or "tiền" in q or "bảng giá" in q or "chi phí" in q:
        return "🏸 **Bảng Giá Thuê Sân BADMINTON.AI**:\n- **Giờ hành chính (8h - 14h)**: ~70.000đ - 100.000đ/h *(AI giảm giá 15% kích cầu)*\n- **Giờ bình thường (14h - 17h)**: ~100.000đ - 120.000đ/h\n- **Giờ vàng cao điểm (17h - 21h)**: ~130.000đ - 160.000đ/h *(Phụ thu AI +25%)*\n\nBạn có thể vào mục **Đặt Sân** để xem biểu đồ giá trực tiếp theo thời gian thực nhé!"
    elif "đặt sân" in q or "giữ chỗ" in q or "cọc" in q or "thanh toán" in q:
        return "⏰ **Quy Trình Giữ Chỗ & Đặt Sân**:\n1. Chọn cụm sân & khung giờ mong muốn.\n2. Hệ thống áp dụng **Khóa Giữ Chỗ Nguyên Tử (10 Phút)** để chống trùng lịch.\n3. Thanh toán đặt cọc 50% qua cổng VNPay hoặc Chuyển khoản QR.\n4. Nhận mã QR check-in vào sân tức thì!"
    elif "ghép kèo" in q or "tìm bạn" in q or "elo" in q or "đội" in q:
        return "🏆 **AI Matchmaking & Xếp Hạng ELO**:\n- Hệ thống tự động phân tích điểm ELO (1000 - 2000+) để gợi ý phòng ghép kèo công bằng nhất.\n- Bạn có thể tạo phòng mới hoặc tham gia phòng ghép tại tab **AI Ghép Đội / Kèo Đấu** để giao lưu với các tay vợt cùng trình độ!"
    elif "vợt" in q or "chọn vợt" in q or "dụng cụ" in q or "smash" in q:
        return "🏸 **Tư Vấn Chọn Vợt Cầu Lông Phù Hợp**:\n- **Lối chơi Tấn công / Smash mạnh**: Vợt nặng đầu (Head-Heavy, điểm cân bằng > 295mm), trọng lượng 3U/4U, thân cứng (ví dụ: Yonex Astrox 88D/99/100ZZ, Lining Tectonic 7).\n- **Lối chơi Thủ / Phản tạt / Linh hoạt**: Vợt nhẹ đầu (Head-Light, < 285mm), trọng lượng 4U/5U, thân dẻo (ví dụ: Yonex Nanoflare 700/800).\n- **Lối chơi Toàn diện**: Vợt cân bằng 290mm (Arcsaber 11 Pro, Lining Halbertec 8000).\n- **Độ căng cước**: Người mới chơi 9.5 - 10.5 kg, phong trào 10.5 - 11.5 kg."
    elif "hủy sân" in q or "đổi giờ" in q or "hoàn cọc" in q:
        return "📋 **Chính Sách Hoàn Hủy Sân**:\n- **Trước 24 giờ**: Miễn phí hủy, hoàn cọc **100%** vào ví tài khoản.\n- **Trước 12 - 24 giờ**: Hoàn cọc 50%.\n- **Dưới 12 giờ**: Không hỗ trợ hoàn cọc theo quy định của ban quản lý sân.\n\nBạn có thể quản lý tại mục **Lịch Đặt Của Tôi**."
    elif "gần" in q or "địa chỉ" in q or "khu vực" in q or "hà nội" in q:
        return "📍 **Cụm Sân Nổi Bật Tại Hà Nội**:\n- **Cầu Giấy**: Sân Cầu Lông Cầu Giấy Arena (Duy Tân), Nhà Thi Đấu Cầu Giấy (Trần Quý Kiên).\n- **Hoàng Mai**: Sân Cầu Lông Tân Khai (136 Tân Khai), Sân Đền Lừ.\n- **Đống Đa**: Sân Đại Học Y Hà Nội (Tôn Thất Tùng), Sân Hoàng Cầu.\n- **Thanh Xuân**: Sân Thể Thao Khương Đình, Sân Nhân Chính.\n\nHãy bấm vào tab **Bản Đồ** để định vị sân gần bạn nhất theo GPS nhé!"
    else:
        return "👋 Xin chào! Tôi là **Trợ lý AI Thông Minh BADMINTON.AI**.\n\nTôi có thể hỗ trợ bạn:\n- 📍 Tìm cụm sân gần nhất & xem sân còn trống.\n- ⚡ Tra cứu bảng giá thuê giờ hành chính / giờ vàng.\n- 🏸 Tư vấn chọn vợt & dụng cụ phù hợp phong cách chơi.\n- 🏆 Hướng dẫn ghép kèo giao lưu theo điểm ELO.\n- 📋 Quy định đặt cọc, thanh toán và hoàn hủy 24h.\n\nBạn muốn tìm hiểu thông tin gì ạ? Hãy nhắn cho tôi nhé! ✨🏸"

def ask_gemini(user_message: str, context: str = "", messages: list = None) -> str:
    api_key = get_gemini_api_key()
    if not api_key:
        return get_smart_fallback(user_message)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    full_system = SYSTEM_INSTRUCTION
    if context:
        full_system += f"\nNgữ cảnh trang web hiện tại:\n{context}"

    # Build contents from message history or single message
    contents = []
    if messages and isinstance(messages, list) and len(messages) > 0:
        for m in messages[-8:]: # keep last 8 turns for efficiency
            role = "user" if m.get("role") == "user" or m.get("sender") == "user" else "model"
            text = m.get("content") or m.get("text") or m.get("message") or ""
            if text:
                contents.append({
                    "role": role,
                    "parts": [{"text": str(text)}]
                })
    if not contents and user_message:
        contents.append({
            "role": "user",
            "parts": [{"text": user_message}]
        })

    models_to_try = [
        ("gemini-1.5-flash", True),
        ("gemini-2.0-flash", True),
        ("gemini-pro", False)
    ]

    for model_name, use_sys_inst in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        payload = {
            "contents": list(contents),
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1000
            }
        }
        if use_sys_inst:
            payload["systemInstruction"] = {
                "parts": [{"text": full_system}]
            }

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    res_body = response.read().decode("utf-8")
                    res_json = json.loads(res_body)
                    candidates = res_json.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            text = parts[0].get("text", "")
                            if text:
                                return text
        except Exception:
            continue

    return get_smart_fallback(user_message)

class BadmintonServerHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Cache-Control")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/database":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    self.wfile.write(f.read().encode("utf-8"))
            else:
                self.wfile.write(b"{}")
            return
        
        if self.path == "/api/sqlite/download":
            db_path = os.path.join(os.path.dirname(__file__), "badminton.db")
            if os.path.exists(db_path):
                self.send_response(200)
                self.send_header("Content-Type", "application/x-sqlite3")
                self.send_header("Content-Disposition", 'attachment; filename="badminton.db"')
                with open(db_path, "rb") as f:
                    content = f.read()
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_response(404)
                self.end_headers()
            return

        if self.path == "/api/sqlite/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            try:
                import sqlite_sync
                conn = sqlite_sync.get_connection()
                data = sqlite_sync.export_sqlite_to_dict(conn)
                conn.close()
                self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
            except Exception as e:
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        if self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            db_path = os.path.join(os.path.dirname(__file__), "badminton.db")
            has_sqlite = os.path.exists(db_path)
            has_gemini = bool(get_gemini_api_key())
            self.wfile.write(json.dumps({
                "status": "running",
                "server": "Badminton AI Central DB Server",
                "sqlite_enabled": has_sqlite,
                "sqlite_file": "badminton.db" if has_sqlite else None,
                "gemini_configured": has_gemini,
                "model": "gemini-1.5-flash"
            }).encode("utf-8"))
            return

        return super().do_GET()

    def do_POST(self):
        # AI CHATBOT PROXY ENDPOINT (Secures GEMINI_API_KEY on Server)
        if self.path == "/api/chat" or self.path == "/api/v1/ai/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            user_msg = ""
            try:
                incoming = json.loads(post_data.decode("utf-8"))
                user_msg = incoming.get("message", "")
                messages = incoming.get("messages", [])
                context = incoming.get("context", "")
                
                reply = ask_gemini(user_msg, context=context, messages=messages)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": True,
                    "reply": reply,
                    "model": "gemini-1.5-flash"
                }, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                fallback_reply = get_smart_fallback(user_msg)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": True,
                    "reply": fallback_reply,
                    "fallback": True,
                    "error": str(e)
                }, ensure_ascii=False).encode("utf-8"))
            return

        if self.path == "/api/database":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            try:
                incoming_data = json.loads(post_data.decode("utf-8"))
                current_data = {}
                if os.path.exists(DATA_FILE):
                    try:
                        with open(DATA_FILE, "r", encoding="utf-8") as f:
                            current_data = json.load(f)
                    except Exception:
                        current_data = {}

                merged_database = {**current_data}

                # 1. Merge users: match by phone, preserve all users from both
                merged_users = []
                user_phones = set()
                for u in current_data.get("users", []):
                    if u.get("phone") and u.get("phone") not in user_phones:
                        user_phones.add(u.get("phone"))
                        merged_users.append(u)
                for u in incoming_data.get("users", []):
                    if u.get("phone") not in user_phones:
                        user_phones.add(u.get("phone"))
                        merged_users.append(u)
                    else:
                        for idx, eu in enumerate(merged_users):
                            if eu.get("phone") == u.get("phone"):
                                merged_users[idx] = {**eu, **u}
                merged_database["users"] = merged_users

                # 2. Merge facilities: match by id
                merged_facilities = []
                fac_ids = set()
                for f in current_data.get("facilities", []):
                    if f.get("id") and f.get("id") not in fac_ids:
                        fac_ids.add(f.get("id"))
                        merged_facilities.append(f)
                for f in incoming_data.get("facilities", []):
                    if f.get("id") not in fac_ids:
                        fac_ids.add(f.get("id"))
                        merged_facilities.append(f)
                    else:
                        for idx, ef in enumerate(merged_facilities):
                            if ef.get("id") == f.get("id"):
                                merged_facilities[idx] = {**ef, **f}
                merged_database["facilities"] = merged_facilities

                # 3. Merge other tables: courts, bookings, booking_orders, etc
                other_keys = ['courts', 'time_slots', 'equipments', 'booking_orders', 'invoices', 'matchmaking_rooms', 'occupancy_heatmap', 'bookings', 'orders']
                for k in other_keys:
                    if k in incoming_data and isinstance(incoming_data[k], list) and len(incoming_data[k]) > 0:
                        merged_database[k] = incoming_data[k]
                    elif k in current_data:
                        merged_database[k] = current_data[k]

                # Save merged data to JSON
                with open(DATA_FILE, "w", encoding="utf-8") as f:
                    json.dump(merged_database, f, ensure_ascii=False, indent=2)

                # Also sync directly to SQLite database
                try:
                    import sqlite_sync
                    conn = sqlite_sync.get_connection()
                    sqlite_sync.sync_json_to_sqlite(merged_database, conn)
                    conn.close()
                except Exception as sqle:
                    print(f"Warning: could not sync to SQLite: {sqle}")

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": True, 
                    "database_type": "SQLite3 + JSON",
                    "sqlite_file": "badminton.db",
                    "users_count": len(merged_users),
                    "facilities_count": len(merged_facilities)
                }).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    try:
        with http.server.ThreadingHTTPServer(("", PORT), BadmintonServerHandler) as httpd:
            print(f"🏸 Badminton AI Threading Server running on http://localhost:{PORT}")
            httpd.serve_forever()
    except Exception as e:
        print(f"Failed to start server on port {PORT}: {e}")
