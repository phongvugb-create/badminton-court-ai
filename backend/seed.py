import asyncio
from datetime import datetime, timedelta
from app.core.database import AsyncSessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models.all_models import (
    User, Facility, Court, TimeSlot, SlotPricing, Equipment, MatchmakingRoom
)
from app.ai.dynamic_pricing import calculate_dynamic_price

async def seed_data():
    print("🌱 Initializing Database Schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        # pyrefly: ignore [missing-import]
        from sqlalchemy import select
        res = await session.execute(select(User))
        if res.scalars().first():
            print("Database already contains data. Skipping seed.")
            return

        print("🌱 Seeding Users...")
        # 1. Users
        admin = User(
            full_name="Quản Trị Viên Hệ Thống",
            phone="0901234567",
            email="admin@badminton.ai",
            password_hash=get_password_hash("123456"),
            role="ADMIN",
            elo_rating=1500,
            is_approved=True
        )
        owner1 = User(
            full_name="Alobo Sports Club",
            phone="0911222333",
            email="owner.alobo@gmail.com",
            password_hash=get_password_hash("123456"),
            role="OWNER",
            elo_rating=1300,
            is_approved=True
        )
        customer1 = User(
            full_name="Nguyễn Văn Phong",
            phone="0987654321",
            email="phong@gmail.com",
            password_hash=get_password_hash("123456"),
            role="CUSTOMER",
            elo_rating=1250,
            is_approved=True
        )
        session.add_all([admin, owner1, customer1])
        await session.flush()

        print("🌱 Seeding Facilities & Courts...")
        # 2. Facilities
        fac1 = Facility(
            owner_id=owner1.id,
            name="CLB Cầu Lông & Pickleball Alobo Sports",
            address="Số 22, Đường D5, Phường 25, Bình Thạnh, TP.HCM",
            latitude=10.8038,
            longitude=106.7145,
            open_time="05:00",
            close_time="23:30",
            image_url="https://images.unsplash.com/photo-1626224583764-f87db24ac4ea?w=800",
            rating=4.9,
            is_approved=True
        )
        fac2 = Facility(
            owner_id=owner1.id,
            name="Sân Cầu Lông Thảo Điền Sport Hub",
            address="18 Quốc Hương, Thảo Điền, Quận 2, TP.HCM",
            latitude=10.8055,
            longitude=106.7320,
            open_time="06:00",
            close_time="23:00",
            image_url="https://images.unsplash.com/photo-1544717305-2782549b5136?w=800",
            rating=4.8,
            is_approved=True
        )
        session.add_all([fac1, fac2])
        await session.flush()

        # Courts
        c1 = Court(facility_id=fac1.id, court_number="Sân Alobo 01 (Vip)", surface_type="Thảm PVC Enlio 5.0mm")
        c2 = Court(facility_id=fac1.id, court_number="Sân Alobo 02", surface_type="Thảm PVC Enlio tiêu chuẩn")
        c3 = Court(facility_id=fac1.id, court_number="Sân Pickleball P01", surface_type="Mặt sân Acrylic giảm chấn")
        session.add_all([c1, c2, c3])
        await session.flush()

        print("🌱 Seeding Slots with AI Dynamic Pricing...")
        today = datetime.now().strftime("%Y-%m-%d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        slots_to_generate = [
            ("06:00", "07:00", 70000),
            ("07:00", "08:00", 80000),
            ("09:00", "10:00", 80000),
            ("14:00", "15:00", 80000),
            ("17:00", "18:00", 120000),
            ("18:00", "19:00", 130000),
            ("19:00", "20:00", 130000),
            ("20:00", "21:00", 120000),
        ]

        for date_str in [today, tomorrow]:
            for st, et, base_p in slots_to_generate:
                slot = TimeSlot(
                    court_id=c1.id,
                    date=date_str,
                    start_time=st,
                    end_time=et,
                    status="AVAILABLE"
                )
                session.add(slot)
                await session.flush()

                pricing_info = calculate_dynamic_price(base_p, date_str, st)
                pricing = SlotPricing(
                    slot_id=slot.id,
                    base_price=pricing_info["base_price"],
                    dynamic_price=pricing_info["dynamic_price"],
                    adjustment_reason=pricing_info["adjustment_reason"],
                    is_ai_applied=True
                )
                session.add(pricing)

        print("🌱 Seeding Equipment & Matchmaking Rooms...")
        eq1 = Equipment(facility_id=fac1.id, name="Vợt Yonex Astrox 88D Pro", type="RACKET", total_qty=10, available_qty=8, rental_price=30000)
        eq2 = Equipment(facility_id=fac1.id, name="Ống cầu lông Thành Công (12 quả)", type="SHUTTLECOCK", total_qty=20, available_qty=18, rental_price=25000)
        eq3 = Equipment(facility_id=fac1.id, name="Vợt Pickleball Selkirk Vanguard", type="RACKET", total_qty=6, available_qty=6, rental_price=40000)
        session.add_all([eq1, eq2, eq3])

        # Matchmaking Room
        room1 = MatchmakingRoom(
            host_user_id=customer1.id,
            facility_id=fac1.id,
            title="Kèo đôi nam/nữ rèn kỹ năng - ELO ~1200",
            target_elo=1200,
            current_players=2,
            max_players=4,
            play_date=today,
            play_time="18:00 - 20:00",
            status="OPEN"
        )
        session.add(room1)

        await session.commit()
        print("✅ Seed completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed_data())
