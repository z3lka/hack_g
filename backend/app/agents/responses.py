from .. import store
from ..models import OperationsState, Order
from .text import summarize_order_items
from .types import ResolvedRequest


class ResponseGenerationMixin:
    def _order_summary_line(self, order: Order, state: OperationsState) -> str:
        customer = next(
            (
                candidate
                for candidate in state.customers
                if candidate.id == order.customerId
            ),
            None,
        )
        shipment = next(
            (
                candidate
                for candidate in state.shipments
                if candidate.orderId == order.id
            ),
            None,
        )
        shipment_text = (
            f", {shipment.carrier} ETA {shipment.eta}, risk {shipment.risk}"
            if shipment
            else ""
        )
        return (
            f"#{order.id} {order.status} for {customer.name if customer else order.customerId}, "
            f"{summarize_order_items(order, state)}, {order.total} TRY{shipment_text}"
        )

    def _order_summary_line_tr(self, order: Order, state: OperationsState) -> str:
        customer = next(
            (
                candidate
                for candidate in state.customers
                if candidate.id == order.customerId
            ),
            None,
        )
        shipment = next(
            (
                candidate
                for candidate in state.shipments
                if candidate.orderId == order.id
            ),
            None,
        )
        shipment_text = (
            f", {shipment.carrier} ETA {shipment.eta}, risk {shipment.risk}"
            if shipment
            else ""
        )
        return (
            f"#{order.id} {order.status}, müşteri {customer.name if customer else order.customerId}, "
            f"{summarize_order_items(order, state)}, {order.total} TRY{shipment_text}"
        )

    def _build_grounded_reply_prompt(
        self, message: str, context: ResolvedRequest, state: OperationsState
    ) -> str:
        context_lines = self._grounded_context_lines(context, state)

        return f"""
You are a helpful AI assistant for a small Turkish business (KOBİ).
A customer or staff member sent the following message.
Be concise, operational, and accurate. Use only the exact data below. Do not invent facts, dates, carriers, stock, totals, or actions.
If requested data is missing, say clearly that it was not found.

Customer/staff message:
"{message}"

Detected intent: {context["intent"]}

Exact data available for the reply:
{context_lines}

Reply in the conversation language with one short paragraph. No markdown.
""".strip()

    def _grounded_context_lines(
        self, context: ResolvedRequest, state: OperationsState
    ) -> str:
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
            customer = next(
                (c for c in state.customers if c.id == order.customerId), None
            )
            lines.append(
                f"Order {order.id}: status={order.status}, customer={customer.name if customer else order.customerId}, "
                f"items={summarize_order_items(order, state)}, total={order.total} TRY, dueToday={order.dueToday}."
            )
            if shipment:
                lines.append(
                    f"Shipment for order {order.id}: carrier={shipment.carrier}, tracking={shipment.trackingCode}, "
                    f"risk={shipment.risk}, eta={shipment.eta}, lastScan={shipment.lastScan}, notified={shipment.notified}."
                )
            elif context.get("intent") == "customer_update_draft":
                lines.append(
                    f"Shipment for order {order.id}: tracking is not available yet."
                )
        elif context.get("orderId"):
            lines.append(f"Order {context['orderId']} was not found.")

        matching_orders = context.get("matchingOrders") or []
        if matching_orders:
            label = context.get("orderCollectionLabel") or "matching"
            lines.append(f"{len(matching_orders)} {label} orders found.")
            for order in matching_orders[:12]:
                order_customer = next(
                    (item for item in state.customers if item.id == order.customerId),
                    None,
                )
                shipment = next(
                    (item for item in state.shipments if item.orderId == order.id),
                    None,
                )
                shipment_summary = (
                    f", shipment={shipment.carrier} eta={shipment.eta} risk={shipment.risk}"
                    if shipment
                    else ", shipment=N/A"
                )
                lines.append(
                    f"Order {order.id}: status={order.status}, customer={order_customer.name if order_customer else order.customerId}, "
                    f"items={summarize_order_items(order, state)}, total={order.total} TRY, dueToday={order.dueToday}{shipment_summary}."
                )

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

        return (
            "\n".join(f"- {line}" for line in lines)
            or "- No matching operational data found."
        )

    def _fallback_reply(
        self,
        message: str,
        context: ResolvedRequest,
        state: OperationsState,
    ) -> str:
        order_id = context.get("orderId")
        order_context = context.get("orderContext")
        product = context.get("product")
        customer = context.get("customer")
        intent = context.get("intent")
        matching_orders = context.get("matchingOrders") or []

        if matching_orders:
            label = context.get("orderCollectionLabel") or "matching"
            details = "; ".join(
                self._order_summary_line_tr(order, state)
                for order in matching_orders[:6]
            )
            return f"{len(matching_orders)} {label} sipariş buldum: {details}."

        if intent == "customer_lookup" and customer:
            latest = order_context[0] if order_context else None
            latest_text = (
                f" Son siparişi #{latest.id}, durum {latest.status}."
                if latest
                else " Kayıtlı yakın sipariş yok."
            )
            return (
                f"{customer.name}: varsayılan kanal {customer.channel}, telefon {customer.phone}, "
                f"e-posta {customer.email or 'N/A'}.{latest_text}"
            )

        if order_id:
            if order_context is None:
                return f"{order_id} numaralı siparişi bulamadım. Lütfen sipariş numarasını kontrol edin."
            order, shipment = order_context
            item_summary = summarize_order_items(order, state)
            if shipment:
                return (
                    f"Sipariş {order.id} içeriği: {item_summary}. "
                    f"Güncel durum: {order.status}. "
                    f"{shipment.carrier} ETA {shipment.eta}. "
                    f"Son güncelleme: {shipment.lastScan}."
                )
            return (
                f"Sipariş {order.id} içeriği: {item_summary}. "
                f"Güncel durum: {order.status}."
            )

        if product:
            return (
                f"{product.name} için mevcut stok {product.stock} {product.unit}. "
                f"Günlük ortalama satış {round(store.average_daily_sales(product), 1)} {product.unit}; "
                f"kalan stok yaklaşık {store.remaining_days(product)} gün yeter."
            )

        if intent == "issue_check":
            issues = context["activeIssues"]
            if not issues:
                return "Şu anda açık operasyon hatası kayıtlı değil."

            issue_summary = "; ".join(
                f"{issue.title} ({issue.severity})" for issue in issues[:4]
            )
            return f"{len(issues)} açık operasyon hatası buldum: {issue_summary}."

        if intent == "shipment_risk":
            shipments = context["riskyShipments"]
            if not shipments:
                return "Şu anda açık kargo riski yok."

            shipment_summary = "; ".join(
                f"sipariş {shipment.orderId} {shipment.carrier} ile {shipment.risk}"
                for shipment in shipments[:4]
            )
            return f"{len(shipments)} kargo riski buldum: {shipment_summary}."

        if intent == "return_exchange":
            return "Mesajınızı aldık. İade veya değişim talebinizi kontrol edip sipariş bilgileriyle birlikte size dönüş yapacağız."

        if intent == "complaint":
            return "Mesajınızı aldık. Yaşadığınız sorunu sipariş ve ürün bilgileriyle birlikte kontrol edip size net bilgi vereceğiz."

        return (
            "Açık siparişleri, stok risklerini, kargo istisnalarını ve operasyon hatalarını kontrol ettim. "
            f"{len(context['activeAlerts'])} stok uyarısı, "
            f"{len(context['riskyShipments'])} kargo riski ve "
            f"{len(context['activeIssues'])} açık hata var."
        )
