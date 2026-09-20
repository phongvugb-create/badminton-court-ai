import http.server
import json
import os
import sys

PORT = 8085
DATA_FILE = os.path.join(os.path.dirname(__file__), "database.json")

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
        
        if self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "running", "server": "Badminton AI Central DB Server"}).encode("utf-8"))
            return

        return super().do_GET()

    def do_POST(self):
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

                # Save merged data
                with open(DATA_FILE, "w", encoding="utf-8") as f:
                    json.dump(merged_database, f, ensure_ascii=False, indent=2)

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": True, 
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

