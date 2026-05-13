INTENTS = {
    "customer_update_draft",
    "stock_check",
    "order_lookup",
    "shipment_risk",
    "issue_check",
    "customer_lookup",
    "task_summary",
    "operations_summary",
    "return_exchange",
    "complaint",
    "general",
    "unknown",
}

INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": sorted(INTENTS),
        },
        "orderId": {"type": "string"},
        "productId": {"type": "string"},
        "productName": {"type": "string"},
        "customerName": {"type": "string"},
        "customerEmail": {"type": "string"},
        "orderStatus": {
            "type": "string",
            "enum": ["", "new", "packing", "shipped", "delayed", "delivered"],
        },
        "orderTimeframe": {
            "type": "string",
            "enum": ["", "due_today"],
        },
    },
    "required": ["intent"],
}

CONTACT_DRAFT_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string"},
        "body": {"type": "string"},
    },
    "required": ["subject", "body"],
}

OPERATIONS_SYSTEM_PROMPT = """
You are Çırak, an AI operations assistant for a small Turkish business.
Use the conversation language naturally unless the user explicitly requests another language.
Infer operational intent from the full meaning of the message, including mixed-language messages, without relying on language tags.
Use only the operational facts provided in the user prompt. Do not invent orders, stock, dates, carriers, totals, discounts, reservations, or sent-message confirmations.
Write naturally and concisely for the requested channel and business context.
""".strip()

CONTACT_DRAFT_SYSTEM_PROMPT = """
You draft customer-facing messages for a small Turkish business.
Use the customer-facing language implied by the owner's request.
Follow the owner's requested content exactly, especially quantities, products, status, and channel.
If the owner gives a direct message request without an order number, do not substitute the customer's latest order.
Use only the provided data and the owner's request. Do not invent tracking, delivery dates, stock reservations, discounts, or actions already completed.
For WhatsApp or Telegram, use a warm, short, natural message. For email, use a concise customer support tone.
Return only JSON matching the requested schema.
""".strip()

BLOCKED_REPLY_SYSTEM_PROMPT = """
You are Çırak, an AI operations assistant.
Explain briefly why a customer message draft was not created.
Use the conversation language naturally.
Do not add extra facts or alternatives beyond the provided reason.
""".strip()
