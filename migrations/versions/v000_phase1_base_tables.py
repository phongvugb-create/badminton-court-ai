"""
Migration Revision 000: Base Application Schema (Phase 1)
Creates the 15 core domain tables required for badminton court rental,
player profiling, and matchmaking:
1. users
2. facilities
3. courts
4. time_slots
5. slot_pricing
6. bookings
7. equipment
8. rental_items
9. matchmaking_rooms
10. player_profiles
11. match_requests
12. matches
13. match_players
14. elo_histories
15. matchmaking_queues

Supports both PostgreSQL and SQLite. Strictly created before Phase 2 conversations.
"""

REVISION = "000_phase1_base_tables"
DESCRIPTION = "Create 15 base domain tables (users, facilities, courts, time_slots, bookings, matchmaking)"

SQL_UPGRADE_POSTGRES = [
    # 1. users
    """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        phone VARCHAR(20) NOT NULL UNIQUE,
        email VARCHAR(255),
        password_hash VARCHAR(255) NOT NULL,
        role VARCHAR(50) NOT NULL DEFAULT 'CUSTOMER',
        elo_rating INTEGER DEFAULT 1200,
        is_approved BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_users_id ON users(id);",
    "CREATE INDEX IF NOT EXISTS ix_users_phone ON users(phone);",

    # 2. facilities
    """
    CREATE TABLE IF NOT EXISTS facilities (
        id SERIAL PRIMARY KEY,
        owner_id INTEGER NOT NULL REFERENCES users(id),
        name VARCHAR(255) NOT NULL,
        address VARCHAR(500) NOT NULL,
        latitude FLOAT NOT NULL,
        longitude FLOAT NOT NULL,
        open_time VARCHAR(10) DEFAULT '06:00',
        close_time VARCHAR(10) DEFAULT '23:00',
        image_url VARCHAR(500),
        rating FLOAT DEFAULT 4.8,
        is_approved BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_facilities_id ON facilities(id);",
    "CREATE INDEX IF NOT EXISTS ix_facilities_name ON facilities(name);",

    # 3. courts
    """
    CREATE TABLE IF NOT EXISTS courts (
        id SERIAL PRIMARY KEY,
        facility_id INTEGER NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
        court_number VARCHAR(50) NOT NULL,
        surface_type VARCHAR(100) DEFAULT 'Thảm PVC chuyên dụng Enlio',
        is_active BOOLEAN DEFAULT TRUE
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_courts_id ON courts(id);",

    # 4. time_slots
    """
    CREATE TABLE IF NOT EXISTS time_slots (
        id SERIAL PRIMARY KEY,
        court_id INTEGER NOT NULL REFERENCES courts(id) ON DELETE CASCADE,
        date VARCHAR(20) NOT NULL,
        start_time VARCHAR(10) NOT NULL,
        end_time VARCHAR(10) NOT NULL,
        status VARCHAR(50) DEFAULT 'AVAILABLE'
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_time_slots_id ON time_slots(id);",
    "CREATE INDEX IF NOT EXISTS ix_time_slots_date ON time_slots(date);",

    # 5. slot_pricing
    """
    CREATE TABLE IF NOT EXISTS slot_pricing (
        id SERIAL PRIMARY KEY,
        slot_id INTEGER NOT NULL UNIQUE REFERENCES time_slots(id) ON DELETE CASCADE,
        base_price FLOAT NOT NULL,
        dynamic_price FLOAT NOT NULL,
        adjustment_reason VARCHAR(255) DEFAULT 'AI Base Rate',
        is_ai_applied BOOLEAN DEFAULT TRUE
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_slot_pricing_id ON slot_pricing(id);",

    # 6. bookings
    """
    CREATE TABLE IF NOT EXISTS bookings (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id),
        slot_id INTEGER NOT NULL REFERENCES time_slots(id),
        total_amount FLOAT NOT NULL,
        deposit_amount FLOAT NOT NULL,
        payment_status VARCHAR(50) DEFAULT 'PENDING',
        qr_checkin_code VARCHAR(100) UNIQUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_bookings_id ON bookings(id);",
    "CREATE INDEX IF NOT EXISTS ix_bookings_qr_checkin_code ON bookings(qr_checkin_code);",

    # 7. equipment
    """
    CREATE TABLE IF NOT EXISTS equipment (
        id SERIAL PRIMARY KEY,
        facility_id INTEGER NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
        name VARCHAR(255) NOT NULL,
        type VARCHAR(100) NOT NULL,
        total_qty INTEGER DEFAULT 10,
        available_qty INTEGER DEFAULT 10,
        rental_price FLOAT DEFAULT 20000.0
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_equipment_id ON equipment(id);",

    # 8. rental_items
    """
    CREATE TABLE IF NOT EXISTS rental_items (
        id SERIAL PRIMARY KEY,
        booking_id INTEGER NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
        equipment_id INTEGER NOT NULL REFERENCES equipment(id),
        quantity INTEGER DEFAULT 1,
        price FLOAT NOT NULL
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_rental_items_id ON rental_items(id);",

    # 9. matchmaking_rooms
    """
    CREATE TABLE IF NOT EXISTS matchmaking_rooms (
        id SERIAL PRIMARY KEY,
        host_user_id INTEGER NOT NULL REFERENCES users(id),
        facility_id INTEGER NOT NULL REFERENCES facilities(id),
        title VARCHAR(255) DEFAULT 'Giao lưu cầu lông vui vẻ',
        target_elo INTEGER DEFAULT 1200,
        current_players INTEGER DEFAULT 1,
        max_players INTEGER DEFAULT 4,
        play_date VARCHAR(20) NOT NULL,
        play_time VARCHAR(50) NOT NULL,
        status VARCHAR(50) DEFAULT 'OPEN',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_matchmaking_rooms_id ON matchmaking_rooms(id);",

    # 10. player_profiles
    """
    CREATE TABLE IF NOT EXISTS player_profiles (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
        gender VARCHAR(20) DEFAULT 'Khác',
        birth_year INTEGER,
        preferred_area VARCHAR(255) DEFAULT 'Cầu Giấy, Hà Nội',
        skill_level VARCHAR(100) DEFAULT 'Trung Bình Khá',
        current_elo INTEGER DEFAULT 1200,
        games_played INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        rating_confidence FLOAT DEFAULT 0.20,
        is_searching BOOLEAN DEFAULT FALSE,
        available_time VARCHAR(100) DEFAULT '18:00 - 21:00',
        preferred_court VARCHAR(255),
        play_style VARCHAR(100) DEFAULT 'Công thủ toàn diện',
        streak VARCHAR(50) DEFAULT '0',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_player_profiles_id ON player_profiles(id);",

    # 11. match_requests
    """
    CREATE TABLE IF NOT EXISTS match_requests (
        id SERIAL PRIMARY KEY,
        player_id INTEGER NOT NULL REFERENCES users(id),
        match_type VARCHAR(50) DEFAULT 'SINGLES',
        preferred_date VARCHAR(20) NOT NULL,
        start_time VARCHAR(10) NOT NULL,
        end_time VARCHAR(10) NOT NULL,
        preferred_area VARCHAR(255) NOT NULL,
        min_elo INTEGER DEFAULT 1100,
        max_elo INTEGER DEFAULT 1300,
        status VARCHAR(50) DEFAULT 'SEARCHING',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_match_requests_id ON match_requests(id);",

    # 12. matches
    """
    CREATE TABLE IF NOT EXISTS matches (
        id SERIAL PRIMARY KEY,
        court_id INTEGER REFERENCES courts(id),
        facility_id INTEGER REFERENCES facilities(id),
        match_type VARCHAR(50) DEFAULT 'SINGLES',
        start_time VARCHAR(50),
        end_time VARCHAR(50),
        match_date VARCHAR(20),
        status VARCHAR(50) DEFAULT 'SCHEDULED',
        final_score VARCHAR(100),
        winner_team VARCHAR(10),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_matches_id ON matches(id);",

    # 13. match_players
    """
    CREATE TABLE IF NOT EXISTS match_players (
        id SERIAL PRIMARY KEY,
        match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
        player_id INTEGER NOT NULL REFERENCES users(id),
        team VARCHAR(10) DEFAULT 'A',
        elo_before INTEGER NOT NULL,
        elo_after INTEGER,
        elo_change INTEGER DEFAULT 0,
        score_claimed VARCHAR(50),
        result VARCHAR(20) DEFAULT 'PENDING',
        confirmation_status VARCHAR(50) DEFAULT 'PENDING',
        submitted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_match_players_id ON match_players(id);",

    # 14. elo_histories
    """
    CREATE TABLE IF NOT EXISTS elo_histories (
        id SERIAL PRIMARY KEY,
        player_id INTEGER NOT NULL REFERENCES users(id),
        match_id INTEGER REFERENCES matches(id),
        old_elo INTEGER NOT NULL,
        new_elo INTEGER NOT NULL,
        elo_change INTEGER NOT NULL,
        reason VARCHAR(255) DEFAULT 'Match Result',
        opponent_info VARCHAR(255),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_elo_histories_id ON elo_histories(id);",

    # 15. matchmaking_queues
    """
    CREATE TABLE IF NOT EXISTS matchmaking_queues (
        id SERIAL PRIMARY KEY,
        player_id INTEGER NOT NULL REFERENCES users(id),
        match_request_id INTEGER REFERENCES match_requests(id),
        current_range INTEGER DEFAULT 50,
        joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR(50) DEFAULT 'WAITING'
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_matchmaking_queues_id ON matchmaking_queues(id);"
]

SQL_UPGRADE_SQLITE = [
    # 1. users
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL UNIQUE,
        email TEXT,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'CUSTOMER',
        elo_rating INTEGER DEFAULT 1200,
        is_approved BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_users_id ON users(id);",
    "CREATE INDEX IF NOT EXISTS ix_users_phone ON users(phone);",

    # 2. facilities
    """
    CREATE TABLE IF NOT EXISTS facilities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        address TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        open_time TEXT DEFAULT '06:00',
        close_time TEXT DEFAULT '23:00',
        image_url TEXT,
        rating REAL DEFAULT 4.8,
        is_approved BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(owner_id) REFERENCES users(id)
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_facilities_id ON facilities(id);",
    "CREATE INDEX IF NOT EXISTS ix_facilities_name ON facilities(name);",

    # 3. courts
    """
    CREATE TABLE IF NOT EXISTS courts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        facility_id INTEGER NOT NULL,
        court_number TEXT NOT NULL,
        surface_type TEXT DEFAULT 'Thảm PVC chuyên dụng Enlio',
        is_active BOOLEAN DEFAULT 1,
        FOREIGN KEY(facility_id) REFERENCES facilities(id) ON DELETE CASCADE
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_courts_id ON courts(id);",

    # 4. time_slots
    """
    CREATE TABLE IF NOT EXISTS time_slots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        court_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        status TEXT DEFAULT 'AVAILABLE',
        FOREIGN KEY(court_id) REFERENCES courts(id) ON DELETE CASCADE
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_time_slots_id ON time_slots(id);",
    "CREATE INDEX IF NOT EXISTS ix_time_slots_date ON time_slots(date);",

    # 5. slot_pricing
    """
    CREATE TABLE IF NOT EXISTS slot_pricing (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slot_id INTEGER NOT NULL UNIQUE,
        base_price REAL NOT NULL,
        dynamic_price REAL NOT NULL,
        adjustment_reason TEXT DEFAULT 'AI Base Rate',
        is_ai_applied BOOLEAN DEFAULT 1,
        FOREIGN KEY(slot_id) REFERENCES time_slots(id) ON DELETE CASCADE
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_slot_pricing_id ON slot_pricing(id);",

    # 6. bookings
    """
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        slot_id INTEGER NOT NULL,
        total_amount REAL NOT NULL,
        deposit_amount REAL NOT NULL,
        payment_status TEXT DEFAULT 'PENDING',
        qr_checkin_code TEXT UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(slot_id) REFERENCES time_slots(id)
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_bookings_id ON bookings(id);",
    "CREATE INDEX IF NOT EXISTS ix_bookings_qr_checkin_code ON bookings(qr_checkin_code);",

    # 7. equipment
    """
    CREATE TABLE IF NOT EXISTS equipment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        facility_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        total_qty INTEGER DEFAULT 10,
        available_qty INTEGER DEFAULT 10,
        rental_price REAL DEFAULT 20000.0,
        FOREIGN KEY(facility_id) REFERENCES facilities(id) ON DELETE CASCADE
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_equipment_id ON equipment(id);",

    # 8. rental_items
    """
    CREATE TABLE IF NOT EXISTS rental_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER NOT NULL,
        equipment_id INTEGER NOT NULL,
        quantity INTEGER DEFAULT 1,
        price REAL NOT NULL,
        FOREIGN KEY(booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
        FOREIGN KEY(equipment_id) REFERENCES equipment(id)
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_rental_items_id ON rental_items(id);",

    # 9. matchmaking_rooms
    """
    CREATE TABLE IF NOT EXISTS matchmaking_rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        host_user_id INTEGER NOT NULL,
        facility_id INTEGER NOT NULL,
        title TEXT DEFAULT 'Giao lưu cầu lông vui vẻ',
        target_elo INTEGER DEFAULT 1200,
        current_players INTEGER DEFAULT 1,
        max_players INTEGER DEFAULT 4,
        play_date TEXT NOT NULL,
        play_time TEXT NOT NULL,
        status TEXT DEFAULT 'OPEN',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(host_user_id) REFERENCES users(id),
        FOREIGN KEY(facility_id) REFERENCES facilities(id)
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_matchmaking_rooms_id ON matchmaking_rooms(id);",

    # 10. player_profiles
    """
    CREATE TABLE IF NOT EXISTS player_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        gender TEXT DEFAULT 'Khác',
        birth_year INTEGER,
        preferred_area TEXT DEFAULT 'Cầu Giấy, Hà Nội',
        skill_level TEXT DEFAULT 'Trung Bình Khá',
        current_elo INTEGER DEFAULT 1200,
        games_played INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        rating_confidence REAL DEFAULT 0.20,
        is_searching BOOLEAN DEFAULT 0,
        available_time TEXT DEFAULT '18:00 - 21:00',
        preferred_court TEXT,
        play_style TEXT DEFAULT 'Công thủ toàn diện',
        streak TEXT DEFAULT '0',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_player_profiles_id ON player_profiles(id);",

    # 11. match_requests
    """
    CREATE TABLE IF NOT EXISTS match_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER NOT NULL,
        match_type TEXT DEFAULT 'SINGLES',
        preferred_date TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        preferred_area TEXT NOT NULL,
        min_elo INTEGER DEFAULT 1100,
        max_elo INTEGER DEFAULT 1300,
        status TEXT DEFAULT 'SEARCHING',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(player_id) REFERENCES users(id)
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_match_requests_id ON match_requests(id);",

    # 12. matches
    """
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        court_id INTEGER,
        facility_id INTEGER,
        match_type TEXT DEFAULT 'SINGLES',
        start_time TEXT,
        end_time TEXT,
        match_date TEXT,
        status TEXT DEFAULT 'SCHEDULED',
        final_score TEXT,
        winner_team TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(court_id) REFERENCES courts(id),
        FOREIGN KEY(facility_id) REFERENCES facilities(id)
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_matches_id ON matches(id);",

    # 13. match_players
    """
    CREATE TABLE IF NOT EXISTS match_players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id INTEGER NOT NULL,
        player_id INTEGER NOT NULL,
        team TEXT DEFAULT 'A',
        elo_before INTEGER NOT NULL,
        elo_after INTEGER,
        elo_change INTEGER DEFAULT 0,
        score_claimed TEXT,
        result TEXT DEFAULT 'PENDING',
        confirmation_status TEXT DEFAULT 'PENDING',
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(match_id) REFERENCES matches(id) ON DELETE CASCADE,
        FOREIGN KEY(player_id) REFERENCES users(id)
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_match_players_id ON match_players(id);",

    # 14. elo_histories
    """
    CREATE TABLE IF NOT EXISTS elo_histories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER NOT NULL,
        match_id INTEGER,
        old_elo INTEGER NOT NULL,
        new_elo INTEGER NOT NULL,
        elo_change INTEGER NOT NULL,
        reason TEXT DEFAULT 'Match Result',
        opponent_info TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(player_id) REFERENCES users(id),
        FOREIGN KEY(match_id) REFERENCES matches(id)
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_elo_histories_id ON elo_histories(id);",

    # 15. matchmaking_queues
    """
    CREATE TABLE IF NOT EXISTS matchmaking_queues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER NOT NULL,
        match_request_id INTEGER,
        current_range INTEGER DEFAULT 50,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'WAITING',
        FOREIGN KEY(player_id) REFERENCES users(id),
        FOREIGN KEY(match_request_id) REFERENCES match_requests(id)
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_matchmaking_queues_id ON matchmaking_queues(id);"
]

# Reverse dependency order for safe dropping without foreign key violations
SQL_DOWNGRADE = [
    "DROP TABLE IF EXISTS matchmaking_queues;",
    "DROP TABLE IF EXISTS elo_histories;",
    "DROP TABLE IF EXISTS match_players;",
    "DROP TABLE IF EXISTS matches;",
    "DROP TABLE IF EXISTS match_requests;",
    "DROP TABLE IF EXISTS player_profiles;",
    "DROP TABLE IF EXISTS matchmaking_rooms;",
    "DROP TABLE IF EXISTS rental_items;",
    "DROP TABLE IF EXISTS equipment;",
    "DROP TABLE IF EXISTS bookings;",
    "DROP TABLE IF EXISTS slot_pricing;",
    "DROP TABLE IF EXISTS time_slots;",
    "DROP TABLE IF EXISTS courts;",
    "DROP TABLE IF EXISTS facilities;",
    "DROP TABLE IF EXISTS users;"
]

def upgrade(connection_or_cursor, dialect_name: str = "sqlite"):
    stmts = SQL_UPGRADE_POSTGRES if "postgres" in dialect_name.lower() else SQL_UPGRADE_SQLITE
    for sql in stmts:
        connection_or_cursor.execute(sql)

def downgrade(connection_or_cursor, dialect_name: str = "sqlite"):
    for sql in SQL_DOWNGRADE:
        connection_or_cursor.execute(sql)
