from dataclasses import dataclass, field
from typing import Any

from ..models import (
    ContactDraftChannel,
    Customer,
    InventoryAlert,
    OperationalIssue,
    Order,
    Product,
    Shipment,
    Task,
)


@dataclass
class ResolvedRequest:
    intent: str | None
    orderId: str | None = None
    orderStatusFilter: str | None = None
    orderTimeframeFilter: str | None = None
    orderResolvedFromCustomer: bool = False
    orderContext: tuple[Order, Shipment | None] | None = None
    product: Product | None = None
    customer: Customer | None = None
    namedCustomer: Customer | None = None
    orderCustomer: Customer | None = None
    customerOrderMismatch: bool = False
    requestedChannel: ContactDraftChannel | None = None
    directCustomerMessage: bool = False
    matchingOrders: list[Order] = field(default_factory=list)
    orderCollectionLabel: str = "matching"
    activeIssues: list[OperationalIssue] = field(default_factory=list)
    activeAlerts: list[InventoryAlert] = field(default_factory=list)
    riskyShipments: list[Shipment] = field(default_factory=list)
    openTasks: list[Task] = field(default_factory=list)
    memoryRecords: list[Any] = field(default_factory=list)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)
