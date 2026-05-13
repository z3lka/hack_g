import {
  AlertTriangle,
  ArrowUpRight,
  Boxes,
  CheckCircle2,
  ClipboardList,
  ShoppingBag,
  Sparkles,
  Truck,
  UserRoundCheck,
  Users,
} from "lucide-react";
import type { InventoryAlert, OperationsState, ProactiveInsight } from "../types";
import {
  compactText,
  firstSentence,
  formatCurrency,
  formatTime,
  summarizeItems,
} from "../app/format";
import type { PageView } from "../app/uiTypes";
import { Empty, MetricCard, PriorityTag, StatusPill } from "../components/common";

export function DashboardPage({
  state,
  actionableInsights,
  insights,
  insightsGeneratedAt,
  isMutating,
  onNavigate,
  onInsightAction,
  onCompleteTask,
  onResolveInventoryAlert,
  onOpenShipmentDraft,
}: {
  state: OperationsState;
  actionableInsights: ProactiveInsight[];
  insights: ProactiveInsight[];
  insightsGeneratedAt: string;
  isMutating: boolean;
  onNavigate: (page: PageView, ordersFilter?: string) => void;
  onInsightAction: (insight: ProactiveInsight) => void;
  onCompleteTask: (taskId: string) => void;
  onResolveInventoryAlert: (alert: InventoryAlert) => void;
  onOpenShipmentDraft: (orderId: string) => void;
}) {
  const activeAlerts = state.inventoryAlerts.filter((alert) => !alert.resolved);
  const criticalAlerts = activeAlerts.filter(
    (alert) => alert.severity === "critical",
  );
  const dueToday = state.orders.filter(
    (order) => order.dueToday && order.status !== "delivered",
  );
  const openTasks = state.tasks.filter((task) => task.status === "open");
  const riskyShipments = state.shipments.filter(
    (shipment) => shipment.risk !== "clear" && !shipment.notified,
  );
  const activeOrders = state.orders.filter(
    (order) => order.status !== "delivered",
  );
  const followUpInsights = insights.filter(
    (insight) => insight.actionType === "create_customer_reminder_draft",
  );

  return (
    <div className="dashboard">
      <div className="metric-row">
        <MetricCard
          icon={<ShoppingBag size={20} />}
          label="Aktif Sipariş"
          value={activeOrders.length}
          sub={`${dueToday.length} bugün aksiyon`}
          color="green"
          onClick={() => onNavigate("orders", "Tümü")}
        />
        <MetricCard
          icon={<AlertTriangle size={20} />}
          label="Kritik Stok"
          value={criticalAlerts.length}
          sub={`${activeAlerts.length} ürün izleniyor`}
          color="red"
          onClick={() => onNavigate("stock")}
        />
        <MetricCard
          icon={<Users size={20} />}
          label="Takip Müşteri"
          value={followUpInsights.length}
          sub="ritim değişti"
          color="blue"
          onClick={() => onNavigate("customers")}
        />
        <MetricCard
          icon={<Truck size={20} />}
          label="Kargo Riski"
          value={riskyShipments.length}
          sub="bildirim bekliyor"
          color="orange"
          onClick={() => onNavigate("orders", "Risk")}
        />
      </div>

      <section className="section">
        <div className="section-header">
          <div>
            <p className="eyebrow">Sabah Özeti</p>
            <h2>Proaktif Uyarılar</h2>
          </div>
          <span className="badge-pill">
            {insightsGeneratedAt ? formatTime(insightsGeneratedAt) : "Yükleniyor"}
          </span>
        </div>
        <div className="insight-grid">
          {actionableInsights.length > 0 ? (
            actionableInsights.map((insight) => (
              <InsightCard
                key={insight.id}
                insight={insight}
                onAction={() => onInsightAction(insight)}
              />
            ))
          ) : (
            <div className="empty-full">
              <Sparkles size={22} />
              <span>Aksiyon gerektiren uyarı yok.</span>
            </div>
          )}
        </div>
      </section>

      <div className="dashboard-grid">
        <div className="dashboard-left">
          <section className="section">
            <div className="section-header">
              <div>
                <p className="eyebrow">Siparişler</p>
                <h2>Bugünkü Kontrol Panosu</h2>
              </div>
            </div>
            <div className="order-list">
              {dueToday.length > 0 ? (
                dueToday.map((order) => {
                  const customer = state.customers.find(
                    (item) => item.id === order.customerId,
                  );
                  const shipment = state.shipments.find(
                    (item) => item.orderId === order.id,
                  );

                  return (
                    <div
                      className="order-row"
                      key={order.id}>
                      <div className="order-row-left">
                        <span className="order-num">#{order.id}</span>
                        <div>
                          <strong>{customer?.name}</strong>
                          <span>{summarizeItems(order, state)}</span>
                        </div>
                      </div>
                      <div className="order-row-right">
                        <StatusPill status={shipment?.risk ?? order.status} />
                        <span className="order-amount">
                          {formatCurrency(order.total)}
                        </span>
                      </div>
                    </div>
                  );
                })
              ) : (
                <Empty text="Bugün aksiyon gerektiren sipariş yok." />
              )}
            </div>
          </section>

          <section className="section">
            <div className="section-header">
              <div>
                <p className="eyebrow">Görevler</p>
                <h2>Ekip Sırası</h2>
              </div>
              <ClipboardList
                size={18}
                className="section-icon"
              />
            </div>
            <div className="task-list">
              {openTasks.slice(0, 5).map((task) => (
                <div
                  className="task-row"
                  key={task.id}>
                  <button
                    className="check-btn"
                    onClick={() => onCompleteTask(task.id)}
                    disabled={isMutating}
                    aria-label="Tamamla"
                    type="button">
                    <CheckCircle2 size={16} />
                  </button>
                  <div className="task-info">
                    <strong>{task.title}</strong>
                    <span>
                      {task.owner}
                      {task.orderId ? ` · Sipariş ${task.orderId}` : ""}
                    </span>
                  </div>
                  <PriorityTag priority={task.priority} />
                </div>
              ))}
              {!openTasks.length && <Empty text="Tüm görevler tamamlandı." />}
            </div>
          </section>
        </div>

        <div className="dashboard-right">
          <section className="section">
            <div className="section-header">
              <div>
                <p className="eyebrow">Stok</p>
                <h2>Yeniden Sipariş Riskleri</h2>
              </div>
              <Boxes
                size={18}
                className="section-icon"
              />
            </div>
            <div className="alert-list">
              {activeAlerts.slice(0, 4).map((alert) => {
                const product = state.products.find(
                  (item) => item.id === alert.productId,
                );

                if (!product) {
                  return null;
                }

                const percent = Math.min(
                  100,
                  Math.round((product.stock / product.threshold) * 100),
                );

                return (
                  <div
                    className="alert-row"
                    key={alert.productId}>
                    <img
                      src={product.image}
                      alt=""
                      className="alert-thumb"
                    />
                    <div className="alert-info">
                      <strong>{product.name}</strong>
                      <span>{alert.message}</span>
                      <div className="stock-bar">
                        <div
                          className="stock-bar-fill"
                          style={{ width: `${percent}%` }}
                        />
                      </div>
                      <small>
                        {product.stock}/{product.threshold} {product.unit}
                      </small>
                    </div>
                    <button
                      className="btn-draft"
                      onClick={() => onResolveInventoryAlert(alert)}
                      disabled={isMutating}
                      type="button">
                      Taslak
                    </button>
                  </div>
                );
              })}
              {!activeAlerts.length && (
                <Empty text="Tüm stok uyarıları çözüldü." />
              )}
            </div>
          </section>

          <section className="section">
            <div className="section-header">
              <div>
                <p className="eyebrow">Kargo</p>
                <h2>Gecikmeler</h2>
              </div>
              <Truck
                size={18}
                className="section-icon"
              />
            </div>
            <div className="shipment-list">
              {riskyShipments.map((shipment) => (
                <div
                  className="shipment-row"
                  key={shipment.id}>
                  <div className="shipment-info">
                    <div className="shipment-top">
                      <span className="order-num">#{shipment.orderId}</span>
                      <StatusPill status={shipment.risk} />
                    </div>
                    <strong>{shipment.carrier}</strong>
                    <span>{shipment.lastScan}</span>
                  </div>
                  <button
                    className="btn-notify"
                    onClick={() => onOpenShipmentDraft(shipment.orderId)}
                    disabled={isMutating}
                    type="button">
                    <UserRoundCheck size={14} /> Bildir
                  </button>
                </div>
              ))}
              {!riskyShipments.length && (
                <Empty text="Bekleyen kargo bildirimi yok." />
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function InsightCard({
  insight,
  onAction,
}: {
  insight: ProactiveInsight;
  onAction: () => void;
}) {
  const title = translateInsightText(insight.title);
  const summary = compactText(firstSentence(translateInsightText(insight.summary)), 110);
  const buttonLabel =
    insight.actionType === "create_supplier_order_draft"
      ? "Sipariş Maili"
      : insight.actionType === "create_customer_reminder_draft"
        ? "WhatsApp Mesajı"
        : insight.actionType === "suggest_shipping_alternative"
          ? "Alternatif Göster"
          : "Detay";

  return (
    <article className={`insight-card ${insight.color}`}>
      <div className="insight-top">
        <span className="insight-dot" />
        <div className="insight-meta">
          <p className="eyebrow">{insight.entityName}</p>
          <h3>{title}</h3>
        </div>
      </div>
      <p className="insight-summary">{summary}</p>
      <button
        className="insight-btn"
        onClick={onAction}
        type="button">
        <ArrowUpRight size={14} />
        {buttonLabel}
      </button>
    </article>
  );
}

function translateInsightText(value: string): string {
  const translations: Record<string, string> = {
    "Critical Stock Out Risk": "Kritik Stok Tükenme Riski",
    "Immediate Restock Required": "Acil Stok Yenileme Gerekli",
    "Shipping Delay Follow-up": "Kargo Gecikmesi Takibi",
    "Urgent Supplier Confirmation": "Acil Tedarikçi Onayı",
    "Current stock is 9 jars with daily sales of 24.3, putting us at 1 day of inventory.":
      "Mevcut stok 9 kavanoz ve günlük satış 24,3; bu da yaklaşık 1 günlük stok kaldığını gösteriyor.",
    "Only 8 kg of tomatoes left with 15 kg/day sales; history shows we frequently run out on weekends.":
      "Günde 15 kg satışa karşı yalnızca 8 kg domates kaldı; geçmiş veriler hafta sonları sık sık tükendiğini gösteriyor.",
    "Customer order 131 has had no scan updates for 22 hours and is marked as delayed.":
      "Müşteri siparişi 131 için 22 saattir tarama güncellemesi yok ve gecikmiş olarak işaretlendi.",
    "Stock is at 18 sets, falling below the 20-set warning threshold; requires immediate supplier confirmation.":
      "Stok 18 sete düştü ve 20 setlik uyarı eşiğinin altında; acil tedarikçi onayı gerekiyor.",
  };

  return translations[value] ?? value;
}
