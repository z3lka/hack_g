import { FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  approveAssistantDraft,
  completeTaskRequest,
  createRestockDraft,
  fetchConnectorHealth,
  fetchInboxThreads,
  fetchMemoryRecords,
  fetchMorningInsights,
  fetchState,
  generateTaskPlan,
  ingestMemory,
  notifyShipment,
  resetDemoState,
  sendCustomerMessage,
  syncInbox,
} from "../api";
import { emptyState, initialMessages } from "./constants";
import {
  getDefaultMockChannelMessage,
  getDraftDestination,
  getDraftTargetForInsight,
  getDraftTitle,
  getMockSendChannelLabel,
  getSupplierDraftTarget,
} from "./drafts";
import { formatTodayLabel, getErrorMessage, summarizeItems } from "./format";
import { isActionableInsight } from "./insights";
import { labelStatus } from "./labels";
import { buildNotificationItems } from "./notifications";
import { buildGlobalSearchResults } from "./search";
import type {
  ChatState,
  DraftModal,
  FloatingMockChannel,
  MockComposerState,
  MockSendChannel,
  NotificationItem,
  PageView,
  SearchResult,
} from "./uiTypes";
import type {
  AgentAction,
  ChatMessage,
  ConnectorHealth,
  ContactDraft,
  CustomerThread,
  InventoryAlert,
  MemoryRecord,
  MemoryStatus,
  OperationsState,
  Product,
  ProactiveInsight,
} from "../types";

