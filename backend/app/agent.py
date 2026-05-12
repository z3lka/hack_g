import re
from datetime import datetime
from uuid import uuid4

from . import store
from .commerce import get_commerce_connector
from .gemini_client import gemini_client
from .memory import query_memory
from .models import (
    AgentAction,
    AgentResult,
    AssistantInterpretation,
    ChatMessage,
    Customer,
    MessageEntities,
    OperationsState,
    Order,
    Product,
    Shipment,
    Task,
)

ORDER_ID_PATTERN = re.compile(r"(?:order|siparis|#)?\s*(\d{3,})", re.IGNORECASE)
PRODUCT_MATCH_STOPWORDS = {
    "set",
    "seti",
    "paket",
    "paketi",
    "adet",
    "kg",
    "sise",
    "sisesi",
    "stok",
    "durum",
    "durumu",
    "var",
    "mi",
}
INTENTS = {
    "stock_check",
    "order_lookup",
    "shipment_risk",
    "issue_check",
    "customer_lookup",
    "task_summary",
    "operations_summary",
    "return_exchange",
    "complaint",
    "general",
    "unknown",
}
INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": sorted(INTENTS),
        },
        "orderId": {"type": "string"},
        "productId": {"type": "string"},
        "productName": {"type": "string"},
        "customerName": {"type": "string"},
        "customerEmail": {"type": "string"},
    },
    "required": ["intent"],
}


