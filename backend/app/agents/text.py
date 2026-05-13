import re

from ..models import (
    ContactDraftChannel,
    Customer,
    OperationsState,
    Order,
    Product,
    Shipment,
)

ORDER_ID_PATTERN = re.compile(r"(?:order|siparis|#)?\s*(\d{3,})", re.IGNORECASE)
QUANTITY_PATTERN = re.compile(
    r"\b(\d+)\s*(adet|set|paket|paketi|kavanoz|kg|sise|sisesi|demet|unit|units|piece|pieces|pcs)?\b",
    re.IGNORECASE,
)
PRODUCT_MATCH_STOPWORDS = {
    "set",
    "seti",
    "paket",
    "paketi",
    "adet",
    "kg",
    "sise",
    "sisesi",
    "stok",
    "durum",
    "durumu",
    "var",
    "mi",
}
CUSTOMER_MATCH_STOPWORDS = {
    "bey",
    "hanim",
    "market",
    "kafe",
    "cafe",
    "otel",
    "satin",
    "alma",
}


def summarize_order_items(order: Order, state: OperationsState) -> str:
    parts: list[str] = []
    for item in order.items:
        product = next((p for p in state.products if p.id == item.productId), None)
        parts.append(
            f"{item.quantity}x {product.name if product else 'Unknown product'}"
        )
    return ", ".join(parts)


def _normalize(value: str) -> str:
    replacements = {
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u",
    }
    normalized = value.replace("İ", "i").replace("I", "i").lower()
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return " ".join(re.sub(r"[^a-z0-9\s]", " ", normalized).split())


def _phrase_in_normalized_text(normalized: str, phrase: str) -> bool:
    normalized_phrase = _normalize(phrase)
    if not normalized_phrase:
        return False

    return bool(
        re.search(rf"(?:^|\s){re.escape(normalized_phrase)}(?:\s|$)", normalized)
    )


def _is_customer_update_request(message: str) -> bool:
    normalized = _normalize(message)
    tokens = set(normalized.split())

    if {"tell", "notify"} & tokens:
        return True
    if "message" in tokens and ({"send", "draft", "write"} & tokens or "to" in tokens):
        return True
    if "send" in tokens and (
        {"email", "mail", "whatsapp", "telegram"} & tokens
        or _phrase_in_normalized_text(normalized, "customer update")
    ):
        return True
    if "update" in tokens and ({"customer", "client"} & tokens or "about" in tokens):
        return True
    if {"mesaj", "gonder", "gonderin", "bilgilendir", "haber"} & tokens:
        return True
    if any(token.startswith(("soyle", "ilet")) for token in tokens):
        return True

    return False


def _has_direct_customer_message_content(
    message: str,
    product: Product | None,
) -> bool:
    if not _is_customer_update_request(message):
        return False

    normalized = _normalize(message)
    if _mentions_explicit_order_reference(message):
        return False

    tokens = set(normalized.split())
    has_directive = bool(
        {"tell", "notify", "say", "let"} & tokens
        or any(
            token.startswith(("soyle", "bildir", "bilgilendir", "ilet"))
            for token in tokens
        )
        or "haber" in tokens
    )
    has_content = bool(
        product
        or _extract_quantity_phrase(message)
        or _direct_update_status(normalized)
    )

    return has_directive and has_content


def _fallback_contact_draft_payload(
    message: str,
    customer: Customer,
    order: Order | None,
    shipment: Shipment | None,
    tracking_url: str | None,
    state: OperationsState,
    product: Product | None,
    direct_customer_message: bool,
) -> dict[str, str]:
    return {
        "subject": _fallback_contact_draft_subject(message, order, product),
        "body": _fallback_contact_draft_body(
            message,
            customer,
            order,
            shipment,
            tracking_url,
            state,
            product,
            direct_customer_message,
        ),
    }


def _fallback_contact_draft_subject(
    message: str,
    order: Order | None,
    product: Product | None,
) -> str:
    fallback_language = _fallback_response_language(message)

    if order:
        return (
            f"Sipariş #{order.id} güncellemesi"
            if fallback_language == "tr"
            else f"Update on order #{order.id}"
        )

    if product:
        status = _direct_update_status(_normalize(message))
        if fallback_language == "tr":
            suffix = "geldi" if status == "arrived" else "hazır"
            return f"{product.name} {suffix}"
        suffix = "arrived" if status == "arrived" else "is ready"
        return f"{product.name} {suffix}"

    return "Müşteri mesajı" if fallback_language == "tr" else "Customer message"


