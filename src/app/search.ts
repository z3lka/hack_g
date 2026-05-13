import type {
  ChatMessage,
  CustomerThread,
  MemoryRecord,
  OperationsState,
  ProactiveInsight,
} from "../types";
import {
  compactText,
  formatCurrency,
  formatDate,
  normalizeSearch,
  summarizeItems,
} from "./format";
import { labelIntent, labelPriority, labelStatus } from "./labels";
import type { SearchResult, SearchResultKind } from "./uiTypes";

export const searchKindOrder: SearchResultKind[] = [
  "product",
  "customer",
  "order",
  "shipment",
  "issue",
  "message",
  "thread",
  "alert",
  "task",
  "insight",
  "memory",
];

export const searchKindLabels: Record<SearchResultKind, string> = {
  product: "Ürünler",
  customer: "Müşteriler",
  order: "Siparişler",
  shipment: "Takip",
  issue: "Operasyon Hataları",
  message: "Mesajlar",
  thread: "Gelen Kutusu",
  alert: "Stok Uyarıları",
  task: "Görevler",
  insight: "İçgörüler",
  memory: "Hafıza",
};

export function buildGlobalSearchResults({
  state,
  messages,
  inboxThreads,
  insights,
  memoryRecords,
  query,
}: {
  state: OperationsState;
  messages: ChatMessage[];
  inboxThreads: CustomerThread[];
  insights: ProactiveInsight[];
  memoryRecords: MemoryRecord[];
  query: string;
}): SearchResult[] {
  const normalizedQuery = normalizeSearch(query);

  if (!normalizedQuery) {
    return [];
  }

  const activeAlerts = state.inventoryAlerts.filter((alert) => !alert.resolved);
  const alertsByProduct = new Map(
    activeAlerts.map((alert) => [alert.productId, alert]),
  );
  const customersById = new Map(
    state.customers.map((customer) => [customer.id, customer]),
  );
  const shipmentsByOrder = new Map(
    state.shipments.map((shipment) => [shipment.orderId, shipment]),
  );
  const results: SearchResult[] = [];

  function add(result: SearchResult) {
    if (matchesSearchResult(result, normalizedQuery)) {
      results.push(result);
    }
  }

  state.products.forEach((product) => {
    const alert = alertsByProduct.get(product.id);
    add({
      id: `product-${product.id}`,
      kind: "product",
      title: product.name,
      description: `${product.category} · ${product.supplier}`,
      meta: `SKU ${product.sku} · ${product.stock}/${product.threshold} ${product.unit}`,
      keywords: [
        "ürün product stok stock",
        alert?.severity === "critical" ? "kritik critical" : "",
        alert?.message ?? "",
      ],
      target: { type: "page", page: "stock" },
    });
  });

  state.customers.forEach((customer) => {
    add({
      id: `customer-${customer.id}`,
      kind: "customer",
      title: customer.name,
      description: `${customer.channel} · ${customer.phone}`,
      meta: "Müşteri kaydı",
      keywords: ["müşteri customer takip follow-up"],
      target: { type: "page", page: "customers" },
    });
  });

  state.orders.forEach((order) => {
    const customer = customersById.get(order.customerId);
    const shipment = shipmentsByOrder.get(order.id);
    const shipmentRisk =
      shipment?.risk === "delayed" || shipment?.risk === "watch";
    const ordersFilter =
      order.status === "delayed" || shipmentRisk
        ? "Risk"
        : order.dueToday
          ? "Bugün"
          : "Tümü";

    add({
      id: `order-${order.id}`,
      kind: "order",
      title: `Sipariş #${order.id}`,
      description: `${customer?.name ?? "Müşteri"} · ${summarizeItems(order, state)}`,
      meta: `${labelStatus(order.status)} · ${formatCurrency(order.total)} · ${formatDate(order.createdAt)}`,
      keywords: [
        "sipariş order",
        order.dueToday ? "bugün today teslim" : "",
        shipment?.trackingCode ?? "",
        shipment?.carrier ?? "",
        shipment?.lastScan ?? "",
      ],
      target: { type: "page", page: "orders", ordersFilter },
    });
  });

  state.shipments.forEach((shipment) => {
    const order = state.orders.find(
      (candidate) => candidate.id === shipment.orderId,
    );
    const customer = order ? customersById.get(order.customerId) : undefined;

    add({
      id: `shipment-${shipment.id}`,
      kind: "shipment",
      title: shipment.trackingCode,
      description: `#${shipment.orderId} · ${shipment.carrier} · ${customer?.name ?? "Müşteri"}`,
      meta: `${labelStatus(shipment.risk)} · ${shipment.eta} · ${shipment.city}`,
      keywords: [
        "takip tracking kargo shipment",
        shipment.lastScan,
        shipment.notified ? "bildirildi" : "bildirim bekliyor",
      ],
      target: {
        type: "page",
        page: "orders",
        ordersFilter: shipment.risk === "clear" ? "Tümü" : "Risk",
      },
    });
  });

  state.issues.forEach((issue) => {
    add({
      id: `issue-${issue.id}`,
      kind: "issue",
      title: issue.title,
      description: issue.message,
      meta: `${labelStatus(issue.severity)} · ${issue.source}`,
      keywords: [
        "hata error issue problem uyarı warning operasyon",
        issue.category,
        issue.entityId ?? "",
      ],
      target: { type: "page", page: "dashboard" },
    });
  });

  messages.forEach((message) => {
    add({
      id: `message-${message.id}`,
      kind: "message",
      title: message.role === "customer" ? "Müşteri mesajı" : "Asistan mesajı",
      description: compactText(message.text, 120),
      meta: message.timestamp,
      keywords: ["mesaj message sohbet chat"],
      target: { type: "chat" },
    });
  });

  inboxThreads.forEach((thread) => {
    const latestMessage = [...thread.messages]
      .reverse()
      .find((message) => message.direction === "inbound");
    const latestDraft = thread.drafts[thread.drafts.length - 1];

    add({
      id: `thread-${thread.id}`,
      kind: "thread",
      title: `${thread.customerName} · ${thread.subject}`,
      description: compactText(latestMessage?.body ?? "E-posta konuşması", 120),
      meta: `${labelStatus(thread.status)} · ${
        latestDraft ? labelIntent(latestDraft.intent) : "Bilinmiyor"
      }`,
      keywords: [
        "email inbox gelen kutusu müşteri mesaj",
        thread.customerEmail,
        latestDraft?.requiredReviewReason ?? "",
        latestDraft?.body ?? "",
      ],
      target: { type: "page", page: "inbox" },
    });
  });

  activeAlerts.forEach((alert) => {
    const product = state.products.find(
      (candidate) => candidate.id === alert.productId,
    );

    add({
      id: `alert-${alert.productId}`,
      kind: "alert",
      title: `${product?.name ?? alert.productId} stok ${labelStatus(alert.severity)}`,
      description: alert.message,
      meta: alert.severity === "critical" ? "Kritik stok" : "Stok uyarısı",
      keywords: ["stok stock kritik critical uyarı alert"],
      target: { type: "page", page: "stock" },
    });
  });

  state.tasks.forEach((task) => {
    add({
      id: `task-${task.id}`,
      kind: "task",
      title: task.title,
      description: `${task.owner}${task.orderId ? ` · Sipariş ${task.orderId}` : ""}`,
      meta: `${labelPriority(task.priority)} · ${labelStatus(task.status)}`,
      keywords: ["görev task aksiyon action"],
      target: { type: "page", page: "dashboard" },
    });
  });

  insights.forEach((insight) => {
    add({
      id: `insight-${insight.id}`,
      kind: "insight",
      title: insight.title,
      description: compactText(insight.summary, 120),
      meta: `${insight.entityName} · ${labelStatus(insight.color)}`,
      keywords: [
        "içgörü insight uyarı alert proaktif",
        insight.evidence.join(" "),
        insight.draftAction,
      ],
      target: {
        type: "page",
        page: "memory",
        memorySearch: query.trim(),
      },
    });
  });

  memoryRecords.forEach((record) => {
    add({
      id: `memory-${record.id}`,
      kind: "memory",
      title: record.entityName ?? record.category,
      description: compactText(record.text, 120),
      meta: `${record.category} · ${record.eventDate ?? "tarihsiz"}`,
      keywords: ["hafıza memory kayıt record"],
      target: {
        type: "page",
        page: "memory",
        memorySearch: query.trim(),
      },
    });
  });

  return results
    .sort((left, right) => {
      const leftScore = scoreSearchResult(left, normalizedQuery);
      const rightScore = scoreSearchResult(right, normalizedQuery);

      return (
        leftScore - rightScore ||
        searchKindOrder.indexOf(left.kind) - searchKindOrder.indexOf(right.kind)
      );
    })
    .slice(0, 24);
}

function matchesSearchResult(
  result: SearchResult,
  normalizedQuery: string,
): boolean {
  const haystack = normalizeSearch(
    [result.title, result.description, result.meta, ...result.keywords].join(" "),
  );

  return normalizedQuery
    .split(" ")
    .filter(Boolean)
    .every((part) => haystack.includes(part));
}

function scoreSearchResult(
  result: SearchResult,
  normalizedQuery: string,
): number {
  const title = normalizeSearch(result.title);
  const description = normalizeSearch(result.description);

  if (title.startsWith(normalizedQuery)) {
    return 0;
  }

  if (title.includes(normalizedQuery)) {
    return 1;
  }

  if (description.includes(normalizedQuery)) {
    return 2;
  }

  return 3;
}
