import { CheckCircle2 } from "lucide-react";
import type { ReactNode } from "react";

export function MetricCard({
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

export function SegCtrl({
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

export function StatusPill({ status }: { status: string }) {
  return (
    <span
      className={`pill ${status}`}
      role="status">
      {status}
    </span>
  );
}

export function PriorityTag({ priority }: { priority: string }) {
  return <span className={`priority ${priority}`}>{priority}</span>;
}

export function Empty({ text, compact }: { text: string; compact?: boolean }) {
  return (
    <div className={`empty ${compact ? "compact" : ""}`}>
      <CheckCircle2 size={20} />
      <span>{text}</span>
    </div>
  );
}
