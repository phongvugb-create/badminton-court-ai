"""
Export and Synchronization Utility for SQLite <-> JSON <-> MockData
Creates/updates badminton.db with full schemas and tables matching the 9 tables.
"""
import sqlite3
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "badminton.db")
JSON_FILE = os.path.join(BASE_DIR, "database.json")

def get_connection(db_path=DB_FILE):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_sqlite_tables(conn):
    cursor = conn.cursor()
    
    # 1. users
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT UNIQUE NOT NULL,
        password TEXT,
        password_hash TEXT,
        email TEXT,
        role TEXT DEFAULT 'CUSTOMER',
        elo_rating INTEGER DEFAULT 1000,
        avatar TEXT,
        facility_id INTEGER,
        is_approved INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. facilities
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS facilities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER,
        name TEXT NOT NULL,
        address TEXT NOT NULL,
        distance TEXT,
        latitude REAL,
        longitude REAL,
        open_time TEXT DEFAULT '05:00',
        close_time TEXT DEFAULT '23:00',
        open_hours TEXT,
        rating REAL DEFAULT 5.0,
        reviews_count INTEGER DEFAULT 0,
        img TEXT,
        club_logo TEXT,
        club_avatar_bg TEXT,
        club_avatar_color TEXT,
        badges TEXT,
        sport_type TEXT DEFAULT 'badminton',
        sport_icon TEXT DEFAULT '🏸',
        courts_count INTEGER DEFAULT 8,
        is_approved INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3. courts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS courts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        facility_id INTEGER,
        name TEXT NOT NULL,
        court_number TEXT,
        court_type TEXT,
        surface_type TEXT,
        base_price REAL DEFAULT 120000,
        status TEXT DEFAULT 'AVAILABLE',
        is_active INTEGER DEFAULT 1
    );
    """)

    # 4. time_slots
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS time_slots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        court_id INTEGER,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        price REAL NOT NULL,
        is_ai_dynamic INTEGER DEFAULT 0,
        price_type TEXT,
        status TEXT DEFAULT 'AVAILABLE',
        adjustment TEXT,
        held_until TEXT
    );
    """)

    # 5. equipments
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS equipments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        facility_id INTEGER,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        quantity INTEGER DEFAULT 10,
        unit TEXT DEFAULT 'cái',
        style TEXT
    );
    """)

    # 6. booking_orders
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS booking_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_code TEXT UNIQUE NOT NULL,
        user_name TEXT NOT NULL,
        user_phone TEXT NOT NULL,
        facility_name TEXT,
        court_name TEXT,
        slot_time TEXT,
        booking_date TEXT,
        total_amount REAL,
        deposit_amount REAL,
        deposit_status TEXT,
        order_status TEXT,
        created_at TEXT,
        qr_ticket_code TEXT
    );
    """)

    # 7. invoices
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_code TEXT UNIQUE NOT NULL,
        booking_code TEXT,
        customer_name TEXT,
        facility_name TEXT,
        checkin_time TEXT,
        checkout_time TEXT,
        booking_fee REAL,
        deposit_deducted REAL,
        extra_fee REAL,
        overtime_fee REAL,
        final_amount REAL,
        payment_method TEXT,
        staff_name TEXT,
        created_at TEXT
    );
    """)

    # 8. matchmaking_rooms
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS matchmaking_rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_name TEXT NOT NULL,
        facility_name TEXT,
        match_date TEXT,
        match_time TEXT,
        required_elo_min INTEGER,
        required_elo_max INTEGER,
        match_type TEXT,
        current_players INTEGER,
        max_players INTEGER,
        status TEXT,
        host_name TEXT,
        host_elo INTEGER,
        chat_messages TEXT
    );
    """)

    # 9. occupancy_heatmap
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS occupancy_heatmap (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hour TEXT NOT NULL,
        rate INTEGER,
        status TEXT
    );
    """)

    conn.commit()

def sync_json_to_sqlite(data_dict, conn):
    """Imports records from JSON/MockData dictionary into SQLite"""
    init_sqlite_tables(conn)
    cursor = conn.cursor()

    # 1. users
    if "users" in data_dict:
        for u in data_dict["users"]:
            cursor.execute("""
            INSERT INTO users (id, name, phone, password, role, elo_rating, avatar, facility_id, is_approved)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(phone) DO UPDATE SET
                name=excluded.name,
                password=excluded.password,
                role=excluded.role,
                elo_rating=excluded.elo_rating,
                avatar=excluded.avatar,
                facility_id=excluded.facility_id,
                is_approved=excluded.is_approved;
            """, (
                u.get("id"),
                u.get("name") or u.get("full_name") or "Người Dùng",
                u.get("phone"),
                u.get("password") or "123456",
                u.get("role", "CUSTOMER"),
                u.get("elo_rating", 1000),
                u.get("avatar", "U"),
                u.get("facility_id"),
                1 if u.get("is_approved", True) else 0
            ))

    # 2. facilities
    if "facilities" in data_dict:
        for f in data_dict["facilities"]:
            badges_str = json.dumps(f.get("badges", []), ensure_ascii=False) if isinstance(f.get("badges"), list) else str(f.get("badges", ""))
            cursor.execute("""
            INSERT INTO facilities (id, owner_id, name, address, distance, latitude, longitude, open_time, close_time, open_hours, rating, reviews_count, img, club_logo, club_avatar_bg, club_avatar_color, badges, sport_type, sport_icon, courts_count, is_approved)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                address=excluded.address,
                distance=excluded.distance,
                latitude=excluded.latitude,
                longitude=excluded.longitude,
                open_time=excluded.open_time,
                close_time=excluded.close_time,
                rating=excluded.rating,
                reviews_count=excluded.reviews_count,
                img=excluded.img,
                club_logo=excluded.club_logo,
                courts_count=excluded.courts_count,
                is_approved=excluded.is_approved;
            """, (
                f.get("id"),
                f.get("owner_id", 1),
                f.get("name"),
                f.get("address"),
                f.get("distance", "3.0km"),
                f.get("latitude", 21.0285),
                f.get("longitude", 105.8542),
                f.get("open_time", "05:00"),
                f.get("close_time", "23:00"),
                f.get("open_hours", "05:00 - 23:00"),
                f.get("rating", 4.9),
                f.get("reviews_count", 100),
                f.get("img", "images/court1.jpg"),
                f.get("club_logo", "BADMINTON"),
                f.get("club_avatar_bg", "#f0fdf4"),
                f.get("club_avatar_color", "#16a34a"),
                badges_str,
                f.get("sport_type", "badminton"),
                f.get("sport_icon", "🏸"),
                f.get("courts_count", 8),
                1 if f.get("is_approved", True) else 0
            ))

    # 3. courts
    if "courts" in data_dict:
        cursor.execute("DELETE FROM courts")
        for c in data_dict["courts"]:
            cursor.execute("""
            INSERT INTO courts (id, facility_id, name, court_type, base_price, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                c.get("id"),
                c.get("facility_id", 101),
                c.get("name"),
                c.get("court_type", "Thảm Yonex"),
                c.get("base_price", 120000),
                c.get("status", "AVAILABLE")
            ))

    # 4. time_slots
    if "time_slots" in data_dict:
        cursor.execute("DELETE FROM time_slots")
        for s in data_dict["time_slots"]:
            cursor.execute("""
            INSERT INTO time_slots (id, court_id, start_time, end_time, price, is_ai_dynamic, price_type, status, adjustment, held_until)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                s.get("id"),
                s.get("court_id", 1),
                s.get("start_time"),
                s.get("end_time"),
                s.get("price", 120000),
                1 if s.get("is_ai_dynamic") else 0,
                s.get("price_type", "Tiêu chuẩn"),
                s.get("status", "AVAILABLE"),
                s.get("adjustment", ""),
                s.get("held_until", "")
            ))

    # 5. equipments
    if "equipments" in data_dict:
        cursor.execute("DELETE FROM equipments")
        for eq in data_dict["equipments"]:
            cursor.execute("""
            INSERT INTO equipments (id, name, price, quantity, unit, style)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                eq.get("id"),
                eq.get("name"),
                eq.get("price", 20000),
                eq.get("quantity", 10),
                eq.get("unit", "cái"),
                eq.get("style", "")
            ))

    # 6. booking_orders
    if "booking_orders" in data_dict:
        for b in data_dict["booking_orders"]:
            cursor.execute("""
            INSERT INTO booking_orders (id, booking_code, user_name, user_phone, facility_name, court_name, slot_time, booking_date, total_amount, deposit_amount, deposit_status, order_status, created_at, qr_ticket_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(booking_code) DO UPDATE SET
                order_status=excluded.order_status,
                deposit_status=excluded.deposit_status;
            """, (
                b.get("id"),
                b.get("booking_code"),
                b.get("user_name"),
                b.get("user_phone"),
                b.get("facility_name"),
                b.get("court_name"),
                b.get("slot_time"),
                b.get("booking_date"),
                b.get("total_amount", 0),
                b.get("deposit_amount", 0),
                b.get("deposit_status", "Chờ Cọc"),
                b.get("order_status", "Chờ Xác Nhận"),
                b.get("created_at", ""),
                b.get("qr_ticket_code", "")
            ))

    # 7. invoices
    if "invoices" in data_dict:
        for inv in data_dict["invoices"]:
            cursor.execute("""
            INSERT INTO invoices (id, invoice_code, booking_code, customer_name, facility_name, checkin_time, checkout_time, booking_fee, deposit_deducted, extra_fee, overtime_fee, final_amount, payment_method, staff_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(invoice_code) DO NOTHING;
            """, (
                inv.get("id"),
                inv.get("invoice_code"),
                inv.get("booking_code", ""),
                inv.get("customer_name"),
                inv.get("facility_name"),
                inv.get("checkin_time", ""),
                inv.get("checkout_time", ""),
                inv.get("booking_fee", 0),
                inv.get("deposit_deducted", 0),
                inv.get("extra_fee", 0),
                inv.get("overtime_fee", 0),
                inv.get("final_amount", 0),
                inv.get("payment_method", "CASH"),
                inv.get("staff_name", "Thu Ngân"),
                inv.get("created_at", "")
            ))

    # 8. matchmaking_rooms
    if "matchmaking_rooms" in data_dict:
        cursor.execute("DELETE FROM matchmaking_rooms")
        for room in data_dict["matchmaking_rooms"]:
            chat_str = json.dumps(room.get("chat_messages", []), ensure_ascii=False) if isinstance(room.get("chat_messages"), list) else str(room.get("chat_messages", ""))
            cursor.execute("""
            INSERT INTO matchmaking_rooms (id, room_name, facility_name, match_date, match_time, required_elo_min, required_elo_max, match_type, current_players, max_players, status, host_name, host_elo, chat_messages)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                room.get("id"),
                room.get("room_name"),
                room.get("facility_name"),
                room.get("match_date"),
                room.get("match_time"),
                room.get("required_elo_min", 1000),
                room.get("required_elo_max", 2000),
                room.get("match_type", "Đôi Nam/Nữ"),
                room.get("current_players", 1),
                room.get("max_players", 4),
                room.get("status", "OPEN"),
                room.get("host_name"),
                room.get("host_elo", 1200),
                chat_str
            ))

    # 9. occupancy_heatmap
    if "occupancy_heatmap" in data_dict:
        cursor.execute("DELETE FROM occupancy_heatmap")
        for heat in data_dict["occupancy_heatmap"]:
            cursor.execute("""
            INSERT INTO occupancy_heatmap (hour, rate, status)
            VALUES (?, ?, ?)
            """, (
                heat.get("hour"),
                heat.get("rate", 50),
                heat.get("status", "mid")
            ))

    conn.commit()

def export_sqlite_to_dict(conn):
    """Exports all 9 tables from SQLite into a Python dictionary"""
    cursor = conn.cursor()
    data = {}
    table_names = [
        "users", "facilities", "courts", "time_slots",
        "equipments", "booking_orders", "invoices",
        "matchmaking_rooms", "occupancy_heatmap"
    ]
    for tbl in table_names:
        try:
            cursor.execute(f"SELECT * FROM {tbl}")
            rows = cursor.fetchall()
            data[tbl] = [dict(row) for row in rows]
        except Exception:
            data[tbl] = []
    return data

if __name__ == "__main__":
    conn = get_connection()
    init_sqlite_tables(conn)
    print(f"✅ Initialized SQLite tables in {DB_FILE}")
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            jdata = json.load(f)
            sync_json_to_sqlite(jdata, conn)
            print(f"✅ Synced data from {JSON_FILE} to SQLite.")
    conn.close()