export function useOperationsController() {
  const [state, setState] = useState<OperationsState | null>(null);
  const [chatInput, setChatInput] = useState("");
  const [messages, setMessages] = useState(initialMessages);
  const [actions, setActions] = useState<AgentAction[]>([]);
  const [insights, setInsights] = useState<ProactiveInsight[]>([]);
  const [memoryRecords, setMemoryRecords] = useState<MemoryRecord[]>([]);
  const [memoryStatus, setMemoryStatus] = useState<MemoryStatus | null>(null);
  const [inboxThreads, setInboxThreads] = useState<CustomerThread[]>([]);
  const [activeInboxThreadId, setActiveInboxThreadId] = useState<string | null>(null);
  const [connectorHealth, setConnectorHealth] = useState<ConnectorHealth[]>([]);
  const [llmMode, setLlmMode] = useState<"gemini" | "fallback">("fallback");
  const [insightsGeneratedAt, setInsightsGeneratedAt] = useState("");
  const [apiError, setApiError] = useState("");
  const [isMutating, setIsMutating] = useState(false);
  const [isChatPending, setIsChatPending] = useState(false);
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
  }, [messages, chatState, isChatPending]);

  const currentState = state ?? emptyState;
  const dueToday = currentState.orders.filter(
    (order) => order.dueToday && order.status !== "delivered",
  );
  const actionableInsights = insights.filter((insight) =>
    isActionableInsight(insight, currentState),
  );
  const globalSearchResults = useMemo(
    () =>
      buildGlobalSearchResults({
        state: currentState,
        messages,
        inboxThreads,
        insights,
        memoryRecords,
        query: globalSearch,
      }),
    [currentState, globalSearch, inboxThreads, insights, memoryRecords, messages],
  );
  const notificationItems = useMemo(
    () => buildNotificationItems(currentState, actionableInsights),
    [actionableInsights, currentState],
  );
  const activeInboxThread =
    inboxThreads.find((thread) => thread.id === activeInboxThreadId) ??
    inboxThreads[0] ??
    null;

  function navigate(page: PageView, nextOrdersFilter?: string) {
    if (nextOrdersFilter) {
      setOrdersFilter(nextOrdersFilter);
    }

    setActivePage(page);

    if (page === "inbox") {
      void handleInboxSync();
    }
  }

  function toggleSidebar() {
    setIsSidebarCollapsed((current) => !current);
  }

  function handleSearchChange(value: string) {
    setGlobalSearch(value);
    setIsSearchOpen(true);
    setIsNotificationsOpen(false);
  }

  function handleSearchFocus() {
    setIsSearchOpen(true);
    setIsNotificationsOpen(false);
  }

  function clearSearch() {
    setGlobalSearch("");
    setIsSearchOpen(false);
  }

  function toggleNotifications() {
    setIsNotificationsOpen((current) => !current);
    setIsSearchOpen(false);
  }

  function closeDraft() {
    setDraftModal(null);
  }

  function closeMockComposer() {
    setMockComposer(null);
  }

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

    navigate(result.target.page, result.target.ordersFilter);
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
      navigate("orders", "Risk");
      return;
    }

    if (item.action.type === "order") {
      navigate("orders", "Bugün");
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
      await refreshInbox();
      await refreshConnectorHealth();
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

  async function refreshInbox() {
    const threads = await fetchInboxThreads();
    setInboxThreads(threads);
    setActiveInboxThreadId((current) => current ?? threads[0]?.id ?? null);
  }

  async function refreshConnectorHealth() {
    setConnectorHealth(await fetchConnectorHealth());
  }

  async function handleChatSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const messageText = chatInput.trim();
    if (!messageText) {
      return;
    }

    const pendingMessage = createLocalChatMessage(messageText, "customer");
    setMessages((current) => [...current, pendingMessage]);
    setChatInput("");
    setIsChatPending(true);

    try {
      await runMutation(async () => {
        await delay(1000);
        const response = await sendCustomerMessage(messageText);
        setMessages((current) => [
          ...current.map((message) =>
            message.id === pendingMessage.id ? response.customerMessage : message,
          ),
          response.agentMessage,
        ]);
        prependActions(response.actions);
        setState(response.state);
        if (response.contactDraft) {
          openContactDraft(response.contactDraft);
        }
      });
    } finally {
      setIsChatPending(false);
    }
  }

  async function handleInboxSync() {
    await runMutation(async () => {
      const response = await syncInbox();
      setInboxThreads(response.threads);
      setConnectorHealth(response.connectorHealth);
      setActiveInboxThreadId((current) => current ?? response.threads[0]?.id ?? null);
      prependActions([
        {
          id: crypto.randomUUID(),
          label: `${response.syncedMessages} email mesajı senkronize edildi`,
          type: "read_inbox",
          payload: { syncedMessages: response.syncedMessages },
        },
      ]);
    });
  }

  async function approveInboxDraft(draftId: string, body?: string, subject?: string) {
    await runMutation(async () => {
      const response = await approveAssistantDraft(draftId, body, subject);
      setInboxThreads((current) =>
        current
          .map((thread) =>
            thread.id === response.thread.id ? response.thread : thread,
          )
          .sort(
            (left, right) =>
              new Date(right.lastMessageAt).getTime() -
              new Date(left.lastMessageAt).getTime(),
          ),
      );
      setActiveInboxThreadId(response.thread.id);
      prependActions([response.action]);
      await refreshConnectorHealth();
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

  function openShipmentDraft(orderId: string) {
    const order = currentState.orders.find((item) => item.id === orderId);
    const shipment = currentState.shipments.find((item) => item.orderId === orderId);
    const customer = order
      ? currentState.customers.find((item) => item.id === order.customerId)
      : null;

    if (!order || !shipment || !customer) {
      return;
    }

    const recommendedChannel = getRecommendedChannel(customer.channel);

    setDraftNotice("");
    setDraftModal({
      title: `Müşteri Güncellemesi: ${customer.name}`,
      subtitle: `Önerilen kanal: ${getMockSendChannelLabel(recommendedChannel)}`,
      subject: `Sipariş #${order.id} kargo güncellemesi`,
      body: [
        `Merhaba ${customer.name},`,
        "",
        `Sipariş #${order.id} için kısa bir kargo güncellemesi paylaşmak istedik.`,
        `Güncel durum: ${labelStatus(order.status)}.`,
        `Kargo firması: ${shipment.carrier}.`,
        `Son kargo durumu: ${shipment.lastScan}.`,
        `Tahmini teslim: ${shipment.eta}.`,
        `Sipariş içeriği: ${summarizeItems(order, currentState)}.`,
        "",
        "Yeni kargo hareketi oluştuğunda tekrar bilgilendireceğiz.",
        "",
        "Sevgiler,",
        "Çırak",
      ].join("\n"),
      target: {
        name: customer.name,
        kind: "customer",
        phone: customer.phone,
        email: customer.email ?? "E-posta yok",
      },
      recommendedChannel,
      confidence: shipment.risk === "delayed" ? 0.86 : 0.82,
      reviewReason: "Owner review is required before any customer message is sent.",
      shipmentOrderId: order.id,
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
      await refreshInbox();
      await refreshConnectorHealth();
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

  function openContactDraft(contactDraft: ContactDraft) {
    setDraftNotice("");
    setDraftModal({
      title: `Müşteri Güncellemesi: ${contactDraft.customerName}`,
      subtitle: `Önerilen kanal: ${getMockSendChannelLabel(contactDraft.recommendedChannel)}`,
      subject: contactDraft.subject,
      body: contactDraft.body,
      target: {
        name: contactDraft.customerName,
        kind: "customer",
        phone: contactDraft.phone,
        email: contactDraft.email ?? "E-posta yok",
      },
      recommendedChannel: contactDraft.recommendedChannel,
      confidence: contactDraft.confidence,
      reviewReason: contactDraft.requiredReviewReason,
    });
  }

  async function copyDraft() {
    if (!draftModal) {
      return;
    }

    await navigator.clipboard.writeText(
      draftModal.subject
        ? `Konu: ${draftModal.subject}\n\n${draftModal.body}`
        : draftModal.body,
    );
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

  function updateDraftSubject(subject: string) {
    setDraftNotice("");
    setDraftModal((current) => (current ? { ...current, subject } : current));
  }

  function mockSendDraft(channel: MockSendChannel) {
    if (!draftModal) {
      return;
    }

    const destination = getDraftDestination(draftModal.target, channel);
    const channelLabel = getMockSendChannelLabel(channel);
    const notice = `${channelLabel} gönderildi: ${destination}`;

    setDraftNotice(notice);
    prependActions([
      {
        id: crypto.randomUUID(),
        label: `${channelLabel} ile gönderildi: ${draftModal.target.name} (${destination})`,
        type: "mock_send_message",
        payload: {
          channel,
          recipient: draftModal.target.name,
          destination,
          draft: draftModal.title,
          subject: draftModal.subject ?? "",
          message: draftModal.body,
        },
      },
    ]);

    if (draftModal.shipmentOrderId) {
      void markShipmentNotified(draftModal.shipmentOrderId);
    }
  }

  function openMockComposer(channel: FloatingMockChannel) {
    const firstCustomer = currentState.customers[0];

    setMockComposer({
      channel,
      customerId: firstCustomer?.id ?? "",
      subject: channel === "email" ? "Sipariş güncellemesi" : "",
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
    const destination =
      mockComposer.channel === "email"
        ? (customer.email ?? "E-posta yok")
        : customer.phone;
    const notice = `${channelLabel} gönderildi: ${customer.name} (${destination})`;

    setMockComposer({ ...mockComposer, notice });
    prependActions([
      {
        id: crypto.randomUUID(),
        label: `${channelLabel} mesajı gönderildi: ${customer.name}`,
        type: "mock_send_message",
        payload: {
          channel: mockComposer.channel,
          recipient: customer.name,
          destination,
          subject: mockComposer.subject,
          message: mockComposer.message.trim(),
        },
      },
    ]);
  }

  return {
    state,
    actions,
    insights,
    memoryRecords,
    memoryStatus,
    inboxThreads,
    activeInboxThread,
    activeInboxThreadId,
    connectorHealth,
    llmMode,
    insightsGeneratedAt,
    apiError,
    isMutating,
    isChatPending,
    activePage,
    ordersFilter,
    draftModal,
    draftNotice,
    mockComposer,
    memorySearch,
    memoryInput,
    chatState,
    isSidebarCollapsed,
    globalSearch,
    isSearchOpen,
    isNotificationsOpen,
    chatInput,
    messages,
    dueToday,
    actionableInsights,
    globalSearchResults,
    notificationItems,
    chatLogRef,
    searchMenuRef,
    notificationsMenuRef,
    todayLabel,
    navigate,
    toggleSidebar,
    setActivePage,
    setOrdersFilter,
    setActiveInboxThreadId,
    setMemorySearch,
    setMemoryInput,
    setChatInput,
    setChatState,
    handleSearchChange,
    handleSearchFocus,
    clearSearch,
    toggleNotifications,
    handleGlobalSearchSubmit,
    handleGlobalSearchKeyDown,
    selectSearchResult,
    handleNotificationSelect,
    handleChatSubmit,
    handleInboxSync,
    approveInboxDraft,
    handleMemoryIngest,
    markShipmentNotified,
    openShipmentDraft,
    resolveInventoryAlert,
    draftProduct,
    handleGeneratePlan,
    completeTask,
    resetDemo,
    handleInsightAction,
    closeDraft,
    copyDraft,
    updateDraftBody,
    updateDraftSubject,
    mockSendDraft,
    openMockComposer,
    updateMockComposer,
    closeMockComposer,
    sendMockComposerMessage,
  };
}

function createLocalChatMessage(
  text: string,
  role: ChatMessage["role"],
): ChatMessage {
  return {
    id: `local-${crypto.randomUUID()}`,
    role,
    text,
    timestamp: new Date().toLocaleTimeString("tr-TR", {
      hour: "2-digit",
      minute: "2-digit",
    }),
  };
}

function delay(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function getRecommendedChannel(
  channel: "WhatsApp" | "Email" | "Phone",
): MockSendChannel {
  if (channel === "Email") {
    return "email";
  }

  return "whatsapp";
}
