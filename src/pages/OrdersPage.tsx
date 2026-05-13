import { useMemo, useState } from "react";
import {
  CheckCircle2,
  ClipboardCheck,
  MapPin,
  PackageCheck,
  Truck,
  Warehouse,
  X,
} from "lucide-react";
import { formatCurrency, summarizeItems } from "../app/format";
import { labelStatus } from "../app/labels";
import { Empty, SegCtrl, StatusPill } from "../components/common";
import type { OperationsState, Order, OrderStatus, Shipment } from "../types";

type TimelineState = "done" | "current" | "todo";
type TimelineTone = "green" | "yellow" | "red" | "gray";
type TimelineIcon = typeof ClipboardCheck;

type TimelineStep = {
  label: string;
  detail: string;
  state: TimelineState;
  tone: TimelineTone;
  icon: TimelineIcon;
};

const statusTimelineIndex: Record<OrderStatus, number> = {
  new: 0,
  packing: 2,
  shipped: 4,
  delayed: 4,
  delivered: 6,
};

export function OrdersPage({
  state,
  filter,
  onFilterChange,
}: {
  state: OperationsState;
  filter: string;
  onFilterChange: (value: string) => void;
}) {
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const customersById = useMemo(
    () => new Map(state.customers.map((customer) => [customer.id, customer])),
    [state.customers],
  );
  const shipmentsByOrderId = useMemo(
    () => new Map(state.shipments.map((shipment) => [shipment.orderId, shipment])),
    [state.shipments],
  );
  const visibleOrders = state.orders.filter((order) => {
    if (filter === "Bugün") {
      return order.dueToday;
    }

    if (filter === "Risk") {
      const shipment = shipmentsByOrderId.get(order.id);
      return (
        order.status === "delayed" ||
        shipment?.risk === "delayed" ||
        shipment?.risk === "watch"
      );
    }

    return true;
  });
  const selectedOrder =
    visibleOrders.find((order) => order.id === selectedOrderId) ?? null;
  const selectedCustomer = selectedOrder
    ? customersById.get(selectedOrder.customerId)
    : null;
  const selectedShipment = selectedOrder
    ? shipmentsByOrderId.get(selectedOrder.id)
    : undefined;
  const selectedTimeline = selectedOrder
    ? buildOrderTimeline(selectedOrder, selectedShipment, state)
    : [];

  return (
    <div className="page-content">
      <div className={`orders-layout${selectedOrder ? " has-detail" : ""}`}>
        <div className="page-panel orders-table-panel">
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
              const customer = customersById.get(order.customerId);
              const shipment = shipmentsByOrderId.get(order.id);
              const isSelected = order.id === selectedOrderId;

              return (
                <button
                  className={`table-row orders-cols order-row${isSelected ? " active" : ""}`}
                  key={order.id}
                  onClick={() => setSelectedOrderId(order.id)}
                  type="button"
                  aria-label={`Sipariş ${order.id} durum panelini aç`}
                  aria-pressed={isSelected}>
                  <strong>#{order.id}</strong>
                  <span>{customer?.name}</span>
                  <StatusPill status={shipment?.risk ?? order.status} />
                  <span>{shipment?.carrier ?? "Depo"}</span>
                  <span>{shipment?.eta ?? "-"}</span>
                  <span className="note-cell">
                    {shipment?.lastScan ?? "Teslim bekleniyor"}
                  </span>
                </button>
              );
            })}
            {!visibleOrders.length && (
              <Empty text="Bu filtre için sipariş yok." />
            )}
          </div>
        </div>

        {selectedOrder && (
          <aside
            className="order-status-panel"
            aria-label={`Sipariş ${selectedOrder.id} durum detayı`}>
            <div className="order-status-header">
              <div>
                <p className="eyebrow">Sipariş durumu</p>
                <h3>#{selectedOrder.id}</h3>
              </div>
              <button
                className="order-status-close"
                onClick={() => setSelectedOrderId(null)}
                type="button"
                aria-label="Durum panelini kapat">
                <X size={16} />
              </button>
            </div>

            <div className="order-status-summary">
              <div>
                <span>Müşteri</span>
                <strong>{selectedCustomer?.name ?? selectedOrder.customerId}</strong>
              </div>
              <div>
                <span>Tutar</span>
                <strong>{formatCurrency(selectedOrder.total)}</strong>
              </div>
              <div>
                <span>Durum</span>
                <strong>{labelStatus(selectedOrder.status)}</strong>
              </div>
            </div>

            <div className="order-status-shipment">
              <Truck size={16} />
              <div>
                <strong>{selectedShipment?.carrier ?? "Kargo bekleniyor"}</strong>
                <span>
                  {selectedShipment
                    ? `${selectedShipment.trackingCode} - ETA ${formatTimelineDate(selectedShipment.eta)}`
                    : "Takip kodu henüz oluşmadı"}
                </span>
              </div>
            </div>

            <div className="order-timeline">
              {selectedTimeline.map((step) => {
                const Icon = step.icon;

                return (
                  <div
                    className={`order-timeline-item ${step.state} ${step.tone}`}
                    key={step.label}>
                    <div className="timeline-icon">
                      <Icon size={15} />
                    </div>
                    <div className="timeline-rail">
                      <span />
                    </div>
                    <div className="timeline-copy">
                      <strong>{step.label}</strong>
                      <span>{step.detail}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}

function buildOrderTimeline(
  order: Order,
  shipment: Shipment | undefined,
  state: OperationsState,
): TimelineStep[] {
  const currentIndex = getTimelineIndex(order, shipment);
  const currentTone = getCurrentTimelineTone(order, shipment);
  const steps = [
    {
      label: "Sipariş Alındı",
      detail: formatTimelineDate(order.createdAt),
      icon: ClipboardCheck,
    },
    {
      label: "Sipariş Onaylandı",
      detail: order.status === "new" ? "Onay bekliyor" : "Operasyon onayladı",
      icon: CheckCircle2,
    },
    {
      label: "Ürün Paketlendi",
      detail:
        order.status === "new"
          ? "Paketleme bekliyor"
          : summarizeItems(order, state),
      icon: PackageCheck,
    },
    {
      label: "Kargoya Verildi",
      detail: shipment
        ? `${shipment.carrier} - ${shipment.trackingCode}`
        : "Kargo teslimi bekleniyor",
      icon: Warehouse,
    },
    {
      label:
        order.status === "delayed" || shipment?.risk === "delayed"
          ? "Kargo Gecikmesi"
          : shipment?.risk === "watch"
            ? "Kargo İzlemede"
            : "Kargo Merkezinde",
      detail: shipment?.lastScan ?? "Henüz kargo taraması yok",
      icon: MapPin,
    },
    {
      label: "Dağıtıma Çıktı",
      detail:
        order.status === "delivered"
          ? "Teslimat turu tamamlandı"
          : shipment?.eta
            ? `Planlanan teslimat ${formatTimelineDate(shipment.eta)}`
            : "Teslimat planı bekleniyor",
      icon: Truck,
    },
    {
      label: "Teslim Edildi",
      detail:
        order.status === "delivered" ? "Teslimat tamamlandı" : "Beklemede",
      icon: CheckCircle2,
    },
  ];

  return steps.map((step, index) => {
    const stepState = getStepState(index, currentIndex);

    return {
      ...step,
      state: stepState,
      tone:
        stepState === "todo"
          ? "gray"
          : stepState === "current"
            ? currentTone
            : "green",
    };
  });
}

function getTimelineIndex(order: Order, shipment: Shipment | undefined) {
  if (order.status === "shipped" && isOutForDelivery(shipment)) {
    return 5;
  }

  return statusTimelineIndex[order.status];
}

function getStepState(index: number, currentIndex: number): TimelineState {
  if (index < currentIndex) {
    return "done";
  }

  if (index === currentIndex) {
    return "current";
  }

  return "todo";
}

function getCurrentTimelineTone(
  order: Order,
  shipment: Shipment | undefined,
): TimelineTone {
  if (order.status === "delayed" || shipment?.risk === "delayed") {
    return "red";
  }

  if (shipment?.risk === "watch") {
    return "yellow";
  }

  return "green";
}

function isOutForDelivery(shipment: Shipment | undefined) {
  const lastScan = shipment?.lastScan.toLocaleLowerCase("tr") ?? "";

  return lastScan.includes("dağıtım") || lastScan.includes("teslimat arac");
}

function formatTimelineDate(value: string): string {
  const normalized = value.includes("T") ? value : value.replace(" ", "T");
  const date = new Date(normalized);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("tr-TR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}
