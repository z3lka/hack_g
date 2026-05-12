import type { InventoryAlert, Product } from "../types";
import { average } from "../app/format";
import { StatusPill } from "../components/common";

export function StockPage({
  products,
  alerts,
  onDraft,
  disabled,
}: {
  products: Product[];
  alerts: InventoryAlert[];
  onDraft: (product: Product) => void;
  disabled: boolean;
}) {
  const alertsByProduct = new Map(
    alerts.map((alert) => [alert.productId, alert]),
  );

  return (
    <div className="page-content">
      <div className="page-panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">Stok Sayfası</p>
            <h2>Stok Tükenme Tahminleri</h2>
          </div>
        </div>
        <div className="table-wrap">
          <div className="table-head stock-cols">
            <span>Ürün</span>
            <span>Mevcut Stok</span>
            <span>Günlük Satış</span>
            <span>Kalan Gün</span>
            <span>Durum</span>
            <span>Aksiyon</span>
          </div>
          {products.map((product) => {
            const averageSales = average(product.weeklySales);
            const daysLeft = averageSales ? product.stock / averageSales : 99;
            const displayDaysLeft = Math.ceil(daysLeft);
            const alert = alertsByProduct.get(product.id);
            const tone =
              alert?.severity === "critical"
                ? "red"
                : alert
                  ? "yellow"
                  : daysLeft <= 7
                    ? "yellow"
                    : "green";

            return (
              <div
                className="table-row stock-cols"
                key={product.id}>
                <strong>{product.name}</strong>
                <span>
                  {product.stock} {product.unit}
                </span>
                <span>
                  {Math.round(averageSales)} {product.unit}/gün
                </span>
                <span className={`days-left ${tone}`}>
                  {displayDaysLeft} gün
                </span>
                <StatusPill status={tone} />
                {daysLeft <= 7 ? (
                  <button
                    className="btn-draft-sm"
                    onClick={() => onDraft(product)}
                    disabled={disabled}
                    type="button">
                    Sipariş Taslağı
                  </button>
                ) : (
                  <span className="table-empty-cell">-</span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
