import type { ChatMessage, OperationsState } from "../types";

export const starterMessages = [
  "Sipariş 128 ne zaman gelir?",
  "İncir reçeli stokta var mı?",
  "Bugün kargo riski var mı?",
];

export const emptyState: OperationsState = {
  products: [],
  customers: [],
  orders: [],
  shipments: [],
  inventoryAlerts: [],
  tasks: [],
};

export const initialMessages: ChatMessage[] = [
  {
    id: "demo-customer-128",
    role: "customer",
    text: "Sipariş 128 ne zaman gelir?",
    timestamp: "09:18",
  },
  {
    id: "demo-agent-128",
    role: "agent",
    text: "Sipariş 128 MNG Kargo ile yolda, tahmini teslimat 11 Mayıs 15:00. Son tarama İstanbul aktarma merkezi saat 09:18.",
    timestamp: "09:18",
  },
];
