import type { OperationsState, Order } from "../types";

export function summarizeItems(order: Order, state: OperationsState): string {
  return order.items
    .map((item) => {
      const product = state.products.find(
        (candidate) => candidate.id === item.productId,
      );
      return `${item.quantity}x ${product?.name ?? "?"}`;
    })
    .join(", ");
}

export function average(values: number[]): number {
  if (!values.length) {
    return 0;
  }

  return values.reduce((total, value) => total + value, 0) / values.length;
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatDate(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("tr-TR", {
    day: "2-digit",
    month: "short",
  }).format(date);
}

export function formatTime(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("tr-TR", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function formatTodayLabel(date: Date): string {
  const parts = new Intl.DateTimeFormat("tr-TR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).formatToParts(date);
  const byType = Object.fromEntries(
    parts.map((part) => [part.type, part.value]),
  );
  const weekday = byType.weekday
    ? byType.weekday.charAt(0).toLocaleUpperCase("tr") + byType.weekday.slice(1)
    : "";

  return [weekday, `${byType.day} ${byType.month} ${byType.year}`]
    .filter(Boolean)
    .join(", ");
}

export function firstSentence(value: string): string {
  const trimmed = value.trim();
  const match = trimmed.match(/^.*?[.!?](?:\s|$)/);
  return (match?.[0] ?? trimmed).trim();
}

export function compactText(value: string, maxLength: number): string {
  const normalized = value.replace(/\s+/g, " ").trim();

  if (normalized.length <= maxLength) {
    return normalized;
  }

  return `${normalized.slice(0, maxLength - 1).trimEnd()}…`;
}

export function normalizeSearch(value: string): string {
  const replacements: Record<string, string> = {
    ç: "c",
    ğ: "g",
    ı: "i",
    ö: "o",
    ş: "s",
    ü: "u",
  };

  return value
    .toLocaleLowerCase("tr")
    .replace(/[çğıöşü]/g, (char) => replacements[char] ?? char)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function namesMatch(left: string, right: string): boolean {
  const normalize = (value: string) =>
    value
      .toLocaleLowerCase("tr")
      .replace(/[^\w\s]/g, "")
      .trim();

  return (
    normalize(left).includes(normalize(right)) ||
    normalize(right).includes(normalize(left))
  );
}

export function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "API hatası.";
}
