import { Bot, ChevronDown, Mail, MessageCircle, Send, X } from "lucide-react";
import type { FormEventHandler, RefObject } from "react";
import { getMockSendChannelLabel } from "../app/drafts";
import { starterMessages } from "../app/constants";
import type {
  ChatState,
  ExternalBotChannel,
  FloatingMockChannel,
  MockComposerState,
} from "../app/uiTypes";
import type { ChatMessage, Customer } from "../types";

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
  {
    id: "email",
    label: "E-posta",
    icon: <Mail size={17} />,
  },
];

export function FloatingAssistant({
  chatState,
  mockComposer,
  customers,
  messages,
  chatInput,
  isResponding,
  disabled,
  chatLogRef,
  onOpenMockComposer,
  onMockComposerChange,
  onCloseMockComposer,
  onSendMockComposer,
  onChatStateChange,
  onChatInputChange,
  onChatSubmit,
}: {
  chatState: ChatState;
  mockComposer: MockComposerState | null;
  customers: Customer[];
  messages: ChatMessage[];
  chatInput: string;
  isResponding: boolean;
  disabled: boolean;
  chatLogRef: RefObject<HTMLDivElement | null>;
  onOpenMockComposer: (channel: FloatingMockChannel) => void;
  onMockComposerChange: (next: Partial<MockComposerState>) => void;
  onCloseMockComposer: () => void;
  onSendMockComposer: () => void;
  onChatStateChange: (state: ChatState) => void;
  onChatInputChange: (value: string) => void;
  onChatSubmit: FormEventHandler<HTMLFormElement>;
}) {
  if (chatState === "closed" && !mockComposer) {
    return (
      <div
        className="assistant-launcher"
        aria-label="Asistan kanalları">
        <div className="channel-fabs">
          {botChannels.map((channel) => (
            <BotChannelButton
              channel={channel}
              key={channel.id}
              onOpen={onOpenMockComposer}
            />
          ))}
        </div>
        <button
          className="chat-fab"
          onClick={() => onChatStateChange("open")}
          aria-label="Sohbeti aç"
          type="button">
          <Bot size={22} />
          <span>AI Asistan</span>
          {messages.length > 2 && (
            <span className="chat-fab-badge">{messages.length - 2}</span>
          )}
        </button>
      </div>
    );
  }

  if (chatState === "closed" && mockComposer) {
    return (
      <MockChannelComposer
        composer={mockComposer}
        customers={customers}
        onChange={onMockComposerChange}
        onClose={onCloseMockComposer}
        onSend={onSendMockComposer}
      />
    );
  }

  return (
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
              onChatStateChange(chatState === "minimized" ? "open" : "minimized")
            }
            aria-label="Küçült"
            type="button">
            <ChevronDown
              size={16}
              className={chatState === "minimized" ? "rotate-180" : ""}
            />
          </button>
          <button
            onClick={() => onChatStateChange("closed")}
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
                onClick={() => onChatInputChange(message)}
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
            {isResponding && (
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
            onSubmit={onChatSubmit}>
            <input
              value={chatInput}
              onChange={(event) => onChatInputChange(event.target.value)}
              placeholder="Bir şey sorun..."
              aria-label="Mesaj"
              disabled={disabled}
            />
            <button
              type="submit"
              disabled={disabled || !chatInput.trim()}
              aria-label="Gönder">
              <Send size={15} />
            </button>
          </form>
        </>
      )}
    </div>
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
    ) : composer.channel === "email" ? (
      <Mail size={16} />
    ) : (
      <Send size={16} />
    );
  const destination =
    composer.channel === "email"
      ? (selectedCustomer?.email ?? "Mock e-posta yok")
      : (selectedCustomer?.phone ?? "Mock telefon yok");

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
        <span>{composer.channel === "email" ? "E-posta" : "Telefon"}</span>
        <strong>{destination}</strong>
      </div>

      {composer.channel === "email" && (
        <label className="mock-field">
          <span>Konu</span>
          <input
            value={composer.subject}
            onChange={(event) =>
              onChange({ subject: event.target.value, notice: "" })
            }
            aria-label="E-posta konusu"
          />
        </label>
      )}

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
