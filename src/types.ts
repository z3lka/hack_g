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
    | "check_errors"
    | "summarize_operations"
    | "notify_customer"
    | "create_restock_draft"
    | "create_task_plan"
    | "complete_task"
    | "create_supplier_order_draft"
    | "create_customer_reminder_draft"
    | "suggest_shipping_alternative"
    | "memory_insight_generated";
  payload: Record<string, string | number | boolean>;
};

export type OperationalIssue = {
  id: string;
  category: "inventory" | "order" | "payment" | "integration" | "shipping" | "system";
  severity: "info" | "warning" | "critical";
  title: string;
  message: string;
  source: string;
  entityId?: string | null;
  createdAt: string;
  resolved: boolean;
};

export type OperationsState = {
  products: Product[];
  customers: Customer[];
  orders: Order[];
  shipments: Shipment[];
  inventoryAlerts: InventoryAlert[];
  tasks: Task[];
  issues: OperationalIssue[];
};

export type MemoryCategory = "inventory" | "customer" | "supplier" | "shipping" | "product" | "note";

export type MemoryRecordInput = {
  text: string;
  category?: MemoryCategory;
  entityName?: string | null;
  eventDate?: string | null;
  metadata?: Record<string, string | number | boolean>;
};

export type MemoryRecord = Required<Pick<MemoryRecordInput, "text">> & {
  id: string;
  category: MemoryCategory;
  entityName?: string | null;
  eventDate?: string | null;
  metadata: Record<string, string | number | boolean>;
};

export type MemoryStatus = {
  backend: "chromadb" | "fallback";
  recordCount: number;
  persistPath: string;
  collectionName: string;
  seeded: boolean;
  embeddingBackend: "gemini" | "sentence-transformers" | "hash";
  embeddingModel: string;
  error?: string | null;
};

export type ProactiveInsight = {
  id: string;
  color: "red" | "yellow" | "orange" | "green";
  entityName: string;
  title: string;
  summary: string;
  evidence: string[];
  draftAction: string;
  actionType: AgentAction["type"];
  confidence: number;
};

export type MorningInsightsResponse = {
  generatedAt: string;
  llmMode: "gemini" | "fallback";
  memoryStatus: MemoryStatus;
  insights: ProactiveInsight[];
  actions: AgentAction[];
};
