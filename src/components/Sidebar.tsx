import {
  ClipboardList,
  Clock3,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import type { MemoryStatus } from "../types";
import { navIcon, navLabel, pageViews } from "../app/navigation";
import type { PageView } from "../app/uiTypes";
import compactAppIcon from "../../assets/new_icon.png";
import expandedAppIcon from "../../assets/cirak.png";

export function Sidebar({
  activePage,
  isCollapsed,
  dueTodayCount,
  memoryStatus,
  llmMode,
  isMutating,
  onNavigate,
  onToggleCollapsed,
  onGeneratePlan,
}: {
  activePage: PageView;
  isCollapsed: boolean;
  dueTodayCount: number;
  memoryStatus: MemoryStatus | null;
  llmMode: "gemini" | "fallback";
  isMutating: boolean;
  onNavigate: (page: PageView) => void;
  onToggleCollapsed: () => void;
  onGeneratePlan: () => void;
}) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-main">
          <button
            className="brand-icon"
            onClick={() => onNavigate("dashboard")}
            type="button"
            aria-label="Dashboard'a git"
            title="Dashboard'a git">
            <img
              src={isCollapsed ? compactAppIcon : expandedAppIcon}
              alt=""
            />
          </button>
        </div>
        <button
          className="sidebar-toggle"
          onClick={onToggleCollapsed}
          type="button"
          aria-label={isCollapsed ? "Menüyü genişlet" : "Menüyü daralt"}
          title={isCollapsed ? "Menüyü genişlet" : "Menüyü daralt"}>
          {isCollapsed ? (
            <PanelLeftOpen size={16} />
          ) : (
            <PanelLeftClose size={16} />
          )}
        </button>
      </div>

      <nav className="nav">
        {pageViews.map((page) => {
          const label = navLabel(page);

          return (
            <button
              key={page}
              className={`nav-btn${activePage === page ? " active" : ""}`}
              onClick={() => onNavigate(page)}
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
          title={`Günlük Plan: ${dueTodayCount} sipariş bugün teslim`}>
          <div className="auto-run-header">
            <Clock3 size={15} />
            <span className="sidebar-label">Günlük Plan</span>
          </div>
          <p className="auto-run-count sidebar-label">
            {dueTodayCount} sipariş bugün teslim
          </p>
          <button
            className="btn-outline-green"
            onClick={onGeneratePlan}
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
  );
}
