import {
  AlertTriangle,
  ArrowUpRight,
  Bell,
  Bot,
  Boxes,
  CheckCircle2,
  ChevronDown,
  ClipboardList,
  Clock3,
  Copy,
  History,
  Mail,
  MessageCircle,
  MessageSquareText,
  PanelLeftClose,
  PanelLeftOpen,
  RefreshCw,
  Search,
  Send,
  ShoppingBag,
  Sparkles,
  Truck,
  UserRoundCheck,
  Users,
  Warehouse,
  X,
} from "lucide-react";
import {
  FormEvent,
  KeyboardEvent,
  ReactNode,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  completeTaskRequest,
  createRestockDraft,
  fetchMemoryRecords,
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
  Customer,
  InventoryAlert,
  MemoryRecord,
  MemoryStatus,
  OperationsState,
  Order,
  Product,
  ProactiveInsight,
} from "./types";
import compactAppIcon from "../assets/new_icon.png";
import expandedAppIcon from "../assets/cirak.png";

const starterMessages = [
  "Sipariş 128 ne zaman gelir?",
  "İncir reçeli stokta var mı?",
  "Bugün kargo riski var mı?",
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
    text: "Sipariş 128 ne zaman gelir?",
    timestamp: "09:18",
  },
  {
    id: "demo-agent-128",
    role: "agent",
    text: "Sipariş 128 MNG Kargo ile yolda, tahmini teslimat 11 Mayıs 15:00. Son tarama İstanbul aktarma merkezi saat 09:18.",
    timestamp: "09:18",
  },
];

type PageView = "dashboard" | "stock" | "customers" | "orders" | "memory";
type ChatState = "closed" | "minimized" | "open";
type MockSendChannel = "whatsapp" | "telegram" | "email";
type FloatingMockChannel = Extract<MockSendChannel, "whatsapp" | "telegram">;
type DraftTargetKind = "customer" | "supplier" | "carrier" | "internal";
type DraftTarget = {
  name: string;
  kind: DraftTargetKind;
  phone: string;
  email: string;
};
type DraftModal = {
  title: string;
  subtitle: string;
  body: string;
  target: DraftTarget;
};
type MockComposerState = {
  channel: FloatingMockChannel;
  customerId: string;
  message: string;
  notice: string;
};
type SearchResultKind =
  | "product"
  | "customer"
  | "order"
  | "shipment"
  | "message"
  | "alert"
  | "task"
  | "insight"
  | "memory";
type SearchTarget =
  | {
      type: "page";
      page: PageView;
      ordersFilter?: string;
      memorySearch?: string;
    }
  | { type: "chat" };
type SearchResult = {
  id: string;
  kind: SearchResultKind;
  title: string;
  description: string;
  meta: string;
  keywords: string[];
  target: SearchTarget;
};
type NotificationTone = "red" | "orange" | "yellow" | "blue" | "green";
type NotificationAction =
  | { type: "stock"; productId: string }
  | { type: "shipment" }
  | { type: "order" }
  | { type: "insight"; insightId: string }
  | { type: "task" };
type NotificationItem = {
  id: string;
  tone: NotificationTone;
  title: string;
  description: string;
  meta: string;
  action: NotificationAction;
};
type ExternalBotChannel = {
  id: FloatingMockChannel;
  label: string;
  icon: ReactNode;
};

const searchKindOrder: SearchResultKind[] = [
  "product",
  "customer",
  "order",
  "shipment",
  "message",
  "alert",
  "task",
  "insight",
  "memory",
];

const searchKindLabels: Record<SearchResultKind, string> = {
  product: "Ürünler",
  customer: "Müşteriler",
  order: "Siparişler",
  shipment: "Takip",
  message: "Mesajlar",
  alert: "Stok Uyarıları",
  task: "Görevler",
  insight: "İçgörüler",
  memory: "Hafıza",
};

const botChannels: ExternalBotChannel[] = [
  {
    id: "telegram",
    label: "Telegram",
    icon: <Send size={17} />,
  },
  {
    id: "whatsapp",
    label: "WhatsApp",
    icon: <MessageCircle size={17} />,
  },
];

