import type { OperationsState } from "../types";
import { Empty, SegCtrl, StatusPill } from "../components/common";

export function OrdersPage({
  state,
  filter,
  onFilterChange,
}: {
  state: OperationsState;
  filter: string;
  onFilterChange: (value: string) => void;
}) {
  const visibleOrders = state.orders.filter((order) => {
    if (filter === "Bugün") {
      return order.dueToday;
    }

    if (filter === "Risk") {
      const shipment = state.shipments.find(
        (item) => item.orderId === order.id,
      );
      return (
        order.status === "delayed" ||
        shipment?.risk === "delayed" ||
        shipment?.risk === "watch"
      );
    }

    return true;
  });

  return (
    <div className="page-content">
      <div className="page-panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">Siparişler</p>
            <h2>Aktif Siparişler</h2>
          </div>
          <SegCtrl
            value={filter}
            options={["Tümü", "Bugün", "Risk"]}
            onChange={onFilterChange}
          />
        </div>
        <div className="table-wrap">
          <div className="table-head orders-cols">
            <span>Sipariş</span>
            <span>Müşteri</span>
            <span>Durum</span>
            <span>Kargo</span>
            <span>ETA</span>
            <span>Not</span>
          </div>
          {visibleOrders.map((order) => {
            const customer = state.customers.find(
              (item) => item.id === order.customerId,
            );
            const shipment = state.shipments.find(
              (item) => item.orderId === order.id,
            );

            return (
              <div
                className="table-row orders-cols"
                key={order.id}>
                <strong>#{order.id}</strong>
                <span>{customer?.name}</span>
                <StatusPill status={shipment?.risk ?? order.status} />
                <span>{shipment?.carrier ?? "Depo"}</span>
                <span>{shipment?.eta ?? "-"}</span>
                <span className="note-cell">
                  {shipment?.lastScan ?? "Teslim bekleniyor"}
                </span>
              </div>
            );
          })}
          {!visibleOrders.length && (
            <Empty text="Bu filtre için sipariş yok." />
          )}
        </div>
      </div>
    </div>
  );
}
