from .. import store
from ..gemini_client import gemini_client
from ..memory import query_memory
from ..models import (
    AssistantInterpretation,
    ContactDraft,
    ContactDraftChannel,
    Customer,
    MessageEntities,
    OperationsState,
    Order,
    Product,
    Shipment,
)
from .constants import (
    BLOCKED_REPLY_SYSTEM_PROMPT,
    CONTACT_DRAFT_SCHEMA,
    CONTACT_DRAFT_SYSTEM_PROMPT,
    OPERATIONS_SYSTEM_PROMPT,
)
from .text import (
    _default_contact_channel,
    _fallback_contact_draft_payload,
    _tracking_url,
    get_channel_display_name,
)
from .types import ResolvedRequest


class DraftGenerationMixin:
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
        response_text = gemini_client.generate_text(
            prompt,
            system_instruction=OPERATIONS_SYSTEM_PROMPT,
        )

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

    def _build_contact_draft(
        self,
        message: str,
        context: ResolvedRequest,
        state: OperationsState,
        interpretation: AssistantInterpretation,
    ) -> ContactDraft | None:
        if context.get("customerOrderMismatch"):
            return None

        order_context = context.get("orderContext")
        customer = context.get("customer")
        product = context.get("product")
        if not customer:
            return None

        if not order_context and not context.get("directCustomerMessage"):
            return None

        order, shipment = order_context if order_context else (None, None)
        channel = context.get("requestedChannel") or _default_contact_channel(customer)
        tracking_url = _tracking_url(shipment) if shipment else None
        draft_payload = self._generate_contact_draft_payload(
            message,
            context,
            state,
            customer,
            order,
            shipment,
            tracking_url,
            product,
            channel,
        )
        confidence = interpretation.confidence
        review_reason = (
            interpretation.requiredReviewReason
            or "Owner review is required before any customer message is sent."
        )

        return ContactDraft(
            customerId=customer.id,
            customerName=customer.name,
            phone=customer.phone,
            email=customer.email,
            recommendedChannel=channel,
            subject=draft_payload["subject"],
            body=draft_payload["body"],
            entities=MessageEntities(
                orderId=order.id if order else None,
                productId=product.id if product else None,
                productName=product.name if product else None,
                customerId=customer.id,
                customerName=customer.name,
                customerEmail=customer.email,
                shipmentId=shipment.id if shipment else None,
                trackingCode=shipment.trackingCode if shipment else None,
            ),
            confidence=confidence,
            requiredReviewReason=review_reason,
            trackingUrl=tracking_url,
        )

    def _generate_contact_draft_payload(
        self,
        message: str,
        context: ResolvedRequest,
        state: OperationsState,
        customer: Customer,
        order: Order | None,
        shipment: Shipment | None,
        tracking_url: str | None,
        product: Product | None,
        channel: ContactDraftChannel,
    ) -> dict[str, str]:
        prompt = self._build_contact_draft_prompt(
            message,
            context,
            state,
            customer,
            order,
            shipment,
            tracking_url,
            product,
            channel,
        )
        payload = gemini_client.generate_json(
            prompt,
            CONTACT_DRAFT_SCHEMA,
            system_instruction=CONTACT_DRAFT_SYSTEM_PROMPT,
        )
        if payload:
            subject = str(payload.get("subject") or "").strip()
            body = str(payload.get("body") or "").strip()
            if subject and body:
                return {"subject": subject, "body": body}

        return _fallback_contact_draft_payload(
            message,
            customer,
            order,
            shipment,
            tracking_url,
            state,
            product,
            bool(context.get("directCustomerMessage")),
        )

    def _build_contact_draft_prompt(
        self,
        message: str,
        context: ResolvedRequest,
        state: OperationsState,
        customer: Customer,
        order: Order | None,
        shipment: Shipment | None,
        tracking_url: str | None,
        product: Product | None,
        channel: ContactDraftChannel,
    ) -> str:
        context_lines = self._grounded_context_lines(context, state)
        request_kind = (
            "direct customer message from owner"
            if context.get("directCustomerMessage")
            else "operational order/customer update"
        )
        order_note = (
            f"Order #{order.id} is explicitly part of the draft context."
            if order
            else "No order is explicitly part of this draft context."
        )
        shipment_note = (
            f"Tracking URL available: {tracking_url}"
            if shipment and tracking_url
            else "No tracking URL is available."
        )
        product_note = (
            f"Detected product: {product.name} ({product.id})."
            if product
            else "No product was confidently detected."
        )

        return f"""
Owner request:
"{message}"

Target customer:
- Name: {customer.name}
- Preferred channel in CRM: {customer.channel}
- Phone: {customer.phone}
- Email: {customer.email or "N/A"}

Draft channel to write for:
{get_channel_display_name(channel)}

Request kind:
{request_kind}

Context guardrails:
- {order_note}
- {shipment_note}
- {product_note}
- Use the customer-facing language implied by the owner request; do not add translation notes.
- If the owner request contains a quantity or status, preserve it exactly.
- If this is a direct customer message, do not add order number, order status, order contents, tracking, or unrelated products unless the owner explicitly asked for them.

Exact operational data available:
{context_lines}

Return strict JSON:
{{"subject":"short subject or chat title","body":"ready-to-send customer message"}}
""".strip()

    def _contact_draft_ready_reply(self, message: str, draft: ContactDraft) -> str:
        channel = get_channel_display_name(draft.recommendedChannel)
        prompt = f"""
Owner request:
"{message}"

Draft status:
- Customer: {draft.customerName}
- Channel: {channel}
- Draft is ready for owner review, not sent.

Write one short assistant confirmation to the owner.
""".strip()
        response_text = gemini_client.generate_text(
            prompt,
            system_instruction=OPERATIONS_SYSTEM_PROMPT,
        )
        if response_text:
            return response_text.strip()

        return (
            f"{draft.customerName} için {channel} kanalında incelemeye hazır "
            f"bir müşteri güncelleme taslağı oluşturdum."
        )

    def _contact_draft_blocked_reply(
        self,
        message: str,
        context: ResolvedRequest,
        state: OperationsState,
    ) -> str:
        response_text = self._llm_contact_draft_blocked_reply(message, context, state)
        if response_text:
            return response_text

        order_id = context.get("orderId")

        if context.get("customerOrderMismatch"):
            named_customer = context.get("namedCustomer")
            order_customer = context.get("orderCustomer")
            return (
                f"Sipariş {order_id}, {named_customer.name if named_customer else 'seçilen müşteri'} "
                f"yerine {order_customer.name if order_customer else 'başka bir müşteri'} "
                "adına kayıtlı. "
                "Bu nedenle taslak oluşturmadım."
            )

        if order_id and not context.get("orderContext"):
            return f"Sipariş {order_id} bulunamadı; müşteri mesajı taslağı oluşturmadım."

        if not context.get("customer"):
            return "Hedef müşteriyi belirleyemedim; taslak oluşturmadım."

        if not state.orders:
            return "Taslak oluşturmak için kullanılabilir sipariş yok."

        return "Taslak oluşturmak için sipariş ve müşteri bilgisini netleştirmem gerekiyor."

    def _llm_contact_draft_blocked_reply(
        self,
        message: str,
        context: ResolvedRequest,
        state: OperationsState,
    ) -> str | None:
        order_id = context.get("orderId") or "N/A"
        customer = context.get("customer")
        named_customer = context.get("namedCustomer")
        order_customer = context.get("orderCustomer")
        reasons: list[str] = []

        if context.get("customerOrderMismatch"):
            reasons.append(
                "Named customer does not match the order owner: "
                f"named={named_customer.name if named_customer else 'N/A'}, "
                f"orderOwner={order_customer.name if order_customer else 'N/A'}."
            )
        if context.get("orderId") and not context.get("orderContext"):
            reasons.append(f"Order {order_id} was not found.")
        if not customer:
            reasons.append("No target customer was identified.")
        if not state.orders:
            reasons.append("No orders are available.")
        if not reasons:
            reasons.append("A clear customer and order were not available.")

        prompt = f"""
Owner request:
"{message}"

Draft was blocked for these exact reasons:
{chr(10).join(f"- {reason}" for reason in reasons)}

Write one short reply to the owner.
""".strip()
        response_text = gemini_client.generate_text(
            prompt,
            system_instruction=BLOCKED_REPLY_SYSTEM_PROMPT,
        )
        return response_text.strip() if response_text else None

    def _build_customer_email_draft_prompt(
        self,
        message: str,
        subject: str,
        context: ResolvedRequest,
        state: OperationsState,
        interpretation: AssistantInterpretation,
    ) -> str:
        context_lines = self._grounded_context_lines(context, state)
        memory_context = "\n".join(f"- {item}" for item in interpretation.memory)

        return f"""
You are drafting a customer support email for a small Turkish business.
The business owner must approve this draft before it is sent.
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
        return (
            normalized
            if normalized.lower().startswith("re:")
            else f"Re: {normalized or 'Customer message'}"
        )

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
Prepare a ready-to-send supplier email draft in the language that best fits the supplier and business context.
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
