import hashlib
import os
import re
from uuid import uuid4

from .models import MemoryRecord, MemoryRecordInput, MemoryStatus


COLLECTION_NAME = "business_memory"
PERSIST_PATH = os.getenv("CHROMA_PATH", "./chroma_store")
EMBEDDING_DIMENSIONS = 96

DEMO_MEMORY: list[MemoryRecordInput] = [
    MemoryRecordInput(
        category="inventory",
        entityName="Tomatoes",
        eventDate="2025-04-15",
        text="2025-04-15: Tomatoes ran out on Sunday, 20 customers complained, and Mehmet Bey was contacted for an emergency restock.",
        metadata={"severity": "red", "supplier": "Mehmet Bey"},
    ),
    MemoryRecordInput(
        category="inventory",
        entityName="Tomatoes",
        eventDate="2025-04-22",
        text="2025-04-22: Tomatoes ran out again on Sunday afternoon. Weekend demand was higher than expected.",
        metadata={"severity": "red", "supplier": "Mehmet Bey"},
    ),
    MemoryRecordInput(
        category="supplier",
        entityName="Mehmet Bey",
        eventDate="2025-04-23",
        text="Mehmet Bey can deliver tomatoes within 24 hours if the order is sent before 11:00.",
        metadata={"supplier": "Mehmet Bey", "product": "Tomatoes"},
    ),
    MemoryRecordInput(
        category="customer",
        entityName="Ahmet Bey",
        eventDate="2025-05-05",
        text="Ahmet Bey places an average 500 TL order every Monday, usually before lunch.",
        metadata={"weekday": "Monday", "averageOrderValue": 500},
    ),
    MemoryRecordInput(
        category="customer",
        entityName="Ahmet Bey",
        eventDate="2025-05-12",
        text="Ahmet Bey responded well to a short WhatsApp reminder when he missed his usual Monday order.",
        metadata={"channel": "WhatsApp", "weekday": "Monday"},
    ),
    MemoryRecordInput(
        category="shipping",
        entityName="Shipping Company X",
        eventDate="2025-05-01",
        text="Shipping Company X delivered late on 3 of the last 3 orders and caused two customer support calls.",
        metadata={"lateDeliveries": 3, "severity": "orange"},
    ),
    MemoryRecordInput(
        category="shipping",
        entityName="Alternative Carrier Y",
        eventDate="2025-05-02",
        text="Alternative Carrier Y delivered regional orders on time for the last 6 shipments.",
        metadata={"onTimeShipments": 6},
    ),
    MemoryRecordInput(
        category="product",
        entityName="Olive Oil",
        eventDate="2025-05-09",
        text="Olive Oil demand is stable. Current stock usually covers 3 weeks, so no purchase action is needed.",
        metadata={"coverageWeeks": 3, "severity": "green"},
    ),
]

_fallback_records: list[MemoryRecord] = []
_last_error: str | None = None


def memory_status() -> MemoryStatus:
    collection = _get_collection()

    if collection is None:
        return MemoryStatus(
            backend="fallback",
            recordCount=len(_fallback_records),
            persistPath=PERSIST_PATH,
            collectionName=COLLECTION_NAME,
            seeded=bool(_fallback_records),
            error=_last_error,
        )

    return MemoryStatus(
        backend="chromadb",
        recordCount=collection.count(),
        persistPath=PERSIST_PATH,
        collectionName=COLLECTION_NAME,
        seeded=collection.count() > 0,
    )


def seed_memory(force: bool = False) -> MemoryStatus:
    collection = _get_collection()

    if collection is None:
        if force or not _fallback_records:
            _fallback_records.clear()
            _fallback_records.extend(_build_records(DEMO_MEMORY, prefix="demo"))
        return memory_status()

    if force:
        client = _get_client()
        if client is not None:
            try:
                client.delete_collection(COLLECTION_NAME)
            except ValueError:
                pass
            collection = _get_collection()

    if collection.count() == 0:
        records = _build_records(DEMO_MEMORY, prefix="demo")
        _add_records_to_collection(collection, records)

    return memory_status()


