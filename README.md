# Orbio AI Ops

Working website prototype for a hackathon challenge focused on AI-supported operations for SMEs and cooperatives. The app now uses a React frontend with a FastAPI/Python backend.

## Demo Story

Orbio AI Ops is a single-page operations dashboard for a small e-commerce business with 20-200 products and 10-100 daily orders. It shows how an AI agent can reduce manual work across customer communication, order tracking, shipping exceptions, stock alerts, and team task routing.

Suggested 3-minute demo:

1. Open the dashboard and show overnight orders, stock risks, delayed shipments, and the team queue.
2. In the AI Desk, send: `When will order 128 arrive?`
3. Show the agent lookup trace and customer-ready shipment response.
4. Trigger `Notify` on a delayed shipment and show shipping-risk counts update.
5. Trigger `Draft` on a low-stock product and show an agent action for the supplier draft.
6. Click `Generate tasks` to create warehouse and customer-service tasks from current operational data.

## AI Approach

The prototype uses an API-ready Python mock agent. The current implementation is deterministic for demo reliability, but it is organized around tool-like functions that map directly to a real LLM agent:

- `lookupOrderStatus(orderId)`
- `checkStock(productId)`
- `detectShippingRisks()`
- `suggestRestock(productId)`
- `generateCustomerReply(message, context)`
- `createDailyTaskPlan()`

A live model integration can replace the deterministic response generation inside `backend/app/agent.py` while keeping the same FastAPI endpoints and typed business tools.

## Architecture

- `backend/app/main.py`: FastAPI routes for state, chat, task generation, inventory drafts, and shipping notifications.
- `backend/app/agent.py`: Python agent runtime, customer reply generation, and operational tools.
- `backend/app/store.py`: in-memory demo state for products, orders, customers, shipments, alerts, and tasks.
- `src/api.ts`: frontend API client for `/api/*`.
- `src/types.ts`: TypeScript domain types mirrored from the backend schemas.
- `src/App.tsx`: dashboard UI and action flows.
- `src/styles.css`: responsive operations UI.

Actions mutate the FastAPI in-memory state so the dashboard changes visibly during the demo. `Reset demo` restores the initial state.

## Run Locally

Start the backend:

```bash
python3 -m pip install -r requirements.txt
npm run dev:backend
```

Start the frontend in a second terminal:

```bash
npm install
npm run dev:frontend
```

Open `http://localhost:5173/`. The Vite dev server proxies `/api` to FastAPI on `http://127.0.0.1:8000`.

For a production build:

```bash
npm run build
```

FastAPI docs are available at `http://127.0.0.1:8000/docs` while the backend is running.
