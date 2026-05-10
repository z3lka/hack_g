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
1. Red tomato stockout risk with a Mehmet Bey supplier order draft.
2. Yellow Ahmet Bey missed Monday order with WhatsApp reminder draft.
3. Orange Shipping Company X repeated delays with alternative carrier suggestion.
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
            entityName="Tomatoes",
            title="Tomatoes: Sunday stockout risk",
            summary="Tomatoes ran out during the last two Sundays, so this Sunday is a high-risk stockout window.",
            evidence=_evidence(records, "Tomatoes"),
            draftAction="Draft order to Mehmet Bey: Please prepare a Sunday safety restock of 80 kg tomatoes before 11:00.",
            actionType="create_supplier_order_draft",
            confidence=0.93,
        ),
        ProactiveInsight(
            id="fallback-ahmet",
            color="yellow",
            entityName="Ahmet Bey",
            title="Ahmet Bey: usual Monday order missing",
            summary="Ahmet Bey normally orders around 500 TL every Monday, but no order is visible this week.",
            evidence=_evidence(records, "Ahmet Bey"),
            draftAction="WhatsApp draft: Merhaba Ahmet Bey, bu haftaki siparisiniz icin yardimci olmami ister misiniz?",
            actionType="create_customer_reminder_draft",
            confidence=0.88,
        ),
        ProactiveInsight(
            id="fallback-shipping-x",
            color="orange",
            entityName="Shipping Company X",
            title="Shipping Company X: repeated delay pattern",
            summary="The last three Shipping Company X deliveries were late, so regional orders should be routed elsewhere today.",
            evidence=_evidence(records, "Shipping Company X") + _evidence(records, "Alternative Carrier Y"),
            draftAction="Suggestion: Use Alternative Carrier Y for regional shipments until Shipping Company X performance improves.",
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
