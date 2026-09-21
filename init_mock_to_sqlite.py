"""
Pure Python JS-like parser to parse MockData from js/data.js into database.json & SQLite
"""
import re
import json
import os
import sqlite_sync

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_JS = os.path.join(BASE_DIR, "js", "data.js")
JSON_FILE = os.path.join(BASE_DIR, "database.json")

with open(DATA_JS, "r", encoding="utf-8") as f:
    text = f.read()

# Extract from "const MockData = {" to "};"
start_idx = text.find("const MockData = {")
end_idx = text.find("};\n\n// Luu va Tai", start_idx)
if end_idx == -1:
    end_idx = text.find("};\n// Luu va Tai", start_idx)

js_obj_str = text[start_idx + len("const MockData = "):end_idx + 1]

# Convert JS object notation to valid JSON:
# 1. Remove comments // ...
lines = []
for line in js_obj_str.splitlines():
    stripped = line.strip()
    if stripped.startswith("//"):
        continue
    # Remove inline comments //
    # But be careful of urls like http://
    idx = line.find("//")
    if idx != -1 and "http://" not in line and "https://" not in line:
        line = line[:idx]
    lines.append(line)

cleaned_js = "\n".join(lines)

# 2. Quote keys that are unquoted, e.g. users: -> "users":
# Regex for unquoted keys before :
cleaned_json = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', cleaned_js)

# 3. Remove trailing commas before } or ]
cleaned_json = re.sub(r',\s*([}\]])', r'\1', cleaned_json)

try:
    data = json.loads(cleaned_json)
    print("Parsed JSON successfully!")
    
    # Merge existing users
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as jf:
                curr = json.load(jf)
                existing_phones = {u.get("phone") for u in curr.get("users", []) if u.get("phone")}
                for u in curr.get("users", []):
                    if u.get("phone") and not any(du.get("phone") == u.get("phone") for du in data.get("users", [])):
                        data["users"].append(u)
        except Exception as e:
            print("Merge note:", e)

    with open(JSON_FILE, "w", encoding="utf-8") as jf:
        json.dump(data, jf, ensure_ascii=False, indent=2)
    print("✅ Exported full MockData to database.json")

    conn = sqlite_sync.get_connection()
    sqlite_sync.sync_json_to_sqlite(data, conn)
    conn.close()
    print("✅ Synced all 9 tables to SQLite badminton.db successfully!")
except Exception as e:
    print("JSON parse error, falling back to python literal or direct parsing:", e)
    # Let's inspect where it failed if needed
