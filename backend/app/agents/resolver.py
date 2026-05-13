from uuid import uuid4

from ..commerce import get_commerce_connector
from ..gemini_client import gemini_client
from ..memory import query_memory
from ..models import (
    AgentAction,
    AssistantInterpretation,
    Customer,
    MessageEntities,
    OperationsState,
    Order,
    Product,
)
from .constants import INTENTS, INTENT_SCHEMA, OPERATIONS_SYSTEM_PROMPT
from .text import (
    CUSTOMER_MATCH_STOPWORDS,
    ORDER_ID_PATTERN,
    _detect_requested_channel,
    _has_direct_customer_message_content,
    _is_customer_update_request,
    _looks_like_customer_lookup,
    _normalize,
    _phrase_in_normalized_text,
    _product_match_tokens,
)
from .types import ResolvedRequest


class RequestResolverMixin:
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
            if _phrase_in_normalized_text(normalized, alias):
                product = self.check_stock(product_id, state)
                if product:
                    return product

        query_tokens = _product_match_tokens(normalized)
        best_product: Product | None = None
        best_score = 0

        for product in state.products:
            product_name = _normalize(product.name)
            product_tokens = _product_match_tokens(product_name)

            if _phrase_in_normalized_text(normalized, product_name):
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
                  - customer_update_draft: owner asks to send, message, tell, or update a customer through WhatsApp, Telegram, or email
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

                  For order collection questions, set:
                  - orderStatus to one of new, packing, shipped, delayed, delivered when the user asks for orders by status.
                  - orderTimeframe to due_today when the user asks for orders due, expected, or needing action today.
                  Leave those fields empty when they are not part of the request.
                  Classify by meaning from the full message. Do not require language flags or caller-provided locale hints.

                  Products:
                  {product_lines}

                  Customers:
                  {customer_lines}
                  """.strip()
        payload = gemini_client.generate_json(
            prompt,
            INTENT_SCHEMA,
            system_instruction=OPERATIONS_SYSTEM_PROMPT,
        )

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
    ) -> ResolvedRequest:
        if interpretation:
            intent_payload = {
                "intent": interpretation.intent,
                "orderId": interpretation.entities.orderId or "",
                "orderStatus": interpretation.entities.orderStatus or "",
                "orderTimeframe": interpretation.entities.orderTimeframe or "",
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
        explicit_channel = _detect_requested_channel(message)
        direct_customer_message = _has_direct_customer_message_content(
            message,
            product,
        )

        if intent not in INTENTS:
            intent = self._heuristic_intent(message, order_id, product, customer)

        if _is_customer_update_request(message):
            intent = "customer_update_draft"

        order_status_filter = self._order_status_filter(intent_payload)
        order_timeframe_filter = self._order_timeframe_filter(intent_payload)
        order_resolved_from_customer = False
        can_infer_order = intent in {
            "order_lookup",
            "shipment_risk",
            "customer_lookup",
        } or (intent == "customer_update_draft" and not direct_customer_message)
        if not order_id and customer and can_infer_order:
            latest_order = self._latest_order_for_customer(customer, state)
            if latest_order:
                order_id = latest_order.id
                order_resolved_from_customer = True

        order_context = self.lookup_order_status(order_id, state) if order_id else None
        named_customer = customer
        order_customer = None
        customer_order_mismatch = False
        if order_context:
            order, _ = order_context
            order_customer = next(
                (
                    candidate
                    for candidate in state.customers
                    if candidate.id == order.customerId
                ),
                None,
            )
            if intent == "customer_update_draft":
                if (
                    named_customer
                    and order_customer
                    and named_customer.id != order_customer.id
                ):
                    customer_order_mismatch = True
                elif order_customer and not customer:
                    customer = order_customer

        matching_orders = (
            self._matching_orders_for_filters(
                state,
                order_status_filter,
                order_timeframe_filter,
            )
            if (
                intent == "order_lookup"
                and not order_id
                and (order_status_filter or order_timeframe_filter)
            )
            else []
        )
        active_issues = [issue for issue in state.issues if not issue.resolved]
        active_alerts = get_commerce_connector().stock_alerts(state)
        risky_shipments = self.detect_shipping_risks(state)
        open_tasks = [task for task in state.tasks if task.status == "open"]

        return ResolvedRequest(
            intent=intent,
            orderId=order_id,
            orderStatusFilter=order_status_filter,
            orderTimeframeFilter=order_timeframe_filter,
            orderResolvedFromCustomer=order_resolved_from_customer,
            orderContext=order_context,
            product=product,
            customer=customer,
            namedCustomer=named_customer,
            orderCustomer=order_customer,
            customerOrderMismatch=customer_order_mismatch,
            requestedChannel=explicit_channel,
            directCustomerMessage=direct_customer_message,
            matchingOrders=matching_orders,
            orderCollectionLabel=self._order_collection_label(
                order_status_filter,
                order_timeframe_filter,
            ),
            activeIssues=active_issues,
            activeAlerts=active_alerts,
            riskyShipments=risky_shipments,
            openTasks=open_tasks,
            memoryRecords=interpretation.memory if interpretation else [],
        )

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
        message_tokens = set(normalized.split())
        for customer in state.customers:
            if _normalize(customer.name) in normalized:
                return customer
            if customer.email and _normalize(customer.email) in normalized:
                return customer
            name_tokens = {
                token
                for token in _normalize(customer.name).split()
                if len(token) >= 3 and token not in CUSTOMER_MATCH_STOPWORDS
            }
            if name_tokens & message_tokens:
                return customer

        return None

    def _latest_order_for_customer(
        self,
        customer: Customer,
        state: OperationsState,
    ) -> Order | None:
        customer_orders = [
            order for order in state.orders if order.customerId == customer.id
        ]
        if not customer_orders:
            return None

        return sorted(customer_orders, key=lambda order: order.createdAt, reverse=True)[
            0
        ]

    def _entities_for_context(self, context: ResolvedRequest) -> MessageEntities:
        product = context.get("product")
        customer = context.get("customer")
        order_context = context.get("orderContext")
        shipment = order_context[1] if order_context else None

        return MessageEntities(
            orderId=context.get("orderId"),
            orderStatus=context.get("orderStatusFilter"),
            orderTimeframe=context.get("orderTimeframeFilter"),
            productId=product.id if product else None,
            productName=product.name if product else None,
            customerId=customer.id if customer else None,
            customerName=customer.name if customer else None,
            customerEmail=customer.email if customer else None,
            shipmentId=shipment.id if shipment else None,
            trackingCode=shipment.trackingCode if shipment else None,
        )

    def _confidence_for_context(self, context: ResolvedRequest) -> float:
        intent = context.get("intent")

        if intent == "customer_update_draft":
            if context.get("customerOrderMismatch"):
                return 0.2
            if context.get("directCustomerMessage") and context.get("customer"):
                return 0.88
            if context.get("orderContext") and context.get("customer"):
                return 0.82 if context.get("orderResolvedFromCustomer") else 0.94
            if context.get("orderId") and not context.get("orderContext"):
                return 0.32
            return 0.45

        if context.get("matchingOrders"):
            return 0.88

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

    def _required_review_reason(
        self, context: ResolvedRequest, confidence: float
    ) -> str | None:
        reasons = ["Human approval is required before any customer email is sent."]

        if context.get("intent") == "customer_update_draft":
            reasons = ["Owner review is required before any customer message is sent."]
            if context.get("requestedChannel"):
                reasons.append(f"Requested channel: {context['requestedChannel']}.")
            if context.get("orderResolvedFromCustomer"):
                reasons.append("Order ID was inferred from the customer record.")
            if context.get("customerOrderMismatch"):
                reasons.append("Named customer does not match the order owner.")
            if context.get("orderId") and not context.get("orderContext"):
                reasons.append("No matching order was found.")
            if not context.get("customer"):
                reasons.append("No target customer was identified.")
            if confidence < 0.7:
                reasons.append(
                    "Assistant confidence is below the auto-clear threshold."
                )
            return " ".join(reasons)

        if context.get("intent") in {
            "order_lookup",
            "shipment_risk",
        } and not context.get("orderContext"):
            reasons.append("No matching order was found.")

        if context.get("orderResolvedFromCustomer"):
            reasons.append(
                "Order ID was inferred from the customer email rather than stated explicitly."
            )

        if context.get("intent") == "stock_check" and not context.get("product"):
            reasons.append("The requested product was not identified.")

        if confidence < 0.7:
            reasons.append("Assistant confidence is below the auto-clear threshold.")

        return " ".join(reasons)

    def _memory_query_for_context(self, message: str, context: ResolvedRequest) -> str:
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
        self,
        message: str,
        order_id: str | None,
        product: Product | None,
        customer: Customer | None,
    ) -> str:
        normalized = _normalize(message)

        if _is_customer_update_request(message):
            return "customer_update_draft"

        if order_id:
            return "order_lookup"

        if _looks_like_customer_lookup(normalized):
            return "customer_lookup"

        if any(
            word in normalized
            for word in [
                "iade",
                "degisim",
                "iptal",
                "refund",
                "return",
                "exchange",
                "cancel",
            ]
        ):
            return "return_exchange"

        if any(
            word in normalized
            for word in [
                "sikayet",
                "kirik",
                "hasar",
                "yanlis",
                "complaint",
                "damaged",
                "wrong",
                "broken",
            ]
        ):
            return "complaint"

        if product or any(
            word in normalized for word in ["stok", "stock", "kalan", "restock"]
        ):
            return "stock_check"

        if any(
            word in normalized
            for word in [
                "hata",
                "error",
                "issue",
                "uyari",
                "warning",
                "problem",
                "fail",
            ]
        ):
            return "issue_check"

        if any(word in normalized for word in ["kargo", "cargo", "shipment", "teslim"]):
            return "shipment_risk"

        if any(word in normalized for word in ["gorev", "task", "todo"]):
            return "task_summary"

        if customer:
            return "order_lookup"

        return "operations_summary"

    def _order_status_filter(self, intent_payload: dict[str, str]) -> str | None:
        status = (intent_payload.get("orderStatus") or "").strip().lower()
        valid_statuses = {"new", "packing", "shipped", "delayed", "delivered"}
        return status if status in valid_statuses else None

    def _order_timeframe_filter(self, intent_payload: dict[str, str]) -> str | None:
        timeframe = (intent_payload.get("orderTimeframe") or "").strip().lower()
        return timeframe if timeframe == "due_today" else None

    def _actions_for_context(
        self,
        context: ResolvedRequest,
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
                    payload={
                        "orderId": shipment.orderId,
                        "trackingCode": shipment.trackingCode,
                    },
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

    def _matching_orders_for_filters(
        self,
        state: OperationsState,
        status_filter: str | None,
        timeframe_filter: str | None,
    ) -> list[Order]:
        orders = state.orders

        if status_filter:
            orders = [order for order in orders if order.status == status_filter]

        if timeframe_filter == "due_today":
            orders = [
                order
                for order in orders
                if order.dueToday and (status_filter or order.status != "delivered")
            ]

        return orders

    def _order_collection_label(
        self,
        status_filter: str | None,
        timeframe_filter: str | None,
    ) -> str:
        if status_filter and timeframe_filter == "due_today":
            return f"{status_filter} due today"
        if status_filter:
            return status_filter
        if timeframe_filter == "due_today":
            return "due today"
        return "matching"

    def _interpret_message(
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
        memory_records = query_memory(
            self._memory_query_for_context(message, context), limit=4
        )
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