def _fallback_contact_draft_body(
    message: str,
    customer: Customer,
    order: Order | None,
    shipment: Shipment | None,
    tracking_url: str | None,
    state: OperationsState,
    product: Product | None,
    direct_customer_message: bool,
) -> str:
    fallback_language = _fallback_response_language(message)

    if not direct_customer_message and order:
        items = summarize_order_items(order, state)
        if fallback_language == "tr":
            lines = [
                f"Merhaba {customer.name},",
                "",
                (
                    f"Sipariş #{order.id} için kısa bir güncelleme paylaşmak istedik. "
                    f"Güncel durum: {order.status}."
                ),
                f"Sipariş içeriği: {items}.",
            ]
            if shipment and tracking_url:
                lines.extend(
                    [
                        f"Kargo firması: {shipment.carrier}. Tahmini teslim: {shipment.eta}.",
                        f"Son kargo hareketi: {shipment.lastScan}.",
                        f"Takip bağlantısı: {tracking_url}",
                    ]
                )
            else:
                lines.append(
                    "Takip bilgisi henüz oluşmadı; kargo kaydı açıldığında paylaşacağız."
                )
            lines.extend(["", "Sevgiler,", "Çırak"])
            return "\n".join(lines)

        lines = [
            f"Hi {customer.name},",
            "",
            f"Quick update on order #{order.id}: the current status is {order.status}.",
            f"Order items: {items}.",
        ]
        if shipment and tracking_url:
            lines.extend(
                [
                    f"Carrier: {shipment.carrier}. Estimated delivery: {shipment.eta}.",
                    f"Latest scan: {shipment.lastScan}.",
                    f"Tracking link: {tracking_url}",
                ]
            )
        else:
            lines.append(
                "Tracking is not available yet; we will share it as soon as "
                "the carrier record is created."
            )
        lines.extend(["", "Best,", "Çırak"])
        return "\n".join(lines)

    normalized = _normalize(message)
    status = _direct_update_status(normalized)
    quantity = _extract_quantity_phrase(message)
    product_phrase = _customer_product_phrase(product, quantity)
    first_name = _first_name(customer.name)

    if fallback_language == "tr":
        if status == "arrived":
            if _mentions_special_order(normalized):
                update = (
                    f"Daha önce özel olarak sipariş ettiğiniz {product_phrase} geldi."
                )
            else:
                update = f"{product_phrase} geldi."
            follow_up = "Teslimat için nasıl ilerlememizi istersiniz?"
        elif status == "ready":
            update = f"{product_phrase} hazır."
            follow_up = "Teslimat veya teslim alma için nasıl ilerleyelim?"
        else:
            update = f"{product_phrase} için size bilgi vermek istedik."
            follow_up = "Uygun olduğunuzda dönüş yapabilirsiniz."

        return "\n".join(
            [
                f"Merhaba {first_name},",
                "",
                f"{update} {follow_up}",
                "",
                "Sevgiler,",
                "Çırak",
            ]
        )

    if status == "arrived":
        if _mentions_special_order(normalized):
            update = f"The {product_phrase} you special ordered has arrived."
        else:
            update = f"{product_phrase} has arrived."
        follow_up = "How would you like us to proceed with delivery?"
    elif status == "ready":
        update = f"{product_phrase} is ready."
        follow_up = "How would you like to handle delivery or pickup?"
    else:
        update = f"We wanted to share a quick update about {product_phrase}."
        follow_up = "Please let us know what works best for you."

    return "\n".join(
        [
            f"Hi {first_name},",
            "",
            f"{update} {follow_up}",
            "",
            "Best,",
            "Çırak",
        ]
    )


def _direct_update_status(normalized: str) -> str | None:
    tokens = set(normalized.split())

    if (
        any(token.startswith("geld") for token in tokens)
        or {"ulasti", "arrived", "received"} & tokens
        or _phrase_in_normalized_text(normalized, "came in")
    ):
        return "arrived"

    if {"hazir", "ready", "available", "stokta"} & tokens or _phrase_in_normalized_text(
        normalized, "in stock"
    ):
        return "ready"

    return None


