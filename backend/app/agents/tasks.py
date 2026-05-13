from ..models import OperationsState, Task


def dedupe_tasks(next_tasks: list[Task], existing_tasks: list[Task]) -> list[Task]:
    existing_keys = {f"{t.owner}-{t.orderId}-{t.title}" for t in existing_tasks}
    return [
        t for t in next_tasks if f"{t.owner}-{t.orderId}-{t.title}" not in existing_keys
    ]


class TaskPlanningMixin:
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
                orderId=(
                    issue.entityId
                    if issue.category in {"order", "shipping", "payment"}
                    else None
                ),
                status="open",
            )
            for issue in state.issues
            if not issue.resolved
        ]

        return dedupe_tasks(
            [*packing_tasks, *risk_tasks, *stock_tasks, *issue_tasks], state.tasks
        )
