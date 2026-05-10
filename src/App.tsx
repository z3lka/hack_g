import {
  AlertTriangle,
  ArrowUpRight,
  Bell,
  Bot,
  Boxes,
  CheckCircle2,
  ClipboardList,
  Clock3,
  MessageSquareText,
  PackageCheck,
  RefreshCw,
  Search,
  Send,
  ShoppingBag,
  Sparkles,
  Truck,
  UserRoundCheck,
  Warehouse,
} from "lucide-react";
import {
  FormEvent,
  ReactNode,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  completeTaskRequest,
  createRestockDraft,
  fetchMorningInsights,
  fetchState,
  generateTaskPlan,
  ingestMemory,
  notifyShipment,
  resetDemoState,
  sendCustomerMessage,
} from "./api";
import type {
  AgentAction,
  ChatMessage,
  InventoryAlert,
  MemoryStatus,
  OperationsState,
  Order,
  Product,
  ProactiveInsight,
} from "./types";

const starterMessages = [
  "When will order 128 arrive?",
  "Is roasted fig jam in stock?",
  "Any shipping delays today?",
];

const emptyState: OperationsState = {
  products: [],
  customers: [],
  orders: [],
  shipments: [],
  inventoryAlerts: [],
  tasks: [],
};

const initialMessages: ChatMessage[] = [
  {
    id: "demo-customer-128",
    role: "customer",
    text: "When will order 128 arrive?",
    timestamp: "09:18",
  },
  {
    id: "demo-agent-128",
    role: "agent",
    text: "Order 128 is with MNG Cargo and ETA is 2026-05-11 15:00. Last scan was Istanbul transfer center at 09:18.",
    timestamp: "09:18",
  },
];

