import math
from copy import deepcopy

from .models import (
    Customer,
    InventoryAlert,
    OperationsState,
    Order,
    OperationalIssue,
    Product,
    Shipment,
    Task,
)

CRITICAL_COVERAGE_DAYS = 2
WARNING_COVERAGE_DAYS = 7


INITIAL_STATE = OperationsState(
    products=[
        Product(
            id="p-101",
            name="Zeytinyağı Hediye Seti",
            sku="ZY-HED-500",
            category="Gıda",
            stock=18,
            threshold=35,
            unit="set",
            supplier="Ege Tarım A.Ş.",
            image="https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?auto=format&fit=crop&w=480&q=80",
            weeklySales=[15, 16, 17, 18, 17, 18, 18],
        ),
        Product(
            id="p-102",
            name="El Dokuması Pamuk Havlu",
            sku="TKS-HVL-TR",
            category="Tekstil",
            stock=96,
            threshold=40,
            unit="adet",
            supplier="Denizli Dokuma Evi",
            image="https://images.unsplash.com/photo-1583847268964-b28dc8f51f92?auto=format&fit=crop&w=480&q=80",
            weeklySales=[8, 9, 10, 11, 10, 11, 11],
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
            image="https://images.unsplash.com/photo-1546948630-50a0af017138?q=80&w=987&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D",
            weeklySales=[18, 22, 19, 24, 27, 29, 31],
        ),
        Product(
            id="p-104",
            name="Çini Kahve Fincanı",
            sku="CNK-FNC-04",
            category="Ev",
            stock=96,
            threshold=24,
            unit="adet",
            supplier="Kütahya Çini Atölyesi",
            image="https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?auto=format&fit=crop&w=480&q=80",
            weeklySales=[8, 9, 10, 11, 10, 12, 10],
        ),
        Product(
            id="p-105",
            name="Kurutulmuş Domates Paketi",
            sku="GD-KDT-100",
            category="Gıda",
            stock=42,
            threshold=70,
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
            stock=38,
            threshold=14,
            unit="adet",
            supplier="Gaziantep Bakırcılar Çarşısı",
            image="https://images.unsplash.com/photo-1509042239860-f550ce710b93?auto=format&fit=crop&w=480&q=80",
            weeklySales=[5, 6, 6, 7, 6, 7, 7],
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
        Product(
            id="p-108",
            name="Nar Ekşisi Şişesi",
            sku="GD-NES-330",
            category="Gıda",
            stock=54,
            threshold=45,
            unit="şişe",
            supplier="Hatay Lezzetleri",
            image="https://images.unsplash.com/photo-1601493700631-2b16ec4b4716?auto=format&fit=crop&w=480&q=80",
            weeklySales=[7, 8, 8, 9, 8, 7, 9],
        ),
        Product(
            id="p-109",
            name="Organik Sabun Seti",
            sku="KSM-SBN-03",
            category="Kozmetik",
            stock=140,
            threshold=60,
            unit="set",
            supplier="Urla Sabunhanesi",
            image="https://images.unsplash.com/photo-1607006483224-5dd6d9ea3952?auto=format&fit=crop&w=480&q=80",
            weeklySales=[12, 14, 16, 15, 15, 17, 16],
        ),
        Product(
            id="p-110",
            name="Kilim Yastık Kılıfı",
            sku="EV-KLM-45",
            category="Ev",
            stock=28,
            threshold=20,
            unit="adet",
            supplier="Uşak Dokuma Kooperatifi",
            image="https://images.unsplash.com/photo-1582582494705-f8ce0b0c24f0?auto=format&fit=crop&w=480&q=80",
            weeklySales=[3, 4, 4, 5, 4, 4, 4],
        ),
        Product(
            id="p-111",
            name="Adaçayı Demeti",
            sku="BTK-ADA-50",
            category="Bitki",
            stock=16,
            threshold=35,
            unit="demet",
            supplier="Bozdağ Yayla Ürünleri",
            image="https://images.unsplash.com/photo-1515688594390-b649af70d282?auto=format&fit=crop&w=480&q=80",
            weeklySales=[10, 11, 12, 12, 13, 12, 14],
        ),
        Product(
            id="p-112",
            name="Seramik Sunum Tabağı",
            sku="SRM-TBK-28",
            category="Ev",
            stock=67,
            threshold=25,
            unit="adet",
            supplier="Avanos Seramik",
            image="https://images.unsplash.com/photo-1612196808214-b8e1d6145a8c?auto=format&fit=crop&w=480&q=80",
            weeklySales=[5, 6, 6, 7, 6, 6, 6],
        ),
    ],
    customers=[
        Customer(id="c-1", name="Mina Yılmaz", channel="WhatsApp", phone="+90 532 000 1414"),
        Customer(id="c-2", name="Arda Market", channel="Email", phone="+90 216 000 2020"),
        Customer(id="c-3", name="Selin Kaya", channel="WhatsApp", phone="+90 555 000 3030"),
        Customer(id="c-4", name="Kuzey İskele Kafe", channel="Phone", phone="+90 212 000 4040"),
        Customer(id="c-5", name="Ahmet Bey", channel="WhatsApp", phone="+90 533 000 5050"),
        Customer(id="c-6", name="Dara Boutique", channel="Email", phone="+90 212 000 6060"),
        Customer(id="c-7", name="Fırın 38", channel="WhatsApp", phone="+90 352 000 7070"),
        Customer(id="c-8", name="Liva Otel Satın Alma", channel="Email", phone="+90 242 000 8080"),
        Customer(id="c-9", name="Deniz Ergin", channel="WhatsApp", phone="+90 544 000 9090"),
        Customer(id="c-10", name="Mavi Kooperatif", channel="Phone", phone="+90 232 000 1010"),
        Customer(id="c-11", name="Esra Atelier", channel="Email", phone="+90 212 000 1111"),
        Customer(id="c-12", name="Lotus Vegan Cafe", channel="WhatsApp", phone="+90 216 000 1212"),
    ],
    orders=[
        Order(id="128", customerId="c-1", createdAt="2026-05-10T02:12:00+03:00", status="shipped", items=[{"productId": "p-101", "quantity": 1}, {"productId": "p-103", "quantity": 2}], total=1870, dueToday=False),
        Order(id="129", customerId="c-2", createdAt="2026-05-10T03:44:00+03:00", status="packing", items=[{"productId": "p-105", "quantity": 12}, {"productId": "p-102", "quantity": 4}], total=6420, dueToday=True),
        Order(id="130", customerId="c-3", createdAt="2026-05-10T06:21:00+03:00", status="new", items=[{"productId": "p-104", "quantity": 2}, {"productId": "p-109", "quantity": 1}], total=1720, dueToday=True),
        Order(id="131", customerId="c-4", createdAt="2026-05-09T17:12:00+03:00", status="delayed", items=[{"productId": "p-103", "quantity": 8}, {"productId": "p-106", "quantity": 1}], total=3910, dueToday=False),
        Order(id="132", customerId="c-3", createdAt="2026-05-10T07:38:00+03:00", status="packing", items=[{"productId": "p-101", "quantity": 3}], total=2550, dueToday=True),
        Order(id="133", customerId="c-5", createdAt="2026-05-11T09:05:00+03:00", status="new", items=[{"productId": "p-107", "quantity": 6}, {"productId": "p-111", "quantity": 2}], total=1130, dueToday=True),
        Order(id="134", customerId="c-6", createdAt="2026-05-08T11:18:00+03:00", status="delivered", items=[{"productId": "p-102", "quantity": 10}, {"productId": "p-110", "quantity": 4}], total=8200, dueToday=False),
        Order(id="135", customerId="c-7", createdAt="2026-05-09T15:02:00+03:00", status="shipped", items=[{"productId": "p-105", "quantity": 20}, {"productId": "p-107", "quantity": 10}], total=4100, dueToday=False),
        Order(id="136", customerId="c-8", createdAt="2026-05-09T18:47:00+03:00", status="shipped", items=[{"productId": "p-101", "quantity": 6}, {"productId": "p-108", "quantity": 12}], total=9850, dueToday=False),
        Order(id="137", customerId="c-9", createdAt="2026-05-11T08:22:00+03:00", status="packing", items=[{"productId": "p-109", "quantity": 2}, {"productId": "p-112", "quantity": 1}], total=2420, dueToday=True),
        Order(id="138", customerId="c-10", createdAt="2026-05-10T13:28:00+03:00", status="shipped", items=[{"productId": "p-106", "quantity": 3}, {"productId": "p-104", "quantity": 4}], total=5640, dueToday=False),
        Order(id="139", customerId="c-11", createdAt="2026-05-10T16:40:00+03:00", status="shipped", items=[{"productId": "p-110", "quantity": 8}, {"productId": "p-112", "quantity": 2}], total=7900, dueToday=False),
        Order(id="140", customerId="c-12", createdAt="2026-05-11T10:05:00+03:00", status="new", items=[{"productId": "p-111", "quantity": 6}, {"productId": "p-108", "quantity": 4}], total=1880, dueToday=True),
        Order(id="141", customerId="c-2", createdAt="2026-05-08T14:15:00+03:00", status="delayed", items=[{"productId": "p-105", "quantity": 30}, {"productId": "p-103", "quantity": 10}], total=11200, dueToday=False),
        Order(id="142", customerId="c-4", createdAt="2026-05-11T12:30:00+03:00", status="packing", items=[{"productId": "p-107", "quantity": 18}, {"productId": "p-108", "quantity": 6}], total=3360, dueToday=True),
        Order(id="143", customerId="c-1", createdAt="2026-05-07T09:10:00+03:00", status="delivered", items=[{"productId": "p-104", "quantity": 1}, {"productId": "p-101", "quantity": 1}], total=1410, dueToday=False),
        Order(id="144", customerId="c-6", createdAt="2026-05-12T07:40:00+03:00", status="new", items=[{"productId": "p-102", "quantity": 18}, {"productId": "p-109", "quantity": 5}], total=7350, dueToday=True),
        Order(id="145", customerId="c-8", createdAt="2026-05-09T08:55:00+03:00", status="shipped", items=[{"productId": "p-112", "quantity": 4}, {"productId": "p-110", "quantity": 6}], total=9600, dueToday=False),
        Order(id="146", customerId="c-5", createdAt="2026-05-12T08:35:00+03:00", status="packing", items=[{"productId": "p-111", "quantity": 4}, {"productId": "p-103", "quantity": 3}], total=2220, dueToday=True),
        Order(id="147", customerId="c-10", createdAt="2026-05-10T10:11:00+03:00", status="shipped", items=[{"productId": "p-106", "quantity": 5}, {"productId": "p-108", "quantity": 10}], total=6100, dueToday=False),
        Order(id="148", customerId="c-7", createdAt="2026-05-12T09:12:00+03:00", status="new", items=[{"productId": "p-105", "quantity": 15}, {"productId": "p-107", "quantity": 12}], total=3890, dueToday=True),
        Order(id="149", customerId="c-12", createdAt="2026-05-09T20:30:00+03:00", status="delayed", items=[{"productId": "p-101", "quantity": 2}, {"productId": "p-111", "quantity": 8}], total=4440, dueToday=False),
    ],
    shipments=[
        Shipment(id="s-128", orderId="128", carrier="MNG Kargo", trackingCode="MNG128-TR", eta="2026-05-12 15:00", lastScan="İstanbul aktarma merkezi, 09:18", city="İstanbul", risk="clear", notified=False),
        Shipment(id="s-131", orderId="131", carrier="Yurtiçi Kargo", trackingCode="YIC131-TR", eta="2026-05-10 18:00", lastScan="İzmir hub'ından sonra 22 saattir tarama yok", city="İzmir", risk="delayed", notified=False),
        Shipment(id="s-132", orderId="132", carrier="Aras Kargo", trackingCode="ARS132-TR", eta="2026-05-12 12:30", lastScan="Etiket oluşturuldu, teslim alım bekleniyor", city="Ankara", risk="watch", notified=False),
        Shipment(id="s-135", orderId="135", carrier="Sürat Kargo", trackingCode="SRT135-TR", eta="2026-05-12 17:00", lastScan="Kayseri dağıtım merkezine ulaştı", city="Kayseri", risk="clear", notified=False),
        Shipment(id="s-136", orderId="136", carrier="DHL eCommerce", trackingCode="DHL136-TR", eta="2026-05-11 16:00", lastScan="Antalya transfer merkezinde gecikme kaydı", city="Antalya", risk="delayed", notified=False),
        Shipment(id="s-138", orderId="138", carrier="Horoz Lojistik", trackingCode="HRZ138-TR", eta="2026-05-13 11:00", lastScan="Araç çıkışı bekleniyor", city="İzmir", risk="watch", notified=False),
        Shipment(id="s-139", orderId="139", carrier="Yurtiçi Kargo", trackingCode="YIC139-TR", eta="2026-05-12 18:30", lastScan="Dağıtım şubesinde", city="İstanbul", risk="clear", notified=False),
        Shipment(id="s-141", orderId="141", carrier="MNG Kargo", trackingCode="MNG141-TR", eta="2026-05-10 14:00", lastScan="Aktarma merkezinde hasar kontrolü bekliyor", city="Kadıköy", risk="delayed", notified=False),
        Shipment(id="s-143", orderId="143", carrier="Aras Kargo", trackingCode="ARS143-TR", eta="2026-05-08 13:00", lastScan="Teslim edildi", city="İstanbul", risk="clear", notified=True),
        Shipment(id="s-145", orderId="145", carrier="Kolay Gelsin", trackingCode="KLG145-TR", eta="2026-05-13 10:30", lastScan="Otel teslim saat aralığı onayı bekliyor", city="Antalya", risk="watch", notified=False),
        Shipment(id="s-147", orderId="147", carrier="UPS Türkiye", trackingCode="UPS147-TR", eta="2026-05-12 16:45", lastScan="Teslimat aracına yüklendi", city="İzmir", risk="clear", notified=False),
        Shipment(id="s-149", orderId="149", carrier="Aras Kargo", trackingCode="ARS149-TR", eta="2026-05-11 19:00", lastScan="Bostancı şubesinde ödeme teyidi bekleniyor", city="İstanbul", risk="delayed", notified=False),
    ],
    inventoryAlerts=[
        InventoryAlert(productId="p-101", severity="critical", message="Zeytinyağı Hediye Seti mevcut satış hızıyla 2 gün içinde tükenecek.", resolved=False),
        InventoryAlert(productId="p-103", severity="critical", message="Kavrulmuş İncir Reçeli mevcut satış hızıyla 1 gün içinde tükenecek.", resolved=False),
        InventoryAlert(productId="p-105", severity="critical", message="Kurutulmuş Domates Paketi mevcut satış hızıyla 2 gün içinde tükenecek.", resolved=False),
        InventoryAlert(productId="p-106", severity="warning", message="Bakır Cezve için yaklaşık 7 günlük stok kaldı.", resolved=False),
        InventoryAlert(productId="p-107", severity="critical", message="Taze Domates mevcut satış hızıyla 1 gün içinde tükenecek.", resolved=False),
        InventoryAlert(productId="p-108", severity="warning", message="Nar Ekşisi Şişesi için yaklaşık 7 günlük stok kaldı.", resolved=False),
        InventoryAlert(productId="p-110", severity="warning", message="Kilim Yastık Kılıfı için yaklaşık 7 günlük stok kaldı.", resolved=False),
        InventoryAlert(productId="p-111", severity="critical", message="Adaçayı Demeti mevcut satış hızıyla 2 gün içinde tükenecek.", resolved=False),
    ],
    tasks=[
        Task(id="t-1", owner="Depo", title="Sipariş 129'u öğlen teslim alımından önce paketle", priority="high", orderId="129", status="open"),
        Task(id="t-2", owner="Müşteri Masası", title="Sipariş 131 için gecikmiş kargo durumunu incele", priority="high", orderId="131", status="open"),
        Task(id="t-3", owner="Satın Alma", title="İncir reçeli için tedarikçi kapasitesini onayla", priority="medium", status="open"),
        Task(id="t-4", owner="Satın Alma", title="Zeytinyağı hediye seti için acil tedarik talebi hazırla", priority="high", status="open"),
        Task(id="t-5", owner="Operasyon", title="Trendyol stok senkronizasyon hatasını kontrol et", priority="high", status="open"),
        Task(id="t-6", owner="Depo", title="Bugünkü yeni siparişleri öncelik sırasına al", priority="medium", status="open"),
        Task(id="t-7", owner="Satın Alma", title="Adaçayı Demeti için Bozdağ Yayla Ürünleri ile teyitleş", priority="high", status="open"),
        Task(id="t-8", owner="Finans", title="Sipariş 149 ödeme teyidini kontrol et", priority="medium", orderId="149", status="open"),
    ],
    issues=[
        OperationalIssue(id="i-1", category="inventory", severity="critical", title="Raf sayımı stoktan düşük", message="Zeytinyağı Hediye Seti için fiziksel sayım 18 set, pazar yeri bekleyen siparişleri 21 set gösteriyor.", source="Depo Sayım", entityId="p-101", createdAt="2026-05-12T08:10:00+03:00", resolved=False),
        OperationalIssue(id="i-2", category="integration", severity="critical", title="Pazar yeri stok senkronizasyonu gecikti", message="Trendyol stok servisi 42 dakikadır başarılı yanıt dönmedi; kritik ürünlerde fazla satış riski var.", source="Marketplace Sync", createdAt="2026-05-12T08:22:00+03:00", resolved=False),
        OperationalIssue(id="i-3", category="payment", severity="warning", title="Ödeme teyidi bekliyor", message="Sipariş 149 için ödeme sağlayıcıdan kesinleşmiş tahsilat bildirimi alınmadı.", source="POS Gateway", entityId="149", createdAt="2026-05-12T08:45:00+03:00", resolved=False),
        OperationalIssue(id="i-4", category="shipping", severity="critical", title="Kargo taraması gecikti", message="Sipariş 131 için 22 saattir yeni tarama yok; müşteri bildirimi bekliyor.", source="Kargo Takip", entityId="131", createdAt="2026-05-12T09:00:00+03:00", resolved=False),
        OperationalIssue(id="i-5", category="system", severity="warning", title="E-arşiv kuyruğu birikti", message="Son 4 fatura yeniden deneme kuyruğunda; gün sonu kapanışından önce kontrol edilmeli.", source="E-Arşiv", createdAt="2026-05-12T09:15:00+03:00", resolved=False),
        OperationalIssue(id="i-6", category="order", severity="warning", title="Parçalı gönderim gerekiyor", message="Sipariş 141 içindeki kurutulmuş domates miktarı mevcut stok riskini artırıyor; müşteriyle parçalı gönderim planı yapılmalı.", source="Sipariş Kontrol", entityId="141", createdAt="2026-05-12T09:25:00+03:00", resolved=False),
    ],
)

_state = deepcopy(INITIAL_STATE)


def get_state() -> OperationsState:
    sync_inventory_alerts(_state)
    return _state


def reset_state() -> OperationsState:
    global _state
    _state = deepcopy(INITIAL_STATE)
    sync_inventory_alerts(_state)
    return _state


def average_daily_sales(product: Product) -> float:
    if not product.weeklySales:
        return 0

    return sum(product.weeklySales) / len(product.weeklySales)


def coverage_days(product: Product) -> float:
    average_demand = average_daily_sales(product)
    return product.stock / average_demand if average_demand else 999


def remaining_days(product: Product) -> int:
    return math.ceil(coverage_days(product))


def inventory_severity(product: Product) -> str | None:
    days_left = coverage_days(product)

    if days_left <= CRITICAL_COVERAGE_DAYS:
        return "critical"

    if days_left <= WARNING_COVERAGE_DAYS or product.stock <= product.threshold:
        return "warning"

    return None


def inventory_alert_message(product: Product) -> str:
    days_left = remaining_days(product)

    if inventory_severity(product) == "critical":
        return (
            f"{product.name} mevcut satış hızıyla {days_left} gün içinde "
            "tükenecek; tedarik yenilemesi gerekiyor."
        )

    return (
        f"{product.name} için yaklaşık {days_left} günlük stok kaldı; "
        "yeniden sipariş planı kontrol edilmeli."
    )


def sync_inventory_alerts(state: OperationsState) -> None:
    alerts_by_product = {alert.productId: alert for alert in state.inventoryAlerts}

    for product in state.products:
        severity = inventory_severity(product)
        alert = alerts_by_product.get(product.id)

        if severity is None:
            if alert and not alert.resolved:
                alert.resolved = True
            continue

        if alert:
            if not alert.resolved:
                alert.severity = severity  # type: ignore[assignment]
                alert.message = inventory_alert_message(product)
            continue

        state.inventoryAlerts.append(
            InventoryAlert(
                productId=product.id,
                severity=severity,  # type: ignore[arg-type]
                message=inventory_alert_message(product),
                resolved=False,
            )
        )
