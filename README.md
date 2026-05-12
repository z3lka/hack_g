# Orbio AI Ops

Working website prototype for a hackathon challenge focused on AI-supported operations for SMEs and cooperatives. The app uses a React frontend with a FastAPI/Python backend, plus a local business-memory layer powered by ChromaDB and Gemini-ready RAG.

## Demo Story

Orbio AI Ops is a single-page operations dashboard for a small e-commerce business with 20-200 products and 10-100 daily orders. It shows how an AI assistant remembers customer habits, supplier behavior, and recurring stock risks, then turns that memory into proactive morning alerts.

Suggested 3-minute demo:

1. Open the dashboard and show the Business Memory panel: tomatoes, Ahmet Bey, Shipping Company X, and olive oil.
2. Point out ChromaDB record count and whether Gemini is live or fallback.
3. Save a short note in `Teach the assistant` to show live memory ingestion.
4. Click `Use draft` on the red tomatoes insight to show a supplier order draft in the agent trace.
5. In the AI Desk, send: `When will order 128 arrive?`
6. Trigger `Notify` on a delayed shipment and show shipping-risk counts update.

## AI Approach

The prototype uses three AI layers:

1. A memory/RAG layer that retrieves historical business events from ChromaDB and sends them to Gemini.
2. A deterministic operational agent that keeps order lookup, stock checks, and task generation reliable during the demo.
3. An email assistant pipeline that classifies inbound customer email, extracts order/customer/product entities, calls commerce tools, retrieves memory, and creates human-approved reply drafts.

When `GEMINI_API_KEY` is available, `/api/insights/morning` asks Gemini to produce structured insight cards and ChromaDB uses Gemini embeddings for memory search. Without a key, the backend returns deterministic fallback insights and local hash embeddings using the same memory records.

- `lookupOrderStatus(orderId)`
- `checkStock(productId)`
- `detectShippingRisks()`
- `suggestRestock(productId)`
- `generateCustomerReply(message, context)`
- `createDailyTaskPlan()`

The Gemini integration uses `google-genai` and defaults to `gemini-2.5-flash`. Set `GEMINI_MODEL` to change it. Memory search defaults to `GEMINI_EMBEDDING_MODEL=gemini-embedding-001`; set it to `text-embedding-004` only if that model is available for your key.

## Architecture

- `backend/app/main.py`: FastAPI routes for state, chat, task generation, inventory drafts, and shipping notifications.
- `backend/app/agent.py`: Python agent runtime, customer reply generation, and operational tools.
- `backend/app/inbox.py`: IMAP ingestion, idempotent email threading, draft creation, and SMTP send-on-approval recording.
- `backend/app/commerce.py`: provider-neutral commerce connector interface with generic REST and in-memory demo adapters.
- `backend/app/memory.py`: ChromaDB persistent memory, Gemini embeddings with local fallbacks, seed data, and retrieval.
- `backend/app/insights.py`: RAG prompt construction, Gemini/fallback insight generation, and insight actions.
- `backend/app/gemini_client.py`: Gemini API wrapper.
- `backend/app/store.py`: in-memory demo state for products, orders, customers, shipments, alerts, and tasks.
- `src/api.ts`: frontend API client for `/api/*`.
- `src/types.ts`: TypeScript domain types mirrored from the backend schemas.
- `src/App.tsx`: thin composition layer for the frontend shell and pages.
- `src/app/`: frontend controller hook, UI-specific types, search/notification/draft helpers, and formatting utilities.
- `src/components/`: reusable shell, drawer, assistant, search, notification, and shared UI components.
- `src/pages/`: dashboard, stock, customers, orders, and memory page modules.
- `src/styles.css`: responsive operations UI.

Actions mutate the FastAPI in-memory state so the dashboard changes visibly during the demo. `Reset demo` restores the operational state and reseeds ChromaDB memory.

## Memory API

- `GET /api/memory/status`: returns ChromaDB/fallback status and record count.
- `GET /api/memory/records`: lists stored business memory records for the Memory page.
- `POST /api/memory/seed`: resets demo memory records.
- `POST /api/memory/ingest`: adds new memory records.
- `POST /api/insights/morning`: retrieves memory and generates proactive insight cards.

## Inbox & Connector API

- `POST /api/inbox/sync`: syncs IMAP email when configured, otherwise loads demo inbox messages once.
- `GET /api/inbox/threads`: lists customer email threads with generated assistant drafts.
- `GET /api/inbox/threads/{id}`: returns a single customer email thread.
- `POST /api/assistant/drafts/{id}/approve`: records human approval and sends through SMTP when configured; without SMTP it records a dry-run send action.
- `GET /api/connectors/health`: reports IMAP, SMTP, and commerce adapter status.

## Run Locally

Start the backend:

```bash
python3 -m pip install -r requirements.txt
npm run dev:backend
```

Optional Gemini setup:

```bash
export GEMINI_API_KEY="your-key"
export GEMINI_MODEL="gemini-2.5-flash"
export GEMINI_EMBEDDING_MODEL="gemini-embedding-001"
export CHROMA_DB_PATH="./chroma_store"
```

Optional email and commerce setup:

```bash
export IMAP_HOST="imap.example.com"
export IMAP_USERNAME="support@example.com"
export IMAP_PASSWORD="..."
export SMTP_HOST="smtp.example.com"
export SMTP_FROM_EMAIL="support@example.com"
export COMMERCE_API_BASE_URL="https://commerce.example.com"
export COMMERCE_API_TOKEN="..."
```

The Telegram and WhatsApp floating buttons are local mock composers. They do not
redirect to external apps or require bot credentials. Email drafts require human
approval before SMTP is called.


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
