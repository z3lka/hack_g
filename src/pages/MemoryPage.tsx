import { ArrowUpRight, MessageSquareText, Sparkles } from "lucide-react";
import type { FormEvent } from "react";
import type {
  AgentAction,
  MemoryRecord,
  MemoryStatus,
  ProactiveInsight,
} from "../types";
import { Empty, StatusPill } from "../components/common";

export function MemoryPage({
  insights,
  records,
  memoryStatus,
  llmMode,
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