class OperationsAgent:
    def lookup_order_status(
        self, order_id: str, state: OperationsState
    ) -> tuple[Order, Shipment | None] | None:
        commerce = get_commerce_connector()
        order = commerce.lookup_order(order_id, state)

        if order is None:
            return None

        shipment = commerce.shipment_lookup(order.id, state)
        return order, shipment

    def check_stock(self, product_id: str, state: OperationsState) -> Product | None:
        return get_commerce_connector().stock_snapshot(product_id, state)

    def lookup_customer(
        self,
        state: OperationsState,
        customer_id: str | None = None,
        email: str | None = None,
        name: str | None = None,
    ) -> Customer | None:
        return get_commerce_connector().lookup_customer(
            state,
            customer_id=customer_id,
            email=email,
            name=name,
        )

    def detect_shipping_risks(self, state: OperationsState) -> list[Shipment]:
        return [s for s in state.shipments if s.risk != "clear" and not s.notified]

    def suggest_restock(self, product_id: str, state: OperationsState) -> str:
        product = self.check_stock(product_id, state)

        if product is None:
            return "No supplier draft available because the product could not be found."

        average_demand = store.average_daily_sales(product)
        recommended_quantity = max(
            product.threshold * 2 - product.stock, round(average_demand * 10)
        )
        memory_records = query_memory(
            f"{product.name} {product.supplier} supplier restock delivery",
            limit=4,
        )
        prompt = self._build_supplier_draft_prompt(
            product,
            round(average_demand, 1),
            recommended_quantity,
            [record.text for record in memory_records],
        )
        response_text = gemini_client.generate_text(prompt)

        if response_text:
            return response_text.strip()

        return (
            f"Konu: {product.name} Siparişi\n\n"
            f"Merhaba {product.supplier},\n\n"
            f"Mevcut {product.name} stoğumuz {product.stock} {product.unit} seviyesinde. "
            f"Yeniden sipariş eşiğimiz {product.threshold} {product.unit} ve günlük ortalama "
            f"satışımız yaklaşık {round(average_demand)} {product.unit}.\n\n"
            f"Bu hafta için {recommended_quantity} {product.unit} {product.name} siparişi "
            "oluşturmak istiyoruz. Uygunluk durumunuzu paylaşabilir misiniz?"
        )

    def generate_customer_reply(
        self, message: str, state: OperationsState
    ) -> AgentResult:
        interpretation = self.interpret_message(message, state)
        context = self._resolve_request(message, state, interpretation=interpretation)
        actions = interpretation.actions

        prompt = self._build_grounded_reply_prompt(message, context, state)
        response_text = gemini_client.generate_text(prompt)

        if response_text:
            return AgentResult(response=response_text, actions=actions)

        return AgentResult(
            response=self._fallback_reply(message, context, state),
            actions=actions,
        )

    def interpret_message(
        self,
        message: str,
        state: OperationsState,
        customer_email: str | None = None,
        customer_name: str | None = None,
    ) -> AssistantInterpretation:
        context = self._resolve_request(
            message,
            state,
            customer_email=customer_email,
            customer_name=customer_name,
        )
        memory_records = query_memory(self._memory_query_for_context(message, context), limit=4)
        context["memoryRecords"] = memory_records
        entities = self._entities_for_context(context)
        confidence = self._confidence_for_context(context)
        required_review_reason = self._required_review_reason(context, confidence)
        actions = self._actions_for_context(context, entities, confidence)

        return AssistantInterpretation(
            intent=context.get("intent") or "unknown",
            entities=entities,
            confidence=confidence,
            requiredReviewReason=required_review_reason,
            memory=[record.text for record in memory_records],
            actions=actions,
        )

    def generate_customer_email_draft(
        self,
        message: str,
        state: OperationsState,
        customer_email: str,
        customer_name: str,
        subject: str,
    ) -> tuple[str, str, AssistantInterpretation]:
        interpretation = self.interpret_message(
            message,
            state,
            customer_email=customer_email,
            customer_name=customer_name,
        )
        context = self._resolve_request(
            message,
            state,
            customer_email=customer_email,
            customer_name=customer_name,
            interpretation=interpretation,
        )
        prompt = self._build_customer_email_draft_prompt(
            message,
            subject,
            context,
            state,
            interpretation,
        )
        response_text = gemini_client.generate_text(prompt)
        body = response_text.strip() if response_text else self._fallback_reply(message, context, state)

        return self._reply_subject(subject), body, interpretation

    def _detect_order_id(self, message: str) -> str | None:
        match = ORDER_ID_PATTERN.search(message.lower())
        return match.group(1) if match else None

    def _detect_product(self, message: str, state: OperationsState) -> Product | None:
        normalized = _normalize(message)
        alias_to_id = {
            "zeytinyagi": "p-101",
            "hediye seti": "p-101",
            "olive oil": "p-101",
            "havlu": "p-102",
            "incir": "p-103",
            "fig jam": "p-103",
            "recel": "p-103",
            "domates paketi": "p-105",
            "kurutulmus domates": "p-105",
            "dried tomato": "p-105",
            "cezve": "p-106",
            "taze domates": "p-107",
            "tomatoes": "p-107",
            "domates": "p-107",
            "nar eksisi": "p-108",
            "sabun": "p-109",
            "sabun seti": "p-109",
            "kilim": "p-110",
            "sage": "p-111",
            "adacayi": "p-111",
            "seramik": "p-112",
        }

        for alias, product_id in sorted(
            alias_to_id.items(), key=lambda item: len(item[0]), reverse=True
        ):
            if alias in normalized:
                product = self.check_stock(product_id, state)
                if product:
                    return product

        query_tokens = _product_match_tokens(normalized)
        best_product: Product | None = None
        best_score = 0

        for product in state.products:
            product_name = _normalize(product.name)
            product_tokens = _product_match_tokens(product_name)

            if product_name in normalized:
                score = 100
            else:
                overlap = query_tokens & product_tokens
                if not overlap:
                    continue

                score = sum(len(token) for token in overlap) + len(overlap) * 5
                if query_tokens and query_tokens.issubset(product_tokens):
                    score += 20

            if score > best_score:
                best_product = product
                best_score = score

        return best_product

    def _product_from_id_or_name(
        self, product_id: str | None, product_name: str | None, state: OperationsState
    ) -> Product | None:
        if product_id:
            product = self.check_stock(product_id, state)
            if product:
                return product

        if product_name:
            return self._detect_product(product_name, state)

        return None

    def _detect_intent_with_gemini(
        self, message: str, state: OperationsState
    ) -> dict[str, str] | None:
        product_lines = "\n".join(f"- {p.id}: {p.name}" for p in state.products)
        customer_lines = "\n".join(
            f"- {c.id}: {c.name} ({c.email or 'no email'})" for c in state.customers
        )
        prompt = f"""
Classify this operations assistant message.
Return only JSON matching the schema.

Message:
"{message}"

Valid intents:
- stock_check: product stock, daily sales, remaining days, restock need
- order_lookup: order status, order items, ETA, customer order question
- shipment_risk: cargo, shipping, delivery risks
- issue_check: errors, failures, warnings, exceptions, operational issues
- customer_lookup: customer rhythm or customer-specific question
- task_summary: team task or todo question
- operations_summary: broad "what needs attention" question
- return_exchange: return, exchange, cancellation, or refund request
- complaint: damaged item, wrong item, angry customer, or service complaint
- general: anything else

Products:
{product_lines}

Customers:
{customer_lines}
""".strip()
        payload = gemini_client.generate_json(prompt, INTENT_SCHEMA)

        if not payload:
            return None

        return {key: str(value) for key, value in payload.items() if value}

    def _resolve_request(
        self,
        message: str,
        state: OperationsState,
        customer_email: str | None = None,
        customer_name: str | None = None,
        interpretation: AssistantInterpretation | None = None,
    ) -> dict:
        if interpretation:
            intent_payload = {
                "intent": interpretation.intent,
                "orderId": interpretation.entities.orderId or "",
                "productId": interpretation.entities.productId or "",
                "productName": interpretation.entities.productName or "",
                "customerName": interpretation.entities.customerName or "",
                "customerEmail": interpretation.entities.customerEmail or "",
            }
        else:
            intent_payload = self._detect_intent_with_gemini(message, state) or {}

        customer = self._detect_customer(
            state,
            message=message,
            customer_email=customer_email or intent_payload.get("customerEmail"),
            customer_name=customer_name or intent_payload.get("customerName"),
        )
        order_id = self._detect_order_id(message) or intent_payload.get("orderId")
        product = self._detect_product(message, state) or self._product_from_id_or_name(
            intent_payload.get("productId"),
            intent_payload.get("productName"),
            state,
        )
        intent = intent_payload.get("intent")

        if intent not in INTENTS:
            intent = self._heuristic_intent(message, order_id, product)

        order_resolved_from_customer = False
        if not order_id and customer and intent in {"order_lookup", "shipment_risk"}:
            latest_order = self._latest_order_for_customer(customer, state)
            if latest_order:
                order_id = latest_order.id
                order_resolved_from_customer = True

        order_context = self.lookup_order_status(order_id, state) if order_id else None
        active_issues = [issue for issue in state.issues if not issue.resolved]
        active_alerts = get_commerce_connector().stock_alerts(state)
        risky_shipments = self.detect_shipping_risks(state)
        open_tasks = [task for task in state.tasks if task.status == "open"]

        return {
            "intent": intent,
            "orderId": order_id,
            "orderResolvedFromCustomer": order_resolved_from_customer,
            "orderContext": order_context,
            "product": product,
            "customer": customer,
            "activeIssues": active_issues,
            "activeAlerts": active_alerts,
            "riskyShipments": risky_shipments,
            "openTasks": open_tasks,
            "memoryRecords": interpretation.memory if interpretation else [],
        }

    def _detect_customer(
        self,
        state: OperationsState,
        message: str,
        customer_email: str | None = None,
        customer_name: str | None = None,
    ) -> Customer | None:
        if customer_email or customer_name:
            customer = self.lookup_customer(
                state,
                email=customer_email,
                name=customer_name,
            )
            if customer:
                return customer

        normalized = _normalize(message)
        for customer in state.customers:
            if _normalize(customer.name) in normalized:
                return customer
            if customer.email and _normalize(customer.email) in normalized:
                return customer

        return None

    def _latest_order_for_customer(
        self,
        customer: Customer,
        state: OperationsState,
    ) -> Order | None:
        customer_orders = [order for order in state.orders if order.customerId == customer.id]
        if not customer_orders:
            return None

        return sorted(customer_orders, key=lambda order: order.createdAt, reverse=True)[0]

    def _entities_for_context(self, context: dict) -> MessageEntities:
        product = context.get("product")
        customer = context.get("customer")
        order_context = context.get("orderContext")
        shipment = order_context[1] if order_context else None

        return MessageEntities(
            orderId=context.get("orderId"),
            productId=product.id if product else None,
            productName=product.name if product else None,
            customerId=customer.id if customer else None,
            customerName=customer.name if customer else None,
            customerEmail=customer.email if customer else None,
            shipmentId=shipment.id if shipment else None,
            trackingCode=shipment.trackingCode if shipment else None,
        )

    def _confidence_for_context(self, context: dict) -> float:
        intent = context.get("intent")

        if context.get("orderContext"):
            return 0.74 if context.get("orderResolvedFromCustomer") else 0.92

        if context.get("product") and intent == "stock_check":
            return 0.9

        if context.get("customer"):
            return 0.72

        if intent in {"order_lookup", "shipment_risk"} and not context.get("orderId"):
            return 0.38

        if intent in {"return_exchange", "complaint"}:
            return 0.58

        if intent in {"operations_summary", "issue_check", "task_summary"}:
            return 0.8

        return 0.62

    def _required_review_reason(self, context: dict, confidence: float) -> str | None:
        reasons = ["Human approval is required before any customer email is sent."]

        if context.get("intent") in {"order_lookup", "shipment_risk"} and not context.get("orderContext"):
            reasons.append("No matching order was found.")

        if context.get("orderResolvedFromCustomer"):
            reasons.append("Order ID was inferred from the customer email rather than stated explicitly.")

        if context.get("intent") == "stock_check" and not context.get("product"):
            reasons.append("The requested product was not identified.")

        if confidence < 0.7:
            reasons.append("Assistant confidence is below the auto-clear threshold.")

        return " ".join(reasons)

    def _memory_query_for_context(self, message: str, context: dict) -> str:
        product = context.get("product")
        customer = context.get("customer")
        order_id = context.get("orderId") or ""
        parts = [
            message,
            context.get("intent") or "",
            order_id,
            product.name if product else "",
            customer.name if customer else "",
            customer.email if customer and customer.email else "",
        ]
        return " ".join(part for part in parts if part)

    def _heuristic_intent(
        self, message: str, order_id: str | None, product: Product | None
    ) -> str:
        normalized = _normalize(message)

        if order_id:
            return "order_lookup"

        if any(word in normalized for word in ["iade", "degisim", "iptal", "refund", "return", "exchange", "cancel"]):
            return "return_exchange"

        if any(word in normalized for word in ["sikayet", "kirik", "hasar", "yanlis", "complaint", "damaged", "wrong", "broken"]):
            return "complaint"

        if product or any(word in normalized for word in ["stok", "stock", "kalan", "restock"]):
            return "stock_check"

        if any(word in normalized for word in ["siparis", "order", "nerede", "where", "gelir", "arrive", "eta", "teslim", "delivery", "takip", "tracking"]):
            return "order_lookup"

        if any(word in normalized for word in ["hata", "error", "issue", "uyari", "warning", "problem", "fail"]):
            return "issue_check"

        if any(word in normalized for word in ["kargo", "cargo", "shipment", "teslim"]):
            return "shipment_risk"

        if any(word in normalized for word in ["gorev", "task", "todo"]):
            return "task_summary"

        return "operations_summary"

    def _actions_for_context(
        self,
        context: dict,
        entities: MessageEntities | None = None,
        confidence: float | None = None,
    ) -> list[AgentAction]:
        actions: list[AgentAction] = [
            AgentAction(
                id=str(uuid4()),
                label=f"Classified message as {context.get('intent', 'unknown')}",
                type="classify_message",
                payload={
                    "intent": context.get("intent", "unknown"),
                    "confidencePct": round((confidence or 0) * 100),
                },
            )
        ]
        order_id = context.get("orderId")
        product = context.get("product")
        customer = context.get("customer")
        intent = context.get("intent")

        if entities and any(
            [
                entities.orderId,
                entities.productId,
                entities.customerId,
                entities.customerEmail,
            ]
        ):
            actions.append(
                AgentAction(
                    id=str(uuid4()),
                    label="Extracted customer message entities",
                    type="extract_entities",
                    payload={
                        "orderId": entities.orderId or "",
                        "productId": entities.productId or "",
                        "customerId": entities.customerId or "",
                    },
                )
            )

        if customer:
            actions.append(
                AgentAction(
                    id=str(uuid4()),
                    label=f"Looked up customer {customer.name}",
                    type="lookup_customer",
                    payload={"customerId": customer.id},
                )
            )

        if order_id:
            actions.append(
                AgentAction(
                    id=str(uuid4()),
                    label=f"Looked up order {order_id}",
                    type="lookup_order",
                    payload={"orderId": order_id},
                )
            )

        if context.get("orderContext") and context["orderContext"][1]:
            shipment = context["orderContext"][1]
            actions.append(
                AgentAction(
                    id=str(uuid4()),
                    label=f"Looked up shipment {shipment.trackingCode}",
                    type="lookup_shipment",
                    payload={"orderId": shipment.orderId, "trackingCode": shipment.trackingCode},
                )
            )

        if product:
            actions.append(
                AgentAction(
                    id=str(uuid4()),
                    label=f"Checked stock for {product.name}",
                    type="check_stock",
                    payload={"productId": product.id},
                )
            )

        if intent == "issue_check":
            actions.append(
                AgentAction(
                    id=str(uuid4()),
                    label="Checked open operational issues",
                    type="check_errors",
                    payload={"openIssues": len(context["activeIssues"])},
                )
            )

        if intent in {"operations_summary", "shipment_risk", "task_summary"}:
            actions.append(
                AgentAction(
                    id=str(uuid4()),
                    label="Summarized operations state",
                    type="summarize_operations",
                    payload={
                        "stockAlerts": len(context["activeAlerts"]),
                        "shipmentRisks": len(context["riskyShipments"]),
                        "openIssues": len(context["activeIssues"]),
                    },
                )
            )

        return actions

    def _build_grounded_reply_prompt(
        self, message: str, context: dict, state: OperationsState
    ) -> str:
        context_lines = self._grounded_context_lines(context, state)

        return f"""
You are a helpful AI assistant for a small Turkish business (KOBİ).
A customer or staff member sent the following message. Reply in the same language as the message.
Be concise, operational, and accurate. Use only the exact data below. Do not invent facts, dates, carriers, stock, totals, or actions.
If requested data is missing, say clearly that it was not found.

Customer/staff message:
"{message}"

Detected intent: {context["intent"]}

Exact data available for the reply:
{context_lines}

Reply with one short paragraph. No markdown.
""".strip()

    def _build_customer_email_draft_prompt(
        self,
        message: str,
        subject: str,
        context: dict,
        state: OperationsState,
        interpretation: AssistantInterpretation,
    ) -> str:
        context_lines = self._grounded_context_lines(context, state)
        memory_context = "\n".join(f"- {item}" for item in interpretation.memory)

        return f"""
You are drafting a customer support email for a small Turkish business.
The business owner must approve this draft before it is sent.
Reply in the same language as the customer message.
Use only the exact operational data below. Do not invent refunds, reservations, discounts, dates, carriers, or stock updates.
If the customer asks for something the data cannot answer, acknowledge the request and say the team will check it.
Do not say the email has been sent or that inventory was reserved.
Return only the email body. No markdown.

Incoming subject:
"{subject}"

Incoming customer message:
"{message}"

Detected intent: {interpretation.intent}
Confidence: {round(interpretation.confidence, 2)}
Review note: {interpretation.requiredReviewReason or "Human approval required."}

Exact operational data:
{context_lines}

Relevant memory:
{memory_context or "- No relevant memory records found."}
""".strip()

    def _reply_subject(self, subject: str) -> str:
        normalized = subject.strip()
        return normalized if normalized.lower().startswith("re:") else f"Re: {normalized or 'Customer message'}"

    def _grounded_context_lines(self, context: dict, state: OperationsState) -> str:
        lines: list[str] = []
        order_context = context.get("orderContext")
        product = context.get("product")
        customer = context.get("customer")

        if customer:
            lines.append(
                f"Customer {customer.name}: id={customer.id}, channel={customer.channel}, "
                f"phone={customer.phone}, email={customer.email or 'N/A'}."
            )

        if order_context:
            order, shipment = order_context
            customer = next((c for c in state.customers if c.id == order.customerId), None)
            lines.append(
                f"Order {order.id}: status={order.status}, customer={customer.name if customer else order.customerId}, "
                f"items={summarize_order_items(order, state)}, total={order.total} TRY, dueToday={order.dueToday}."
            )
            if shipment:
                lines.append(
                    f"Shipment for order {order.id}: carrier={shipment.carrier}, tracking={shipment.trackingCode}, "
                    f"risk={shipment.risk}, eta={shipment.eta}, lastScan={shipment.lastScan}, notified={shipment.notified}."
                )
        elif context.get("orderId"):
            lines.append(f"Order {context['orderId']} was not found.")

        if product:
            alert = next(
                (
                    item
                    for item in state.inventoryAlerts
                    if item.productId == product.id and not item.resolved
                ),
                None,
            )
            lines.append(
                f"Product {product.name}: stock={product.stock} {product.unit}, "
                f"threshold={product.threshold} {product.unit}, "
                f"averageDailySales={round(store.average_daily_sales(product), 1)} {product.unit}, "
                f"remainingDays={store.remaining_days(product)}, "
                f"severity={alert.severity if alert else store.inventory_severity(product) or 'healthy'}, "
                f"supplier={product.supplier}."
            )
            if alert:
                lines.append(f"Stock alert: {alert.message}")

        intent = context.get("intent")
        if intent in {"stock_check", "operations_summary"} and not product:
            for alert in context["activeAlerts"][:8]:
                alert_product = self.check_stock(alert.productId, state)
                if alert_product:
                    lines.append(
                        f"Stock alert {alert.severity}: {alert_product.name}, "
                        f"stock={alert_product.stock} {alert_product.unit}, "
                        f"averageDailySales={round(store.average_daily_sales(alert_product), 1)}, "
                        f"remainingDays={store.remaining_days(alert_product)}, message={alert.message}"
                    )

        if intent in {"issue_check", "operations_summary"}:
            for issue in context["activeIssues"][:8]:
                lines.append(
                    f"Issue {issue.severity}: {issue.title}, category={issue.category}, "
                    f"source={issue.source}, entityId={issue.entityId or 'N/A'}, message={issue.message}"
                )

        if intent in {"shipment_risk", "operations_summary"}:
            for shipment in context["riskyShipments"][:8]:
                lines.append(
                    f"Shipment risk {shipment.risk}: order={shipment.orderId}, carrier={shipment.carrier}, "
                    f"eta={shipment.eta}, lastScan={shipment.lastScan}"
                )

        if intent in {"task_summary", "operations_summary"}:
            for task in context["openTasks"][:8]:
                lines.append(
                    f"Open task {task.priority}: {task.title}, owner={task.owner}, orderId={task.orderId or 'N/A'}"
                )

        memory_records = context.get("memoryRecords") or []
        for record in memory_records[:4]:
            record_text = record.text if hasattr(record, "text") else str(record)
            lines.append(f"Relevant memory: {record_text}")

        return "\n".join(f"- {line}" for line in lines) or "- No matching operational data found."

    def _build_supplier_draft_prompt(
        self,
        product: Product,
        average_demand: float,
        recommended_quantity: int,
        memory_records: list[str],
    ) -> str:
        memory_context = "\n".join(f"- {record}" for record in memory_records)
        return f"""
You are an AI operations assistant for a Turkish SME.
Prepare a ready-to-send supplier email draft in Turkish.
Do not invent details beyond the data below.
Do not add placeholder names, placeholder signatures, markdown, or commentary.
Return only the email text, including a subject line.

Product:
- Name: {product.name}
- Current stock: {product.stock} {product.unit}
- Reorder threshold: {product.threshold} {product.unit}
- Average daily sales: {average_demand} {product.unit}
- Supplier: {product.supplier}
- Recommended quantity: {recommended_quantity} {product.unit}

Relevant business memory:
{memory_context or "- No extra memory records found."}
""".strip()

    def _fallback_reply(
        self,
        message: str,
        context: dict,
        state: OperationsState,
    ) -> str:
        order_id = context.get("orderId")
        order_context = context.get("orderContext")
        product = context.get("product")
        intent = context.get("intent")

        if order_id:
            if order_context is None:
                return (
                    f"{order_id} numaralı siparişi bulamadım. Lütfen sipariş numarasını kontrol edin."
                    if _prefers_turkish(message)
                    else f"I could not find order {order_id}. Please check the number and try again."
                )
            order, shipment = order_context
            item_summary = summarize_order_items(order, state)
            if shipment:
                if _prefers_turkish(message):
                    return (
                        f"Sipariş {order.id} içeriği: {item_summary}. "
                        f"{shipment.carrier} ETA {shipment.eta}. "
                        f"Son güncelleme: {shipment.lastScan}."
                    )
                return (
                    f"Order {order.id} contains {item_summary}. "
                    f"{shipment.carrier} shows ETA {shipment.eta}. "
                    f"Last update: {shipment.lastScan}."
                )
            if _prefers_turkish(message):
                return (
                    f"Sipariş {order.id} içeriği: {item_summary}. "
                    f"Güncel durum: {order.status}."
                )
            return f"Order {order.id} contains {item_summary}. Current status: {order.status}."

        if product:
            if _prefers_turkish(message):
                return (
                    f"{product.name} için mevcut stok {product.stock} {product.unit}. "
                    f"Günlük ortalama satış {round(store.average_daily_sales(product), 1)} {product.unit}; "
                    f"kalan stok yaklaşık {store.remaining_days(product)} gün yeter."
                )
            return (
                f"{product.name} has {product.stock} {product.unit} available. "
                f"Average daily sales are {round(store.average_daily_sales(product), 1)} {product.unit}; "
                f"remaining coverage is {store.remaining_days(product)} days."
            )

        if intent == "issue_check":
            issues = context["activeIssues"]
            if not issues:
                return (
                    "Şu anda açık operasyon hatası kayıtlı değil."
                    if _prefers_turkish(message)
                    else "No open operational issues are currently recorded."
                )

            issue_summary = "; ".join(
                f"{issue.title} ({issue.severity})" for issue in issues[:4]
            )
            if _prefers_turkish(message):
                return f"{len(issues)} açık operasyon hatası buldum: {issue_summary}."
            return f"I found {len(issues)} open operational issues: {issue_summary}."

        if intent == "shipment_risk":
            shipments = context["riskyShipments"]
            if not shipments:
                return (
                    "Şu anda açık kargo riski yok."
                    if _prefers_turkish(message)
                    else "There are no open shipment risks right now."
                )

            shipment_summary = "; ".join(
                f"order {shipment.orderId} via {shipment.carrier} is {shipment.risk}"
                for shipment in shipments[:4]
            )
            if _prefers_turkish(message):
                shipment_summary_tr = "; ".join(
                    f"sipariş {shipment.orderId} {shipment.carrier} ile {shipment.risk}"
                    for shipment in shipments[:4]
                )
                return f"{len(shipments)} kargo riski buldum: {shipment_summary_tr}."
            return f"I found {len(shipments)} shipment risks: {shipment_summary}."

        if intent == "return_exchange":
            return (
                "Mesajınızı aldık. İade veya değişim talebinizi kontrol edip sipariş bilgileriyle birlikte size dönüş yapacağız."
                if _prefers_turkish(message)
                else "We received your message. We will check the return or exchange request against the order details and follow up."
            )

        if intent == "complaint":
            return (
                "Mesajınızı aldık. Yaşadığınız sorunu sipariş ve ürün bilgileriyle birlikte kontrol edip size net bilgi vereceğiz."
                if _prefers_turkish(message)
                else "We received your message. We will review the issue against the order and product details and reply with a clear update."
            )

        if _prefers_turkish(message):
            return (
                "Açık siparişleri, stok risklerini, kargo istisnalarını ve operasyon hatalarını kontrol ettim. "
                f"{len(context['activeAlerts'])} stok uyarısı, "
                f"{len(context['riskyShipments'])} kargo riski ve "
                f"{len(context['activeIssues'])} açık hata var."
            )

        return (
            "I checked open orders, stock risks, shipment exceptions, and operational issues. "
            f"There are {len(context['activeAlerts'])} stock alerts, "
            f"{len(context['riskyShipments'])} shipment risks, and "
            f"{len(context['activeIssues'])} open issues."
        )

    def create_daily_task_plan(self, state: OperationsState) -> list[Task]:
        packing_tasks = [
            Task(
                id=f"auto-pack-{order.id}",
                owner="Depo",
                title=f"Sipariş {order.id} aynı gün teslim için hazırla",
                priority="high",
                orderId=order.id,
                status="open",
            )
            for order in state.orders
            if order.dueToday and order.status != "delivered"
        ]
        risk_tasks = [
            Task(
                id=f"auto-ship-{shipment.orderId}",
                owner="Müşteri Masası",
                title=f"Sipariş {shipment.orderId} için proaktif durum bildirimi gönder",
                priority="high" if shipment.risk == "delayed" else "medium",
                orderId=shipment.orderId,
                status="open",
            )
            for shipment in self.detect_shipping_risks(state)
        ]
        stock_tasks = [
            Task(
                id=f"auto-stock-{alert.productId}",
                owner="Satın Alma",
                title=f"{product.name} için stok yenileme planı hazırla",
                priority="high" if alert.severity == "critical" else "medium",
                status="open",
            )
            for alert in state.inventoryAlerts
            if not alert.resolved
            for product in state.products
            if product.id == alert.productId
        ]
        issue_tasks = [
            Task(
                id=f"auto-issue-{issue.id}",
                owner="Operasyon",
                title=f"Hata çöz: {issue.title}",
                priority="high" if issue.severity == "critical" else "medium",
                orderId=issue.entityId if issue.category in {"order", "shipping", "payment"} else None,
                status="open",
            )
            for issue in state.issues
            if not issue.resolved
        ]

        return dedupe_tasks(
            [*packing_tasks, *risk_tasks, *stock_tasks, *issue_tasks], state.tasks
        )