def ingest_memory(records: list[MemoryRecordInput]) -> list[MemoryRecord]:
    built_records = _build_records(records, prefix="ingest")
    collection = _get_collection()

    if collection is None:
        _fallback_records.extend(built_records)
        return built_records

    _add_records_to_collection(collection, built_records)
    return built_records


def query_memory(query: str, limit: int = 8) -> list[MemoryRecord]:
    collection = _get_collection()

    if collection is None:
        return _query_fallback(query, limit)

    result = collection.query(
        query_embeddings=[embed_text(query)],
        n_results=limit,
        include=["documents", "metadatas"],
    )
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    ids = result.get("ids", [[]])[0]

    return [
        _record_from_chroma(record_id, document, metadata)
        for record_id, document, metadata in zip(ids, documents, metadatas)
    ]


def query_memory_for_morning() -> list[MemoryRecord]:
    queries = [
        "Tomatoes ran out Sunday Mehmet Bey supplier draft order",
        "Ahmet Bey Monday order WhatsApp reminder average 500 TL",
        "Shipping Company X late deliveries alternative carrier",
        "Olive Oil stock sufficient 3 weeks",
    ]
    records: list[MemoryRecord] = []
    seen: set[str] = set()

    for query in queries:
        for record in query_memory(query, limit=5):
            if record.id not in seen:
                records.append(record)
                seen.add(record.id)

    return records


def embed_text(text: str) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSIONS
        vector[index] += 1.0

    norm = sum(value * value for value in vector) ** 0.5

    if norm == 0:
        return vector

    return [value / norm for value in vector]


def _get_client():
    global _last_error

    try:
        import chromadb

        os.makedirs(PERSIST_PATH, exist_ok=True)
        return chromadb.PersistentClient(path=PERSIST_PATH)
    except Exception as exc:  # pragma: no cover - fallback is for demo resilience.
        _last_error = str(exc)
        return None


def _get_collection():
    client = _get_client()

    if client is None:
        return None

    try:
        return client.get_or_create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
    except Exception as exc:  # pragma: no cover - Chroma version/config fallback.
        global _last_error
        _last_error = str(exc)
        return None


def _build_records(records: list[MemoryRecordInput], prefix: str) -> list[MemoryRecord]:
    return [
        MemoryRecord(
            id=f"{prefix}-{index}-{uuid4()}",
            text=record.text,
            category=record.category,
            entityName=record.entityName,
            eventDate=record.eventDate,
            metadata=record.metadata,
        )
        for index, record in enumerate(records)
    ]


def _add_records_to_collection(collection, records: list[MemoryRecord]) -> None:
    collection.add(
        ids=[record.id for record in records],
        documents=[record.text for record in records],
        embeddings=[embed_text(record.text) for record in records],
        metadatas=[_metadata_for_chroma(record) for record in records],
    )


def _metadata_for_chroma(record: MemoryRecord) -> dict[str, str | int | bool]:
    metadata: dict[str, str | int | bool] = {
        "category": record.category,
        "entityName": record.entityName or "",
        "eventDate": record.eventDate or "",
    }
    metadata.update(record.metadata)
    return metadata


def _record_from_chroma(record_id: str, document: str, metadata: dict[str, str | int | bool]) -> MemoryRecord:
    return MemoryRecord(
        id=record_id,
        text=document,
        category=metadata.get("category", "note"),  # type: ignore[arg-type]
        entityName=str(metadata.get("entityName") or "") or None,
        eventDate=str(metadata.get("eventDate") or "") or None,
        metadata={
            key: value
            for key, value in metadata.items()
            if key not in {"category", "entityName", "eventDate"}
        },
    )


def _query_fallback(query: str, limit: int) -> list[MemoryRecord]:
    query_vector = embed_text(query)

    def score(record: MemoryRecord) -> float:
        record_vector = embed_text(record.text)
        return sum(left * right for left, right in zip(query_vector, record_vector))

    return sorted(_fallback_records, key=score, reverse=True)[:limit]
