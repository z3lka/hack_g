import { Bell, RefreshCw, Search, X } from "lucide-react";
import type {
  FormEventHandler,
  KeyboardEventHandler,
  RefObject,
} from "react";
import { pageTitle } from "../app/navigation";
import type { NotificationItem, PageView, SearchResult } from "../app/uiTypes";
import { NotificationPanel } from "./NotificationPanel";
import { SearchResultsMenu } from "./SearchResultsMenu";

export function Topbar({
  activePage,
  todayLabel,
  globalSearch,
  searchResults,
  isSearchOpen,
  isNotificationsOpen,
  notificationItems,
  searchMenuRef,
  notificationsMenuRef,
  isMutating,
  onSearchSubmit,
  onSearchKeyDown,
  onSearchChange,
  onSearchFocus,
  onClearSearch,
  onToggleNotifications,
  onSelectSearchResult,
  onSelectNotification,
  onResetDemo,
}: {
  activePage: PageView;
  todayLabel: string;
  globalSearch: string;
  searchResults: SearchResult[];
  isSearchOpen: boolean;
  isNotificationsOpen: boolean;
  notificationItems: NotificationItem[];
  searchMenuRef: RefObject<HTMLDivElement | null>;
  notificationsMenuRef: RefObject<HTMLDivElement | null>;
  isMutating: boolean;
  onSearchSubmit: FormEventHandler<HTMLFormElement>;
  onSearchKeyDown: KeyboardEventHandler<HTMLInputElement>;
  onSearchChange: (value: string) => void;
  onSearchFocus: () => void;
  onClearSearch: () => void;
  onToggleNotifications: () => void;
  onSelectSearchResult: (result: SearchResult) => void;
  onSelectNotification: (item: NotificationItem) => void;
  onResetDemo: () => void;
}) {
  return (
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
            onSubmit={onSearchSubmit}>
            <Search size={15} />
            <input
              value={globalSearch}
              onChange={(event) => onSearchChange(event.target.value)}
              onFocus={onSearchFocus}
              onKeyDown={onSearchKeyDown}
              placeholder="Ürün, müşteri, sipariş, takip ara..."
              aria-label="Genel arama"
            />
            {globalSearch && (
              <button
                className="search-clear"
                onClick={onClearSearch}
                type="button"
                aria-label="Aramayı temizle">
                <X size={14} />
              </button>
            )}
          </form>
          {isSearchOpen && globalSearch.trim() && (
            <SearchResultsMenu
              results={searchResults}
              query={globalSearch}
              onSelect={onSelectSearchResult}
            />
          )}
        </div>
        <div
          className="notification-menu"
          ref={notificationsMenuRef}>
          <button
            className="icon-btn notification-trigger"
            onClick={onToggleNotifications}
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
              onSelect={onSelectNotification}
            />
          )}
        </div>
        <button
          className="btn-outline"
          onClick={onResetDemo}
          disabled={isMutating}
          type="button">
          <RefreshCw size={14} />
          Sıfırla
        </button>
      </div>
    </header>
  );
}
