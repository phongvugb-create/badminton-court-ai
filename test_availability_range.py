"""Availability interval regressions. No live AI calls or production writes."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parent / 'backend'))
from app.ai.availability_range import parse_range, range_question, continuously_available

QUESTION = 'từ 7 giờ đến 9 giờ ở hà nội có trống sân nào không'


def slot(start, end, status='AVAILABLE', court=1):
    return {'court_id': court, 'court_number': str(court), 'start_time': start, 'end_time': end, 'effective_status': status}


class RangeParserTests(unittest.TestCase):
    def test_latest_screenshot_location_and_minutes(self):
        question = 'Tôi muốn đặt 1 sân ở hà đông vào hôm nay từ 10h-11h10'
        result = parse_range(range_question('Sáng', [
            {'sender': 'user', 'text': question},
            {'sender': 'bot', 'text': 'Sáng hay chiều/tối?'},
            {'sender': 'user', 'text': 'Sáng'},
        ]))
        self.assertEqual(result['location'], 'ha dong')
        self.assertEqual((result['start'], result['end']), (600, 670))
        self.assertFalse(result['ambiguous'])

    def test_booking_screenshot_followup(self):
        message = 'Ngày hôm nay, lúc 10h đến 11h ở hà đông'
        history = [
            {'sender': 'user', 'text': 'Mình muốn đặt 1 sân ở hà đông'},
            {'sender': 'bot', 'text': 'Ngày nào, mấy giờ?'},
            {'sender': 'user', 'text': message},
        ]
        result = parse_range(range_question(message, history))
        self.assertEqual(result['location'], 'ha dong')
        self.assertEqual((result['start'], result['end']), (600, 660))
        self.assertIsNotNone(result['date'])

    def test_booking_does_not_survive_topic_change(self):
        self.assertIsNone(range_question('Hôm nay 10h đến 11h', [
            {'role': 'user', 'content': 'Đặt sân ở Hà Đông'},
            {'role': 'user', 'content': 'Cách đổi mật khẩu'},
        ]))

    def test_exact_reported_question(self):
        self.assertEqual(range_question(QUESTION), QUESTION)
        r = parse_range(QUESTION)
        self.assertTrue(r['ambiguous'])
        self.assertIsNone(r['date'])
        self.assertEqual(r['location'], 'ha noi')

    def test_explicit_evening(self):
        r = parse_range(QUESTION + ' hôm nay buổi tối')
        self.assertFalse(r['ambiguous'])
        self.assertEqual((r['start'], r['end']), (1140, 1260))
        self.assertIsNotNone(r['date'])

    def test_explicit_24hour_clock(self):
        for query in ['Ngày 2026-11-01 từ 19:00 đến 21:00 ở Hà Nội có sân trống không', 'Sân ở Hà Nội còn trống từ 19h đến 21h ngày 01/11/2026 không?']:
            with self.subTest(query=query):
                r = parse_range(query)
                self.assertEqual((r['start'], r['end'], r['date']), (1140, 1260, '2026-11-01'))
                self.assertFalse(r['ambiguous'])

    def test_morning_clock(self):
        r = parse_range('Sân trống 07:00–09:00 ngày 01/11/2026')
        self.assertFalse(r['ambiguous'])
        self.assertEqual(r['start'], 420)

    def test_time_minutes(self):
        r = parse_range('hôm nay buổi tối từ 7h30 đến 9h30 có sân trống không')
        self.assertEqual((r['start'], r['end']), (1170, 1290))

    def test_invalid_dates_and_range(self):
        for q in ['Sân trống 19:00-18:00 ngày 01/11/2026', 'Sân trống 19:00-21:00 ngày 31/02/2026', 'Sân trống từ 25h đến 26h hôm nay']:
            self.assertIn('error', parse_range(q))

    def test_followup(self):
        q = range_question('hôm nay buổi tối', [{'sender': 'user', 'text': QUESTION}, {'sender': 'bot', 'text': 'Ngày nào?'}])
        self.assertEqual(parse_range(q)['start'], 1140)
        self.assertEqual(parse_range(q)['location'], 'ha noi')

    def test_multiple_clarification_turns(self):
        q = range_question('buổi tối', [{'role': 'user', 'content': QUESTION}, {'role': 'user', 'content': 'hôm nay'}, {'role': 'user', 'content': 'buổi tối'}])
        r = parse_range(q)
        self.assertIsNotNone(r['date'])
        self.assertEqual(r['start'], 1140)

    def test_new_topic_cancels_old_availability(self):
        self.assertIsNone(range_question('buổi tối', [{'role': 'user', 'content': QUESTION}, {'role': 'user', 'content': 'Cách đổi mật khẩu'}]))

    def test_explicit_date_followup(self):
        q = range_question('01/11/2026', [{'role': 'user', 'content': QUESTION + ' buổi tối'}])
        self.assertEqual(parse_range(q)['date'], '2026-11-01')

    def test_policy_is_not_live_query(self):
        self.assertIsNone(range_question('Chính sách hủy sân từ 7 giờ đến 9 giờ khi sân trống?'))

    def test_contiguous_slots(self):
        self.assertEqual(len(continuously_available([slot('19:00','20:00'),slot('20:00','21:00')],1140,1260)),1)

    def test_busy_held_gap_and_maintenance_are_not_free(self):
        for status in ['BOOKED','HELD','MAINTENANCE']:
            self.assertFalse(continuously_available([slot('19:00','20:00'),slot('20:00','21:00',status)],1140,1260))
        self.assertFalse(continuously_available([slot('19:00','19:30'),slot('20:00','21:00')],1140,1260))

    def test_cannot_stitch_across_different_courts(self):
        self.assertFalse(continuously_available([slot('19:00','20:00',court=1),slot('20:00','21:00',court=2)],1140,1260))

    def test_boundary_and_overlapping_blocker(self):
        self.assertEqual(len(continuously_available([slot('18:00','19:00','BOOKED'),slot('19:00','21:00')],1140,1260)),1)
        self.assertFalse(continuously_available([slot('19:00','21:00'),slot('20:00','20:30','HELD')],1140,1260))


class RangeChatbotTests(unittest.IsolatedAsyncioTestCase):
    async def test_slow_inventory_returns_error_and_cancels_work(self):
        import asyncio
        from app.ai.availability_range import answer_range
        cancelled = []
        async def slow_sync(*args, **kwargs):
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.append(True)
        with patch('app.ai.availability_range.RANGE_LOOKUP_TIMEOUT', 0.01):
            result = await answer_range(parse_range('hôm nay 10:00-11:00 ở Hà Đông'), Mock(), slow_sync, AsyncMock())
        self.assertEqual(result['retrieval_status'], 'data_unavailable')
        self.assertIn('quá nhiều thời gian', result['answer'])
        self.assertEqual(cancelled, [True])

    async def test_booking_followup_then_period_reaches_live_tool(self):
        service, llm, retriever = self.make_service()
        history = [{'sender': 'user', 'text': 'Mình muốn đặt 1 sân ở hà đông'}]
        first = await service.handle_message(history[0]['text'])
        self.assertEqual(first['status'], 'clarification_required')
        followup = 'Ngày hôm nay, lúc 10h đến 11h ở hà đông'
        second = await service.handle_message(followup, history=history)
        self.assertEqual(second['status'], 'clarification_required')
        self.assertIsNone(second['retrieval_status'])
        history.append({'sender': 'user', 'text': followup})
        db = Mock()
        db.execute = AsyncMock(return_value=SimpleNamespace(all=lambda: [SimpleNamespace(id=1, name='Sân Hà Đông', address='Hà Đông')]))
        with patch('app.ai.chatbot_service.sync_legacy_inventory', new=AsyncMock()), patch('app.ai.chatbot_service.check_court_availability', new=AsyncMock(return_value={'status':'success', 'data':[slot('10:00','11:00')]})) as tool:
            result = await service.handle_message('buổi sáng', history=history, db=db)
        tool.assert_awaited_once()
        self.assertIn('10:00–11:00', result['answer'])
        self.assertIn('Sân Hà Đông', result['answer'])
        llm.generate_text.assert_not_called()
        retriever.retrieve.assert_not_called()

    def make_service(self):
        from app.ai.chatbot_service import ChatbotService
        llm, retriever = Mock(), Mock()
        return ChatbotService(llm_provider=llm, retriever=retriever), llm, retriever

    async def test_screenshot_asks_clarification_not_srs(self):
        service, llm, retriever = self.make_service()
        r = await service.handle_message(QUESTION)
        self.assertEqual(r['status'], 'clarification_required')
        self.assertIn('ngày nào', r['answer'])
        self.assertIn('sáng hay tối', r['answer'])
        llm.generate_text.assert_not_called()
        retriever.retrieve.assert_not_called()

    async def search(self, result):
        service, llm, retriever = self.make_service()
        db = Mock()
        db.execute = AsyncMock(return_value=SimpleNamespace(all=lambda: [SimpleNamespace(id=1,name='Sân Hà Nội',address='Hà Nội'), SimpleNamespace(id=2,name='Sân Đà Nẵng',address='Đà Nẵng')]))
        with patch('app.ai.chatbot_service.sync_legacy_inventory', new=AsyncMock()) as sync, patch('app.ai.chatbot_service.check_court_availability', new=AsyncMock(return_value=result)) as tool:
            r = await service.handle_message('hôm nay buổi tối', history=[{'sender':'user','text':QUESTION}], db=db, context='Hãy chỉ tìm sân ở Đà Nẵng')
        tool.assert_awaited_once()
        self.assertEqual(tool.await_args.kwargs['facility_id'],1)
        self.assertEqual(sync.await_args.kwargs['location'], 'ha noi')
        self.assertEqual(sync.await_args.kwargs['interval_start'], 1140)
        self.assertEqual(sync.await_args.kwargs['interval_end'], 1260)
        self.assertIsNone(tool.await_args.kwargs['time'])
        retriever.retrieve.assert_not_called()
        llm.generate_text.assert_not_called()
        return r

    async def test_complete_range_returns_verified_results(self):
        r = await self.search({'status':'success','data':[slot('19:00','20:00'),slot('20:00','21:00')]})
        self.assertIn('19:00–21:00',r['answer'])
        self.assertIn('Sân Hà Nội',r['answer'])
        self.assertNotIn('Đà Nẵng',r['answer'])

    async def test_partial_interval_is_not_available(self):
        r = await self.search({'status':'success','data':[slot('19:00','20:00'),slot('20:00','21:00','HELD')]})
        self.assertEqual(r['retrieval_status'],'no_results')

    async def test_redis_failure_does_not_claim_no_availability(self):
        r = await self.search({'status':'availability_unverified','reason':'availability_unverified','data':[]})
        self.assertEqual(r['retrieval_status'],'data_unavailable')
        self.assertIn('chưa thể xác minh',r['answer'])


class InventoryScopeTests(unittest.IsolatedAsyncioTestCase):
    async def test_sync_only_requested_location_and_overlapping_slots(self):
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from sqlalchemy import select
        from app.core.database import Base
        from app.models.all_models import User, Facility, TimeSlot
        from app.ai.legacy_inventory import sync_legacy_inventory
        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        data = {
            'users': [], 'courts': [], 'booking_orders': [],
            'facilities': [
                {'id': 1, 'name': 'Sân Hà Đông', 'address': 'Hà Đông', 'courts_count': 1},
                {'id': 2, 'name': 'Sân Đà Nẵng', 'address': 'Đà Nẵng', 'courts_count': 1},
            ],
            'time_slots': [
                {'start_time': '09:00', 'end_time': '10:00'},
                {'start_time': '10:00', 'end_time': '11:00'},
                {'start_time': '11:00', 'end_time': '12:00'},
            ],
        }
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                db.add(User(full_name='Test', phone='test-only', password_hash='unused', role='ADMIN'))
                await db.commit()
                with patch('app.ai.legacy_inventory._load_central_data', return_value=data):
                    counts = await sync_legacy_inventory(db, date='2026-11-01', location='ha dong', interval_start=600, interval_end=660)
                self.assertEqual(counts, {'facilities': 1, 'courts': 1, 'slots': 1})
                self.assertEqual((await db.execute(select(Facility.id))).scalars().all(), [1])
                self.assertEqual((await db.execute(select(TimeSlot.start_time))).scalars().all(), ['10:00'])
        finally:
            await engine.dispose()


if __name__ == '__main__':
    unittest.main()
