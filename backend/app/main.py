from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import store
from .agent import agent, create_chat_message
from .models import (
    AgentAction,
    ChatRequest,
    ChatResponse,
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


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/state", response_model=OperationsState)
def read_state() -> OperationsState:
    return store.get_state()


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

    if product is None or alert is None:
        raise HTTPException(status_code=404, detail="Inventory alert not found")

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
    return store.reset_state()
