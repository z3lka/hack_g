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
from backend.app.models import DraftApprovalRequest


SMTP_ENV_KEYS = [
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


def _inbound_message(provider_message_id: str) -> InboundEmail:
    return InboundEmail(
        provider_message_id=provider_message_id,
        from_name="Mina Yılmaz",
        from_email="mina.yilmaz@example.com",
        to_email="support@orbio.local",
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