def _extract_quantity_phrase(message: str) -> str | None:
    normalized = _normalize(message)
    unit_labels = {
        "adet": "adet",
        "set": "set",
        "paket": "paket",
        "paketi": "paket",
        "kavanoz": "kavanoz",
        "kg": "kg",
        "sise": "şişe",
        "sisesi": "şişe",
        "demet": "demet",
        "unit": "adet",
        "units": "adet",
        "piece": "adet",
        "pieces": "adet",
        "pcs": "adet",
    }

    for match in QUANTITY_PATTERN.finditer(normalized):
        number = match.group(1)
        unit = match.group(2)
        if unit:
            return f"{number} {unit_labels.get(unit, unit)}"
        return number

    return None


def _customer_product_phrase(product: Product | None, quantity: str | None) -> str:
    if product:
        return f"{quantity} {product.name}" if quantity else product.name
    return quantity or "siparişiniz"


def _mentions_special_order(normalized: str) -> bool:
    tokens = set(normalized.split())
    return bool(
        ({"ozel", "special"} & tokens)
        and (
            {"siparis", "order", "ordered"} & tokens
            or _phrase_in_normalized_text(normalized, "special order")
        )
    )


def _mentions_explicit_order_reference(message: str) -> bool:
    normalized = _normalize(message)
    return bool(
        re.search(r"#\s*\d{3,}", message)
        or re.search(r"#\s*\d{3,}", normalized)
        or re.search(
            r"(?:^|\s)(?:order|siparis)\s*#?\s*\d{3,}(?:\s|$)",
            normalized,
        )
    )


def _first_name(name: str) -> str:
    return name.strip().split()[0] if name.strip() else "Merhaba"


def _detect_requested_channel(message: str) -> ContactDraftChannel | None:
    normalized = _normalize(message)
    tokens = set(normalized.split())

    if "telegram" in tokens:
        return "telegram"
    if "whatsapp" in tokens or _phrase_in_normalized_text(normalized, "whats app"):
        return "whatsapp"
    if {"email", "mail", "eposta"} & tokens or _phrase_in_normalized_text(
        normalized,
        "e posta",
    ):
        return "email"

    return None


def _default_contact_channel(customer: Customer) -> ContactDraftChannel:
    if customer.channel == "Email" and customer.email:
        return "email"
    if customer.phone:
        return "whatsapp"
    return "email"


def _looks_like_customer_lookup(normalized: str) -> bool:
    tokens = set(normalized.split())
    return bool(
        {"who", "kim"} & tokens
        or {"phone", "email", "contact", "channel", "musteri", "customer"} & tokens
    )


def _looks_like_order_lookup(normalized: str) -> bool:
    tokens = set(normalized.split())
    return bool(
        {
            "siparis",
            "order",
            "orders",
            "nerede",
            "where",
            "gelir",
            "arrive",
            "eta",
            "teslim",
            "delivery",
            "takip",
            "tracking",
            "delayed",
            "packing",
        }
        & tokens
        or _mentions_due_today(normalized)
        or "gecik" in normalized
    )


def _mentions_today(normalized: str) -> bool:
    tokens = set(normalized.split())
    return bool({"today", "bugun"} & tokens)


def _mentions_due_today(normalized: str) -> bool:
    return (
        _phrase_in_normalized_text(normalized, "due today")
        or _phrase_in_normalized_text(normalized, "today orders")
        or _phrase_in_normalized_text(normalized, "orders today")
        or _phrase_in_normalized_text(normalized, "bugun")
    )


def _tracking_url(shipment: Shipment) -> str:
    return f"https://tracking.cirak.local/{_slugify(shipment.carrier)}/{shipment.trackingCode}"


def _slugify(value: str) -> str:
    normalized = _normalize(value)
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-") or "carrier"


def get_channel_display_name(channel: ContactDraftChannel) -> str:
    labels: dict[ContactDraftChannel, str] = {
        "whatsapp": "WhatsApp",
        "telegram": "Telegram",
        "email": "email",
    }
    return labels[channel]


def _product_match_tokens(value: str) -> set[str]:
    return {
        token
        for token in value.split()
        if len(token) >= 3 and token not in PRODUCT_MATCH_STOPWORDS
    }


def _fallback_response_language(message: str) -> str:
    # Offline fallback only; production language choice lives in the LLM system prompt.
    return "tr" if any(char in message for char in "çğıöşüÇĞİÖŞÜ") else "en"
