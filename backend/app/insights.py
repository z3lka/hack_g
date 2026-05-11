from datetime import datetime
from uuid import uuid4

from . import memory
from .gemini_client import gemini_client
from .models import AgentAction, MemoryRecord, MorningInsightsResponse, OperationsState, ProactiveInsight


def generate_morning_insights(state: OperationsState) -> MorningInsightsResponse:
    memory.seed_memory(force=False)
    records = memory.query_memory_for_morning()
    payload = gemini_client.generate_json(_build_prompt(state, records))
    insights = _insights_from_payload(payload) if payload else []
    llm_mode = "gemini" if insights else "fallback"

    if not insights:
        insights = _fallback_insights(records)

    actions = [
        AgentAction(
            id=str(uuid4()),
            label=f"Memory insight generated: {insight.title}",
            type="memory_insight_generated",
            payload={"insightId": insight.id, "entityName": insight.entityName},
        )
        for insight in insights
    ]

    return MorningInsightsResponse(
        generatedAt=datetime.now().isoformat(timespec="minutes"),
        llmMode=llm_mode,
        memoryStatus=memory.memory_status(),
        insights=insights,
        actions=actions,
    )


def _build_prompt(state: OperationsState, records: list[MemoryRecord]) -> str:
    product_snapshot = "\n".join(
        f"- {product.name}: stock={product.stock} {product.unit}, threshold={product.threshold}, supplier={product.supplier}"
        for product in state.products
    )
    memory_context = "\n".join(f"- {record.text}" for record in records)

    return f"""
You are an AI operations memory assistant for a small business.
Use only the current operations snapshot and retrieved memory records.
Return strict JSON only with this shape:
{{
  "insights": [
    {{
      "color": "red|yellow|orange|green",
      "entityName": "string",
      "title": "short dashboard title",
      "summary": "one sentence proactive insight",
      "evidence": ["memory evidence sentence", "memory evidence sentence"],
      "draftAction": "ready-to-send operational draft",
      "actionType": "create_supplier_order_draft|create_customer_reminder_draft|suggest_shipping_alternative|memory_insight_generated",
      "confidence": 0.0
    }}
  ]
}}

Required insights:
1. Red TOMATOES: CRITICAL. Mention last 3 weeks, tomatoes running out every Friday, tomorrow being Friday, current stock 8 kg, average daily sales 15 kg, and Mehmet Bey.
2. Yellow CUSTOMER FOLLOW-UP: Ahmet Bey. Mention orders every Monday for the last 6 weeks, no order this Monday, today Wednesday, and a reminder draft.
3. Orange SUPPLIER WARNING: Shipping Company X. Mention average 2-day delay in last 3 orders and Company Y as an active regional alternative.
4. Green Olive Oil sufficient stock for 3 weeks.

Current operations snapshot:
{product_snapshot}

Retrieved memory:
{memory_context}
""".strip()


def _insights_from_payload(payload: dict | None) -> list[ProactiveInsight]:
    if not payload:
        return []

    raw_insights = payload.get("insights")

    if not isinstance(raw_insights, list):
        return []

    insights: list[ProactiveInsight] = []

    for index, item in enumerate(raw_insights):
        if not isinstance(item, dict):
            continue

        try:
            insights.append(
                ProactiveInsight(
                    id=f"gemini-{index}-{uuid4()}",
                    color=item["color"],
                    entityName=item["entityName"],
                    title=item["title"],
                    summary=item["summary"],
                    evidence=item.get("evidence", []),
                    draftAction=item["draftAction"],
                    actionType=item["actionType"],
                    confidence=float(item.get("confidence", 0.75)),
                )
            )
        except Exception:
            continue

    return insights


def _fallback_insights(records: list[MemoryRecord]) -> list[ProactiveInsight]:
    return [
        ProactiveInsight(
            id="fallback-tomatoes",
            color="red",
            entityName="TOMATOES",
            title="TOMATOES: CRITICAL",
            summary="According to the data from the last 3 weeks, your tomato stock runs out every Friday. Tomorrow is Friday. Current stock is 8 kg, while average daily sales are 15 kg. I recommend placing an order with Mehmet Bey.",
            evidence=_evidence(records, "Tomatoes"),
            draftAction="Subject: Urgent Tomato Order\n\nDear Mehmet Bey,\n\nOur current stock has dropped to a critical level. Based on our previous orders, we would like to place an order for 50 kg of tomatoes this week. Could you please let us know your availability?",
            actionType="create_supplier_order_draft",
            confidence=0.93,
        ),
        ProactiveInsight(
            id="fallback-ahmet",
            color="yellow",
            entityName="Ahmet Bey",
            title="CUSTOMER FOLLOW-UP: Ahmet Bey",
            summary="Ahmet Bey has placed an order every Monday for the last 6 weeks. He did not place an order this Monday, and today is Wednesday. I prepared a reminder message.",
            evidence=_evidence(records, "Ahmet Bey"),
            draftAction="Hello Ahmet Bey, can we help you with your order this week? Would you like us to prepare your weekly basket?",
            actionType="create_customer_reminder_draft",
            confidence=0.88,
        ),
        ProactiveInsight(
            id="fallback-shipping-x",
            color="orange",
            entityName="Shipping Company X",
            title="SUPPLIER WARNING: Shipping Company X",
            summary="This company was delayed by an average of 2 days in your last 3 orders. As an alternative, Company Y is active in your region.",
            evidence=_evidence(records, "Shipping Company X") + _evidence(records, "Alternative Carrier Y"),
            draftAction="Alternative suggestion: Use Company Y for regional deliveries this week. It is active in your region and has a better recent delivery record.",
            actionType="suggest_shipping_alternative",
            confidence=0.84,
        ),
        ProactiveInsight(
            id="fallback-olive-oil",
            color="green",
            entityName="Olive Oil",
            title="Olive Oil: stock is healthy",
            summary="Olive oil demand is stable and current stock should cover about three weeks.",
            evidence=_evidence(records, "Olive Oil"),
            draftAction="No purchase action needed. Recheck olive oil coverage next Monday.",
            actionType="memory_insight_generated",
            confidence=0.91,
        ),
    ]


def _evidence(records: list[MemoryRecord], entity_name: str) -> list[str]:
    matching = [record.text for record in records if entity_name.lower() in record.text.lower()]
    return matching[:2] or [f"No direct memory found for {entity_name}; fallback demo rule applied."]
