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


if __name__ == '__main__':
    unittest.main()
