import os
import unittest

from backend.app import store
from backend.app.agent import agent
from backend.app.commerce import GenericRestCommerceConnector
from backend.app.inbox import (
    InboundEmail,
    approve_draft,
    ingest_inbound_email,
    list_threads,
    reset_inbox_state,
)
from backend.app.main import chat
from backend.app.models import ChatRequest, DraftApprovalRequest


SMTP_ENV_KEYS = [
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "COMMERCE_API_BASE_URL",
    "COMMERCE_API_TOKEN",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
    "SMTP_FROM_EMAIL",
    "SMTP_USE_TLS",
    "IMAP_HOST",
    "IMAP_USERNAME",
    "IMAP_PASSWORD",
]


class EmailAssistantTests(unittest.TestCase):
    def setUp(self) -> None:
        self.saved_env = {key: os.environ.get(key) for key in SMTP_ENV_KEYS}
        for key in SMTP_ENV_KEYS:
            os.environ.pop(key, None)
        self.state = store.reset_state()
        reset_inbox_state()

    def tearDown(self) -> None:
        for key, value in self.saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        reset_inbox_state()

    def _stub_intent_classifier(self, payload: dict[str, str]) -> None:
        original = agent._detect_intent_with_gemini
        agent._detect_intent_with_gemini = (  # type: ignore[method-assign]
            lambda message, state: payload
        )
        self.addCleanup(setattr, agent, "_detect_intent_with_gemini", original)

    def test_intent_and_entity_extraction_for_turkish_and_english_messages(self) -> None:
        turkish = agent.interpret_message(
            "Sipariş 128 ne zaman gelir?",
            self.state,
        )
        self.assertEqual(turkish.intent, "order_lookup")
        self.assertEqual(turkish.entities.orderId, "128")
        self.assertGreaterEqual(turkish.confidence, 0.9)

        english_stock = agent.interpret_message(
            "Do you have fig jam in stock?",
            self.state,
        )
        self.assertEqual(english_stock.intent, "stock_check")
        self.assertEqual(english_stock.entities.productId, "p-103")

    def test_vague_order_question_can_use_customer_email_or_request_review(self) -> None:
        self._stub_intent_classifier({"intent": "order_lookup"})

        resolved = agent.interpret_message(
            "Where is my order?",
            self.state,
            customer_email="mina.yilmaz@example.com",
            customer_name="Mina Yılmaz",
        )
        self.assertEqual(resolved.intent, "order_lookup")
        self.assertEqual(resolved.entities.orderId, "128")
        self.assertIn("inferred", resolved.requiredReviewReason or "")

        missing = agent.interpret_message("Where is my order?", self.state)
        self.assertEqual(missing.intent, "order_lookup")
        self.assertIsNone(missing.entities.orderId)
        self.assertLess(missing.confidence, 0.5)
        self.assertIn("No matching order", missing.requiredReviewReason or "")

    def test_generic_rest_commerce_connector_contracts_parse_mock_responses(self) -> None:
        connector = GenericRestCommerceConnector(base_url="https://commerce.example")
        product = self.state.products[0]
        order = self.state.orders[0]
        shipment = self.state.shipments[0]
        customer = self.state.customers[0]
        alert = self.state.inventoryAlerts[0]
        calls: list[tuple[str, dict[str, str] | None]] = []

        def fake_get_json(path: str, params: dict[str, str] | None = None):
            calls.append((path, params))
            if path.startswith("/orders/"):
                return {"order": _dump(order)}
            if path == "/customers":
                return {"customers": [_dump(customer)]}
            if path.startswith("/stock/") and path != "/stock/alerts":
                return {"product": _dump(product)}
            if path == "/stock/alerts":
                return {"alerts": [_dump(alert)]}
            if path.startswith("/shipments/"):
                return {"shipment": _dump(shipment)}
            return {"status": "ok"}

        connector._get_json = fake_get_json  # type: ignore[method-assign]

        self.assertEqual(connector.lookup_order(order.id, self.state).id, order.id)
        self.assertEqual(
            connector.lookup_customer(self.state, email=customer.email).id,
            customer.id,
        )
        self.assertEqual(connector.stock_snapshot(product.id, self.state).id, product.id)
        self.assertEqual(connector.stock_alerts(self.state)[0].productId, alert.productId)
        self.assertEqual(
            connector.shipment_lookup(order.id, self.state).trackingCode,
            shipment.trackingCode,
        )
        self.assertIn(("/customers", {"email": customer.email}), calls)

    def test_email_ingestion_is_idempotent(self) -> None:
        message = _inbound_message("same-message-id")

        first_thread = ingest_inbound_email(message, self.state)
        second_thread = ingest_inbound_email(message, self.state)

        self.assertIsNotNone(first_thread)
        self.assertIsNone(second_thread)
        threads = list_threads()
        self.assertEqual(len(threads), 1)
        self.assertEqual(len(threads[0].messages), 1)
        self.assertEqual(len(threads[0].drafts), 1)

    def test_draft_approval_records_send_after_human_approval(self) -> None:
        thread = ingest_inbound_email(_inbound_message("approval-message-id"), self.state)
        self.assertIsNotNone(thread)
        draft_id = thread.drafts[0].id

        response = approve_draft(draft_id, DraftApprovalRequest())

        self.assertEqual(response.draft.status, "sent")
        self.assertTrue(response.draft.sendRecorded)
        self.assertEqual(response.thread.status, "sent")
        self.assertEqual(response.thread.messages[-1].direction, "outbound")
        self.assertEqual(response.action.type, "send_email")

    def test_chat_customer_update_command_returns_reviewable_contact_draft(self) -> None:
        response = chat(
            ChatRequest(
                message="send a message to Mina about order #128 with tracking"
            )
        )

        draft = response.contactDraft
        self.assertIsNotNone(draft)
        assert draft is not None
        self.assertEqual(draft.customerId, "c-1")
        self.assertEqual(draft.customerName, "Mina Yılmaz")
        self.assertEqual(draft.recommendedChannel, "whatsapp")
        self.assertEqual(draft.entities.orderId, "128")
        self.assertEqual(draft.entities.shipmentId, "s-128")
        self.assertEqual(draft.entities.trackingCode, "MNG128-TR")
        self.assertIsNone(draft.entities.productId)
        self.assertIn("https://tracking.cirak.local/mng-kargo/MNG128-TR", draft.body)
        self.assertIn("MNG Kargo", draft.body)
        self.assertIn("incelemeye hazır", response.agentMessage.text.lower())
        self.assertIn(
            "create_customer_update_draft",
            {action.type for action in response.actions},
        )
        self.assertNotIn("check_stock", {action.type for action in response.actions})

    def test_direct_customer_update_uses_requested_message_content(self) -> None:
        response = chat(
            ChatRequest(
                message=(
                    "deniz ergin'e WhatsApp uzerinden daha once ozel olarak "
                    "sipariş ettigi 50 adet organik sabun setinin geldigini "
                    "söyleyen bir mesaj iletir misin"
                )
            )
        )

        draft = response.contactDraft
        self.assertIsNotNone(draft)
        assert draft is not None
        self.assertEqual(draft.customerId, "c-9")
        self.assertEqual(draft.customerName, "Deniz Ergin")
        self.assertEqual(draft.recommendedChannel, "whatsapp")
        self.assertIsNone(draft.entities.orderId)
        self.assertEqual(draft.entities.productId, "p-109")
        self.assertIn("Merhaba Deniz,", draft.body)
        self.assertIn(
            "Daha önce özel olarak sipariş ettiğiniz 50 adet Organik Sabun Seti geldi.",
            draft.body,
        )
        self.assertIn("Teslimat için nasıl ilerlememizi istersiniz?", draft.body)
        self.assertNotIn("Sipariş #137", draft.body)
        self.assertNotIn("packing", draft.body)
        self.assertNotIn("Seramik Sunum Tabağı", draft.body)

    def test_customer_update_missing_order_returns_no_draft(self) -> None:
        response = chat(
            ChatRequest(
                message="send a message to Mina about order #111 with tracking"
            )
        )

        self.assertIsNone(response.contactDraft)
        self.assertIn("sipariş 111 bulunamadı", response.agentMessage.text.lower())

    def test_customer_update_order_customer_mismatch_blocks_draft(self) -> None:
        response = chat(
            ChatRequest(
                message="send a message to Selin about order #128 with tracking"
            )
        )

        self.assertIsNone(response.contactDraft)
        self.assertIn("Sipariş 128", response.agentMessage.text)
        self.assertIn("Selin Kaya yerine Mina Yılmaz", response.agentMessage.text)

    def test_delayed_order_collection_question_returns_order_details(self) -> None:
        self._stub_intent_classifier(
            {"intent": "order_lookup", "orderStatus": "delayed"}
        )

        result = agent.generate_customer_reply("which orders are delayed?", self.state)

        self.assertIn("3 delayed sipariş", result.response)
        self.assertIn("#131", result.response)
        self.assertIn("#141", result.response)
        self.assertIn("#149", result.response)

    def test_ascii_turkish_customer_order_question_uses_customer_context(self) -> None:
        result = agent.generate_customer_reply(
            "arda market siparisi ne durumda",
            self.state,
        )

        self.assertIn("Sipariş 129", result.response)
        self.assertIn("Güncel durum: packing", result.response)
        self.assertNotIn("I checked open orders", result.response)

    def test_customer_lookup_question_returns_contact_and_latest_order_context(self) -> None:
        result = agent.generate_customer_reply("who is Mina?", self.state)

        self.assertIn("Mina Yılmaz", result.response)
        self.assertIn("WhatsApp", result.response)
        self.assertIn("mina.yilmaz@example.com", result.response)
        self.assertIn("#128", result.response)


def _inbound_message(provider_message_id: str) -> InboundEmail:
    return InboundEmail(
        provider_message_id=provider_message_id,
        from_name="Mina Yılmaz",
        from_email="mina.yilmaz@example.com",
        to_email="support@cirak.local",
        subject="Sipariş 128 teslimat",
        body="Merhaba, sipariş 128 ne zaman gelir?",
        received_at="2026-05-12T10:00:00+03:00",
    )


def _dump(model):
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


if __name__ == "__main__":
    unittest.main()
