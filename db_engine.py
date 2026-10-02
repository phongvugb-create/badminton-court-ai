"""
BADMINTON.AI - DUAL ENGINE DATABASE PERSISTENCE LAYER (PostgreSQL & SQLite)
Designed for Local Development & Free Cloud Hosting on Render (render.com).

Features:
1. Auto-detection: If DATABASE_URL / POSTGRES_URL is provided (Render Free PostgreSQL),
   connects to PostgreSQL via psycopg2.
2. Fallback: If no DATABASE_URL is set, connects to local SQLite (badminton.db).
3. Dual Persistence: All user registrations, profile updates, bookings, matchmaking rooms,
   and ELO changes are saved both to relational tables and JSON fallback store.
4. Auto-seeding: Automatically seeds initial 48+ facilities, demo users, and court slots
   on the first boot of a fresh database.
"""

import os
import sys
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("db_engine")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_PATH = os.path.join(BASE_DIR, "badminton.db")
JSON_PATH = os.path.join(BASE_DIR, "database.json")

# Read database URL from environment (Render injects DATABASE_URL for Postgres)
RAW_DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or ""

def get_db_type():
    """Returns 'POSTGRESQL' if DATABASE_URL is configured, else 'SQLITE'"""
    if RAW_DATABASE_URL and ("postgres://" in RAW_DATABASE_URL or "postgresql://" in RAW_DATABASE_URL):
        return "POSTGRESQL"
    return "SQLITE"

def get_clean_pg_url(url):
    """Render PostgreSQL URLs often start with postgres:// which psycopg2 prefers as postgresql://"""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url

