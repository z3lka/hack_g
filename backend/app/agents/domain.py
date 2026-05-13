from ..commerce import get_commerce_connector
from ..models import Customer, OperationsState, Order, Product, Shipment


class DomainToolsMixin:
    def lookup_order_status(
        self, order_id: str, state: OperationsState
    ) -> tuple[Order, Shipment | None] | None:
        commerce = get_commerce_connector()
        order = commerce.lookup_order(order_id, state)

        if order is None:
            return None

        shipment = commerce.shipment_lookup(order.id, state)
        return order, shipment

    def check_stock(self, product_id: str, state: OperationsState) -> Product | None:
        return get_commerce_connector().stock_snapshot(product_id, state)

    def lookup_customer(
        self,
        state: OperationsState,
        customer_id: str | None = None,
        email: str | None = None,
        name: str | None = None,
    ) -> Customer | None:
        return get_commerce_connector().lookup_customer(
            state,
            customer_id=customer_id,
            email=email,
            name=name,
        )

    def detect_shipping_risks(self, state: OperationsState) -> list[Shipment]:
        return [s for s in state.shipments if s.risk != "clear" and not s.notified]
