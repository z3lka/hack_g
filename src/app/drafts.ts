import type { OperationsState, Product, ProactiveInsight } from "../types";
import { namesMatch } from "./format";
import type {
  DraftTarget,
  DraftTargetKind,
  FloatingMockChannel,
  MockSendChannel,
} from "./uiTypes";

export function getDraftTitle(insight: ProactiveInsight): string {
  const titles: Record<string, string> = {
    create_supplier_order_draft: "Tedarikçi Sipariş Maili",
    create_customer_reminder_draft: "WhatsApp Hatırlatması",
    suggest_shipping_alternative: "Kargo Alternatifi",
  };
  return titles[insight.actionType] ?? "Taslak";
}

export function getDraftTargetForInsight(
  insight: ProactiveInsight,
  state: OperationsState,
): DraftTarget {
  if (insight.actionType === "create_customer_reminder_draft") {
    const customer = state.customers.find((candidate) =>
      namesMatch(insight.entityName, candidate.name),
    );

    return buildDraftTarget(
      customer?.name ?? insight.entityName,
      "customer",
      customer?.phone,
    );
  }

  if (insight.actionType === "create_supplier_order_draft") {
    const product = state.products.find(
      (candidate) =>
        namesMatch(insight.entityName, candidate.name) ||
        namesMatch(insight.title, candidate.name),
    );

    return product
      ? getSupplierDraftTarget(product)
      : buildDraftTarget(insight.entityName, "supplier");
  }

  if (insight.actionType === "suggest_shipping_alternative") {
    return buildDraftTarget(insight.entityName, "carrier");
  }

  return buildDraftTarget(insight.entityName, "internal");
}

export function getSupplierDraftTarget(product: Product): DraftTarget {
  return buildDraftTarget(product.supplier, "supplier");
}

export function getDraftTargetKindLabel(kind: DraftTargetKind): string {
  const labels: Record<DraftTargetKind, string> = {
    customer: "Müşteri",
    supplier: "Tedarikçi",
    carrier: "Kargo Firması",
    internal: "Ekip",
  };
  return labels[kind];
}

export function getDraftDestination(
  target: DraftTarget,
  channel: MockSendChannel,
): string {
  return channel === "email" ? target.email : target.phone;
}

export function getMockSendChannelLabel(channel: MockSendChannel): string {
  const labels: Record<MockSendChannel, string> = {
    whatsapp: "WhatsApp",
    telegram: "Telegram",
    email: "E-posta",
  };
  return labels[channel];
}

export function getDefaultMockChannelMessage(channel: FloatingMockChannel): string {
  const channelLabel = getMockSendChannelLabel(channel);

  return `Merhaba, ${channelLabel} üzerinden siparişiniz hakkında yardımcı olmak için yazıyorum.`;
}

function buildDraftTarget(
  name: string,
  kind: DraftTargetKind,
  phone?: string,
): DraftTarget {
  const targetName = name.trim() || "Mock Alıcı";

  return {
    name: targetName,
    kind,
    phone: phone ?? mockPhoneForName(targetName),
    email: mockEmailForName(targetName, kind),
  };
}

function mockPhoneForName(name: string): string {
  const hash = hashText(name);
  const operator = 530 + (hash % 60);
  const block = 100 + (Math.floor(hash / 60) % 900);
  const first = Math.floor(hash / 54000) % 100;
  const second = Math.floor(hash / 5400000) % 100;

  return `+90 ${operator} ${block} ${String(first).padStart(2, "0")} ${String(second).padStart(2, "0")}`;
}

function mockEmailForName(name: string, kind: DraftTargetKind): string {
  const domains: Record<DraftTargetKind, string> = {
    customer: "customer.example",
    supplier: "supplier.example",
    carrier: "carrier.example",
    internal: "ops.example",
  };

  return `${toContactSlug(name)}@${domains[kind]}`;
}

function toContactSlug(value: string): string {
  const replacements: Record<string, string> = {
    ç: "c",
    ğ: "g",
    ı: "i",
    ö: "o",
    ş: "s",
    ü: "u",
  };
  const slug = value
    .toLocaleLowerCase("tr")
    .replace(/[çğıöşü]/g, (char) => replacements[char] ?? char)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, ".")
    .replace(/^\.+|\.+$/g, "");

  return slug || "mock";
}

function hashText(value: string): number {
  return Array.from(value).reduce(
    (hash, char) => (hash * 31 + char.charCodeAt(0)) >>> 0,
    7,
  );
}