function App() {
  const [state, setState] = useState<OperationsState | null>(null);
  const [chatInput, setChatInput] = useState(starterMessages[0]);
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [actions, setActions] = useState<AgentAction[]>([]);
  const [insights, setInsights] = useState<ProactiveInsight[]>([]);
  const [memoryStatus, setMemoryStatus] = useState<MemoryStatus | null>(null);
  const [llmMode, setLlmMode] = useState<"gemini" | "fallback">("fallback");
  const [insightsGeneratedAt, setInsightsGeneratedAt] = useState("");
  const [apiError, setApiError] = useState("");
  const [isMutating, setIsMutating] = useState(false);
  const [selectedFilter, setSelectedFilter] = useState("Today");
  const [memoryInput, setMemoryInput] = useState(
    "Ahmet Bey prefers a WhatsApp reminder before 11:00 when his Monday order is missing.",
  );

  useEffect(() => {
    void loadState();
  }, []);

  const currentState = state ?? emptyState;
  const riskyShipments = useMemo(
    () =>
      currentState.shipments.filter((shipment) => shipment.risk !== "clear" && !shipment.notified),
    [currentState.shipments],
  );
  const activeAlerts = currentState.inventoryAlerts.filter((alert) => !alert.resolved);
  const dueToday = currentState.orders.filter(
    (order) => order.dueToday && order.status !== "delivered",
  );
  const openTasks = currentState.tasks.filter((task) => task.status === "open");
  const lowStockProducts = currentState.products.filter(
    (product) => product.stock <= product.threshold,
  );
  const overnightOrders = currentState.orders.filter((order) =>
    order.createdAt.includes("2026-05-10"),
  );
  const visibleOrders = currentState.orders.filter((order) => {
    if (selectedFilter === "Today") {
      return order.dueToday;
    }

    if (selectedFilter === "Risk") {
      const shipment = currentState.shipments.find((item) => item.orderId === order.id);
      return order.status === "delayed" || shipment?.risk === "watch" || shipment?.risk === "delayed";
    }

    return true;
  });

  async function loadState() {
    try {
      setApiError("");
      const nextState = await fetchState();
      setState(nextState);
      await refreshMorningInsights();
    } catch (error) {
      setApiError(getErrorMessage(error));
    }
  }

  async function refreshMorningInsights() {
    const response = await fetchMorningInsights();
    setInsights(response.insights);
    setMemoryStatus(response.memoryStatus);
    setLlmMode(response.llmMode);
    setInsightsGeneratedAt(response.generatedAt);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!chatInput.trim()) {
      return;
    }

    await runMutation(async () => {
      const response = await sendCustomerMessage(chatInput);
      setMessages((current) => [...current, response.customerMessage, response.agentMessage]);
      prependActions(response.actions);
      setState(response.state);
      setChatInput("");
    });
  }

  async function handleMemoryIngest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!memoryInput.trim()) {
      return;
    }

    await runMutation(async () => {
      const response = await ingestMemory([
        {
          text: memoryInput,
          category: "note",
          eventDate: "2026-05-10",
        },
      ]);
      setMemoryStatus(response.status);
      await refreshMorningInsights();
      prependActions([
        {
          id: crypto.randomUUID(),
          label: "New memory note saved to ChromaDB",
          type: "memory_insight_generated",
          payload: { records: response.records.length },
        },
      ]);
      setMemoryInput("");
    });
  }

  async function markShipmentNotified(orderId: string) {
    await runMutation(async () => {
      const response = await notifyShipment(orderId);
      setState(response.state);
      prependActions([response.action]);
    });
  }

  async function resolveInventoryAlert(alert: InventoryAlert) {
    await runMutation(async () => {
      const response = await createRestockDraft(alert.productId);
      setState(response.state);
      prependActions([response.action]);
    });
  }

  async function generateDailyPlan() {
    await runMutation(async () => {
      const response = await generateTaskPlan();
      setState(response.state);
      prependActions([response.action]);
    });
  }

  async function completeTask(taskId: string) {
    await runMutation(async () => {
      const response = await completeTaskRequest(taskId);
      setState(response.state);
      prependActions([response.action]);
    });
  }

  async function resetDemo() {
    await runMutation(async () => {
      setState(await resetDemoState());
      await refreshMorningInsights();
      setActions([]);
      setMessages(initialMessages);
    });
  }

  async function runMutation(operation: () => Promise<void>) {
    try {
      setIsMutating(true);
      setApiError("");
      await operation();
    } catch (error) {
      setApiError(getErrorMessage(error));
    } finally {
      setIsMutating(false);
    }
  }

  function prependActions(nextActions: AgentAction[]) {
    setActions((current) => [...nextActions, ...current].slice(0, 8));
  }

  function handleInsightAction(insight: ProactiveInsight) {
    prependActions([
      {
        id: crypto.randomUUID(),
        label: insight.draftAction,
        type: insight.actionType,
        payload: {
          insightId: insight.id,
          entityName: insight.entityName,
        },
      },
    ]);
  }

  if (!state) {
    return (
      <main className="loading-screen">
        <Bot size={34} />
        <strong>Connecting to FastAPI backend</strong>
        <span>{apiError || "Loading operations state from /api/state..."}</span>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <aside className="sidebar" aria-label="Main navigation">
        <div className="brand-lockup">
          <div className="brand-mark">
            <Sparkles size={21} />
          </div>
          <div>
            <strong>Orbio AI Ops</strong>
            <span>SME command center</span>
          </div>
        </div>

        <nav className="nav-list">
          <a className="active" href="#dashboard">
            <Boxes size={18} /> Dashboard
          </a>
          <a href="#orders">
            <ShoppingBag size={18} /> Orders
          </a>
          <a href="#shipments">
            <Truck size={18} /> Shipping
          </a>
          <a href="#inventory">
            <Warehouse size={18} /> Inventory
          </a>
          <a href="#assistant">
            <Bot size={18} /> AI Desk
          </a>
        </nav>

        <div className="runbook-panel">
          <div className="panel-icon">
            <Clock3 size={18} />
          </div>
          <p>08:00 auto-run</p>
          <strong>{dueToday.length} orders need handoff</strong>
          <button
            className="ghost-button"
            type="button"
            onClick={generateDailyPlan}
            disabled={isMutating}
          >
            <ClipboardList size={16} />
            Generate tasks
          </button>
        </div>
      </aside>

      <section className="workspace" id="dashboard">
        <header className="topbar">
          <div>
            <p className="eyebrow">Sunday, May 10</p>
            <h1>Operations pulse</h1>
          </div>
          <div className="topbar-actions">
            <div className="search-box">
              <Search size={17} />
              <span>Order, product, customer</span>
            </div>
            <button className="icon-button" type="button" aria-label="Notifications">
              <Bell size={18} />
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={resetDemo}
              disabled={isMutating}
            >
              <RefreshCw size={16} />
              Reset demo
            </button>
          </div>
        </header>
        {apiError ? <div className="api-banner">{apiError}</div> : null}

        <section className="metric-grid" aria-label="Operations metrics">
          <MetricCard
            icon={<ShoppingBag size={22} />}
            label="Overnight orders"
            value={overnightOrders.length.toString()}
            detail={`${dueToday.length} due today`}
            tone="green"
          />
          <MetricCard
            icon={<AlertTriangle size={22} />}
            label="Stock risks"
            value={activeAlerts.length.toString()}
            detail={`${lowStockProducts.length} below threshold`}
            tone="orange"
          />
          <MetricCard
            icon={<Truck size={22} />}
            label="Shipping watch"
            value={riskyShipments.length.toString()}
            detail="proactive updates ready"
            tone="blue"
          />
          <MetricCard
            icon={<PackageCheck size={22} />}
            label="Open tasks"
            value={openTasks.length.toString()}
            detail="warehouse and support"
            tone="neutral"
          />
        </section>

        <section className="memory-section" aria-label="Business memory insights">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Business Memory</p>
              <h2>Morning proactive insights</h2>
            </div>
            <MemoryStatusBadge
              status={memoryStatus}
              llmMode={llmMode}
              generatedAt={insightsGeneratedAt}
            />
          </div>
          <div className="insight-grid">
            {insights.map((insight) => (
              <InsightCard
                insight={insight}
                key={insight.id}
                onAction={() => handleInsightAction(insight)}
              />
            ))}
            {!insights.length ? (
              <div className="empty-state memory-empty">
                <Sparkles size={24} />
                <span>Memory insights will appear after FastAPI generates the morning briefing.</span>
              </div>
            ) : null}
          </div>
        </section>

        <div className="content-grid">
          <section className="main-column">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Live workspace</p>
                <h2>Today&apos;s control board</h2>
              </div>
              <SegmentedControl
                value={selectedFilter}
                options={["Today", "Risk", "All"]}
                onChange={setSelectedFilter}
              />
            </div>

            <section className="order-board" id="orders">
              {visibleOrders.map((order) => {
                const customer = state.customers.find((item) => item.id === order.customerId);
                const shipment = state.shipments.find((item) => item.orderId === order.id);

                return (
                  <article className="order-card" key={order.id}>
                    <div className="order-card-header">
                      <div>
                        <span className="order-id">#{order.id}</span>
                        <h3>{customer?.name}</h3>
                      </div>
                      <StatusPill status={shipment?.risk ?? order.status} />
                    </div>
                    <p>{summarizeOrderItems(order, state)}</p>
                    <div className="order-meta">
                      <span>{customer?.channel}</span>
                      <span>{formatCurrency(order.total)}</span>
                      <span>{order.dueToday ? "Due today" : "Scheduled"}</span>
                    </div>
                    {shipment ? (
                      <div className="shipment-strip">
                        <Truck size={16} />
                        <span>{shipment.carrier}</span>
                        <strong>{shipment.eta}</strong>
                      </div>
                    ) : (
                      <div className="shipment-strip muted">
                        <Warehouse size={16} />
                        <span>Awaiting warehouse handoff</span>
                      </div>
                    )}
                  </article>
                );
              })}
            </section>

            <section className="split-grid">
              <div className="panel" id="inventory">
                <div className="panel-heading">
                  <div>
                    <p className="eyebrow">Inventory</p>
                    <h2>Reorder risks</h2>
                  </div>
                  <Boxes size={20} />
                </div>
                <div className="inventory-list">
                  {activeAlerts.map((alert) => {
                    const product = state.products.find((item) => item.id === alert.productId);

                    if (!product) {
                      return null;
                    }

                    return (
                      <InventoryRow
                        key={alert.productId}
                        alert={alert}
                        product={product}
                        onResolve={() => resolveInventoryAlert(alert)}
                        disabled={isMutating}
                      />
                    );
                  })}
                  {!activeAlerts.length ? (
                    <div className="empty-state">
                      <CheckCircle2 size={24} />
                      <span>All reorder alerts have drafts.</span>
                    </div>
                  ) : null}
                </div>
              </div>

              <div className="panel" id="shipments">
                <div className="panel-heading">
                  <div>
                    <p className="eyebrow">Shipping</p>
                    <h2>Exceptions</h2>
                  </div>
                  <Truck size={20} />
                </div>
                <div className="exception-list">
                  {riskyShipments.map((shipment) => (
                    <article className="exception-card" key={shipment.id}>
                      <div>
                        <span className="order-id">#{shipment.orderId}</span>
                        <h3>{shipment.carrier}</h3>
                        <p>{shipment.lastScan}</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => markShipmentNotified(shipment.orderId)}
                        disabled={isMutating}
                      >
                        <UserRoundCheck size={16} />
                        Notify
                      </button>
                    </article>
                  ))}
                  {!riskyShipments.length ? (
                    <div className="empty-state">
                      <CheckCircle2 size={24} />
                      <span>No unnotified shipping risks.</span>
                    </div>
                  ) : null}
                </div>
              </div>
            </section>

            <section className="panel">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Workflow</p>
                  <h2>Team queue</h2>
                </div>
                <ClipboardList size={20} />
              </div>
              <div className="task-list">
                {openTasks.slice(0, 6).map((task) => (
                  <article className="task-row" key={task.id}>
                    <button
                      className="check-button"
                      type="button"
                      aria-label={`Complete ${task.title}`}
                      onClick={() => completeTask(task.id)}
                      disabled={isMutating}
                    >
                      <CheckCircle2 size={18} />
                    </button>
                    <div>
                      <strong>{task.title}</strong>
                      <span>
                        {task.owner} {task.orderId ? `- order ${task.orderId}` : ""}
                      </span>
                    </div>
                    <PriorityTag priority={task.priority} />
                  </article>
                ))}
              </div>
            </section>
          </section>

          <aside className="assistant-column" id="assistant">
            <section className="assistant-panel">
              <div className="assistant-header">
                <div className="assistant-avatar">
                  <Bot size={23} />
                </div>
                <div>
                  <p className="eyebrow">AI Desk</p>
                  <h2>Customer automation</h2>
                </div>
              </div>

              <div className="starter-row">
                {starterMessages.map((message) => (
                  <button type="button" key={message} onClick={() => setChatInput(message)}>
                    {message}
                  </button>
                ))}
              </div>

              <div className="chat-log" aria-live="polite">
                {messages.map((message) => (
                  <div className={`chat-bubble ${message.role}`} key={message.id}>
                    <span>{message.role === "agent" ? "AI agent" : "Customer"}</span>
                    <p>{message.text}</p>
                    <time>{message.timestamp}</time>
                  </div>
                ))}
              </div>

              <form className="chat-form" onSubmit={handleSubmit}>
                <input
                  value={chatInput}
                  onChange={(event) => setChatInput(event.target.value)}
                  placeholder="Customer message"
                />
                <button type="submit" aria-label="Send message" disabled={isMutating}>
                  <Send size={18} />
                </button>
              </form>
            </section>

            <section className="panel memory-ingest-panel">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Memory Input</p>
                  <h2>Teach the assistant</h2>
                </div>
                <Sparkles size={20} />
              </div>
              <form className="memory-ingest-form" onSubmit={handleMemoryIngest}>
                <textarea
                  value={memoryInput}
                  onChange={(event) => setMemoryInput(event.target.value)}
                  placeholder="Business note, customer rhythm, supplier issue"
                />
                <button type="submit" disabled={isMutating}>
                  <ArrowUpRight size={16} />
                  Save to memory
                </button>
              </form>
            </section>

            <section className="panel action-feed">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Agent trace</p>
                  <h2>Actions</h2>
                </div>
                <MessageSquareText size={20} />
              </div>
              <div className="action-list">
                {actions.length ? (
                  actions.map((action) => (
                    <article className="action-row" key={action.id}>
                      <ArrowUpRight size={16} />
                      <span>{action.label}</span>
                    </article>
                  ))
                ) : (
                  <div className="empty-state compact">
                    <Sparkles size={22} />
                    <span>Agent actions appear here.</span>
                  </div>
                )}
              </div>
            </section>
          </aside>
        </div>
      </section>
    </main>
  );
}