export default function App() {
  const [state, setState] = useState<OperationsState | null>(null);
  const [chatInput, setChatInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [actions, setActions] = useState<AgentAction[]>([]);
  const [insights, setInsights] = useState<ProactiveInsight[]>([]);
  const [memoryRecords, setMemoryRecords] = useState<MemoryRecord[]>([]);
  const [memoryStatus, setMemoryStatus] = useState<MemoryStatus | null>(null);
  const [llmMode, setLlmMode] = useState<"gemini" | "fallback">("fallback");
  const [insightsGeneratedAt, setInsightsGeneratedAt] = useState("");
  const [apiError, setApiError] = useState("");
  const [isMutating, setIsMutating] = useState(false);
  const [activePage, setActivePage] = useState<PageView>("dashboard");
  const [ordersFilter, setOrdersFilter] = useState("Tümü");
  const [draftModal, setDraftModal] = useState<DraftModal | null>(null);
  const [draftNotice, setDraftNotice] = useState("");
  const [mockComposer, setMockComposer] = useState<MockComposerState | null>(
    null,
  );
  const [memorySearch, setMemorySearch] = useState("");
  const [memoryInput, setMemoryInput] = useState("");
  const [chatState, setChatState] = useState<ChatState>("closed");
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [globalSearch, setGlobalSearch] = useState("");
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const chatLogRef = useRef<HTMLDivElement>(null);
  const searchMenuRef = useRef<HTMLDivElement>(null);
  const notificationsMenuRef = useRef<HTMLDivElement>(null);
  const todayLabel = useMemo(() => formatTodayLabel(new Date()), []);

  useEffect(() => {
    void loadState();
  }, []);

  useEffect(() => {
    function closeFloatingMenus(event: MouseEvent) {
      const target = event.target;

      if (!(target instanceof Node)) {
        return;
      }

      if (searchMenuRef.current && !searchMenuRef.current.contains(target)) {
        setIsSearchOpen(false);
      }

      if (
        notificationsMenuRef.current &&
        !notificationsMenuRef.current.contains(target)
      ) {
        setIsNotificationsOpen(false);
      }
    }

    document.addEventListener("mousedown", closeFloatingMenus);

    return () => document.removeEventListener("mousedown", closeFloatingMenus);
  }, []);

  useEffect(() => {
    if (chatLogRef.current) {
      chatLogRef.current.scrollTop = chatLogRef.current.scrollHeight;
    }
  }, [messages, chatState]);

  const currentState = state ?? emptyState;
  const activeAlerts = currentState.inventoryAlerts.filter(
    (alert) => !alert.resolved,
  );
  const criticalAlerts = activeAlerts.filter(
    (alert) => alert.severity === "critical",
  );
  const dueToday = currentState.orders.filter(
    (order) => order.dueToday && order.status !== "delivered",
  );
  const openTasks = currentState.tasks.filter((task) => task.status === "open");
  const riskyShipments = useMemo(
    () =>
      currentState.shipments.filter(
        (shipment) => shipment.risk !== "clear" && !shipment.notified,
      ),
    [currentState.shipments],
  );
  const activeOrders = currentState.orders.filter(
    (order) => order.status !== "delivered",
  );
  const followUpInsights = insights.filter(
    (insight) => insight.actionType === "create_customer_reminder_draft",
  );
  const actionableInsights = insights.filter((insight) =>
    isActionableInsight(insight, currentState),
  );
  const globalSearchResults = useMemo(
    () =>
      buildGlobalSearchResults({
        state: currentState,
        messages,
        insights,
        memoryRecords,
        query: globalSearch,
      }),
    [currentState, globalSearch, insights, memoryRecords, messages],
  );
  const notificationItems = useMemo(
    () => buildNotificationItems(currentState, actionableInsights),
    [actionableInsights, currentState],
  );

  function handleGlobalSearchSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (globalSearchResults[0]) {
      selectSearchResult(globalSearchResults[0]);
    }
  }

  function handleGlobalSearchKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      setIsSearchOpen(false);
      event.currentTarget.blur();
    }
  }

  function selectSearchResult(result: SearchResult) {
    setIsSearchOpen(false);

    if (result.target.type === "chat") {
      setChatState("open");
      return;
    }

    if (result.target.ordersFilter) {
      setOrdersFilter(result.target.ordersFilter);
    }

    if (result.target.memorySearch !== undefined) {
      setMemorySearch(result.target.memorySearch);
    }

    setActivePage(result.target.page);
  }

  function handleNotificationSelect(item: NotificationItem) {
    setIsNotificationsOpen(false);

    if (item.action.type === "stock") {
      const { productId } = item.action;
      const alert = currentState.inventoryAlerts.find(
        (candidate) => !candidate.resolved && candidate.productId === productId,
      );

      if (alert) {
        void resolveInventoryAlert(alert);
      }

      return;
    }

    if (item.action.type === "shipment") {
      setOrdersFilter("Risk");
      setActivePage("orders");
      return;
    }

    if (item.action.type === "order") {
      setOrdersFilter("Bugün");
      setActivePage("orders");
      return;
    }

    if (item.action.type === "insight") {
      const { insightId } = item.action;
      const insight = actionableInsights.find(
        (candidate) => candidate.id === insightId,
      );

      if (insight) {
        handleInsightAction(insight);
      }

      return;
    }

    setActivePage("dashboard");
  }

  async function loadState() {
    try {
      setApiError("");
      const nextState = await fetchState();
      setState(nextState);
      await refreshMorningInsights();
      await refreshMemoryRecords();
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

  async function refreshMemoryRecords() {
    setMemoryRecords(await fetchMemoryRecords());
  }

  async function handleChatSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!chatInput.trim()) {
      return;
    }

    await runMutation(async () => {
      const response = await sendCustomerMessage(chatInput);
      setMessages((current) => [
        ...current,
        response.customerMessage,
        response.agentMessage,
      ]);
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
          eventDate: new Date().toISOString().slice(0, 10),
        },
      ]);
      setMemoryStatus(response.status);
      await refreshMorningInsights();
      await refreshMemoryRecords();
      prependActions([
        {
          id: crypto.randomUUID(),
          label: "Yeni hafıza notu kaydedildi",
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
      openRestockDraft(response.state, alert.productId);
    });
  }

  async function draftProduct(product: Product) {
    await runMutation(async () => {
      const response = await createRestockDraft(product.id);
      setState(response.state);
      prependActions([response.action]);
      openRestockDraft(response.state, product.id);
    });
  }

  async function handleGeneratePlan() {
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
      await refreshMemoryRecords();
      setActions([]);
      setMessages(initialMessages);
      setChatInput("");
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
    setDraftNotice("");
    setDraftModal({
      title: getDraftTitle(insight),
      subtitle: insight.entityName,
      body: insight.draftAction,
      target: getDraftTargetForInsight(insight, currentState),
    });
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

  function openRestockDraft(nextState: OperationsState, productId: string) {
    const product = nextState.products.find((item) => item.id === productId);
    const alert = nextState.inventoryAlerts.find(
      (item) => item.productId === productId,
    );

    if (!product || !alert?.restockDraft) {
      return;
    }

    setDraftNotice("");
    setDraftModal({
      title: `Sipariş Taslağı: ${product.name}`,
      subtitle: product.supplier,
      body: alert.restockDraft,
      target: getSupplierDraftTarget(product),
    });
  }

  async function copyDraft() {
    if (!draftModal) {
      return;
    }

    await navigator.clipboard.writeText(draftModal.body);
    prependActions([
      {
        id: crypto.randomUUID(),
        label: "Taslak kopyalandı",
        type: "memory_insight_generated",
        payload: { draft: draftModal.title },
      },
    ]);
  }

  function updateDraftBody(body: string) {
    setDraftNotice("");
    setDraftModal((current) => (current ? { ...current, body } : current));
  }

  function mockSendDraft(channel: MockSendChannel) {
    if (!draftModal) {
      return;
    }

    const destination = getDraftDestination(draftModal.target, channel);
    const channelLabel = getMockSendChannelLabel(channel);
    const notice = `${channelLabel} mock gönderim: ${destination}`;

    setDraftNotice(notice);
    prependActions([
      {
        id: crypto.randomUUID(),
        label: `${channelLabel} ile mock gönderildi: ${draftModal.target.name} (${destination})`,
        type: "memory_insight_generated",
        payload: {
          channel,
          recipient: draftModal.target.name,
          destination,
          draft: draftModal.title,
          message: draftModal.body,
        },
      },
    ]);
  }

  function openMockComposer(channel: FloatingMockChannel) {
    const firstCustomer = currentState.customers[0];

    setMockComposer({
      channel,
      customerId: firstCustomer?.id ?? "",
      message: getDefaultMockChannelMessage(channel),
      notice: "",
    });
  }

  function updateMockComposer(next: Partial<MockComposerState>) {
    setMockComposer((current) => (current ? { ...current, ...next } : current));
  }

  function sendMockComposerMessage() {
    if (!mockComposer || !mockComposer.message.trim()) {
      return;
    }

    const customer = currentState.customers.find(
      (candidate) => candidate.id === mockComposer.customerId,
    );

    if (!customer) {
      return;
    }

    const channelLabel = getMockSendChannelLabel(mockComposer.channel);
    const notice = `${channelLabel} mock gönderim: ${customer.name} (${customer.phone})`;

    setMockComposer({ ...mockComposer, notice });
    prependActions([
      {
        id: crypto.randomUUID(),
        label: `${channelLabel} mock mesaj gönderildi: ${customer.name}`,
        type: "memory_insight_generated",
        payload: {
          channel: mockComposer.channel,
          recipient: customer.name,
          destination: customer.phone,
          message: mockComposer.message.trim(),
        },
      },
    ]);
  }

  if (!state) {
    return (
      <main className="loading-screen">
        <div className="loading-spinner" />
        <strong>Sisteme bağlanıyor...</strong>
        <span>{apiError || "Veriler yükleniyor, lütfen bekleyin."}</span>
      </main>
    );
  }

  return (
    <div
      className={`app-shell${isSidebarCollapsed ? " sidebar-collapsed" : ""}`}>
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-main">
            <button
              className="brand-icon"
              onClick={() => setActivePage("dashboard")}
              type="button"
              aria-label="Dashboard'a git"
              title="Dashboard'a git">
              <img
                src={isSidebarCollapsed ? compactAppIcon : expandedAppIcon}
                alt=""
              />
            </button>
          </div>
          <button
            className="sidebar-toggle"
            onClick={() => setIsSidebarCollapsed((current) => !current)}
            type="button"
            aria-label={
              isSidebarCollapsed ? "Menüyü genişlet" : "Menüyü daralt"
            }
            title={isSidebarCollapsed ? "Menüyü genişlet" : "Menüyü daralt"}>
            {isSidebarCollapsed ? (
              <PanelLeftOpen size={16} />
            ) : (
              <PanelLeftClose size={16} />
            )}
          </button>
        </div>

        <nav className="nav">
          {(
            [
              "dashboard",
              "stock",
              "customers",
              "orders",
              "memory",
            ] as PageView[]
          ).map((page) => {
            const label = navLabel(page);

            return (
              <button
                key={page}
                className={`nav-btn${activePage === page ? " active" : ""}`}
                onClick={() => setActivePage(page)}
                type="button"
                aria-label={label}
                title={label}>
                <span className="nav-icon">{navIcon(page)}</span>
                <span className="nav-label">{label}</span>
              </button>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div
            className="auto-run-card"
            title={`Günlük Plan: ${dueToday.length} sipariş bugün teslim`}>
            <div className="auto-run-header">
              <Clock3 size={15} />
              <span className="sidebar-label">Günlük Plan</span>
            </div>
            <p className="auto-run-count sidebar-label">
              {dueToday.length} sipariş bugün teslim
            </p>
            <button
              className="btn-outline-green"
              onClick={handleGeneratePlan}
              disabled={isMutating}
              type="button"
              aria-label="Görev Planı Oluştur"
              title="Görev Planı Oluştur">
              <ClipboardList size={14} />
              <span className="sidebar-label">Görev Planı Oluştur</span>
            </button>
          </div>

          <div
            className="memory-badge"
            title={`Hafıza: ${
              memoryStatus?.backend === "chromadb" ? "ChromaDB" : "Fallback"
            }, ${memoryStatus?.recordCount ?? 0} kayıt`}>
            <div
              className={`mem-dot ${
                memoryStatus?.backend === "chromadb" ? "green" : "yellow"
              }`}
            />
            <div className="sidebar-label">
              <span>
                {memoryStatus?.backend === "chromadb" ? "ChromaDB" : "Fallback"}
              </span>
              <span>
                {memoryStatus?.recordCount ?? 0} kayıt ·{" "}
                {llmMode === "gemini" ? "Gemini aktif" : "Fallback mod"}
              </span>
            </div>
          </div>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <div className="topbar-left">
            <h1 className="page-title">{pageTitle(activePage)}</h1>
            <p className="page-date">{todayLabel}</p>
          </div>
          <div className="topbar-right">
            <div
              className="topbar-search"
              ref={searchMenuRef}>
              <form
                className="search-pill"
                onSubmit={handleGlobalSearchSubmit}>
                <Search size={15} />
                <input
                  value={globalSearch}
                  onChange={(event) => {
                    setGlobalSearch(event.target.value);
                    setIsSearchOpen(true);
                    setIsNotificationsOpen(false);
                  }}
                  onFocus={() => {
                    setIsSearchOpen(true);
                    setIsNotificationsOpen(false);
                  }}
                  onKeyDown={handleGlobalSearchKeyDown}
                  placeholder="Ürün, müşteri, sipariş, takip ara..."
                  aria-label="Genel arama"
                />
                {globalSearch && (
                  <button
                    className="search-clear"
                    onClick={() => {
                      setGlobalSearch("");
                      setIsSearchOpen(false);
                    }}
                    type="button"
                    aria-label="Aramayı temizle">
                    <X size={14} />
                  </button>
                )}
              </form>
              {isSearchOpen && globalSearch.trim() && (
                <SearchResultsMenu
                  results={globalSearchResults}
                  query={globalSearch}
                  onSelect={selectSearchResult}
                />
              )}
            </div>
            <div
              className="notification-menu"
              ref={notificationsMenuRef}>
              <button
                className="icon-btn notification-trigger"
                onClick={() => {
                  setIsNotificationsOpen((current) => !current);
                  setIsSearchOpen(false);
                }}
                aria-label={`${notificationItems.length} bildirim`}
                type="button">
                <Bell size={17} />
                {notificationItems.length > 0 && (
                  <span className="notification-count">
                    {notificationItems.length > 99 ? "99+" : notificationItems.length}
                  </span>
                )}
              </button>
              {isNotificationsOpen && (
                <NotificationPanel
                  items={notificationItems}
                  onSelect={handleNotificationSelect}
                />
              )}
            </div>
            <button
              className="btn-outline"
              onClick={resetDemo}
              disabled={isMutating}
              type="button">
              <RefreshCw size={14} />
              Sıfırla
            </button>
          </div>
        </header>

        {apiError && <div className="error-bar">{apiError}</div>}

        {activePage === "dashboard" && (
          <div className="dashboard">
            <div className="metric-row">
              <MetricCard
                icon={<ShoppingBag size={20} />}
                label="Aktif Sipariş"
                value={activeOrders.length}
                sub={`${dueToday.length} bugün aksiyon`}
                color="green"
                onClick={() => {
                  setOrdersFilter("Tümü");
                  setActivePage("orders");
                }}
              />
              <MetricCard
                icon={<AlertTriangle size={20} />}
                label="Kritik Stok"
                value={criticalAlerts.length}
                sub={`${activeAlerts.length} ürün izleniyor`}
                color="red"
                onClick={() => setActivePage("stock")}
              />
              <MetricCard
                icon={<Users size={20} />}
                label="Takip Müşteri"
                value={followUpInsights.length}
                sub="ritim değişti"
                color="blue"
                onClick={() => setActivePage("customers")}
              />
              <MetricCard
                icon={<Truck size={20} />}
                label="Kargo Riski"
                value={riskyShipments.length}
                sub="bildirim bekliyor"
                color="orange"
                onClick={() => {
                  setOrdersFilter("Risk");
                  setActivePage("orders");
                }}
              />
            </div>

            <section className="section">
              <div className="section-header">
                <div>
                  <p className="eyebrow">Sabah Özeti</p>
                  <h2>Proaktif Uyarılar</h2>
                </div>
                <span className="badge-pill">
                  {insightsGeneratedAt
                    ? formatTime(insightsGeneratedAt)
                    : "Yükleniyor"}
                </span>
              </div>
              <div className="insight-grid">
                {actionableInsights.length > 0 ? (
                  actionableInsights.map((insight) => (
                    <InsightCard
                      key={insight.id}
                      insight={insight}
                      onAction={() => handleInsightAction(insight)}
                    />
                  ))
                ) : (
                  <div className="empty-full">
                    <Sparkles size={22} />
                    <span>Aksiyon gerektiren uyarı yok.</span>
                  </div>
                )}
              </div>
            </section>

            <div className="dashboard-grid">
              <div className="dashboard-left">
                <section className="section">
                  <div className="section-header">
                    <div>
                      <p className="eyebrow">Siparişler</p>
                      <h2>Bugünkü Kontrol Panosu</h2>
                    </div>
                  </div>
                  <div className="order-list">
                    {dueToday.length > 0 ? (
                      dueToday.map((order) => {
                        const customer = state.customers.find(
                          (item) => item.id === order.customerId,
                        );
                        const shipment = state.shipments.find(
                          (item) => item.orderId === order.id,
                        );

                        return (
                          <div
                            className="order-row"
                            key={order.id}>
                            <div className="order-row-left">
                              <span className="order-num">#{order.id}</span>
                              <div>
                                <strong>{customer?.name}</strong>
                                <span>{summarizeItems(order, state)}</span>
                              </div>
                            </div>
                            <div className="order-row-right">
                              <StatusPill
                                status={shipment?.risk ?? order.status}
                              />
                              <span className="order-amount">
                                {formatCurrency(order.total)}
                              </span>
                            </div>
                          </div>
                        );
                      })
                    ) : (
                      <Empty text="Bugün aksiyon gerektiren sipariş yok." />
                    )}
                  </div>
                </section>

                <section className="section">
                  <div className="section-header">
                    <div>
                      <p className="eyebrow">Görevler</p>
                      <h2>Ekip Sırası</h2>
                    </div>
                    <ClipboardList
                      size={18}
                      className="section-icon"
                    />
                  </div>
                  <div className="task-list">
                    {openTasks.slice(0, 5).map((task) => (
                      <div
                        className="task-row"
                        key={task.id}>
                        <button
                          className="check-btn"
                          onClick={() => completeTask(task.id)}
                          disabled={isMutating}
                          aria-label="Tamamla"
                          type="button">
                          <CheckCircle2 size={16} />
                        </button>
                        <div className="task-info">
                          <strong>{task.title}</strong>
                          <span>
                            {task.owner}
                            {task.orderId ? ` · Sipariş ${task.orderId}` : ""}
                          </span>
                        </div>
                        <PriorityTag priority={task.priority} />
                      </div>
                    ))}
                    {!openTasks.length && (
                      <Empty text="Tüm görevler tamamlandı." />
                    )}
                  </div>
                </section>
              </div>

              <div className="dashboard-right">
                <section className="section">
                  <div className="section-header">
                    <div>
                      <p className="eyebrow">Stok</p>
                      <h2>Yeniden Sipariş Riskleri</h2>
                    </div>
                    <Boxes
                      size={18}
                      className="section-icon"
                    />
                  </div>
                  <div className="alert-list">
                    {activeAlerts.slice(0, 4).map((alert) => {
                      const product = state.products.find(
                        (item) => item.id === alert.productId,
                      );

                      if (!product) {
                        return null;
                      }

                      const percent = Math.min(
                        100,
                        Math.round((product.stock / product.threshold) * 100),
                      );

                      return (
                        <div
                          className="alert-row"
                          key={alert.productId}>
                          <img
                            src={product.image}
                            alt=""
                            className="alert-thumb"
                          />
                          <div className="alert-info">
                            <strong>{product.name}</strong>
                            <span>{alert.message}</span>
                            <div className="stock-bar">
                              <div
                                className="stock-bar-fill"
                                style={{ width: `${percent}%` }}
                              />
                            </div>
                            <small>
                              {product.stock}/{product.threshold} {product.unit}
                            </small>
                          </div>
                          <button
                            className="btn-draft"
                            onClick={() => resolveInventoryAlert(alert)}
                            disabled={isMutating}
                            type="button">
                            Taslak
                          </button>
                        </div>
                      );
                    })}
                    {!activeAlerts.length && (
                      <Empty text="Tüm stok uyarıları çözüldü." />
                    )}
                  </div>
                </section>

                <section className="section">
                  <div className="section-header">
                    <div>
                      <p className="eyebrow">Kargo</p>
                      <h2>Gecikmeler</h2>
                    </div>
                    <Truck
                      size={18}
                      className="section-icon"
                    />
                  </div>
                  <div className="shipment-list">
                    {riskyShipments.map((shipment) => (
                      <div
                        className="shipment-row"
                        key={shipment.id}>
                        <div className="shipment-info">
                          <div className="shipment-top">
                            <span className="order-num">
                              #{shipment.orderId}
                            </span>
                            <StatusPill status={shipment.risk} />
                          </div>
                          <strong>{shipment.carrier}</strong>
                          <span>{shipment.lastScan}</span>
                        </div>
                        <button
                          className="btn-notify"
                          onClick={() => markShipmentNotified(shipment.orderId)}
                          disabled={isMutating}
                          type="button">
                          <UserRoundCheck size={14} /> Bildir
                        </button>
                      </div>
                    ))}
                    {!riskyShipments.length && (
                      <Empty text="Bekleyen kargo bildirimi yok." />
                    )}
                  </div>
                </section>
              </div>
            </div>
          </div>
        )}

        {activePage === "stock" && (
          <StockPage
            products={state.products}
            alerts={state.inventoryAlerts}
            onDraft={draftProduct}
            disabled={isMutating}
          />
        )}

        {activePage === "customers" && (
          <CustomersPage
            state={state}
            insights={insights}
          />
        )}

        {activePage === "orders" && (
          <OrdersPage
            state={state}
            filter={ordersFilter}
            onFilterChange={setOrdersFilter}
          />
        )}

        {activePage === "memory" && (
          <MemoryPage
            insights={insights}
            records={memoryRecords}
            memoryStatus={memoryStatus}
            llmMode={llmMode}
            generatedAt={insightsGeneratedAt}
            search={memorySearch}
            onSearchChange={setMemorySearch}
            memoryInput={memoryInput}
            onMemoryInputChange={setMemoryInput}
            onMemoryIngest={handleMemoryIngest}
            isMutating={isMutating}
            actions={actions}
          />
        )}
      </div>

      {chatState === "closed" && !mockComposer && (
        <div
          className="assistant-launcher"
          aria-label="Asistan kanalları">
          <div className="channel-fabs">
            {botChannels.map((channel) => (
              <BotChannelButton
                channel={channel}
                key={channel.id}
                onOpen={openMockComposer}
              />
            ))}
          </div>
          <button
            className="chat-fab"
            onClick={() => setChatState("open")}
            aria-label="Sohbeti aç"
            type="button">
            <Bot size={22} />
            <span>AI Asistan</span>
            {messages.length > 2 && (
              <span className="chat-fab-badge">{messages.length - 2}</span>
            )}
          </button>
        </div>
      )}

      {chatState === "closed" && mockComposer && (
        <MockChannelComposer
          composer={mockComposer}
          customers={state.customers}
          onChange={updateMockComposer}
          onClose={() => setMockComposer(null)}
          onSend={sendMockComposerMessage}
        />
      )}

      {chatState !== "closed" && (
        <div
          className={`chat-float${chatState === "minimized" ? " minimized" : ""}`}>
          <div className="chat-float-header">
            <div className="chat-float-title">
              <div className="chat-avatar">
                <Bot size={16} />
              </div>
              <div>
                <strong>AI Asistan</strong>
                <span className="chat-status">● Çevrimiçi</span>
              </div>
            </div>
            <div className="chat-float-controls">
              <button
                onClick={() =>
                  setChatState(chatState === "minimized" ? "open" : "minimized")
                }
                aria-label="Küçült"
                type="button">
                <ChevronDown
                  size={16}
                  className={chatState === "minimized" ? "rotate-180" : ""}
                />
              </button>
              <button
                onClick={() => setChatState("closed")}
                aria-label="Kapat"
                type="button">
                <X size={16} />
              </button>
            </div>
          </div>

          {chatState === "open" && (
            <>
              <div className="chat-starters">
                {starterMessages.map((message) => (
                  <button
                    key={message}
                    className="starter-chip"
                    onClick={() => setChatInput(message)}
                    type="button">
                    {message}
                  </button>
                ))}
              </div>
              <div
                className="chat-log"
                ref={chatLogRef}
                aria-live="polite">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`bubble ${message.role}`}>
                    <span className="bubble-role">
                      {message.role === "agent" ? "AI" : "Siz"}
                    </span>
                    <p>{message.text}</p>
                    <time>{message.timestamp}</time>
                  </div>
                ))}
                {isMutating && (
                  <div className="bubble agent typing">
                    <span className="bubble-role">AI</span>
                    <p>
                      <span className="dot-pulse" />
                    </p>
                  </div>
                )}
              </div>
              <form
                className="chat-input-row"
                onSubmit={handleChatSubmit}>
                <input
                  value={chatInput}
                  onChange={(event) => setChatInput(event.target.value)}
                  placeholder="Bir şey sorun..."
                  aria-label="Mesaj"
                  disabled={isMutating}
                />
                <button
                  type="submit"
                  disabled={isMutating || !chatInput.trim()}
                  aria-label="Gönder">
                  <Send size={15} />
                </button>
              </form>
            </>
          )}
        </div>
      )}

      {draftModal && (
        <div
          className="drawer-overlay"
          onClick={() => setDraftModal(null)}>
          <aside
            className="drawer"
            role="dialog"
            aria-modal="true"
            onClick={(event) => event.stopPropagation()}>
            <div className="drawer-header">
              <div>
                <p className="eyebrow">{draftModal.subtitle}</p>
                <h2>{draftModal.title}</h2>
              </div>
              <button
                onClick={() => setDraftModal(null)}
                aria-label="Kapat"
                type="button">
                <X size={18} />
              </button>
            </div>
            <div className="drawer-target">
              <div>
                <span>{getDraftTargetKindLabel(draftModal.target.kind)}</span>
                <strong>{draftModal.target.name}</strong>
              </div>
              <div>
                <span>Telefon</span>
                <strong>{draftModal.target.phone}</strong>
              </div>
              <div>
                <span>E-posta</span>
                <strong>{draftModal.target.email}</strong>
              </div>
            </div>
            <textarea
              className="drawer-body drawer-body-input"
              value={draftModal.body}
              onChange={(event) => updateDraftBody(event.target.value)}
              aria-label="Gönderilecek mesaj içeriği"
            />
            <div
              className="mock-send-grid"
              aria-label="Mock gönderim kanalları">
              <button
                className="drawer-send whatsapp"
                onClick={() => mockSendDraft("whatsapp")}
                type="button">
                <MessageCircle size={15} />
                <span>
                  WhatsApp
                  <small>{draftModal.target.phone}</small>
                </span>
              </button>
              <button
                className="drawer-send telegram"
                onClick={() => mockSendDraft("telegram")}
                type="button">
                <Send size={15} />
                <span>
                  Telegram
                  <small>{draftModal.target.phone}</small>
                </span>
              </button>
              <button
                className="drawer-send email"
                onClick={() => mockSendDraft("email")}
                type="button">
                <Mail size={15} />
                <span>
                  E-posta
                  <small>{draftModal.target.email}</small>
                </span>
              </button>
            </div>
            {draftNotice && (
              <div className="mock-send-notice">{draftNotice}</div>
            )}
            <button
              className="btn-copy"
              onClick={copyDraft}
              type="button">
              <Copy size={15} /> Kopyala
            </button>
          </aside>
        </div>
      )}
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
  const summary = compactText(firstSentence(insight.summary), 110);
  const buttonLabel =
    insight.actionType === "create_supplier_order_draft"
      ? "Sipariş Maili"
      : insight.actionType === "create_customer_reminder_draft"
        ? "WhatsApp Mesajı"
        : insight.actionType === "suggest_shipping_alternative"
          ? "Alternatif Göster"
          : "Detay";

  return (
    <article className={`insight-card ${insight.color}`}>
      <div className="insight-top">
        <span className="insight-dot" />
        <div className="insight-meta">
          <p className="eyebrow">{insight.entityName}</p>
          <h3>{insight.title}</h3>
        </div>
      </div>
      <p className="insight-summary">{summary}</p>
      <button
        className="insight-btn"
        onClick={onAction}
        type="button">
        <ArrowUpRight size={14} />
        {buttonLabel}
      </button>
    </article>
  );
}

function BotChannelButton({
  channel,
  onOpen,
}: {
  channel: ExternalBotChannel;
  onOpen: (channel: FloatingMockChannel) => void;
}) {
  return (
    <button
      className={`channel-fab ${channel.id}`}
      onClick={() => onOpen(channel.id)}
      type="button"
      aria-label={`${channel.label} mock mesaj panelini aç`}>
      {channel.icon}
      <span>{channel.label}</span>
    </button>
  );
}

function MockChannelComposer({
  composer,
  customers,
  onChange,
  onClose,
  onSend,
}: {
  composer: MockComposerState;
  customers: Customer[];
  onChange: (next: Partial<MockComposerState>) => void;
  onClose: () => void;
  onSend: () => void;
}) {
  const selectedCustomer = customers.find(
    (customer) => customer.id === composer.customerId,
  );
  const title = getMockSendChannelLabel(composer.channel);
  const icon =
    composer.channel === "whatsapp" ? (
      <MessageCircle size={16} />
    ) : (
      <Send size={16} />
    );

  return (
    <aside
      className={`mock-channel-panel ${composer.channel}`}
      aria-label={`${title} mock mesaj paneli`}>
      <div className="mock-channel-header">
        <div>
          <span className="mock-channel-icon">{icon}</span>
          <div>
            <strong>{title}</strong>
            <span>Mock mesaj</span>
          </div>
        </div>
        <button
          onClick={onClose}
          type="button"
          aria-label="Paneli kapat">
          <X size={16} />
        </button>
      </div>

      <label className="mock-field">
        <span>Alıcı</span>
        <select
          value={composer.customerId}
          onChange={(event) =>
            onChange({ customerId: event.target.value, notice: "" })
          }
          disabled={!customers.length}>
          {customers.map((customer) => (
            <option
              key={customer.id}
              value={customer.id}>
              {customer.name}
            </option>
          ))}
        </select>
      </label>

      <div className="mock-recipient-line">
        <span>Telefon</span>
        <strong>{selectedCustomer?.phone ?? "Mock telefon yok"}</strong>
      </div>

      <label className="mock-field">
        <span>Mesaj</span>
        <textarea
          value={composer.message}
          onChange={(event) =>
            onChange({ message: event.target.value, notice: "" })
          }
          rows={5}
          aria-label={`${title} mock mesaj içeriği`}
        />
      </label>

      {composer.notice && (
        <div className="mock-send-notice">{composer.notice}</div>
      )}

      <button
        className={`mock-channel-send ${composer.channel}`}
        onClick={onSend}
        disabled={!selectedCustomer || !composer.message.trim()}
        type="button">
        {icon}
        Mock Gönder
      </button>
    </aside>
  );
}

function StockPage({
  products,
  alerts,
  onDraft,
  disabled,
}: {
  products: Product[];
  alerts: InventoryAlert[];
  onDraft: (product: Product) => void;
  disabled: boolean;
}) {
  const alertsByProduct = new Map(
    alerts.map((alert) => [alert.productId, alert]),
  );

  return (
    <div className="page-content">
      <div className="page-panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">Stok Sayfası</p>
            <h2>Stok Tükenme Tahminleri</h2>
          </div>
        </div>
        <div className="table-wrap">
          <div className="table-head stock-cols">
            <span>Ürün</span>
            <span>Mevcut Stok</span>
            <span>Günlük Satış</span>
            <span>Kalan Gün</span>
            <span>Durum</span>
            <span>Aksiyon</span>
          </div>
          {products.map((product) => {
            const averageSales = average(product.weeklySales);
            const daysLeft = averageSales ? product.stock / averageSales : 99;
            const alert = alertsByProduct.get(product.id);
            const tone =
              alert?.severity === "critical"
                ? "red"
                : alert
                  ? "yellow"
                  : daysLeft <= 7
                    ? "yellow"
                    : "green";

            return (
              <div
                className="table-row stock-cols"
                key={product.id}>
                <strong>{product.name}</strong>
                <span>
                  {product.stock} {product.unit}
                </span>
                <span>
                  {Math.round(averageSales)} {product.unit}/gün
                </span>
                <span className={`days-left ${tone}`}>
                  {daysLeft.toFixed(1)} gün
                </span>
                <StatusPill status={tone} />
                {daysLeft <= 7 ? (
                  <button
                    className="btn-draft-sm"
                    onClick={() => onDraft(product)}
                    disabled={disabled}
                    type="button">
                    Sipariş Taslağı
                  </button>
                ) : (
                  <span className="table-empty-cell">-</span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function CustomersPage({
  state,
  insights,
}: {
  state: OperationsState;
  insights: ProactiveInsight[];
}) {
  const followUpInsights = insights.filter(
    (insight) => insight.actionType === "create_customer_reminder_draft",
  );
  const rows = state.customers.map((customer) => {
    const customerOrders = state.orders
      .filter((order) => order.customerId === customer.id)
      .sort(
        (left, right) =>
          new Date(right.createdAt).getTime() -
          new Date(left.createdAt).getTime(),
      );
    const latestOrder = customerOrders[0];
    const riskyShipment = state.shipments.find(
      (shipment) =>
        customerOrders.some((order) => order.id === shipment.orderId) &&
        shipment.risk !== "clear" &&
        !shipment.notified,
    );
    const followUpInsight = followUpInsights.find((insight) =>
      namesMatch(insight.entityName, customer.name),
    );
    const status = followUpInsight
      ? "risky"
      : riskyShipment
        ? "watch"
        : "healthy";
    const note =
      followUpInsight?.summary ??
      (riskyShipment
        ? `Kargo riski: sipariş ${riskyShipment.orderId}`
        : latestOrder
          ? `Son sipariş ${latestOrder.id} - ${latestOrder.status}`
          : "Henüz sipariş yok");

    return {
      id: customer.id,
      name: customer.name,
      channel: customer.channel,
      lastOrder: latestOrder ? formatDate(latestOrder.createdAt) : "-",
      count: customerOrders.length,
      status,
      note,
    };
  });

  return (
    <div className="page-content">
      <div className="page-panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">Müşteriler</p>
            <h2>Müşteri Ritmi ve Takip Riski</h2>
          </div>
        </div>
        <div className="table-wrap">
          <div className="table-head customer-cols">
            <span>Müşteri</span>
            <span>Son Sipariş</span>
            <span>Kanal</span>
            <span>Sipariş</span>
            <span>Durum</span>
            <span>Not</span>
          </div>
          {rows.map((row) => (
            <div
              className="table-row customer-cols"
              key={row.id}>
              <strong>{row.name}</strong>
              <span>{row.lastOrder}</span>
              <span>{row.channel}</span>
              <span>{row.count} sipariş</span>
              <StatusPill status={row.status} />
              <span className="note-cell">{row.note}</span>
            </div>
          ))}
          {!rows.length && <Empty text="Kayıtlı müşteri yok." />}
        </div>
      </div>
    </div>
  );
}

function OrdersPage({
  state,
  filter,
  onFilterChange,
}: {
  state: OperationsState;
  filter: string;
  onFilterChange: (value: string) => void;
}) {
  const visibleOrders = state.orders.filter((order) => {
    if (filter === "Bugün") {
      return order.dueToday;
    }

    if (filter === "Risk") {
      const shipment = state.shipments.find(
        (item) => item.orderId === order.id,
      );
      return (
        order.status === "delayed" ||
        shipment?.risk === "delayed" ||
        shipment?.risk === "watch"
      );
    }

    return true;
  });

  return (
    <div className="page-content">
      <div className="page-panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">Siparişler</p>
            <h2>Aktif Siparişler</h2>
          </div>
          <SegCtrl
            value={filter}
            options={["Tümü", "Bugün", "Risk"]}
            onChange={onFilterChange}
          />
        </div>
        <div className="table-wrap">
          <div className="table-head orders-cols">
            <span>Sipariş</span>
            <span>Müşteri</span>
            <span>Durum</span>
            <span>Kargo</span>
            <span>ETA</span>
            <span>Not</span>
          </div>
          {visibleOrders.map((order) => {
            const customer = state.customers.find(
              (item) => item.id === order.customerId,
            );
            const shipment = state.shipments.find(
              (item) => item.orderId === order.id,
            );

            return (
              <div
                className="table-row orders-cols"
                key={order.id}>
                <strong>#{order.id}</strong>
                <span>{customer?.name}</span>
                <StatusPill status={shipment?.risk ?? order.status} />
                <span>{shipment?.carrier ?? "Depo"}</span>
                <span>{shipment?.eta ?? "-"}</span>
                <span className="note-cell">
                  {shipment?.lastScan ?? "Teslim bekleniyor"}
                </span>
              </div>
            );
          })}
          {!visibleOrders.length && (
            <Empty text="Bu filtre için sipariş yok." />
          )}
        </div>
      </div>
    </div>
  );
}

function MemoryPage({
  insights,
  records,
  memoryStatus,
  llmMode,
  generatedAt,
  search,
  onSearchChange,
  memoryInput,
  onMemoryInputChange,
  onMemoryIngest,
  isMutating,
  actions,
}: {
  insights: ProactiveInsight[];
  records: MemoryRecord[];
  memoryStatus: MemoryStatus | null;
  llmMode: "gemini" | "fallback";
  generatedAt: string;
  search: string;
  onSearchChange: (value: string) => void;
  memoryInput: string;
  onMemoryInputChange: (value: string) => void;
  onMemoryIngest: (event: FormEvent<HTMLFormElement>) => void;
  isMutating: boolean;
  actions: AgentAction[];
}) {
  const filteredRecords = records.filter((record) => {
    if (!search.trim()) {
      return true;
    }

    return [
      record.text,
      record.category,
      record.entityName ?? "",
      record.eventDate ?? "",
    ]
      .join(" ")
      .toLocaleLowerCase("tr")
      .includes(search.toLocaleLowerCase("tr"));
  });

  return (
    <div className="page-content memory-layout">
      <div className="memory-left">
        <div className="page-panel">
          <div className="section-header">
            <div>
              <p className="eyebrow">Karar Geçmişi</p>
              <h2>Sistem Neden Bu Kararı Verdi?</h2>
            </div>
            <div className="mem-status-badge">
              <span
                className={`mem-dot ${
                  memoryStatus?.backend === "chromadb" ? "green" : "yellow"
                }`}
              />
              <span>{memoryStatus?.recordCount ?? 0} kayıt</span>
              <span>{llmMode === "gemini" ? "Gemini" : "Fallback"}</span>
            </div>
          </div>
          <div className="evidence-list">
            {insights.map((insight) => (
              <div
                className="evidence-card"
                key={insight.id}>
                <StatusPill status={insight.color} />
                <div>
                  <h3>{insight.title}</h3>
                  <p>{insight.summary}</p>
                  {insight.evidence.map((item) => (
                    <span
                      key={item}
                      className="ev-item">
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            ))}
            {!insights.length && <Empty text="Henüz insight yok." />}
          </div>
        </div>

        <div className="page-panel">
          <div className="section-header">
            <div>
              <p className="eyebrow">Hafıza Deposu</p>
              <h2>Tüm Kayıtlar</h2>
            </div>
          </div>
          <input
            className="search-input"
            placeholder="Kayıtlarda ara..."
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            aria-label="Hafızada ara"
          />
          <div className="record-list">
            {filteredRecords.map((record) => (
              <div
                className="record-card"
                key={record.id}>
                <div className="record-header">
                  <div className="record-tags">
                    <span className="category-tag">{record.category}</span>
                    {record.entityName && <strong>{record.entityName}</strong>}
                  </div>
                  <time>{record.eventDate ?? "-"}</time>
                </div>
                <p>{record.text}</p>
              </div>
            ))}
            {!filteredRecords.length && <Empty text="Eşleşen kayıt yok." />}
          </div>
        </div>
      </div>

      <div className="memory-right">
        <div className="page-panel">
          <div className="section-header">
            <div>
              <p className="eyebrow">Hafıza Girişi</p>
              <h2>Asistanı Eğit</h2>
            </div>
            <Sparkles size={18} />
          </div>
          <form
            className="memory-form"
            onSubmit={onMemoryIngest}>
            <textarea
              value={memoryInput}
              onChange={(event) => onMemoryInputChange(event.target.value)}
              placeholder="İşletme notu, müşteri ritmi, tedarikçi bilgisi..."
              rows={4}
              aria-label="Hafıza notu"
            />
            <button
              type="submit"
              className="btn-green"
              disabled={isMutating || !memoryInput.trim()}>
              <ArrowUpRight size={15} /> Hafızaya Kaydet
            </button>
          </form>
        </div>

        <div className="page-panel">
          <div className="section-header">
            <div>
              <p className="eyebrow">Agent İzi</p>
              <h2>Son Aksiyonlar</h2>
            </div>
            <MessageSquareText size={18} />
          </div>
          <div className="action-feed">
            {actions.length > 0 ? (
              actions.map((action) => (
                <div
                  className="action-item"
                  key={action.id}>
                  <ArrowUpRight size={14} />
                  <span>{action.label}</span>
                </div>
              ))
            ) : (
              <Empty
                text="Henüz aksiyon yok."
                compact
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function SearchResultsMenu({
  results,
  query,
  onSelect,
}: {
  results: SearchResult[];
  query: string;
  onSelect: (result: SearchResult) => void;
}) {
  const groups = searchKindOrder
    .map((kind) => ({
      kind,
      results: results.filter((result) => result.kind === kind),
    }))
    .filter((group) => group.results.length > 0);

  return (
    <div
      className="search-menu"
      role="listbox"
      aria-label="Arama sonuçları">
      {groups.length > 0 ? (
        groups.map((group) => (
          <div
            className="search-group"
            key={group.kind}>
            <div className="search-group-label">{searchKindLabels[group.kind]}</div>
            {group.results.map((result) => (
              <button
                className="search-result-item"
                key={result.id}
                onClick={() => onSelect(result)}
                type="button"
                role="option">
                <span className={`search-result-icon ${result.kind}`}>
                  {searchResultIcon(result.kind)}
                </span>
                <span className="search-result-copy">
                  <strong>{result.title}</strong>
                  <span>{result.description}</span>
                  <small>{result.meta}</small>
                </span>
              </button>
            ))}
          </div>
        ))
      ) : (
        <div className="search-empty">
          <Search size={18} />
          <span>"{query.trim()}" için sonuç yok.</span>
        </div>
      )}
    </div>
  );
}

function NotificationPanel({
  items,
  onSelect,
}: {
  items: NotificationItem[];
  onSelect: (item: NotificationItem) => void;
}) {
  return (
    <div
      className="notification-panel"
      aria-label="Bildirimler">
      <div className="notification-panel-header">
        <div>
          <p className="eyebrow">Bildirimler</p>
          <strong>Aksiyon Bekleyenler</strong>
        </div>
        <span>{items.length}</span>
      </div>
      {items.length > 0 ? (
        <div className="notification-list">
          {items.map((item) => (
            <button
              className="notification-item"
              key={item.id}
              onClick={() => onSelect(item)}
              type="button">
              <span className={`notification-item-icon ${item.tone}`}>
                {notificationItemIcon(item)}
              </span>
              <span className="notification-copy">
                <strong>{item.title}</strong>
                <span>{item.description}</span>
                <small>{item.meta}</small>
              </span>
            </button>
          ))}
        </div>
      ) : (
        <div className="notification-empty">
          <CheckCircle2 size={20} />
          <span>Aksiyon gerektiren bildirim yok.</span>
        </div>
      )}
    </div>
  );
}

function MetricCard({
  icon,
  label,
  value,
  sub,
  color,
  onClick,
}: {
  icon: ReactNode;
  label: string;
  value: number;
  sub: string;
  color: "green" | "red" | "blue" | "orange";
  onClick: () => void;
}) {
  return (
    <button
      className={`metric-card ${color}`}
      onClick={onClick}
      type="button"
      aria-label={`${label} sayfasına git`}>
      <div className="metric-icon">{icon}</div>
      <div className="metric-body">
        <span className="metric-label">{label}</span>
        <strong className="metric-value">{value}</strong>
        <span className="metric-sub">{sub}</span>
      </div>
    </button>
  );
}

function SegCtrl({
  value,
  options,
  onChange,
}: {
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <div
      className="seg-ctrl"
      role="tablist">
      {options.map((option) => (
        <button
          key={option}
          className={value === option ? "active" : ""}
          onClick={() => onChange(option)}
          role="tab"
          type="button">
          {option}
        </button>
      ))}
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  return (
    <span
      className={`pill ${status}`}
      role="status">
      {status}
    </span>
  );
}

function PriorityTag({ priority }: { priority: string }) {
  return <span className={`priority ${priority}`}>{priority}</span>;
}

function Empty({ text, compact }: { text: string; compact?: boolean }) {
  return (
    <div className={`empty ${compact ? "compact" : ""}`}>
      <CheckCircle2 size={20} />
      <span>{text}</span>
    </div>
  );
}

function navIcon(page: PageView): ReactNode {
  const icons: Record<PageView, ReactNode> = {
    dashboard: <Boxes size={16} />,
    stock: <Warehouse size={16} />,
    customers: <Users size={16} />,
    orders: <ShoppingBag size={16} />,
    memory: <History size={16} />,
  };
  return icons[page];
}

function navLabel(page: PageView): string {
  const labels: Record<PageView, string> = {
    dashboard: "Dashboard",
    stock: "Stok",
    customers: "Müşteriler",
    orders: "Siparişler",
    memory: "Hafıza",
  };
  return labels[page];
}

function pageTitle(page: PageView): string {
  const titles: Record<PageView, string> = {
    dashboard: "Bugünün Özeti",
    stock: "Stok Yönetimi",
    customers: "Müşteriler",
    orders: "Siparişler",
    memory: "Hafıza & Geçmiş",
  };
  return titles[page];
}

function getDraftTitle(insight: ProactiveInsight): string {
  const titles: Record<string, string> = {
    create_supplier_order_draft: "Tedarikçi Sipariş Maili",
    create_customer_reminder_draft: "WhatsApp Hatırlatması",
    suggest_shipping_alternative: "Kargo Alternatifi",
  };
  return titles[insight.actionType] ?? "Taslak";
}

function getDraftTargetForInsight(
  insight: ProactiveInsight,
  state: OperationsState,
): DraftTarget {
  if (insight.actionType === "create_customer_reminder_draft") {
    const customer = state.customers.find((candidate) =>
      namesMatch(insight.entityName, candidate.name),
    );

    return buildDraftTarget(
      customer?.name ?? insight.entityName,
      "customer",
      customer?.phone,
    );
  }

  if (insight.actionType === "create_supplier_order_draft") {
    const product = state.products.find(
      (candidate) =>
        namesMatch(insight.entityName, candidate.name) ||
        namesMatch(insight.title, candidate.name),
    );

    return product
      ? getSupplierDraftTarget(product)
      : buildDraftTarget(insight.entityName, "supplier");
  }

  if (insight.actionType === "suggest_shipping_alternative") {
    return buildDraftTarget(insight.entityName, "carrier");
  }

  return buildDraftTarget(insight.entityName, "internal");
}

function getSupplierDraftTarget(product: Product): DraftTarget {
  return buildDraftTarget(product.supplier, "supplier");
}

function buildDraftTarget(
  name: string,
  kind: DraftTargetKind,
  phone?: string,
): DraftTarget {
  const targetName = name.trim() || "Mock Alıcı";

  return {
    name: targetName,
    kind,
    phone: phone ?? mockPhoneForName(targetName),
    email: mockEmailForName(targetName, kind),
  };
}

function getDraftTargetKindLabel(kind: DraftTargetKind): string {
  const labels: Record<DraftTargetKind, string> = {
    customer: "Müşteri",
    supplier: "Tedarikçi",
    carrier: "Kargo Firması",
    internal: "Ekip",
  };
  return labels[kind];
}

function getDraftDestination(
  target: DraftTarget,
  channel: MockSendChannel,
): string {
  return channel === "email" ? target.email : target.phone;
}

function getMockSendChannelLabel(channel: MockSendChannel): string {
  const labels: Record<MockSendChannel, string> = {
    whatsapp: "WhatsApp",
    telegram: "Telegram",
    email: "E-posta",
  };
  return labels[channel];
}

function getDefaultMockChannelMessage(channel: FloatingMockChannel): string {
  const channelLabel = getMockSendChannelLabel(channel);

  return `Merhaba, ${channelLabel} üzerinden siparişiniz hakkında yardımcı olmak için yazıyorum.`;
}

function mockPhoneForName(name: string): string {
  const hash = hashText(name);
  const operator = 530 + (hash % 60);
  const block = 100 + (Math.floor(hash / 60) % 900);
  const first = Math.floor(hash / 54000) % 100;
  const second = Math.floor(hash / 5400000) % 100;

  return `+90 ${operator} ${block} ${String(first).padStart(2, "0")} ${String(second).padStart(2, "0")}`;
}

function mockEmailForName(name: string, kind: DraftTargetKind): string {
  const domains: Record<DraftTargetKind, string> = {
    customer: "customer.example",
    supplier: "supplier.example",
    carrier: "carrier.example",
    internal: "ops.example",
  };

  return `${toContactSlug(name)}@${domains[kind]}`;
}

function toContactSlug(value: string): string {
  const replacements: Record<string, string> = {
    ç: "c",
    ğ: "g",
    ı: "i",
    ö: "o",
    ş: "s",
    ü: "u",
  };
  const slug = value
    .toLocaleLowerCase("tr")
    .replace(/[çğıöşü]/g, (char) => replacements[char] ?? char)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, ".")
    .replace(/^\.+|\.+$/g, "");

  return slug || "mock";
}

function hashText(value: string): number {
  return Array.from(value).reduce(
    (hash, char) => (hash * 31 + char.charCodeAt(0)) >>> 0,
    7,
  );
}

function isActionableInsight(
  insight: ProactiveInsight,
  state: OperationsState,
): boolean {
  if (
    insight.color === "green" ||
    insight.actionType === "memory_insight_generated"
  ) {
    return false;
  }

  if (insight.actionType !== "create_supplier_order_draft") {
    return true;
  }

  const product = state.products.find(
    (candidate) =>
      namesMatch(insight.entityName, candidate.name) ||
      namesMatch(insight.title, candidate.name),
  );

  if (!product) {
    return false;
  }

  return state.inventoryAlerts.some(
    (alert) => !alert.resolved && alert.productId === product.id,
  );
}

function buildGlobalSearchResults({
  state,
  messages,
  insights,
  memoryRecords,
  query,
}: {
  state: OperationsState;
  messages: ChatMessage[];
  insights: ProactiveInsight[];
  memoryRecords: MemoryRecord[];
  query: string;
}): SearchResult[] {
  const normalizedQuery = normalizeSearch(query);

  if (!normalizedQuery) {
    return [];
  }

  const activeAlerts = state.inventoryAlerts.filter((alert) => !alert.resolved);
  const alertsByProduct = new Map(
    activeAlerts.map((alert) => [alert.productId, alert]),
  );
  const customersById = new Map(
    state.customers.map((customer) => [customer.id, customer]),
  );
  const shipmentsByOrder = new Map(
    state.shipments.map((shipment) => [shipment.orderId, shipment]),
  );
  const results: SearchResult[] = [];

  function add(result: SearchResult) {
    if (matchesSearchResult(result, normalizedQuery)) {
      results.push(result);
    }
  }

  state.products.forEach((product) => {
    const alert = alertsByProduct.get(product.id);
    add({
      id: `product-${product.id}`,
      kind: "product",
      title: product.name,
      description: `${product.category} · ${product.supplier}`,
      meta: `SKU ${product.sku} · ${product.stock}/${product.threshold} ${product.unit}`,
      keywords: [
        "ürün product stok stock",
        alert?.severity === "critical" ? "kritik critical" : "",
        alert?.message ?? "",
      ],
      target: { type: "page", page: "stock" },
    });
  });

  state.customers.forEach((customer) => {
    add({
      id: `customer-${customer.id}`,
      kind: "customer",
      title: customer.name,
      description: `${customer.channel} · ${customer.phone}`,
      meta: "Müşteri kaydı",
      keywords: ["müşteri customer takip follow-up"],
      target: { type: "page", page: "customers" },
    });
  });

  state.orders.forEach((order) => {
    const customer = customersById.get(order.customerId);
    const shipment = shipmentsByOrder.get(order.id);
    const shipmentRisk = shipment?.risk === "delayed" || shipment?.risk === "watch";
    const ordersFilter =
      order.status === "delayed" || shipmentRisk
        ? "Risk"
        : order.dueToday
          ? "Bugün"
          : "Tümü";

    add({
      id: `order-${order.id}`,
      kind: "order",
      title: `Sipariş #${order.id}`,
      description: `${customer?.name ?? "Müşteri"} · ${summarizeItems(order, state)}`,
      meta: `${order.status} · ${formatCurrency(order.total)} · ${formatDate(order.createdAt)}`,
      keywords: [
        "sipariş order",
        order.dueToday ? "bugün today teslim" : "",
        shipment?.trackingCode ?? "",
        shipment?.carrier ?? "",
        shipment?.lastScan ?? "",
      ],
      target: { type: "page", page: "orders", ordersFilter },
    });
  });

  state.shipments.forEach((shipment) => {
    const order = state.orders.find((candidate) => candidate.id === shipment.orderId);
    const customer = order ? customersById.get(order.customerId) : undefined;

    add({
      id: `shipment-${shipment.id}`,
      kind: "shipment",
      title: shipment.trackingCode,
      description: `#${shipment.orderId} · ${shipment.carrier} · ${customer?.name ?? "Müşteri"}`,
      meta: `${shipment.risk} · ${shipment.eta} · ${shipment.city}`,
      keywords: [
        "takip tracking kargo shipment",
        shipment.lastScan,
        shipment.notified ? "bildirildi" : "bildirim bekliyor",
      ],
      target: {
        type: "page",
        page: "orders",
        ordersFilter: shipment.risk === "clear" ? "Tümü" : "Risk",
      },
    });
  });

  messages.forEach((message) => {
    add({
      id: `message-${message.id}`,
      kind: "message",
      title: message.role === "customer" ? "Müşteri mesajı" : "Asistan mesajı",
      description: compactText(message.text, 120),
      meta: message.timestamp,
      keywords: ["mesaj message sohbet chat"],
      target: { type: "chat" },
    });
  });

  activeAlerts.forEach((alert) => {
    const product = state.products.find(
      (candidate) => candidate.id === alert.productId,
    );

    add({
      id: `alert-${alert.productId}`,
      kind: "alert",
      title: `${product?.name ?? alert.productId} stok ${alert.severity}`,
      description: alert.message,
      meta: alert.severity === "critical" ? "Kritik stok" : "Stok uyarısı",
      keywords: ["stok stock kritik critical uyarı alert"],
      target: { type: "page", page: "stock" },
    });
  });

  state.tasks.forEach((task) => {
    add({
      id: `task-${task.id}`,
      kind: "task",
      title: task.title,
      description: `${task.owner}${task.orderId ? ` · Sipariş ${task.orderId}` : ""}`,
      meta: `${task.priority} · ${task.status}`,
      keywords: ["görev task aksiyon action"],
      target: { type: "page", page: "dashboard" },
    });
  });

  insights.forEach((insight) => {
    add({
      id: `insight-${insight.id}`,
      kind: "insight",
      title: insight.title,
      description: compactText(insight.summary, 120),
      meta: `${insight.entityName} · ${insight.color}`,
      keywords: [
        "içgörü insight uyarı alert proaktif",
        insight.evidence.join(" "),
        insight.draftAction,
      ],
      target: {
        type: "page",
        page: "memory",
        memorySearch: query.trim(),
      },
    });
  });

  memoryRecords.forEach((record) => {
    add({
      id: `memory-${record.id}`,
      kind: "memory",
      title: record.entityName ?? record.category,
      description: compactText(record.text, 120),
      meta: `${record.category} · ${record.eventDate ?? "tarihsiz"}`,
      keywords: ["hafıza memory kayıt record"],
      target: {
        type: "page",
        page: "memory",
        memorySearch: query.trim(),
      },
    });
  });

  return results
    .sort((left, right) => {
      const leftScore = scoreSearchResult(left, normalizedQuery);
      const rightScore = scoreSearchResult(right, normalizedQuery);

      return (
        leftScore - rightScore ||
        searchKindOrder.indexOf(left.kind) - searchKindOrder.indexOf(right.kind)
      );
    })
    .slice(0, 24);
}

function buildNotificationItems(
  state: OperationsState,
  actionableInsights: ProactiveInsight[],
): NotificationItem[] {
  const customersById = new Map(
    state.customers.map((customer) => [customer.id, customer]),
  );
  const ordersById = new Map(state.orders.map((order) => [order.id, order]));
  const productsById = new Map(
    state.products.map((product) => [product.id, product]),
  );
  const items: NotificationItem[] = [];

  state.inventoryAlerts
    .filter((alert) => !alert.resolved && alert.severity === "critical")
    .forEach((alert) => {
      const product = productsById.get(alert.productId);
      items.push({
        id: `stock-${alert.productId}`,
        tone: "red",
        title: `${product?.name ?? alert.productId} kritik stok`,
        description: alert.message,
        meta: product
          ? `${product.stock}/${product.threshold} ${product.unit}`
          : "Stok kontrolü",
        action: { type: "stock", productId: alert.productId },
      });
    });

  state.shipments
    .filter((shipment) => shipment.risk !== "clear" && !shipment.notified)
    .forEach((shipment) => {
      const order = ordersById.get(shipment.orderId);
      const customer = order ? customersById.get(order.customerId) : undefined;
      items.push({
        id: `shipment-${shipment.id}`,
        tone: shipment.risk === "delayed" ? "red" : "orange",
        title: `Kargo riski: #${shipment.orderId}`,
        description: `${shipment.carrier} · ${shipment.trackingCode}`,
        meta: customer
          ? `${customer.name} · ${shipment.lastScan}`
          : shipment.lastScan,
        action: { type: "shipment" },
      });
    });

  state.orders
    .filter((order) => order.dueToday && order.status !== "delivered")
    .forEach((order) => {
      const customer = customersById.get(order.customerId);
      items.push({
        id: `order-${order.id}`,
        tone: "blue",
        title: `Bugün teslim: #${order.id}`,
        description: `${customer?.name ?? "Müşteri"} · ${summarizeItems(order, state)}`,
        meta: `${order.status} · ${formatCurrency(order.total)}`,
        action: { type: "order" },
      });
    });

  actionableInsights
    .filter((insight) => insight.actionType === "create_customer_reminder_draft")
    .forEach((insight) => {
      items.push({
        id: `insight-${insight.id}`,
        tone: "yellow",
        title: insight.title,
        description: compactText(insight.summary, 100),
        meta: `${insight.entityName} · müşteri takibi`,
        action: { type: "insight", insightId: insight.id },
      });
    });

  state.tasks
    .filter((task) => task.status === "open" && task.priority === "high")
    .forEach((task) => {
      items.push({
        id: `task-${task.id}`,
        tone: "red",
        title: task.title,
        description: `${task.owner}${task.orderId ? ` · Sipariş ${task.orderId}` : ""}`,
        meta: "Yüksek öncelik",
        action: { type: "task" },
      });
    });

  return items;
}

function matchesSearchResult(result: SearchResult, normalizedQuery: string): boolean {
  const haystack = normalizeSearch(
    [result.title, result.description, result.meta, ...result.keywords].join(" "),
  );

  return normalizedQuery
    .split(" ")
    .filter(Boolean)
    .every((part) => haystack.includes(part));
}

function scoreSearchResult(result: SearchResult, normalizedQuery: string): number {
  const title = normalizeSearch(result.title);
  const description = normalizeSearch(result.description);

  if (title.startsWith(normalizedQuery)) {
    return 0;
  }

  if (title.includes(normalizedQuery)) {
    return 1;
  }

  if (description.includes(normalizedQuery)) {
    return 2;
  }

  return 3;
}

function normalizeSearch(value: string): string {
  const replacements: Record<string, string> = {
    ç: "c",
    ğ: "g",
    ı: "i",
    ö: "o",
    ş: "s",
    ü: "u",
  };

  return value
    .toLocaleLowerCase("tr")
    .replace(/[çğıöşü]/g, (char) => replacements[char] ?? char)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function searchResultIcon(kind: SearchResultKind): ReactNode {
  const icons: Record<SearchResultKind, ReactNode> = {
    product: <Warehouse size={15} />,
    customer: <Users size={15} />,
    order: <ShoppingBag size={15} />,
    shipment: <Truck size={15} />,
    message: <MessageSquareText size={15} />,
    alert: <AlertTriangle size={15} />,
    task: <ClipboardList size={15} />,
    insight: <Sparkles size={15} />,
    memory: <History size={15} />,
  };

  return icons[kind];
}

function notificationItemIcon(item: NotificationItem): ReactNode {
  const icons: Record<NotificationAction["type"], ReactNode> = {
    stock: <AlertTriangle size={15} />,
    shipment: <Truck size={15} />,
    order: <ShoppingBag size={15} />,
    insight: <Users size={15} />,
    task: <ClipboardList size={15} />,
  };

  return icons[item.action.type];
}

function summarizeItems(order: Order, state: OperationsState): string {
  return order.items
    .map((item) => {
      const product = state.products.find(
        (candidate) => candidate.id === item.productId,
      );
      return `${item.quantity}x ${product?.name ?? "?"}`;
    })
    .join(", ");
}

function average(values: number[]): number {
  if (!values.length) {
    return 0;
  }

  return values.reduce((total, value) => total + value, 0) / values.length;
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  }).format(amount);
}

function formatDate(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("tr-TR", {
    day: "2-digit",
    month: "short",
  }).format(date);
}

function formatTime(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("tr-TR", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function formatTodayLabel(date: Date): string {
  const parts = new Intl.DateTimeFormat("tr-TR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).formatToParts(date);
  const byType = Object.fromEntries(
    parts.map((part) => [part.type, part.value]),
  );
  const weekday = byType.weekday
    ? byType.weekday.charAt(0).toLocaleUpperCase("tr") + byType.weekday.slice(1)
    : "";

  return [weekday, `${byType.day} ${byType.month} ${byType.year}`]
    .filter(Boolean)
    .join(", ");
}

function firstSentence(value: string): string {
  const trimmed = value.trim();
  const match = trimmed.match(/^.*?[.!?](?:\s|$)/);
  return (match?.[0] ?? trimmed).trim();
}

function compactText(value: string, maxLength: number): string {
  const normalized = value.replace(/\s+/g, " ").trim();

  if (normalized.length <= maxLength) {
    return normalized;
  }

  return `${normalized.slice(0, maxLength - 1).trimEnd()}…`;
}

function namesMatch(left: string, right: string): boolean {
  const normalize = (value: string) =>
    value
      .toLocaleLowerCase("tr")
      .replace(/[^\w\s]/g, "")
      .trim();

  return (
    normalize(left).includes(normalize(right)) ||
    normalize(right).includes(normalize(left))
  );
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "API hatası.";
}
