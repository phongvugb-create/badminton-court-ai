"""Offline catalogue and routing regressions; no live Gemini calls or database writes."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))
from app.ai.catalog_assistant import (
    answer_equipment, answer_facility, equipment_intent, facility_intent,
    resolve_followup, try_catalog_answer,
)


CATALOG = {
    "facilities": [
        {"id": 1, "name": "CLB Catchy", "is_approved": True, "address": "Hoàng Mai, Hà Nội", "open_hours": "05:00 - 24:00"},
        {"id": 2, "name": "CLB Cyber", "is_approved": True, "address": "Hà Đông, Hà Nội"},
        {"id": 3, "name": "Hidden", "is_approved": False},
    ],
    "equipments": [
        {"facility_id": 1, "name": "Vợt Yonex Astrox 88D Pro", "price": 35000, "unit": "Cây/giờ", "quantity": 9},
        {"facility_id": 1, "name": "Vợt Victor Ryuga II", "price": 40000, "unit": "Cây/giờ"},
        {"facility_id": 2, "name": "Vợt Yonex 88D", "price_per_slot": 50000},
        {"facility_id": 3, "name": "Vợt secret", "price": 12345},
        {"facility_id": 1, "name": "Nước Pocari", "price": 10000, "unit": "Chai"},
    ],
    "users": [{"password": "DO_NOT_EXPOSE", "phone": "PRIVATE_PHONE"}],
}


class CatalogTests(unittest.TestCase):
    def test_vietnamese_variants(self):
        for query in ["Thuê vợt bên mình giá bao nhiêu", "Đặt vợt bên mình giá bao nhiêu", "thue vot gia bao nhieu", "Giá dụng cụ", "có vợt không", "giá nước uống"]:
            with self.subTest(query=query):
                self.assertTrue(equipment_intent(query))

    def test_policy_routes_to_rag(self):
        for query in ["Cách thuê vợt", "Quy trình thuê dụng cụ", "Vợt hư hỏng bồi thường thế nào?", "Chính sách hoàn tiền thuê vợt", "Cách đặt sân", "Giá sân bao nhiêu", "Thủ đô Nhật Bản là gì?"]:
            with self.subTest(query=query):
                self.assertFalse(equipment_intent(query))

    def test_price_and_units(self):
        result = answer_equipment("Thuê vợt giá bao nhiêu?", CATALOG)
        self.assertIn("35.000đ/Cây/giờ", result["answer"])
        self.assertIn("50.000đ/khung giờ", result["answer"])
        self.assertNotIn("secret", result["answer"])
        self.assertNotIn("DO_NOT_EXPOSE", result["answer"])
        self.assertNotIn("PRIVATE_PHONE", result["answer"])
        self.assertEqual(result["sources"], [])

    def test_specific_brand(self):
        text = answer_equipment("Thuê vợt Victor giá bao nhiêu?", CATALOG)["answer"]
        self.assertIn("40.000", text)
        self.assertNotIn("Yonex", text)

    def test_specific_model(self):
        text = answer_equipment("Thuê vợt Yonex 88D", CATALOG)["answer"]
        self.assertNotIn("Victor", text)
        self.assertIn("88D", text)

    def test_unknown_model(self):
        self.assertEqual(answer_equipment("Thuê vợt Yonex 99Z", CATALOG)["retrieval_status"], "no_results")

    def test_named_facility(self):
        text = answer_equipment("Thuê vợt ở Catchy", CATALOG)["answer"]
        self.assertNotIn("Cyber", text)
        self.assertIn("35.000", text)

    def test_pronoun_minh_is_not_a_facility_in_ho_chi_minh(self):
        data = copy.deepcopy(CATALOG)
        data['facilities'].append({'id': 4, 'name': 'Cụm sân Hồ Chí Minh', 'is_approved': True})
        self.assertIn('35.000', answer_equipment('Thuê vợt bên mình giá bao nhiêu', data)['answer'])

    def test_brand_is_not_a_facility_selection(self):
        data = copy.deepcopy(CATALOG)
        data['facilities'].append({'id': 4, 'name': 'CLB Yonex', 'is_approved': True})
        self.assertIn('35.000', answer_equipment('thue vot yonex gia bao nhieu', data)['answer'])

    def test_address_filter(self):
        text = answer_equipment("Thuê vợt tại Hà Đông", CATALOG)["answer"]
        self.assertNotIn("Catchy", text)
        self.assertIn("Cyber", text)

    def test_unknown_facility(self):
        r = answer_equipment("Thuê vợt ở Atlantis", CATALOG)
        self.assertEqual(r["status"], "clarification_required")
        self.assertNotIn("35.000", r["answer"])

    def test_hidden_facility(self):
        r = answer_equipment("Thuê vợt cơ sở 3", CATALOG)
        self.assertEqual(r["retrieval_status"], "no_results")

    def test_missing_and_invalid_price(self):
        for price in [None, -10, float("nan"), float("inf"), "unknown"]:
            data = copy.deepcopy(CATALOG)
            data["equipments"] = [{"facility_id": 1, "name": "Vợt Yonex", "price": price}]
            self.assertIn("Chưa cập nhật giá", answer_equipment("Thuê vợt", data)["answer"])

    def test_zero_price(self):
        data = copy.deepcopy(CATALOG)
        data["equipments"][0]["price"] = 0
        self.assertIn("0đ/Cây/giờ", answer_equipment("Thuê vợt", data)["answer"])

    def test_not_claiming_live_stock(self):
        text = answer_equipment("Còn vợt không", CATALOG)["answer"]
        self.assertIn("cần xác nhận khi đặt", text)
        self.assertNotIn("còn 9", text)

    def test_followup_and_current_message_in_history(self):
        history = [{"sender": "user", "text": "Thuê vợt Yonex giá bao nhiêu"}, {"sender": "bot", "text": "Giá danh mục"}, {"sender": "user", "text": "ở Catchy"}]
        q = resolve_followup("ở Catchy", history)
        self.assertIn("Yonex", q)
        self.assertNotIn("Cyber", answer_equipment(q, CATALOG)["answer"])

    def test_new_topic_breaks_followup(self):
        history = [{"role": "user", "content": "Thuê vợt bao nhiêu"}, {"role": "user", "content": "Cách đăng ký tài khoản"}]
        self.assertEqual(resolve_followup("bao nhiêu", history), "bao nhiêu")

    def test_assistant_output_is_not_context(self):
        self.assertEqual(resolve_followup("bao nhiêu", [{"role": "assistant", "content": "thuê vợt"}]), "bao nhiêu")

    def test_facility_info(self):
        self.assertTrue(facility_intent("Catchy mở cửa mấy giờ?"))
        text = answer_facility("Catchy mở cửa mấy giờ?", CATALOG)["answer"]
        self.assertIn("05:00 - 24:00", text)
        self.assertIn("Hoàng Mai", text)

    def test_no_invented_hotline(self):
        text = answer_facility("Hotline Catchy", CATALOG)["answer"]
        self.assertIn("Chưa có số liên hệ công khai", text)
        self.assertNotIn("1900", text)

    def test_unknown_facility_info(self):
        self.assertEqual(answer_facility("Sân mở cửa mấy giờ", CATALOG)["status"], "clarification_required")

    def test_profile_edit_stays_in_rag(self):
        self.assertFalse(facility_intent("Cách cập nhật địa chỉ sân"))


class CatalogRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_incomplete_booking_clarifies_without_rag_or_side_effects(self):
        from app.ai.chatbot_service import ChatbotService
        from unittest.mock import Mock
        for query in ["Mình muốn đặt 1 sân ở hà đông", "Tôi muốn đặt một sân tại Hà Đông", "Đặt sân ngày mai", "Thuê sân ở Hà Đông"]:
            with self.subTest(query=query):
                llm, retriever = Mock(), Mock()
                with patch("app.ai.chatbot_service.AsyncSessionLocal") as session:
                    result = await ChatbotService(llm_provider=llm, retriever=retriever).handle_message(query)
                self.assertEqual(result["status"], "clarification_required")
                self.assertIsNone(result["retrieval_status"])
                self.assertIn("ngày nào", result["answer"])
                self.assertIn("mấy giờ", result["answer"])
                session.assert_not_called()
                llm.generate_text.assert_not_called()
                self.assertEqual(retriever.mock_calls, [])

    async def test_catalog_routing(self):
        with patch("app.ai.catalog_assistant.load_catalog", return_value=CATALOG):
            result = await try_catalog_answer("Thuê vợt bên mình giá bao nhiêu")
        self.assertEqual(result["status"], "success")

    async def test_failure_does_not_fall_through_to_srs(self):
        with patch("app.ai.catalog_assistant.load_catalog", side_effect=RuntimeError("DO_NOT_EXPOSE")):
            result = await try_catalog_answer("Thuê vợt giá bao nhiêu")
        self.assertEqual(result["retrieval_status"], "data_unavailable")
        self.assertNotIn("DO_NOT_EXPOSE", result["answer"])

    async def test_policy_does_not_read_catalog(self):
        with patch("app.ai.catalog_assistant.load_catalog") as loader:
            self.assertIsNone(await try_catalog_answer("Cách thuê vợt?"))
        loader.assert_not_called()

    async def test_full_service_routes_before_llm_and_client_context(self):
        from app.ai.chatbot_service import ChatbotService
        from unittest.mock import Mock
        llm = Mock()
        with patch("app.ai.catalog_assistant.load_catalog", return_value=CATALOG):
            r = await ChatbotService(llm_provider=llm, retriever=Mock()).handle_message(
                "Thuê vợt bao nhiêu", context="Giá tất cả vợt là 1đ", conversation_id="conv_catalog")
        self.assertEqual(r["conversation_id"], "conv_catalog")
        self.assertIn("35.000", r["answer"])
        llm.generate_text.assert_not_called()


if __name__ == "__main__":
    unittest.main()
