from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import store
from .agent import agent, create_chat_message
from .insights import generate_morning_insights
from .memory import ingest_memory, list_memory_records, memory_status, seed_memory
from .models import (
    AgentAction,
    ChatRequest,
    ChatResponse,
    InventoryAlert,
    MemoryIngestRequest,
    MemoryIngestResponse,
    MemoryRecord,
    MemoryStatus,
    MorningInsightsResponse,
    OperationsState,
    StateActionResponse,
    TaskPlanResponse,
)

app = FastAPI(
    title="Orbio AI Ops API",
    description="FastAPI backend for the SME AI operations hackathon prototype.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    seed_memory(force=False)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/state", response_model=OperationsState)
def read_state() -> OperationsState:
    return store.get_state()


@app.get("/api/memory/status", response_model=MemoryStatus)
def read_memory_status() -> MemoryStatus:
    return memory_status()


@app.get("/api/memory/records", response_model=list[MemoryRecord])
def read_memory_records() -> list[MemoryRecord]:
    return list_memory_records()


@app.post("/api/memory/seed", response_model=MemoryStatus)
def seed_memory_endpoint() -> MemoryStatus:
    return seed_memory(force=True)


@app.post("/api/memory/ingest", response_model=MemoryIngestResponse)
def ingest_memory_endpoint(request: MemoryIngestRequest) -> MemoryIngestResponse:
    records = ingest_memory(request.records)
    return MemoryIngestResponse(status=memory_status(), records=records)


@app.post("/api/insights/morning", response_model=MorningInsightsResponse)
def morning_insights() -> MorningInsightsResponse:
    return generate_morning_insights(store.get_state())


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    state = store.get_state()
    result = agent.generate_customer_reply(request.message, state)

    return ChatResponse(
        customerMessage=create_chat_message(request.message, "customer"),
        agentMessage=create_chat_message(result.response, "agent"),
        actions=result.actions,
        state=state,
    )


@app.post("/api/shipments/{order_id}/notify", response_model=StateActionResponse)
def notify_customer(order_id: str) -> StateActionResponse:
    state = store.get_state()
    shipment = next((item for item in state.shipments if item.orderId == order_id), None)

    if shipment is None:
        raise HTTPException(status_code=404, detail="Shipment not found")

    shipment.notified = True
    action = AgentAction(
        id=str(uuid4()),
        label=f"Customer update sent for order {order_id}",
        type="notify_customer",
        payload={"orderId": order_id},
    )
    return StateActionResponse(state=state, action=action)


@app.post("/api/inventory/{product_id}/draft", response_model=StateActionResponse)
def create_restock_draft(product_id: str) -> StateActionResponse:
    state = store.get_state()
    product = next((item for item in state.products if item.id == product_id), None)
    alert = next((item for item in state.inventoryAlerts if item.productId == product_id), None)

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    if alert is None:
        alert = InventoryAlert(
            productId=product.id,
            severity=store.inventory_severity(product) or "warning",
            message=store.inventory_alert_message(product),
            resolved=False,
        )
        state.inventoryAlerts.append(alert)

    alert.restockDraft = agent.suggest_restock(product_id, state)
    alert.resolved = True
    action = AgentAction(
        id=str(uuid4()),
        label=f"Restock draft created for {product.name}",
        type="create_restock_draft",
        payload={"productId": product_id},
    )
    return StateActionResponse(state=state, action=action)


@app.post("/api/tasks/generate", response_model=TaskPlanResponse)
def generate_task_plan() -> TaskPlanResponse:
    state = store.get_state()
    created_tasks = agent.create_daily_task_plan(state)
    state.tasks = [*created_tasks, *state.tasks]
    action = AgentAction(
        id=str(uuid4()),
        label=(
            f"{len(created_tasks)} daily tasks generated"
            if created_tasks
            else "Daily task plan already up to date"
        ),
        type="create_task_plan",
        payload={"created": len(created_tasks)},
    )
    return TaskPlanResponse(state=state, action=action, createdTasks=created_tasks)


@app.post("/api/tasks/{task_id}/complete", response_model=StateActionResponse)
def complete_task(task_id: str) -> StateActionResponse:
    state = store.get_state()
    task = next((item for item in state.tasks if item.id == task_id), None)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = "done"
    action = AgentAction(
        id=str(uuid4()),
        label=f"Completed task: {task.title}",
        type="complete_task",
        payload={"taskId": task_id},
    )
    return StateActionResponse(state=state, action=action)


@app.post("/api/reset", response_model=OperationsState)
def reset_demo() -> OperationsState:
    seed_memory(force=True)
    return store.reset_state()