function MemoryStatusBadge({
  status,
  llmMode,
  generatedAt,
}: {
  status: MemoryStatus | null;
  llmMode: "gemini" | "fallback";
  generatedAt: string;
}) {
  return (
    <div className="memory-status">
      <span>{status?.backend === "chromadb" ? "ChromaDB" : "Fallback memory"}</span>
      <strong>{status?.recordCount ?? 0} records</strong>
      <small>
        {llmMode === "gemini" ? "Gemini live" : "Deterministic fallback"}
        {generatedAt ? ` - ${formatGeneratedAt(generatedAt)}` : ""}
      </small>
    </div>
  );
}

function InsightCard({
  insight,
  onAction,
}: {
  insight: ProactiveInsight;
  onAction: () => void;
}) {
  return (
    <article className={`insight-card ${insight.color}`}>
      <div className="insight-card-header">
        <span className="insight-dot" />
        <div>
          <p className="eyebrow">{insight.entityName}</p>
          <h3>{insight.title}</h3>
        </div>
        <strong>{Math.round(insight.confidence * 100)}%</strong>
      </div>
      <p className="insight-summary">{insight.summary}</p>
      <div className="evidence-list">
        {insight.evidence.slice(0, 2).map((item) => (
          <span key={item}>{item}</span>
        ))}
      </div>
      <button type="button" onClick={onAction}>
        <ArrowUpRight size={16} />
        Use draft
      </button>
      <small>{insight.draftAction}</small>
    </article>
  );
}

