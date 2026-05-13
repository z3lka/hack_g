import type { OperationsState, ProactiveInsight } from "../types";
import { formatDate, namesMatch } from "../app/format";
import { labelStatus } from "../app/labels";
import { Empty, StatusPill } from "../components/common";

export function CustomersPage({
  state,
  insights,
}: {
  state: OperationsState;
  insights: ProactiveInsight[];
}) {
  const followUpInsights = insights.filter(
    (insight) => insight.actionType === "create_customer_reminder_draft",
  );
  const rows = state.customers.map((customer) => {
    const customerOrders = state.orders
      .filter((order) => order.customerId === customer.id)
      .sort(
        (left, right) =>
          new Date(right.createdAt).getTime() -
          new Date(left.createdAt).getTime(),
      );
    const latestOrder = customerOrders[0];
    const riskyShipment = state.shipments.find(
      (shipment) =>
        customerOrders.some((order) => order.id === shipment.orderId) &&
        shipment.risk !== "clear" &&
        !shipment.notified,
    );
    const followUpInsight = followUpInsights.find((insight) =>
      namesMatch(insight.entityName, customer.name),
    );
    const status = followUpInsight
      ? "risky"
      : riskyShipment
        ? "watch"
        : "healthy";
    const note =
      followUpInsight?.summary ??
      (riskyShipment
        ? `Kargo riski: sipariş ${riskyShipment.orderId}`
        : latestOrder
          ? `Son sipariş ${latestOrder.id} - ${labelStatus(latestOrder.status)}`
          : "Henüz sipariş yok");

    return {
      id: customer.id,
      name: customer.name,
      channel: customer.channel,
      lastOrder: latestOrder ? formatDate(latestOrder.createdAt) : "-",
      count: customerOrders.length,
      status,
      note,
    };
  });

  return (
    <div className="page-content">
      <div className="page-panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">Müşteriler</p>
            <h2>Müşteri Ritmi ve Takip Riski</h2>
          </div>
        </div>
        <div className="table-wrap">
          <div className="table-head customer-cols">
            <span>Müşteri</span>
            <span>Son Sipariş</span>
            <span>Kanal</span>
            <span>Sipariş</span>
            <span>Durum</span>
            <span>Not</span>
          </div>
          {rows.map((row) => (
            <div
              className="table-row customer-cols"
              key={row.id}>
              <strong>{row.name}</strong>
              <span>{row.lastOrder}</span>
              <span>{row.channel}</span>
              <span>{row.count} sipariş</span>
              <StatusPill status={row.status} />
              <span className="note-cell">{row.note}</span>
            </div>
          ))}
          {!rows.length && <Empty text="Kayıtlı müşteri yok." />}
        </div>
      </div>
    </div>
  );
}
