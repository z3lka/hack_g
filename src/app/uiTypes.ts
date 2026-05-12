import type { ReactNode } from "react";

export type PageView = "dashboard" | "stock" | "customers" | "orders" | "memory";

export type ChatState = "closed" | "minimized" | "open";

export type MockSendChannel = "whatsapp" | "telegram" | "email";

export type FloatingMockChannel = Extract<MockSendChannel, "whatsapp" | "telegram">;

export type DraftTargetKind = "customer" | "supplier" | "carrier" | "internal";

export type DraftTarget = {
  name: string;
  kind: DraftTargetKind;
  phone: string;
  email: string;
};

export type DraftModal = {
  title: string;
  subtitle: string;
  body: string;
  target: DraftTarget;
};

export type MockComposerState = {
  channel: FloatingMockChannel;
  customerId: string;
  message: string;
  notice: string;
};

export type SearchResultKind =
  | "product"
  | "customer"
  | "order"
  | "shipment"
  | "issue"
  | "message"
  | "alert"
  | "task"
  | "insight"
  | "memory";

export type SearchTarget =
  | {
      type: "page";
      page: PageView;
      ordersFilter?: string;
      memorySearch?: string;
    }
  | { type: "chat" };

export type SearchResult = {
  id: string;
  kind: SearchResultKind;
  title: string;
  description: string;
  meta: string;
  keywords: string[];
  target: SearchTarget;
};

export type NotificationTone = "red" | "orange" | "yellow" | "blue" | "green";

export type NotificationAction =
  | { type: "stock"; productId: string }
  | { type: "shipment" }
  | { type: "issue" }
  | { type: "order" }
  | { type: "insight"; insightId: string }
  | { type: "task" };

export type NotificationItem = {
  id: string;
  tone: NotificationTone;
  title: string;
  description: string;
  meta: string;
  action: NotificationAction;
};

export type ExternalBotChannel = {
  id: FloatingMockChannel;
  label: string;
  icon: ReactNode;
};
