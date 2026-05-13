import {
  Boxes,
  History,
  Inbox,
  ShoppingBag,
  Users,
  Warehouse,
} from "lucide-react";
import type { ReactNode } from "react";
import type { PageView } from "./uiTypes";

export const pageViews: PageView[] = [
  "dashboard",
  "inbox",
  "stock",
  "customers",
  "orders",
  "memory",
];

export function navIcon(page: PageView): ReactNode {
  const icons: Record<PageView, ReactNode> = {
    dashboard: <Boxes size={16} />,
    inbox: <Inbox size={16} />,
    stock: <Warehouse size={16} />,
    customers: <Users size={16} />,
    orders: <ShoppingBag size={16} />,
    memory: <History size={16} />,
  };
  return icons[page];
}

export function navLabel(page: PageView): string {
  const labels: Record<PageView, string> = {
    dashboard: "Dashboard",
    inbox: "Gelen Kutusu",
    stock: "Stok",
    customers: "Müşteriler",
    orders: "Siparişler",
    memory: "Hafıza",
  };
  return labels[page];
}

export function pageTitle(page: PageView): string {
  const titles: Record<PageView, string> = {
    dashboard: "Bugünün Özeti",
    inbox: "E-posta Gelen Kutusu",
    stock: "Stok Yönetimi",
    customers: "Müşteriler",
    orders: "Siparişler",
    memory: "Hafıza & Geçmiş",
  };
  return titles[page];
}
