import type { OperationsState, ProactiveInsight } from "../types";
import { compactText, formatCurrency, summarizeItems } from "./format";
import type { NotificationItem } from "./uiTypes";

export function buildNotificationItems(
  state: OperationsState,
  actionableInsights: ProactiveInsight[],
): NotificationItem[] {
  const customersById = new Map(
    state.customers.map((customer) => [customer.id, customer]),
  );
  const ordersById = new Map(state.orders.map((order) => [order.id, order]));
  const productsById = new Map(
    state.products.map((product) => [product.id, product]),
  );
  const items: NotificationItem[] = [];

  state.inventoryAlerts
    .filter((alert) => !alert.resolved && alert.severity === "critical")
    .forEach((alert) => {
      const product = productsById.get(alert.productId);
      items.push({
        id: `stock-${alert.productId}`,
        tone: "red",
        title: `${product?.name ?? alert.productId} kritik stok`,
        description: alert.message,
        meta: product
          ? `${product.stock}/${product.threshold} ${product.unit}`
          : "Stok kontrolü",
        action: { type: "stock", productId: alert.productId },
      });
    });

  state.shipments
    .filter((shipment) => shipment.risk !== "clear" && !shipment.notified)
    .forEach((shipment) => {
      const order = ordersById.get(shipment.orderId);
      const customer = order ? customersById.get(order.customerId) : undefined;
      items.push({
        id: `shipment-${shipment.id}`,
        tone: shipment.risk === "delayed" ? "red" : "orange",
        title: `Kargo riski: #${shipment.orderId}`,
        description: `${shipment.carrier} · ${shipment.trackingCode}`,
        meta: customer
          ? `${customer.name} · ${shipment.lastScan}`
          : shipment.lastScan,
        action: { type: "shipment" },
      });
    });

  state.orders
    .filter((order) => order.dueToday && order.status !== "delivered")
    .forEach((order) => {
      const customer = customersById.get(order.customerId);
      items.push({
        id: `order-${order.id}`,
        tone: "blue",
        title: `Bugün teslim: #${order.id}`,
        description: `${customer?.name ?? "Müşteri"} · ${summarizeItems(order, state)}`,
        meta: `${order.status} · ${formatCurrency(order.total)}`,
        action: { type: "order" },
      });
    });

  actionableInsights
    .filter((insight) => insight.actionType === "create_customer_reminder_draft")
    .forEach((insight) => {
      items.push({
        id: `insight-${insight.id}`,
        tone: "yellow",
        title: insight.title,
        description: compactText(insight.summary, 100),
        meta: `${insight.entityName} · müşteri takibi`,
        action: { type: "insight", insightId: insight.id },
      });
    });

  state.tasks
    .filter((task) => task.status === "open" && task.priority === "high")
    .forEach((task) => {
      items.push({
        id: `task-${task.id}`,
        tone: "red",
        title: task.title,
        description: `${task.owner}${task.orderId ? ` · Sipariş ${task.orderId}` : ""}`,
        meta: "Yüksek öncelik",
        action: { type: "task" },
      });
    });

  return items;
}