def create_chat_message(text: str, role: str) -> ChatMessage:
    return ChatMessage(
        id=str(uuid4()),
        role=role,  # type: ignore[arg-type]
        text=text,
        timestamp=datetime.now().strftime("%H:%M"),
    )


def summarize_order_items(order: Order, state: OperationsState) -> str:
    parts: list[str] = []
    for item in order.items:
        product = next((p for p in state.products if p.id == item.productId), None)
        parts.append(
            f"{item.quantity}x {product.name if product else 'Unknown product'}"
        )
    return ", ".join(parts)


def dedupe_tasks(next_tasks: list[Task], existing_tasks: list[Task]) -> list[Task]:
    existing_keys = {f"{t.owner}-{t.orderId}-{t.title}" for t in existing_tasks}
    return [
        t for t in next_tasks if f"{t.owner}-{t.orderId}-{t.title}" not in existing_keys
    ]


def _normalize(value: str) -> str:
    replacements = {
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u",
    }
    normalized = value.replace("İ", "i").replace("I", "i").lower()
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return re.sub(r"[^a-z0-9\s]", " ", normalized).strip()


def _product_match_tokens(value: str) -> set[str]:
    return {
        token
        for token in value.split()
        if len(token) >= 3 and token not in PRODUCT_MATCH_STOPWORDS
    }


def _prefers_turkish(message: str) -> bool:
    normalized = _normalize(message)
    turkish_markers = {
        "siparis",
        "stok",
        "durum",
        "durumu",
        "kargo",
        "hata",
        "bugun",
        "kalan",
        "var",
        "mi",
        "ne",
        "zaman",
        "gun",
        "gunluk",
    }
    return bool(turkish_markers & set(normalized.split())) or any(
        char in message for char in "çğıöşüÇĞİÖŞÜ"
    )


agent = OperationsAgent()
