from copy import deepcopy

from .models import (
    Customer,
    InventoryAlert,
    OperationsState,
    Order,
    Product,
    Shipment,
    Task,
)

INITIAL_STATE = OperationsState(
    products=[
        Product(
            id="p-101",
            name="Zeytinyağı Hediye Seti",
            sku="ZY-HED-500",
            category="Gıda",
            stock=18,
            threshold=25,
            unit="set",
            supplier="Ege Tarım A.Ş.",
            image="https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?auto=format&fit=crop&w=480&q=80",
            weeklySales=[12, 10, 15, 18, 21, 19, 24],
        ),
        Product(
            id="p-102",
            name="El Dokuması Pamuk Havlu",
            sku="TKS-HVL-TR",
            category="Tekstil",
            stock=44,
            threshold=20,
            unit="adet",
            supplier="Denizli Dokuma Evi",
            image="https://images.unsplash.com/photo-1583847268964-b28dc8f51f92?auto=format&fit=crop&w=480&q=80",
            weeklySales=[7, 9, 8, 10, 12, 11, 13],
        ),
        Product(
            id="p-103",
            name="Kavrulmuş İncir Reçeli",
            sku="GD-INC-250",
            category="Gıda",
            stock=9,
            threshold=30,
            unit="kavanoz",
            supplier="Selçuk Mutfağı",
            image="https://images.unsplash.com/photo-1607487998981-8d44fca90343?auto=format&fit=crop&w=480&q=80",
            weeklySales=[18, 22, 19, 24, 27, 29, 31],
        ),
        Product(
            id="p-104",
            name="Çini Kahve Fincanı",
            sku="CNK-FNC-04",
            category="Ev",
            stock=61,
            threshold=18,
            unit="adet",
            supplier="Kütahya Çini Atölyesi",
            image="https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?auto=format&fit=crop&w=480&q=80",
            weeklySales=[8, 7, 11, 12, 10, 13, 12],
        ),
        Product(
            id="p-105",
            name="Kurutulmuş Domates Paketi",
            sku="GD-KDT-100",
            category="Gıda",
            stock=42,
            threshold=50,
            unit="paket",
            supplier="Anadolu Hasat",
            image="https://images.unsplash.com/photo-1592841200221-a6898f307baa?auto=format&fit=crop&w=480&q=80",
            weeklySales=[21, 18, 24, 28, 25, 31, 34],
        ),
        Product(
            id="p-106",
            name="Bakır Cezve",
            sku="BCZ-CEZ-02",
            category="Mutfak",
            stock=27,
            threshold=12,
            unit="adet",
            supplier="Gaziantep Bakırcılar Çarşısı",
            image="https://images.unsplash.com/photo-1509042239860-f550ce710b93?auto=format&fit=crop&w=480&q=80",
            weeklySales=[3, 5, 6, 8, 6, 7, 9],
        ),
        Product(
            id="p-107",
            name="Taze Domates",
            sku="TRF-DMS-KG",
            category="Sebze",
            stock=8,
            threshold=50,
            unit="kg",
            supplier="Mehmet Bey",
            image="https://images.unsplash.com/photo-1546094096-0df4bcaaa337?auto=format&fit=crop&w=480&q=80",
            weeklySales=[15, 16, 14, 15, 17, 15, 13],
        ),
    ],
    customers=[
        Customer(
            id="c-1", name="Mina Yılmaz", channel="WhatsApp", phone="+90 532 000 1414"
        ),
        Customer(
            id="c-2", name="Arda Market", channel="Email", phone="+90 216 000 2020"
        ),
        Customer(
            id="c-3", name="Selin Kaya", channel="WhatsApp", phone="+90 555 000 3030"
        ),
        Customer(
            id="c-4",
            name="Kuzey İskele Kafe",
            channel="Phone",
            phone="+90 212 000 4040",
        ),
        Customer(
            id="c-5", name="Ahmet Bey", channel="WhatsApp", phone="+90 533 000 5050"
        ),
    ],
    orders=[
        Order(
            id="128",
            customerId="c-1",
            createdAt="2026-05-10T02:12:00+03:00",
            status="shipped",
            items=[
                {"productId": "p-101", "quantity": 1},
                {"productId": "p-103", "quantity": 2},
            ],
            total=1870,
            dueToday=False,
        ),
        Order(
            id="129",
            customerId="c-2",
            createdAt="2026-05-10T03:44:00+03:00",
            status="packing",
            items=[
                {"productId": "p-105", "quantity": 12},
                {"productId": "p-102", "quantity": 4},
            ],
            total=6420,
            dueToday=True,
        ),
        Order(
            id="130",
            customerId="c-3",
            createdAt="2026-05-10T06:21:00+03:00",
            status="new",
            items=[{"productId": "p-104", "quantity": 2}],
            total=960,
            dueToday=True,
        ),
        Order(
            id="131",
            customerId="c-4",
            createdAt="2026-05-09T17:12:00+03:00",
            status="delayed",
            items=[
                {"productId": "p-103", "quantity": 8},
                {"productId": "p-106", "quantity": 1},
            ],
            total=3910,
            dueToday=False,
        ),
        Order(
            id="132",
            customerId="c-3",
            createdAt="2026-05-10T07:38:00+03:00",
            status="packing",
            items=[{"productId": "p-101", "quantity": 3}],
            total=2550,
            dueToday=True,
        ),
    ],
    shipments=[
        Shipment(
            id="s-128",
            orderId="128",
            carrier="MNG Kargo",
            trackingCode="MNG128-TR",
            eta="2026-05-11 15:00",
            lastScan="İstanbul aktarma merkezi, 09:18",
            city="İstanbul",
            risk="clear",
            notified=False,
        ),
        Shipment(
            id="s-131",
            orderId="131",
            carrier="Yurtiçi Kargo",
            trackingCode="YIC131-TR",
            eta="2026-05-10 18:00",
            lastScan="İzmir hub'ından sonra 22 saattir tarama yok",
            city="İzmir",
            risk="delayed",
            notified=False,
        ),
        Shipment(
            id="s-132",
            orderId="132",
            carrier="Aras Kargo",
            trackingCode="ARS132-TR",
            eta="2026-05-12 12:30",
            lastScan="Etiket oluşturuldu, teslim alım bekleniyor",
            city="Ankara",
            risk="watch",
            notified=False,
        ),
    ],
    inventoryAlerts=[
        InventoryAlert(
            productId="p-103",
            severity="critical",
            message="İncir reçeli mevcut satış hızıyla 2 günden kısa sürede tükenecek.",
            resolved=False,
        ),
        InventoryAlert(
            productId="p-105",
            severity="warning",
            message="Kurutulmuş domates paketi kooperatif eşiğinin altında.",
            resolved=False,
        ),
        InventoryAlert(
            productId="p-101",
            severity="warning",
            message="Hafta sonu talebinden önce hediye seti yeniden sipariş noktasının altında.",
            resolved=False,
        ),
        InventoryAlert(
            productId="p-107",
            severity="critical",
            message="Domates Pazar güvenlik stoğunun altında, tedarikçi hafızası tekrarlayan stok tükenmesini gösteriyor.",
            resolved=False,
        ),
    ],
    tasks=[
        Task(
            id="t-1",
            owner="Depo",
            title="Sipariş 129'u öğlen teslim alımından önce paketle",
            priority="high",
            orderId="129",
            status="open",
        ),
        Task(
            id="t-2",
            owner="Müşteri Masası",
            title="Sipariş 131 için gecikmiş kargo durumunu incele",
            priority="high",
            orderId="131",
            status="open",
        ),
        Task(
            id="t-3",
            owner="Satın Alma",
            title="İncir reçeli için tedarikçi kapasitesini onayla",
            priority="medium",
            status="open",
        ),
    ],
)

_state = deepcopy(INITIAL_STATE)


def get_state() -> OperationsState:
    return _state


def reset_state() -> OperationsState:
    global _state
    _state = deepcopy(INITIAL_STATE)
    return _state
