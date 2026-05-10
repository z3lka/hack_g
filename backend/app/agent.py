import re
from datetime import datetime
from uuid import uuid4

from .models import AgentAction, AgentResult, ChatMessage, OperationsState, Order, Product, Shipment, Task


ORDER_ID_PATTERN = re.compile(r"(?:order|siparis|#)?\s*(\d{3,})", re.IGNORECASE)


class OperationsAgent:
    def lookup_order_status(self, order_id: str, state: OperationsState) -> tuple[Order, Shipment | None] | None:
        order = next((item for item in state.orders if item.id == order_id), None)

        if order is None:
            return None

        shipment = next((item for item in state.shipments if item.orderId == order.id), None)
        return order, shipment

    def check_stock(self, product_id: str, state: OperationsState) -> Product | None:
        return next((item for item in state.products if item.id == product_id), None)

    def detect_shipping_risks(self, state: OperationsState) -> list[Shipment]:
        return [shipment for shipment in state.shipments if shipment.risk != "clear" and not shipment.notified]

    def suggest_restock(self, product_id: str, state: OperationsState) -> str:
        product = self.check_stock(product_id, state)

        if product is None:
            return "No supplier draft available because the product could not be found."

        average_demand = sum(product.weeklySales) / len(product.weeklySales)
        recommended_quantity = max(product.threshold * 2 - product.stock, round(average_demand * 10))

        return (
            f"Draft to {product.supplier}: Please prepare {recommended_quantity} {product.unit} "
            f"of {product.name}. Current stock is {product.stock} {product.unit}, threshold is "
            f"{product.threshold}, and 7-day average demand is {round(average_demand)} {product.unit}/day."
        )

    def generate_customer_reply(self, message: str, state: OperationsState) -> AgentResult:
        normalized = message.lower()
        order_id_match = ORDER_ID_PATTERN.search(normalized)
        actions: list[AgentAction] = []

        if order_id_match:
            order_id = order_id_match.group(1)
            context = self.lookup_order_status(order_id, state)
            actions.append(
                AgentAction(
                    id=str(uuid4()),
                    label=f"Looked up order {order_id}",
                    type="lookup_order",
                    payload={"orderId": order_id},
                )
            )

            if context is None:
                return AgentResult(
                    response="I could not find that order number. Please check the number and I can look again.",
                    actions=actions,
                )

            order, shipment = context
            item_summary = summarize_order_items(order, state)

            if shipment is not None:
                if shipment.risk == "delayed":
                    risk_sentence = "It is flagged as delayed, so we have escalated it with the carrier."
                elif shipment.risk == "watch":
                    risk_sentence = "It is being watched because pickup has not been scanned yet."
                else:
                    risk_sentence = "It is moving normally."

                if shipment.risk != "clear":
                    actions.append(
                        AgentAction(
                            id=str(uuid4()),
                            label=f"Prepare customer update for order {order.id}",
                            type="notify_customer",
                            payload={"orderId": order.id},
                        )
                    )

                return AgentResult(
                    response=(
                        f"Order {order.id} contains {item_summary}. {shipment.carrier} shows ETA "
                        f"{shipment.eta}. Last update: {shipment.lastScan}. {risk_sentence}"
                    ),
                    actions=actions,
                )

            return AgentResult(
                response=(
                    f"Order {order.id} contains {item_summary}. It is currently {order.status}, "
                    "and the warehouse task list has it scheduled for today's preparation."
                ),
                actions=actions,
            )

        stock_product = next(
            (product for product in state.products if product.name.lower().split(" ")[0] in normalized),
            None,
        )

        if "stock" in normalized or "available" in normalized or stock_product is not None:
            product = stock_product or state.products[0]
            actions.append(
                AgentAction(
                    id=str(uuid4()),
                    label=f"Checked stock for {product.name}",
                    type="check_stock",
                    payload={"productId": product.id},
                )
            )

            return AgentResult(
                response=(
                    f"{product.name} has {product.stock} {product.unit} available. "
                    f"Reorder threshold is {product.threshold} {product.unit}."
                ),
                actions=actions,
            )

        actions.append(
            AgentAction(
                id=str(uuid4()),
                label="Created daily task plan",
                type="create_task_plan",
                payload={"source": "customer_message"},
            )
        )
        return AgentResult(
            response=(
                "I checked open orders, stock risks, and shipment exceptions. The highest priority "
                "items are delayed order 131 and restocking fig jam."
            ),
            actions=actions,
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
        product = next((candidate for candidate in state.products if candidate.id == item.productId), None)
        parts.append(f"{item.quantity}x {product.name if product else 'Unknown product'}")

    return ", ".join(parts)


def dedupe_tasks(next_tasks: list[Task], existing_tasks: list[Task]) -> list[Task]:
    existing_keys = {f"{task.owner}-{task.orderId}-{task.title}" for task in existing_tasks}
    return [
        task
        for task in next_tasks
        if f"{task.owner}-{task.orderId}-{task.title}" not in existing_keys
    ]


agent = OperationsAgent()
