import {
  CheckCircle2,
  Inbox,
  MailCheck,
  RefreshCw,
  Send,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { formatTime, summarizeItems } from "../app/format";
import { labelIntent, labelReviewReason, labelStatus } from "../app/labels";
import { Empty, StatusPill } from "../components/common";
import type {
  AssistantDraft,
  ConnectorHealth,
  CustomerThread,
  OperationsState,
} from "../types";

export function InboxPage({
  threads,
  activeThread,
  state,
  connectorHealth,
  disabled,
  onSelectThread,
  onSync,
  onApproveDraft,
}: {
  threads: CustomerThread[];
  activeThread: CustomerThread | null;
  state: OperationsState;
  connectorHealth: ConnectorHealth[];
  disabled: boolean;
  onSelectThread: (threadId: string) => void;
  onSync: () => void;
  onApproveDraft: (draftId: string, body?: string, subject?: string) => void;
}) {
  const latestDraft =
    activeThread && activeThread.drafts.length
      ? activeThread.drafts[activeThread.drafts.length - 1]
      : null;
  const inboundMessages = activeThread?.messages.filter(
    (message) => message.direction === "inbound",
  ) ?? [];
  const latestMessage = inboundMessages[inboundMessages.length - 1];
  const [draftSubject, setDraftSubject] = useState("");
  const [draftBody, setDraftBody] = useState("");

  useEffect(() => {
    setDraftSubject(latestDraft?.subject ?? "");
    setDraftBody(latestDraft?.body ?? "");
  }, [latestDraft?.id, latestDraft?.subject, latestDraft?.body]);

  const linked = useMemo(
    () => (latestDraft ? buildLinkedContext(latestDraft, state) : []),
    [latestDraft, state],
  );
  const pendingDraft = latestDraft?.status === "pending_review";

  return (
    <div className="page-content inbox-page">
      <div className="inbox-toolbar">
        <div>
          <p className="eyebrow">E-posta Asistanı</p>
          <h2>Müşteri Gelen Kutusu</h2>
        </div>
        <div className="inbox-toolbar-actions">
          <ConnectorHealthStrip items={connectorHealth} />
          <button
            className="btn-outline"
            onClick={onSync}
            disabled={disabled}
            type="button">
            <RefreshCw size={15} />
            Mail Senkronize Et
          </button>
        </div>
      </div>

      <div className="inbox-layout">
        <aside className="inbox-thread-list">
          {threads.map((thread) => {
            const draft = thread.drafts[thread.drafts.length - 1];
            const messages = thread.messages.filter(
              (item) => item.direction === "inbound",
            );
            const message = messages[messages.length - 1];

            return (
              <button
                key={thread.id}
                className={`inbox-thread-item${activeThread?.id === thread.id ? " active" : ""}`}
                onClick={() => onSelectThread(thread.id)}
                type="button">
                <div className="thread-topline">
                  <strong>{thread.customerName}</strong>
                  <time>{formatTime(thread.lastMessageAt)}</time>
                </div>
                <span className="thread-subject">{thread.subject}</span>
                <p>{message?.body ?? "Gelen mesaj yok"}</p>
                <div className="thread-meta">
                  <StatusPill status={thread.status} />
                  <span>{draft ? labelIntent(draft.intent) : "Taslak yok"}</span>
                  {thread.unread && <i>Okunmadı</i>}
                </div>
              </button>
            );
          })}
          {!threads.length && (
            <div className="inbox-empty">
              <Empty text="Henüz e-posta mesajı yok. Senkronizasyon ile gelen kutusu okunur." />
            </div>
          )}
        </aside>

        <section className="inbox-detail">
          {!activeThread ? (
            <Empty text="Bir email konuşması seçin." />
          ) : (
            <>
              <div className="inbox-detail-header">
                <div>
                  <p className="eyebrow">{activeThread.customerEmail}</p>
                  <h2>{activeThread.subject}</h2>
                </div>
                <StatusPill status={activeThread.status} />
              </div>

              <div className="email-message-panel">
                <div className="email-panel-title">
                  <Inbox size={16} />
                  <strong>Gelen Mesaj</strong>
                </div>
                <div className="email-message-meta">
                  <span>{activeThread.customerName}</span>
                  <time>{latestMessage ? formatTime(latestMessage.receivedAt) : "-"}</time>
                </div>
                <p>{latestMessage?.body ?? "Mesaj içeriği yok"}</p>
              </div>

              {latestDraft ? (
                <div className="assistant-draft-panel">
                  <div className="draft-panel-header">
                    <div>
                      <p className="eyebrow">{labelIntent(latestDraft.intent)}</p>
                      <h3>Kontrol Taslağı</h3>
                    </div>
                    <DraftStatusBadge draft={latestDraft} />
                  </div>

                  <div className="draft-confidence">
                    <span>Güven</span>
                    <strong>{Math.round(latestDraft.confidence * 100)}%</strong>
                    <div>
                      <i style={{ width: `${Math.round(latestDraft.confidence * 100)}%` }} />
                    </div>
                  </div>

                  <div className="linked-context-grid">
                    {linked.map((item) => (
                      <div
                        className="linked-context-item"
                        key={`${item.label}-${item.value}`}>
                        <span>{item.label}</span>
                        <strong>{item.value}</strong>
                        {item.detail && <small>{item.detail}</small>}
                      </div>
                    ))}
                    {!linked.length && (
                      <div className="linked-context-item muted">
                        <span>Bağlı Veri</span>
                        <strong>Bağlı sipariş, ürün veya müşteri yok</strong>
                      </div>
                    )}
                  </div>

                  <div className="review-note">
                    <MailCheck size={15} />
                    <span>{labelReviewReason(latestDraft.requiredReviewReason)}</span>
                  </div>

                  <label className="draft-edit-field">
                    <span>Konu</span>
                    <input
                      value={draftSubject}
                      onChange={(event) => setDraftSubject(event.target.value)}
                      disabled={!pendingDraft || disabled}
                    />
                  </label>
                  <label className="draft-edit-field">
                    <span>Taslak</span>
                    <textarea
                      value={draftBody}
                      onChange={(event) => setDraftBody(event.target.value)}
                      disabled={!pendingDraft || disabled}
                      rows={10}
                    />
                  </label>

                  <button
                    className="btn-green approve-send-btn"
                    onClick={() =>
                      onApproveDraft(latestDraft.id, draftBody, draftSubject)
                    }
                    disabled={!pendingDraft || disabled || !draftBody.trim()}
                    type="button">
                    <Send size={15} />
                    Onayla ve Gönder
                  </button>
                </div>
              ) : (
                <Empty text="Bu konuşma için taslak yok." />
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}

function ConnectorHealthStrip({ items }: { items: ConnectorHealth[] }) {
  if (!items.length) {
    return null;
  }

  return (
    <div className="connector-strip">
      {items.map((item) => (
        <span
          key={`${item.type}-${item.name}`}
          className={`connector-dot ${item.status}`}
          title={item.message ?? item.capabilities.join(", ")}>
          {item.name}
        </span>
      ))}
    </div>
  );
}

function DraftStatusBadge({ draft }: { draft: AssistantDraft }) {
  const icon = draft.status === "sent" ? <CheckCircle2 size={14} /> : <MailCheck size={14} />;

  return (
    <span className={`draft-status ${draft.status}`}>
      {icon}
      {labelStatus(draft.status)}
    </span>
  );
}

function buildLinkedContext(draft: AssistantDraft, state: OperationsState) {
  const linked: Array<{ label: string; value: string; detail?: string }> = [];
  const order = draft.entities.orderId
    ? state.orders.find((item) => item.id === draft.entities.orderId)
    : undefined;
  const customer = draft.entities.customerId
    ? state.customers.find((item) => item.id === draft.entities.customerId)
    : undefined;
  const product = draft.entities.productId
    ? state.products.find((item) => item.id === draft.entities.productId)
    : undefined;
  const shipment = draft.entities.orderId
    ? state.shipments.find((item) => item.orderId === draft.entities.orderId)
    : undefined;

  if (customer) {
    linked.push({
      label: "Müşteri",
      value: customer.name,
      detail: customer.email ?? customer.phone,
    });
  }

  if (order) {
    linked.push({
      label: "Sipariş",
      value: `#${order.id} · ${labelStatus(order.status)}`,
      detail: summarizeItems(order, state),
    });
  }

  if (shipment) {
    linked.push({
      label: "Kargo",
      value: shipment.trackingCode,
      detail: `${shipment.carrier} · ${shipment.eta}`,
    });
  }

  if (product) {
    linked.push({
      label: "Ürün",
      value: product.name,
      detail: `${product.stock} ${product.unit} · eşik ${product.threshold}`,
    });
  }

  return linked;
}
