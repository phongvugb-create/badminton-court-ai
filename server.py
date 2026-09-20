import http.server
import socketserver
import json
import os
import sys

PORT = 8085
DATA_FILE = os.path.join(os.path.dirname(__file__), "database.json")

class BadmintonServerHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Enable CORS for all browsers (Brave, Chrome, Edge)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
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
                # Validate JSON
                parsed_json = json.loads(post_data.decode("utf-8"))
                with open(DATA_FILE, "w", encoding="utf-8") as f:
                    json.dump(parsed_json, f, ensure_ascii=False, indent=2)

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "message": "Database saved successfully"}).encode("utf-8"))
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
    # Allow port reuse immediately
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("", PORT), BadmintonServerHandler) as httpd:
            print(f"================================================================")
            print(f"🏸 Badminton AI Centralized DB Server running on http://localhost:{PORT}")
            print(f"📁 Web Interface: http://localhost:{PORT}/index.html")
            print(f"⚡ Central Database: {DATA_FILE}")
            print(f"================================================================")
            httpd.serve_forever()
    except Exception as e:
        print(f"Failed to start server on port {PORT}: {e}")