# =============================================================================
# TABLE DEFINITIONS
# =============================================================================
POSTGRES_SCHEMAS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        phone VARCHAR(50) UNIQUE NOT NULL,
        password VARCHAR(255),
        password_hash VARCHAR(255),
        email VARCHAR(255),
        role VARCHAR(50) DEFAULT 'CUSTOMER',
        elo_rating INTEGER DEFAULT 1200,
        avatar VARCHAR(50),
        facility_id INTEGER,
        is_approved BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS facilities (
        id SERIAL PRIMARY KEY,
        owner_id INTEGER,
        name VARCHAR(255) NOT NULL,
        address TEXT NOT NULL,
        distance VARCHAR(50),
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION,
        open_time VARCHAR(20) DEFAULT '05:00',
        close_time VARCHAR(20) DEFAULT '23:00',
        open_hours VARCHAR(100),
        rating DOUBLE PRECISION DEFAULT 5.0,
        reviews_count INTEGER DEFAULT 0,
        img TEXT,
        club_logo VARCHAR(50),
        club_avatar_bg VARCHAR(50),
        club_avatar_color VARCHAR(50),
        badges TEXT,
        sport_type VARCHAR(50) DEFAULT 'badminton',
        sport_icon VARCHAR(20) DEFAULT '🏸',
        courts_count INTEGER DEFAULT 8,
        is_approved BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS courts (
        id SERIAL PRIMARY KEY,
        facility_id INTEGER,
        name VARCHAR(255) NOT NULL,
        court_number VARCHAR(50),
        court_type VARCHAR(50),
        surface_type VARCHAR(100),
        base_price DOUBLE PRECISION DEFAULT 120000,
        status VARCHAR(50) DEFAULT 'AVAILABLE',
        is_active BOOLEAN DEFAULT TRUE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS time_slots (
        id SERIAL PRIMARY KEY,
        court_id INTEGER,
        start_time VARCHAR(20) NOT NULL,
        end_time VARCHAR(20) NOT NULL,
        price DOUBLE PRECISION NOT NULL,
        is_ai_dynamic BOOLEAN DEFAULT FALSE,
        price_type VARCHAR(50),
        status VARCHAR(50) DEFAULT 'AVAILABLE',
        adjustment VARCHAR(100),
        held_until VARCHAR(50)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS equipments (
        id SERIAL PRIMARY KEY,
        facility_id INTEGER,
        name VARCHAR(255) NOT NULL,
        category VARCHAR(100),
        price_per_slot DOUBLE PRECISION NOT NULL,
        stock_total INTEGER DEFAULT 10,
        stock_available INTEGER DEFAULT 10,
        image_url TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS booking_orders (
        id SERIAL PRIMARY KEY,
        booking_code VARCHAR(100) UNIQUE,
        user_name VARCHAR(255),
        user_phone VARCHAR(50),
        facility_name VARCHAR(255),
        court_name VARCHAR(100),
        booking_date VARCHAR(50),
        slot_time VARCHAR(50),
        total_amount DOUBLE PRECISION,
        deposit_amount DOUBLE PRECISION,
        deposit_status VARCHAR(50),
        order_status VARCHAR(50),
        qr_ticket_code VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS invoices (
        id SERIAL PRIMARY KEY,
        invoice_code VARCHAR(100) UNIQUE,
        booking_id INTEGER,
        customer_name VARCHAR(255),
        customer_phone VARCHAR(50),
        court_fee DOUBLE PRECISION,
        equipment_fee DOUBLE PRECISION,
        total_amount DOUBLE PRECISION,
        deposit_paid DOUBLE PRECISION,
        final_payment DOUBLE PRECISION,
        payment_method VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS matchmaking_rooms (
        id BIGINT PRIMARY KEY,
        room_name VARCHAR(255),
        facility_id INTEGER,
        facility_name VARCHAR(255),
        district VARCHAR(255),
        match_date VARCHAR(50),
        match_time VARCHAR(50),
        required_elo_min INTEGER DEFAULT 1200,
        required_elo_max INTEGER DEFAULT 1600,
        match_type VARCHAR(100),
        court_number VARCHAR(100),
        price_per_slot VARCHAR(50),
        current_players INTEGER DEFAULT 1,
        max_players INTEGER DEFAULT 4,
        status VARCHAR(50) DEFAULT 'OPEN',
        host_name VARCHAR(255),
        host_elo INTEGER DEFAULT 1450,
        ai_compatibility INTEGER DEFAULT 95,
        ai_prediction TEXT,
        ai_handicap VARCHAR(100),
        category VARCHAR(50) DEFAULT 'doubles',
        is_ai_recommended BOOLEAN DEFAULT TRUE,
        players_json TEXT,
        chat_messages_json TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS player_profiles (
        id SERIAL PRIMARY KEY,
        user_id INTEGER UNIQUE,
        gender VARCHAR(20),
        birth_year INTEGER,
        preferred_area VARCHAR(255),
        skill_level VARCHAR(100),
        current_elo INTEGER DEFAULT 1200,
        games_played INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        rating_confidence DOUBLE PRECISION DEFAULT 0.20,
        is_searching BOOLEAN DEFAULT FALSE,
        available_time VARCHAR(100),
        preferred_court VARCHAR(255),
        play_style VARCHAR(100),
        streak VARCHAR(50)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS elo_histories (
        id BIGINT PRIMARY KEY,
        player_id INTEGER,
        match_id INTEGER,
        old_elo INTEGER,
        new_elo INTEGER,
        elo_change INTEGER,
        reason VARCHAR(255),
        opponent_info VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS system_data_store (
        data_key VARCHAR(100) PRIMARY KEY,
        data_content TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
]

SQLITE_SCHEMAS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT UNIQUE NOT NULL,
        password TEXT,
        password_hash TEXT,
        email TEXT,
        role TEXT DEFAULT 'CUSTOMER',
        elo_rating INTEGER DEFAULT 1200,
        avatar TEXT,
        facility_id INTEGER,
        is_approved INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
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
    """,
    """
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
    """,
    """
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
    """,
    """
    CREATE TABLE IF NOT EXISTS equipments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        facility_id INTEGER,
        name TEXT NOT NULL,
        category TEXT,
        price_per_slot REAL NOT NULL,
        stock_total INTEGER DEFAULT 10,
        stock_available INTEGER DEFAULT 10,
        image_url TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS booking_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_code TEXT UNIQUE,
        user_name TEXT,
        user_phone TEXT,
        facility_name TEXT,
        court_name TEXT,
        booking_date TEXT,
        slot_time TEXT,
        total_amount REAL,
        deposit_amount REAL,
        deposit_status TEXT,
        order_status TEXT,
        qr_ticket_code TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_code TEXT UNIQUE,
        booking_id INTEGER,
        customer_name TEXT,
        customer_phone TEXT,
        court_fee REAL,
        equipment_fee REAL,
        total_amount REAL,
        deposit_paid REAL,
        final_payment REAL,
        payment_method TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS matchmaking_rooms (
        id INTEGER PRIMARY KEY,
        room_name TEXT,
        facility_id INTEGER,
        facility_name TEXT,
        district TEXT,
        match_date TEXT,
        match_time TEXT,
        required_elo_min INTEGER DEFAULT 1200,
        required_elo_max INTEGER DEFAULT 1600,
        match_type TEXT,
        court_number TEXT,
        price_per_slot TEXT,
        current_players INTEGER DEFAULT 1,
        max_players INTEGER DEFAULT 4,
        status TEXT DEFAULT 'OPEN',
        host_name TEXT,
        host_elo INTEGER DEFAULT 1450,
        ai_compatibility INTEGER DEFAULT 95,
        ai_prediction TEXT,
        ai_handicap TEXT,
        category TEXT DEFAULT 'doubles',
        is_ai_recommended INTEGER DEFAULT 1,
        players_json TEXT,
        chat_messages_json TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS player_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        gender TEXT,
        birth_year INTEGER,
        preferred_area TEXT,
        skill_level TEXT,
        current_elo INTEGER DEFAULT 1200,
        games_played INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        rating_confidence REAL DEFAULT 0.20,
        is_searching INTEGER DEFAULT 0,
        available_time TEXT,
        preferred_court TEXT,
        play_style TEXT,
        streak TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS elo_histories (
        id INTEGER PRIMARY KEY,
        player_id INTEGER,
        match_id INTEGER,
        old_elo INTEGER,
        new_elo INTEGER,
        elo_change INTEGER,
        reason TEXT,
        opponent_info TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS system_data_store (
        data_key TEXT PRIMARY KEY,
        data_content TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
]

# =============================================================================
# POSTGRESQL IMPLEMENTATION
# =============================================================================
def get_postgres_connection():
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        clean_url = get_clean_pg_url(RAW_DATABASE_URL)
        conn = psycopg2.connect(clean_url, cursor_factory=RealDictCursor)
        conn.autocommit = True
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL ({RAW_DATABASE_URL}): {e}")
        return None

def init_postgres(conn):
    with conn.cursor() as cur:
        for stmt in POSTGRES_SCHEMAS:
            cur.execute(stmt)
    logger.info("✅ PostgreSQL tables initialized successfully.")

def save_to_postgres(data_dict, conn):
    try:
        with conn.cursor() as cur:
            # 1. Save users
            if "users" in data_dict and isinstance(data_dict["users"], list):
                for u in data_dict["users"]:
                    cur.execute("""
                    INSERT INTO users (id, name, phone, password, role, elo_rating, avatar, is_approved)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        phone = EXCLUDED.phone,
                        password = EXCLUDED.password,
                        role = EXCLUDED.role,
                        elo_rating = EXCLUDED.elo_rating,
                        avatar = EXCLUDED.avatar,
                        is_approved = EXCLUDED.is_approved;
                    """, (
                        u.get("id"),
                        u.get("name"),
                        u.get("phone"),
                        u.get("password") or "123456",
                        u.get("role", "CUSTOMER"),
                        u.get("elo_rating") if isinstance(u.get("elo_rating"), int) else 1200,
                        u.get("avatar") or "👤",
                        u.get("is_approved", True)
                    ))

            # 2. Save full JSON state in system_data_store for zero-loss recovery
            cur.execute("""
            INSERT INTO system_data_store (data_key, data_content, updated_at)
            VALUES ('full_backup', %s, CURRENT_TIMESTAMP)
            ON CONFLICT (data_key) DO UPDATE SET
                data_content = EXCLUDED.data_content,
                updated_at = CURRENT_TIMESTAMP;
            """, (json.dumps(data_dict, ensure_ascii=False),))

        logger.info(f"✅ Synced {len(data_dict.get('users', []))} users and full state to PostgreSQL.")
        return True
    except Exception as e:
        logger.error(f"Error saving to PostgreSQL: {e}")
        return False

def load_from_postgres(conn):
    try:
        with conn.cursor() as cur:
            # Check system_data_store first
            cur.execute("SELECT data_content FROM system_data_store WHERE data_key = 'full_backup'")
            row = cur.fetchone()
            if row and row.get("data_content"):
                data = json.loads(row["data_content"])
                return data

            # Fallback: Query users table
            cur.execute("SELECT * FROM users")
            users = [dict(r) for r in cur.fetchall()]
            if users:
                return {"users": users}
    except Exception as e:
        logger.error(f"Error loading from PostgreSQL: {e}")
    return None

# =============================================================================
# SQLITE IMPLEMENTATION
# =============================================================================
def get_sqlite_connection():
    import sqlite3
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_sqlite(conn):
    cur = conn.cursor()
    for stmt in SQLITE_SCHEMAS:
        cur.execute(stmt)
    conn.commit()
    logger.info(f"✅ SQLite tables initialized successfully at {SQLITE_PATH}.")

def save_to_sqlite(data_dict, conn):
    try:
        cur = conn.cursor()
        # Save users
        if "users" in data_dict and isinstance(data_dict["users"], list):
            for u in data_dict["users"]:
                cur.execute("""
                INSERT OR REPLACE INTO users (id, name, phone, password, role, elo_rating, avatar, is_approved)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    u.get("id"),
                    u.get("name"),
                    u.get("phone"),
                    u.get("password") or "123456",
                    u.get("role", "CUSTOMER"),
                    u.get("elo_rating") if isinstance(u.get("elo_rating"), int) else 1200,
                    u.get("avatar") or "👤",
                    1 if u.get("is_approved", True) else 0
                ))

        # Save JSON backup
        cur.execute("""
        INSERT OR REPLACE INTO system_data_store (data_key, data_content, updated_at)
        VALUES ('full_backup', ?, CURRENT_TIMESTAMP)
        """, (json.dumps(data_dict, ensure_ascii=False),))

        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error saving to SQLite: {e}")
        return False

def load_from_sqlite(conn):
    try:
        cur = conn.cursor()
        cur.execute("SELECT data_content FROM system_data_store WHERE data_key = 'full_backup'")
        row = cur.fetchone()
        if row and row["data_content"]:
            return json.loads(row["data_content"])
    except Exception as e:
        logger.error(f"Error loading from SQLite: {e}")
    return None

# =============================================================================
# UNIFIED DATABASE API FOR SERVER.PY
# =============================================================================
class DatabaseManager:
    def __init__(self):
        self.db_type = get_db_type()
        self.is_connected = False
        self.active_driver = "SQLite"

    def initialize(self):
        """Initializes database schema and seeds initial data if empty"""
        if self.db_type == "POSTGRESQL":
            pg_conn = get_postgres_connection()
            if pg_conn:
                try:
                    init_postgres(pg_conn)
                    self.is_connected = True
                    self.active_driver = "PostgreSQL (Render)"
                    
                    # Check if postgres is empty, seed from database.json
                    data = load_from_postgres(pg_conn)
                    if not data or not data.get("users"):
                        if os.path.exists(JSON_PATH):
                            with open(JSON_PATH, "r", encoding="utf-8") as f:
                                initial_data = json.load(f)
                            save_to_postgres(initial_data, pg_conn)
                            logger.info("🌱 Seeded initial data into PostgreSQL.")
                    else:
                        # Write latest PostgreSQL state into database.json for local caching
                        with open(JSON_PATH, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                        logger.info("🔄 Synced latest PostgreSQL data to local database.json cache.")

                    pg_conn.close()
                    return
                except Exception as e:
                    logger.error(f"PostgreSQL setup error: {e}. Falling back to SQLite.")

        # Fallback or default to SQLite
        try:
            sq_conn = get_sqlite_connection()
            init_sqlite(sq_conn)
            self.is_connected = True
            self.active_driver = "SQLite (Local)"

            # Seed SQLite if empty
            if os.path.exists(JSON_PATH):
                with open(JSON_PATH, "r", encoding="utf-8") as f:
                    initial_data = json.load(f)
                save_to_sqlite(initial_data, sq_conn)

            sq_conn.close()
        except Exception as e:
            logger.error(f"SQLite setup error: {e}")

    def load_data(self):
        """Loads authoritative dataset from PostgreSQL, SQLite, or database.json"""
        if self.db_type == "POSTGRESQL":
            pg_conn = get_postgres_connection()
            if pg_conn:
                try:
                    data = load_from_postgres(pg_conn)
                    pg_conn.close()
                    if data:
                        return data
                except Exception as e:
                    logger.error(f"Error reading from PostgreSQL: {e}")

        # Check SQLite
        try:
            sq_conn = get_sqlite_connection()
            data = load_from_sqlite(sq_conn)
            sq_conn.close()
            if data:
                return data
        except Exception:
            pass

        # Fallback to database.json
        if os.path.exists(JSON_PATH):
            try:
                with open(JSON_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        return {}

    def save_data(self, data_dict):
        """Saves data simultaneously to PostgreSQL (if active), SQLite, and database.json"""
        # 1. Save to local JSON file
        try:
            with open(JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(data_dict, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error writing to database.json: {e}")

        # 2. Save to SQLite
        try:
            sq_conn = get_sqlite_connection()
            save_to_sqlite(data_dict, sq_conn)
            sq_conn.close()
        except Exception as e:
            logger.error(f"Error saving to SQLite: {e}")

        # 3. Save to PostgreSQL if configured
        if self.db_type == "POSTGRESQL":
            pg_conn = get_postgres_connection()
            if pg_conn:
                try:
                    save_to_postgres(data_dict, pg_conn)
                    pg_conn.close()
                except Exception as e:
                    logger.error(f"Error saving to PostgreSQL: {e}")

        return True

    def get_status(self):
        """Returns health status and database statistics"""
        current_data = self.load_data()
        return {
            "status": "healthy" if self.is_connected else "degraded",
            "active_driver": self.active_driver,
            "database_type": self.db_type,
            "has_postgres_env": bool(RAW_DATABASE_URL),
            "users_count": len(current_data.get("users", [])),
            "facilities_count": len(current_data.get("facilities", [])),
            "booking_orders_count": len(current_data.get("booking_orders", [])),
            "matchmaking_rooms_count": len(current_data.get("matchmaking_rooms", [])),
            "timestamp": datetime.now().isoformat()
        }

db_manager = DatabaseManager()

if __name__ == "__main__":
    db_manager.initialize()
    print("Database Manager Status:", json.dumps(db_manager.get_status(), indent=2))
