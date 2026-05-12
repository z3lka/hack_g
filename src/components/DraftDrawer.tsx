import { Copy, Mail, MessageCircle, Send, X } from "lucide-react";
import { getDraftTargetKindLabel } from "../app/drafts";
import type { DraftModal, MockSendChannel } from "../app/uiTypes";

export function DraftDrawer({
  draft,
  notice,
  onClose,
  onBodyChange,
  onMockSend,
  onCopy,
}: {
  draft: DraftModal;
  notice: string;
  onClose: () => void;
  onBodyChange: (body: string) => void;
  onMockSend: (channel: MockSendChannel) => void;
  onCopy: () => void;
}) {
  return (
    <div
      className="drawer-overlay"
      onClick={onClose}>
      <aside
        className="drawer"
        role="dialog"
        aria-modal="true"
        onClick={(event) => event.stopPropagation()}>
        <div className="drawer-header">
          <div>
            <p className="eyebrow">{draft.subtitle}</p>
            <h2>{draft.title}</h2>
          </div>
          <button
            onClick={onClose}
            aria-label="Kapat"
            type="button">
            <X size={18} />
          </button>
        </div>
        <div className="drawer-target">
          <div>
            <span>{getDraftTargetKindLabel(draft.target.kind)}</span>
            <strong>{draft.target.name}</strong>
          </div>
          <div>
            <span>Telefon</span>
            <strong>{draft.target.phone}</strong>
          </div>
          <div>
            <span>E-posta</span>
            <strong>{draft.target.email}</strong>
          </div>
        </div>
        <textarea
          className="drawer-body drawer-body-input"
          value={draft.body}
          onChange={(event) => onBodyChange(event.target.value)}
          aria-label="Gönderilecek mesaj içeriği"
        />
        <div
          className="mock-send-grid"
          aria-label="Mock gönderim kanalları">
          <button
            className="drawer-send whatsapp"
            onClick={() => onMockSend("whatsapp")}
            type="button">
            <MessageCircle size={15} />
            <span>
              WhatsApp
              <small>{draft.target.phone}</small>
            </span>
          </button>
          <button
            className="drawer-send telegram"
            onClick={() => onMockSend("telegram")}
            type="button">
            <Send size={15} />
            <span>
              Telegram
              <small>{draft.target.phone}</small>
            </span>
          </button>
          <button
            className="drawer-send email"
            onClick={() => onMockSend("email")}
            type="button">
            <Mail size={15} />
            <span>
              E-posta
              <small>{draft.target.email}</small>
            </span>
          </button>
        </div>
        {notice && <div className="mock-send-notice">{notice}</div>}
        <button
          className="btn-copy"
          onClick={onCopy}
          type="button">
          <Copy size={15} /> Kopyala
        </button>
      </aside>
    </div>
  );
}
