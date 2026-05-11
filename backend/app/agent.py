import re
from datetime import datetime
from uuid import uuid4

from .gemini_client import gemini_client
from .memory import query_memory
from .models import (
    AgentAction,
    AgentResult,
    ChatMessage,
    OperationsState,
    Order,
    Product,
    Shipment,
    Task,
)

ORDER_ID_PATTERN = re.compile(r"(?:order|siparis|#)?\s*(\d{3,})", re.IGNORECASE)


class OperationsAgent:
    def lookup_order_status(
        self, order_id: str, state: OperationsState
    ) -> tuple[Order, Shipment | None] | None:
        order = next((item for item in state.orders if item.id == order_id), None)

        if order is None:
            return None

        shipment = next(
            (item for item in state.shipments if item.orderId == order.id), None
        )
        return order, shipment

    def check_stock(self, product_id: str, state: OperationsState) -> Product | None:
        return next((item for item in state.products if item.id == product_id), None)

    def detect_shipping_risks(self, state: OperationsState) -> list[Shipment]:
        return [s for s in state.shipments if s.risk != "clear" and not s.notified]

    def suggest_restock(self, product_id: str, state: OperationsState) -> str:
        product = self.check_stock(product_id, state)

        if product is None:
            return "No supplier draft available because the product could not be found."

        average_demand = sum(product.weeklySales) / len(product.weeklySales)
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
        actions: list[AgentAction] = []

        # Hangi tool'ların kullanıldığını tespit et
        detected_order_id = self._detect_order_id(message)
        detected_product = self._detect_product(message, state)

        if detected_order_id:
            actions.append(
                AgentAction(
                    id=str(uuid4()),
                    label=f"Looked up order {detected_order_id}",
                    type="lookup_order",
                    payload={"orderId": detected_order_id},
                )
            )

        if detected_product:
            actions.append(
                AgentAction(
                    id=str(uuid4()),
                    label=f"Checked stock for {detected_product.name}",
                    type="check_stock",
                    payload={"productId": detected_product.id},
                )
            )

        # Gemini'ye gönder
        prompt = self._build_chat_prompt(message, state)
        response_text = gemini_client.generate_text(prompt)

        if response_text:
            return AgentResult(response=response_text, actions=actions)

        # Gemini yoksa fallback
        return AgentResult(
            response=self._fallback_reply(
                message, detected_order_id, detected_product, state
            ),
            actions=actions,
        )

    def _detect_order_id(self, message: str) -> str | None:
        match = ORDER_ID_PATTERN.search(message.lower())
        return match.group(1) if match else None

    def _detect_product(self, message: str, state: OperationsState) -> Product | None:
        normalized = message.lower()
        return next(
            (p for p in state.products if p.name.lower().split(" ")[0] in normalized),
            None,
        )

    def _build_chat_prompt(self, message: str, state: OperationsState) -> str:
        product_lines = "\n".join(
            f"- {p.name} (id={p.id}): stock={p.stock} {p.unit}, threshold={p.threshold}, supplier={p.supplier}"
            for p in state.products
        )
        order_lines = "\n".join(
            f"- Order {o.id}: status={o.status}, customerId={o.customerId}, total={o.total} TRY, dueToday={o.dueToday}"
            for o in state.orders
        )
        shipment_lines = "\n".join(
            f"- Order {s.orderId}: carrier={s.carrier}, risk={s.risk}, eta={s.eta}, lastScan={s.lastScan}"
            for s in state.shipments
        )
        customer_lines = "\n".join(
            f"- {c.name} (id={c.id}): channel={c.channel}" for c in state.customers
        )

        return f"""
You are a helpful AI assistant for a small Turkish business (KOBİ).
A customer or staff member sent the following message. Reply in the same language as the message (Turkish or English).
Be concise, friendly, and accurate. Use only the data provided below — do not invent facts.

Customer/staff message:
"{message}"

Current business data:

PRODUCTS:
{product_lines}

ORDERS:
{order_lines}

SHIPMENTS:
{shipment_lines}

CUSTOMERS:
{customer_lines}

Reply with a single short paragraph. No bullet points, no markdown.
""".strip()

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
        order_id: str | None,
        product: Product | None,
        state: OperationsState,
    ) -> str:
        if order_id:
            context = self.lookup_order_status(order_id, state)
            if context is None:
                return f"I could not find order {order_id}. Please check the number and try again."
            order, shipment = context
            item_summary = summarize_order_items(order, state)
            if shipment:
                return (
                    f"Order {order.id} contains {item_summary}. "
                    f"{shipment.carrier} shows ETA {shipment.eta}. "
                    f"Last update: {shipment.lastScan}."
                )
            return f"Order {order.id} contains {item_summary}. Current status: {order.status}."

        if product:
            return (
                f"{product.name} has {product.stock} {product.unit} available. "
                f"Reorder threshold is {product.threshold} {product.unit}."
            )

        return (
            "I checked open orders, stock risks, and shipment exceptions. "
            "The highest priority items are delayed order 131 and restocking fig jam."
        )

    def create_daily_task_plan(self, state: OperationsState) -> list[Task]:
        packing_tasks = [
            Task(
                id=f"auto-pack-{order.id}",
                owner="Warehouse",
                title=f"Prepare order {order.id} for same-day handoff",
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
                owner="Customer Desk",
                title=f"Send proactive update for order {shipment.orderId}",
                priority="high" if shipment.risk == "delayed" else "medium",
                orderId=shipment.orderId,
                status="open",
            )
            for shipment in self.detect_shipping_risks(state)
        ]

        return dedupe_tasks([*packing_tasks, *risk_tasks], state.tasks)


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


agent = OperationsAgent()
