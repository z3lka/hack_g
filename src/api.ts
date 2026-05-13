import type {
  AgentAction,
  ChatMessage,
  ConnectorHealth,
  ContactDraft,
  CustomerThread,
  DraftApprovalResponse,
  InboxSyncResponse,
  MemoryRecord,
  MemoryRecordInput,
  MemoryStatus,
  MorningInsightsResponse,
  OperationsState,
  Task,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

export type ChatResponse = {
  customerMessage: ChatMessage;
  agentMessage: ChatMessage;
  actions: AgentAction[];
  state: OperationsState;
  contactDraft?: ContactDraft | null;
};

export type StateActionResponse = {
  state: OperationsState;
  action: AgentAction;
};

export type TaskPlanResponse = StateActionResponse & {
  createdTasks: Task[];
};

export type MemoryIngestResponse = {
  status: MemoryStatus;
  records: MemoryRecord[];
};

export async function fetchState() {
  return request<OperationsState>("/state");
}

export async function fetchMorningInsights() {
  return request<MorningInsightsResponse>("/insights/morning", { method: "POST" });
}

export async function fetchMemoryStatus() {
  return request<MemoryStatus>("/memory/status");
}

export async function fetchMemoryRecords() {
  return request<MemoryRecord[]>("/memory/records");
}

export async function seedMemory() {
  return request<MemoryStatus>("/memory/seed", { method: "POST" });
}

export async function ingestMemory(records: MemoryRecordInput[]) {
  return request<MemoryIngestResponse>("/memory/ingest", {
    method: "POST",
    body: JSON.stringify({ records }),
  });
}

export async function sendCustomerMessage(message: string) {
  return request<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

export async function syncInbox() {
  return request<InboxSyncResponse>("/inbox/sync", { method: "POST" });
}

export async function fetchInboxThreads() {
  return request<CustomerThread[]>("/inbox/threads");
}

export async function fetchInboxThread(threadId: string) {
  return request<CustomerThread>(`/inbox/threads/${threadId}`);
}

export async function approveAssistantDraft(
  draftId: string,
  body?: string,
  subject?: string,
) {
  return request<DraftApprovalResponse>(`/assistant/drafts/${draftId}/approve`, {
    method: "POST",
    body: JSON.stringify({ body, subject }),
  });
}

export async function fetchConnectorHealth() {
  return request<ConnectorHealth[]>("/connectors/health");
}

export async function notifyShipment(orderId: string) {
  return request<StateActionResponse>(`/shipments/${orderId}/notify`, { method: "POST" });
}

export async function createRestockDraft(productId: string) {
  return request<StateActionResponse>(`/inventory/${productId}/draft`, { method: "POST" });
}

export async function generateTaskPlan() {
  return request<TaskPlanResponse>("/tasks/generate", { method: "POST" });
}

export async function completeTaskRequest(taskId: string) {
  return request<StateActionResponse>(`/tasks/${taskId}/complete`, { method: "POST" });
}

export async function resetDemoState() {
  return request<OperationsState>("/reset", { method: "POST" });
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    ...init,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `API request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}
