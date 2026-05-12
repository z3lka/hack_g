import {
  AlertTriangle,
  ClipboardList,
  History,
  Inbox,
  MessageSquareText,
  Search,
  ShoppingBag,
  Sparkles,
  Truck,
  Users,
  Warehouse,
} from "lucide-react";
import type { ReactNode } from "react";
import { searchKindLabels, searchKindOrder } from "../app/search";
import type { SearchResult, SearchResultKind } from "../app/uiTypes";

export function SearchResultsMenu({
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
            <div className="search-group-label">
              {searchKindLabels[group.kind]}
            </div>
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

function searchResultIcon(kind: SearchResultKind): ReactNode {
  const icons: Record<SearchResultKind, ReactNode> = {
    product: <Warehouse size={15} />,
    customer: <Users size={15} />,
    order: <ShoppingBag size={15} />,
    shipment: <Truck size={15} />,
    issue: <AlertTriangle size={15} />,
    message: <MessageSquareText size={15} />,
    thread: <Inbox size={15} />,
    alert: <AlertTriangle size={15} />,
    task: <ClipboardList size={15} />,
    insight: <Sparkles size={15} />,
    memory: <History size={15} />,
  };

  return icons[kind];
}
