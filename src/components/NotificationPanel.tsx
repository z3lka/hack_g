import {
  AlertTriangle,
  CheckCircle2,
  ClipboardList,
  ShoppingBag,
  Truck,
  Users,
} from "lucide-react";
import type { ReactNode } from "react";
import type { NotificationAction, NotificationItem } from "../app/uiTypes";

export function NotificationPanel({
  items,
  onSelect,
}: {
  items: NotificationItem[];
  onSelect: (item: NotificationItem) => void;
}) {
  return (
    <div
      className="notification-panel"
      aria-label="Bildirimler">
      <div className="notification-panel-header">
        <div>
          <p className="eyebrow">Bildirimler</p>
          <strong>Aksiyon Bekleyenler</strong>
        </div>
        <span>{items.length}</span>
      </div>
      {items.length > 0 ? (
        <div className="notification-list">
          {items.map((item) => (
            <button
              className="notification-item"
              key={item.id}
              onClick={() => onSelect(item)}
              type="button">
              <span className={`notification-item-icon ${item.tone}`}>
                {notificationItemIcon(item)}
              </span>
              <span className="notification-copy">
                <strong>{item.title}</strong>
                <span>{item.description}</span>
                <small>{item.meta}</small>
              </span>
            </button>
          ))}
        </div>
      ) : (
        <div className="notification-empty">
          <CheckCircle2 size={20} />
          <span>Aksiyon gerektiren bildirim yok.</span>
        </div>
      )}
    </div>
  );
}

function notificationItemIcon(item: NotificationItem): ReactNode {
  const icons: Record<NotificationAction["type"], ReactNode> = {
    stock: <AlertTriangle size={15} />,
    shipment: <Truck size={15} />,
    issue: <AlertTriangle size={15} />,
    order: <ShoppingBag size={15} />,
    insight: <Users size={15} />,
    task: <ClipboardList size={15} />,
  };

  return icons[item.action.type];
}
