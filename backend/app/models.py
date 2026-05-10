from typing import Literal

from pydantic import BaseModel


OrderStatus = Literal["new", "packing", "shipped", "delayed", "delivered"]
ShipmentRisk = Literal["clear", "watch", "delayed"]
TaskStatus = Literal["open", "done"]
Priority = Literal["low", "medium", "high"]
ActionType = Literal[
    "lookup_order",
    "check_stock",
    "notify_customer",
    "create_restock_draft",
    "create_task_plan",
    "complete_task",
]


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


class AgentResult(BaseModel):
    response: str
    actions: list[AgentAction]


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