function MetricCard({
  icon,
  label,
  value,
  detail,
  tone,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  detail: string;
  tone: "green" | "orange" | "blue" | "neutral";
}) {
  return (
    <article className={`metric-card ${tone}`}>
      <div className="metric-icon">{icon}</div>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <p>{detail}</p>
      </div>
    </article>
  );
}

function SegmentedControl({
  value,
  options,
  onChange,
}: {
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <div className="segmented-control" role="tablist" aria-label="Board filter">
      {options.map((option) => (
        <button
          type="button"
          className={value === option ? "active" : ""}
          key={option}
          onClick={() => onChange(option)}
        >
          {option}
        </button>
      ))}
    </div>
  );
}

function InventoryRow({
  product,
  alert,
  onResolve,
  disabled,
}: {
  product: Product;
  alert: InventoryAlert;
  onResolve: () => void;
  disabled: boolean;
}) {
  const stockPercent = Math.min(100, Math.round((product.stock / product.threshold) * 100));

  return (
    <article className="inventory-row">
      <img src={product.image} alt="" />
      <div className="inventory-copy">
        <div>
          <strong>{product.name}</strong>
          <span>{alert.message}</span>
        </div>
        <div className="stock-meter" aria-label={`${product.stock} ${product.unit} in stock`}>
          <i style={{ width: `${stockPercent}%` }} />
        </div>
        <small>
          {product.stock}/{product.threshold} {product.unit}
        </small>
      </div>
      <button type="button" onClick={onResolve} disabled={disabled}>
        Draft
      </button>
    </article>
  );
}

function StatusPill({ status }: { status: string }) {
  return <span className={`status-pill ${status}`}>{status}</span>;
}

function PriorityTag({ priority }: { priority: "low" | "medium" | "high" }) {
  return <span className={`priority-tag ${priority}`}>{priority}</span>;
}

function formatCurrency(amount: number) {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  }).format(amount);
}

function formatGeneratedAt(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function summarizeOrderItems(order: Order, state: OperationsState) {
  return order.items
    .map((item) => {
      const product = state.products.find((candidate) => candidate.id === item.productId);
      return `${item.quantity}x ${product?.name ?? "Unknown product"}`;
    })
    .join(", ");
}

function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : "FastAPI request failed.";
}

export default App;
