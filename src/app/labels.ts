import type { MessageIntent } from "../types";

const statusLabels: Record<string, string> = {
  red: "Kritik",
  orange: "Öncelikli",
  yellow: "İzlemede",
  green: "İyi",
  blue: "Bilgi",
  critical: "Kritik",
  warning: "Uyarı",
  info: "Bilgi",
  clear: "Sorunsuz",
  watch: "İzlemede",
  delayed: "Gecikmiş",
  risky: "Riskli",
  healthy: "Sağlıklı",
  new: "Yeni",
  packing: "Paketleniyor",
  shipped: "Kargoda",
  delivered: "Teslim edildi",
  open: "Açık",
  done: "Tamamlandı",
  pending_review: "İncelemede",
  approved: "Onaylandı",
  sent: "Gönderildi",
  failed: "Başarısız",
  drafted: "Taslak hazır",
  closed: "Kapalı",
  ok: "Çalışıyor",
  degraded: "Sorunlu",
  disabled: "Pasif",
  error: "Hata",
};

const priorityLabels: Record<string, string> = {
  high: "Yüksek",
  medium: "Orta",
  low: "Düşük",
};

const intentLabels: Record<MessageIntent, string> = {
  customer_update_draft: "Müşteri güncelleme taslağı",
  order_lookup: "Sipariş sorgusu",
  stock_check: "Stok sorusu",
  shipment_risk: "Kargo takibi",
  issue_check: "Hata kontrolü",
  customer_lookup: "Müşteri sorgusu",
  task_summary: "Görev özeti",
  operations_summary: "Operasyon özeti",
  return_exchange: "İade/değişim",
  complaint: "Şikayet",
  general: "Genel",
  unknown: "Bilinmiyor",
};

const reviewReasonReplacements: Record<string, string> = {
  "Human approval is required before any customer email is sent.":
    "Müşteriye e-posta gönderilmeden önce insan onayı gerekiyor.",
  "Owner review is required before any customer message is sent.":
    "Müşteriye mesaj gönderilmeden önce işletme onayı gerekiyor.",
  "Order ID was inferred from the customer record.":
    "Sipariş numarası müşteri kaydından çıkarıldı.",
  "Order ID was inferred from the customer email rather than stated explicitly.":
    "Sipariş numarası mesajda açıkça yazmadığı için e-postadan çıkarıldı.",
  "Confidence below auto-send threshold.":
    "Güven skoru otomatik gönderim eşiğinin altında.",
  "No matching order was found for the customer.":
    "Müşteri için eşleşen sipariş bulunamadı.",
};

export function labelStatus(status: string): string {
  return statusLabels[status] ?? status.split("_").join(" ");
}

export function labelPriority(priority: string): string {
  return priorityLabels[priority] ?? priority;
}

export function labelIntent(intent: MessageIntent): string {
  return intentLabels[intent];
}

export function labelReviewReason(reason: string): string {
  return Object.entries(reviewReasonReplacements).reduce(
    (current, [source, replacement]) => current.split(source).join(replacement),
    reason,
  );
}
