import os
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from .models import (
    ConnectorHealth,
    Customer,
    InventoryAlert,
    OperationsState,
    Order,
    Product,
    Shipment,
)


class CommerceConnector(ABC):
    name = "commerce"

    @abstractmethod
    def lookup_order(self, order_id: str, state: OperationsState) -> Order | None:
        raise NotImplementedError

    @abstractmethod
    def lookup_customer(
        self,
        state: OperationsState,
        customer_id: str | None = None,
        email: str | None = None,
        name: str | None = None,
    ) -> Customer | None:
        raise NotImplementedError

    @abstractmethod
    def stock_snapshot(self, product_id: str, state: OperationsState) -> Product | None:
        raise NotImplementedError

    @abstractmethod
    def stock_alerts(self, state: OperationsState) -> list[InventoryAlert]:
        raise NotImplementedError

    @abstractmethod
    def shipment_lookup(self, order_id: str, state: OperationsState) -> Shipment | None:
        raise NotImplementedError

    @abstractmethod
    def health(self) -> ConnectorHealth:
        raise NotImplementedError


class DemoCommerceConnector(CommerceConnector):
    name = "demo-commerce"

    def lookup_order(self, order_id: str, state: OperationsState) -> Order | None:
        return next((item for item in state.orders if item.id == order_id), None)

    def lookup_customer(
        self,
        state: OperationsState,
        customer_id: str | None = None,
        email: str | None = None,
        name: str | None = None,
    ) -> Customer | None:
        normalized_email = email.lower().strip() if email else None
        normalized_name = _normalize(name) if name else None

        for customer in state.customers:
            if customer_id and customer.id == customer_id:
                return customer
            if normalized_email and (customer.email or "").lower() == normalized_email:
                return customer
            if normalized_name and normalized_name in _normalize(customer.name):
                return customer

        return None

    def stock_snapshot(self, product_id: str, state: OperationsState) -> Product | None:
        return next((item for item in state.products if item.id == product_id), None)

    def stock_alerts(self, state: OperationsState) -> list[InventoryAlert]:
        return [alert for alert in state.inventoryAlerts if not alert.resolved]

    def shipment_lookup(self, order_id: str, state: OperationsState) -> Shipment | None:
        return next((item for item in state.shipments if item.orderId == order_id), None)

    def health(self) -> ConnectorHealth:
        return ConnectorHealth(
            name="Demo commerce adapter",
            type="commerce",
            status="ok",
            lastChecked=_now(),
            capabilities=[
                "order_lookup",
                "customer_lookup",
                "stock_snapshot",
                "stock_alerts",
                "shipment_lookup",
            ],
            message="Using in-memory demo data.",
        )


class GenericRestCommerceConnector(CommerceConnector):
    name = "generic-rest-commerce"

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float = 5.0,
    ) -> None:
        self.base_url = (base_url or os.getenv("COMMERCE_API_BASE_URL", "")).rstrip("/")
        self.token = token if token is not None else os.getenv("COMMERCE_API_TOKEN")
        self.timeout = timeout
        self.last_error: str | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.base_url)

    def lookup_order(self, order_id: str, state: OperationsState) -> Order | None:
        if not self.enabled:
            return DemoCommerceConnector().lookup_order(order_id, state)

        payload = self._get_json(f"/orders/{urllib.parse.quote(order_id)}")
        data = _unwrap(payload, "order", "data")
        return _parse_model(Order, data) or DemoCommerceConnector().lookup_order(order_id, state)

    def lookup_customer(
        self,
        state: OperationsState,
        customer_id: str | None = None,
        email: str | None = None,
        name: str | None = None,
    ) -> Customer | None:
        if not self.enabled:
            return DemoCommerceConnector().lookup_customer(state, customer_id, email, name)

        if customer_id:
            payload = self._get_json(f"/customers/{urllib.parse.quote(customer_id)}")
        else:
            params = {
                key: value
                for key, value in {"email": email, "name": name}.items()
                if value
            }
            payload = self._get_json("/customers", params=params)

        data = _unwrap(payload, "customer", "data", "customers")
        if isinstance(data, list):
            data = data[0] if data else None

        return _parse_model(Customer, data) or DemoCommerceConnector().lookup_customer(
            state,
            customer_id,
            email,
            name,
        )

    def stock_snapshot(self, product_id: str, state: OperationsState) -> Product | None:
        if not self.enabled:
            return DemoCommerceConnector().stock_snapshot(product_id, state)

        payload = self._get_json(f"/stock/{urllib.parse.quote(product_id)}")
        data = _unwrap(payload, "product", "stock", "data")
        return _parse_model(Product, data) or DemoCommerceConnector().stock_snapshot(
            product_id,
            state,
        )

    def stock_alerts(self, state: OperationsState) -> list[InventoryAlert]:
        if not self.enabled:
            return DemoCommerceConnector().stock_alerts(state)

        payload = self._get_json("/stock/alerts")
        data = _unwrap(payload, "alerts", "data")
        alerts = _parse_model_list(InventoryAlert, data)
        return alerts if alerts else DemoCommerceConnector().stock_alerts(state)

    def shipment_lookup(self, order_id: str, state: OperationsState) -> Shipment | None:
        if not self.enabled:
            return DemoCommerceConnector().shipment_lookup(order_id, state)

        payload = self._get_json(f"/shipments/{urllib.parse.quote(order_id)}")
        data = _unwrap(payload, "shipment", "data")
        return _parse_model(Shipment, data) or DemoCommerceConnector().shipment_lookup(
            order_id,
            state,
        )

    def health(self) -> ConnectorHealth:
        if not self.enabled:
            return ConnectorHealth(
                name="Generic REST commerce adapter",
                type="commerce",
                status="disabled",
                lastChecked=_now(),
                capabilities=[],
                message="Set COMMERCE_API_BASE_URL to enable REST commerce calls.",
            )

        payload = self._get_json("/health")
        status = "ok" if payload is not None else "error"

        return ConnectorHealth(
            name="Generic REST commerce adapter",
            type="commerce",
            status=status,
            lastChecked=_now(),
            capabilities=[
                "order_lookup",
                "customer_lookup",
                "stock_snapshot",
                "stock_alerts",
                "shipment_lookup",
            ],
            message=self.last_error,
        )

    def _get_json(
        self,
        path: str,
        params: dict[str, str] | None = None,
    ) -> Any:
        if not self.enabled:
            return None

        query = f"?{urllib.parse.urlencode(params)}" if params else ""
        request = urllib.request.Request(f"{self.base_url}{path}{query}")
        request.add_header("Accept", "application/json")
        if self.token:
            request.add_header("Authorization", f"Bearer {self.token}")

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                import json

                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            self.last_error = str(exc)
            return None


def get_commerce_connector() -> CommerceConnector:
    if os.getenv("COMMERCE_API_BASE_URL"):
        return GenericRestCommerceConnector()

    return DemoCommerceConnector()


def _parse_model(model: type, data: Any):
    if not isinstance(data, dict):
        return None

    try:
        return model(**data)
    except Exception:
        return None


def _parse_model_list(model: type, data: Any):
    if not isinstance(data, list):
        return []

    return [item for item in (_parse_model(model, row) for row in data) if item]


def _unwrap(payload: Any, *keys: str) -> Any:
    if not isinstance(payload, dict):
        return payload

    for key in keys:
        if key in payload:
            return payload[key]

    return payload


def _normalize(value: str | None) -> str:
    return " ".join((value or "").lower().strip().split())


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
