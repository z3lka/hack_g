from datetime import datetime
from uuid import uuid4

from . import memory
from .gemini_client import gemini_client
from .models import (
    AgentAction,
    MemoryRecord,
    MorningInsightsResponse,
    OperationsState,
    ProactiveInsight,
)


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
    today = datetime.now().strftime("%A, %B %d %Y")

    product_snapshot = "\n".join(
        f"- {p.name}: stock={p.stock} {p.unit}, threshold={p.threshold}, "
        f"avg_daily_sales={round(sum(p.weeklySales)/len(p.weeklySales), 1)} {p.unit}/day, "
        f"days_left={round(p.stock / (sum(p.weeklySales)/len(p.weeklySales)), 1) if sum(p.weeklySales) > 0 else 'N/A'}, "
        f"supplier={p.supplier}"
        for p in state.products
    )

    order_snapshot = "\n".join(
        f"- Order {o.id}: status={o.status}, dueToday={o.dueToday}, total={o.total} TRY"
        for o in state.orders
    )

    shipment_snapshot = "\n".join(
        f"- Order {s.orderId}: carrier={s.carrier}, risk={s.risk}, eta={s.eta}, lastScan={s.lastScan}"
        for s in state.shipments
    )

    memory_context = "\n".join(f"- {r.text}" for r in records)

    return f"""
You are an AI operations assistant for a small Turkish business (KOBİ).
Today is {today}.

Analyze the current operations snapshot and retrieved memory records below.
Identify the most important proactive insights the business owner should act on TODAY.
Focus on: stock risks, unusual customer patterns, shipping issues, restock opportunities.

Return ONLY strict JSON with this exact shape, no markdown, no explanation:
{{
  "insights": [
    {{
      "color": "red|yellow|orange|green",
      "entityName": "string — product name, customer name, or carrier name",
      "title": "short dashboard title (max 6 words)",
      "summary": "one clear sentence explaining why this matters today",
      "evidence": ["memory record that supports this", "another supporting record"],
      "draftAction": "ready-to-send message or operational instruction (Turkish or English)",
      "actionType": "create_supplier_order_draft|create_customer_reminder_draft|suggest_shipping_alternative|memory_insight_generated",
      "confidence": 0.0
    }}
  ]
}}

Rules:
•⁠  ⁠color red = act today, orange = act this week, yellow = watch, green = all good
•⁠  ⁠Generate 3 to 5 insights maximum
•⁠  ⁠Only include insights supported by memory evidence or clear data anomalies
•⁠  ⁠Do NOT invent facts not present in the snapshot or memory
•⁠  ⁠confidence is a float between 0.0 and 1.0

Current operations snapshot:

PRODUCTS:
{product_snapshot}

ORDERS:
{order_snapshot}

SHIPMENTS:
{shipment_snapshot}

Retrieved memory records:
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
            entityName="Domates",
            title="Domates: KRİTİK STOK",
            summary="Son 3 haftanın verisine göre domates her Cuma tükeniyor. Yarın Cuma, mevcut stok 8 kg, günlük ortalama satış 15 kg. Mehmet Bey'e sipariş verilmesi önerilir.",
            evidence=_evidence(records, "Tomatoes"),
            draftAction="Konu: Acil Domates Siparişi\n\nSayın Mehmet Bey,\n\nMevcut stoğumuz kritik seviyeye düştü. Geçmiş siparişlerimize göre bu hafta 50 kg domates siparişi vermek istiyoruz. Müsaitlik durumunuzu paylaşır mısınız?",
            actionType="create_supplier_order_draft",
            confidence=0.93,
        ),
        ProactiveInsight(
            id="fallback-ahmet",
            color="yellow",
            entityName="Ahmet Bey",
            title="Müşteri Takip: Ahmet Bey",
            summary="Ahmet Bey son 6 haftadır her Pazartesi sipariş verdi. Bu Pazartesi sipariş vermedi, bugün Çarşamba. Hatırlatma mesajı hazırlandı.",
            evidence=_evidence(records, "Ahmet Bey"),
            draftAction="Merhaba Ahmet Bey, bu hafta siparişiniz için yardımcı olabilir miyiz? Haftalık sepetinizi hazırlayalım mı?",
            actionType="create_customer_reminder_draft",
            confidence=0.88,
        ),
        ProactiveInsight(
            id="fallback-shipping-x",
            color="orange",
            entityName="Kargo Firması X",
            title="Tedarikçi Uyarı: Kargo X",
            summary="Bu firma son 3 siparişinizde ortalama 2 gün gecikti. Alternatif olarak Firma Y bölgenizde aktif.",
            evidence=_evidence(records, "Shipping Company X")
            + _evidence(records, "Alternative Carrier Y"),
            draftAction="Alternatif öneri: Bu hafta bölgesel teslimatlar için Firma Y kullanılsın. Son 6 siparişte zamanında teslim gerçekleştirdi.",
            actionType="suggest_shipping_alternative",
            confidence=0.84,
        ),
        ProactiveInsight(
            id="fallback-olive-oil",
            color="green",
            entityName="Zeytinyağı",
            title="Zeytinyağı: Stok Yeterli",
            summary="Zeytinyağı talebi stabil, mevcut stok yaklaşık 3 hafta yeterli.",
            evidence=_evidence(records, "Olive Oil"),
            draftAction="Şu an aksiyon gerekmiyor. Zeytinyağı stokunu önümüzdeki Pazartesi tekrar kontrol et.",
            actionType="memory_insight_generated",
            confidence=0.91,
        ),
    ]


def _evidence(records: list[MemoryRecord], entity_name: str) -> list[str]:
    matching = [r.text for r in records if entity_name.lower() in r.text.lower()]
    return matching[:2] or [
        f"No direct memory found for {entity_name}; fallback rule applied."
    ]
