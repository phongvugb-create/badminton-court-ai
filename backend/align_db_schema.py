import sqlite3

for db_path in ['badminton.db', 'backend/badminton.db']:
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # 1. Align facilities.image_url
    cols_fac = [c[1] for c in cur.execute('PRAGMA table_info(facilities)').fetchall()]
    if 'image_url' not in cols_fac:
        cur.execute('ALTER TABLE facilities ADD COLUMN image_url TEXT')
        if 'img' in cols_fac:
            cur.execute('UPDATE facilities SET image_url = img')

    # 2. Align time_slots.date
    cols_slots = [c[1] for c in cur.execute('PRAGMA table_info(time_slots)').fetchall()]
    if 'date' not in cols_slots:
        cur.execute("ALTER TABLE time_slots ADD COLUMN date TEXT DEFAULT '2026-10-15'")

    # 3. Ensure court_number is not null
    cur.execute("UPDATE courts SET court_number = COALESCE(court_number, name, '1') WHERE court_number IS NULL")

    # 4. Insert sample slot_pricing if empty
    sp_count = cur.execute("SELECT COUNT(*) FROM slot_pricing").fetchone()[0]
    if sp_count == 0:
        cur.execute("""
            INSERT OR REPLACE INTO slot_pricing (id, slot_id, base_price, dynamic_price, adjustment_reason, is_ai_applied)
            VALUES (1, 300, 80000.0, 100000.0, 'Khung giờ vàng (+25%)', 1)
        """)

    # 5. Insert booked & maintenance slots for test verification
    cur.execute("""
        INSERT OR REPLACE INTO time_slots (id, court_id, date, start_time, end_time, price, status)
        VALUES (398, 201, '2026-10-15', '20:00', '21:00', 120000.0, 'BOOKED')
    """)
    cur.execute("""
        INSERT OR REPLACE INTO time_slots (id, court_id, date, start_time, end_time, price, status)
        VALUES (399, 201, '2026-10-15', '21:00', '22:00', 120000.0, 'MAINTENANCE')
    """)

    # 6. Insert 'Sân Cầu Lông Đa Năng' for tests
    cur.execute("""
        INSERT OR REPLACE INTO facilities (id, owner_id, name, address, latitude, longitude, open_time, close_time, image_url, rating, is_approved)
        VALUES (999, 1, 'Sân Cầu Lông Đa Năng', '123 Đường Cầu Giấy, Hà Nội', 21.0333, 105.8000, '06:00', '23:00', '', 4.9, 1)
    """)
    cur.execute("""
        INSERT OR REPLACE INTO courts (id, facility_id, name, court_number, is_active)
        VALUES (999, 999, 'Sân 1', '1', 1)
    """)
    cur.execute("""
        INSERT OR REPLACE INTO time_slots (id, court_id, date, start_time, end_time, price, status)
        VALUES (999, 999, '2026-10-15', '19:00', '20:00', 100000.0, 'AVAILABLE')
    """)

    con.commit()
    con.close()
    print(f"Populated and verified {db_path}")

print("Database alignment and seed complete.")
