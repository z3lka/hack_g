from typing import Literal

from pydantic import BaseModel, Field


OrderStatus = Literal["new", "packing", "shipped", "delayed", "delivered"]
ShipmentRisk = Literal["clear", "watch", "delayed"]
TaskStatus = Literal["open", "done"]
Priority = Literal["low", "medium", "high"]
ActionType = Literal[
    "lookup_order",
    "check_stock",
    "check_errors",
    "summarize_operations",
    "notify_customer",
    "create_restock_draft",
    "create_task_plan",
    "complete_task",
    "create_supplier_order_draft",
    "create_customer_reminder_draft",
    "suggest_shipping_alternative",
    "memory_insight_generated",
    "read_inbox",
    "classify_message",
    "extract_entities",
    "lookup_customer",
    "lookup_shipment",
    "create_customer_reply_draft",
    "approve_draft",
    "send_email",
]
InsightColor = Literal["red", "yellow", "orange", "green"]
MemoryCategory = Literal["inventory", "customer", "supplier", "shipping", "product", "note"]
EmbeddingBackend = Literal["gemini", "sentence-transformers", "hash"]
IssueCategory = Literal["inventory", "order", "payment", "integration", "shipping", "system"]
IssueSeverity = Literal["info", "warning", "critical"]
MessageIntent = Literal[
    "order_lookup",
    "stock_check",
    "shipment_risk",
    "issue_check",
    "customer_lookup",
    "task_summary",
    "operations_summary",
    "return_exchange",
    "complaint",
    "general",
    "unknown",
]
DraftStatus = Literal["pending_review", "approved", "sent", "failed"]
ConnectorStatus = Literal["ok", "degraded", "disabled", "error"]
ConnectorType = Literal["commerce", "email_inbound", "email_outbound"]
MessageDirection = Literal["inbound", "outbound"]
ThreadStatus = Literal["open", "drafted", "sent", "closed"]


class Product(BaseModel):
    id: str
    name: str
    sku: str
    category: str
    stock: int
    threshold: int
    unit: str
    supplier: str
    image: str
    weeklySales: list[int]


class Customer(BaseModel):
    id: str
    name: str
    channel: Literal["WhatsApp", "Email", "Phone"]
    phone: str
    email: str | None = None


class OrderItem(BaseModel):
    productId: str
    quantity: int


class Order(BaseModel):
    id: str
    customerId: str
    createdAt: str
    status: OrderStatus
    items: list[OrderItem]
    total: int
    dueToday: bool


class Shipment(BaseModel):
    id: str
    orderId: str
    carrier: str
    trackingCode: str
    eta: str
    lastScan: str
    city: str
    risk: ShipmentRisk
    notified: bool


class InventoryAlert(BaseModel):
    productId: str
    severity: Literal["warning", "critical"]
    message: str
    restockDraft: str | None = None
    resolved: bool


class Task(BaseModel):
    id: str
    owner: str
    title: str
    priority: Priority
    orderId: str | None = None
    status: TaskStatus


class OperationalIssue(BaseModel):
    id: str
    category: IssueCategory
    severity: IssueSeverity
    title: str
    message: str
    source: str
    entityId: str | None = None
    createdAt: str
    resolved: bool


class ChatMessage(BaseModel):
    id: str
    role: Literal["customer", "agent"]
    text: str
    timestamp: str


class AgentAction(BaseModel):
    id: str
    label: str
    type: ActionType
    payload: dict[str, str | int | bool]


class OperationsState(BaseModel):
    products: list[Product]
    customers: list[Customer]
    orders: list[Order]
    shipments: list[Shipment]
    inventoryAlerts: list[InventoryAlert]
    tasks: list[Task]
    issues: list[OperationalIssue]


class AgentResult(BaseModel):
    response: str
    actions: list[AgentAction]


class MessageEntities(BaseModel):
    orderId: str | None = None
    productId: str | None = None
    productName: str | None = None
    customerId: str | None = None
    customerName: str | None = None
    customerEmail: str | None = None
    shipmentId: str | None = None
    trackingCode: str | None = None


class AssistantInterpretation(BaseModel):
    intent: MessageIntent
    entities: MessageEntities = Field(default_factory=MessageEntities)
    confidence: float
    requiredReviewReason: str | None = None
    memory: list[str] = Field(default_factory=list)
    actions: list[AgentAction] = Field(default_factory=list)


class CustomerMessage(BaseModel):
    id: str
    threadId: str
    providerMessageId: str
    direction: MessageDirection
    fromName: str
    fromEmail: str
    toEmail: str
    subject: str
    body: str
    receivedAt: str
    unread: bool
    intent: MessageIntent = "unknown"
    entities: MessageEntities = Field(default_factory=MessageEntities)


class AssistantDraft(BaseModel):
    id: str
    threadId: str
    messageId: str
    subject: str
    body: str
    toEmail: str
    status: DraftStatus
    intent: MessageIntent
    entities: MessageEntities = Field(default_factory=MessageEntities)
    confidence: float
    requiredReviewReason: str
    createdAt: str
    approvedAt: str | None = None
    sentAt: str | None = None
    sendRecorded: bool = False


class CustomerThread(BaseModel):
    id: str
    subject: str
    customerId: str | None = None
    customerName: str
    customerEmail: str
    status: ThreadStatus
    unread: bool
    lastMessageAt: str
    messages: list[CustomerMessage] = Field(default_factory=list)
    drafts: list[AssistantDraft] = Field(default_factory=list)


class ConnectorHealth(BaseModel):
    name: str
    type: ConnectorType
    status: ConnectorStatus
    lastChecked: str
    capabilities: list[str] = Field(default_factory=list)
    message: str | None = None


class InboxSyncResponse(BaseModel):
    syncedMessages: int
    threads: list[CustomerThread]
    connectorHealth: list[ConnectorHealth]


class DraftApprovalRequest(BaseModel):
    subject: str | None = None
    body: str | None = None


class DraftApprovalResponse(BaseModel):
    thread: CustomerThread
    draft: AssistantDraft
    action: AgentAction


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    customerMessage: ChatMessage
    agentMessage: ChatMessage
    actions: list[AgentAction]
    state: OperationsState


class StateActionResponse(BaseModel):
    state: OperationsState
    action: AgentAction


class TaskPlanResponse(BaseModel):
    state: OperationsState
    action: AgentAction
    createdTasks: list[Task]


class MemoryRecordInput(BaseModel):
    text: str
    category: MemoryCategory = "note"
    entityName: str | None = None
    eventDate: str | None = None
    metadata: dict[str, str | int | bool] = Field(default_factory=dict)


class MemoryRecord(MemoryRecordInput):
    id: str


class MemoryStatus(BaseModel):
    backend: Literal["chromadb", "fallback"]
    recordCount: int
    persistPath: str
    collectionName: str
    seeded: bool
    embeddingBackend: EmbeddingBackend
    embeddingModel: str
    error: str | None = None


class MemoryIngestRequest(BaseModel):
    records: list[MemoryRecordInput]


class MemoryIngestResponse(BaseModel):
    status: MemoryStatus
    records: list[MemoryRecord]


class ProactiveInsight(BaseModel):
    id: str
    color: InsightColor
    entityName: str
    title: str
    summary: str
    evidence: list[str]
    draftAction: str
    actionType: ActionType
    confidence: float


class MorningInsightsResponse(BaseModel):
    generatedAt: str
    llmMode: Literal["gemini", "fallback"]
    memoryStatus: MemoryStatus
    insights: list[ProactiveInsight]
    actions: list[AgentAction]
