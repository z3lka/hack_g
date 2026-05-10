export type OrderStatus = "new" | "packing" | "shipped" | "delayed" | "delivered";

export type ShipmentRisk = "clear" | "watch" | "delayed";

export type TaskStatus = "open" | "done";

export type Product = {
  id: string;
  name: string;
  sku: string;
  category: string;
  stock: number;
  threshold: number;
  unit: string;
  supplier: string;
  image: string;
  weeklySales: number[];
};

export type Customer = {
  id: string;
  name: string;
  channel: "WhatsApp" | "Email" | "Phone";
  phone: string;
};

export type OrderItem = {
  productId: string;
  quantity: number;
};

export type Order = {
  id: string;
  customerId: string;
  createdAt: string;
  status: OrderStatus;
  items: OrderItem[];
  total: number;
  dueToday: boolean;
};

export type Shipment = {
  id: string;
  orderId: string;
  carrier: string;
  trackingCode: string;
  eta: string;
  lastScan: string;
  city: string;
  risk: ShipmentRisk;
  notified: boolean;
};

export type InventoryAlert = {
  productId: string;
  severity: "warning" | "critical";
  message: string;
  restockDraft?: string;
  resolved: boolean;
};

export type Task = {
  id: string;
  owner: string;
  title: string;
  priority: "low" | "medium" | "high";
  orderId?: string;
  status: TaskStatus;
};

export type ChatMessage = {
  id: string;
  role: "customer" | "agent";
  text: string;
  timestamp: string;
};

export type AgentAction = {
  id: string;
  label: string;
  type:
    | "lookup_order"
    | "check_stock"
    | "notify_customer"
    | "create_restock_draft"
    | "create_task_plan"
    | "complete_task";
  payload: Record<string, string | number | boolean>;
};

export type OperationsState = {
  products: Product[];
  customers: Customer[];
  orders: Order[];
  shipments: Shipment[];
  inventoryAlerts: InventoryAlert[];
  tasks: Task[];
};
