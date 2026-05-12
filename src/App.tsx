import { useOperationsController } from "./app/useOperationsController";
import { DraftDrawer } from "./components/DraftDrawer";
import { FloatingAssistant } from "./components/FloatingAssistant";
import { Sidebar } from "./components/Sidebar";
import { Topbar } from "./components/Topbar";
import { CustomersPage } from "./pages/CustomersPage";
import { DashboardPage } from "./pages/DashboardPage";
import { InboxPage } from "./pages/InboxPage";
import { MemoryPage } from "./pages/MemoryPage";
import { OrdersPage } from "./pages/OrdersPage";
import { StockPage } from "./pages/StockPage";

export default function App() {
  const app = useOperationsController();

  if (!app.state) {
    return (
      <main className="loading-screen">
        <div className="loading-spinner" />
        <strong>Sisteme bağlanıyor...</strong>
        <span>{app.apiError || "Veriler yükleniyor, lütfen bekleyin."}</span>
      </main>
    );
  }

  return (
    <div
      className={`app-shell${app.isSidebarCollapsed ? " sidebar-collapsed" : ""}`}>
      <Sidebar
        activePage={app.activePage}
        isCollapsed={app.isSidebarCollapsed}
        dueTodayCount={app.dueToday.length}
        memoryStatus={app.memoryStatus}
        llmMode={app.llmMode}
        isMutating={app.isMutating}
        onNavigate={app.setActivePage}
        onToggleCollapsed={app.toggleSidebar}
        onGeneratePlan={app.handleGeneratePlan}
      />

      <div className="workspace">
        <Topbar
          activePage={app.activePage}
          todayLabel={app.todayLabel}
          globalSearch={app.globalSearch}
          searchResults={app.globalSearchResults}
          isSearchOpen={app.isSearchOpen}
          isNotificationsOpen={app.isNotificationsOpen}
          notificationItems={app.notificationItems}
          searchMenuRef={app.searchMenuRef}
          notificationsMenuRef={app.notificationsMenuRef}
          isMutating={app.isMutating}
          onSearchSubmit={app.handleGlobalSearchSubmit}
          onSearchKeyDown={app.handleGlobalSearchKeyDown}
          onSearchChange={app.handleSearchChange}
          onSearchFocus={app.handleSearchFocus}
          onClearSearch={app.clearSearch}
          onToggleNotifications={app.toggleNotifications}
          onSelectSearchResult={app.selectSearchResult}
          onSelectNotification={app.handleNotificationSelect}
          onResetDemo={app.resetDemo}
        />

        {app.apiError && <div className="error-bar">{app.apiError}</div>}

        {app.activePage === "dashboard" && (
          <DashboardPage
            state={app.state}
            actionableInsights={app.actionableInsights}
            insights={app.insights}
            insightsGeneratedAt={app.insightsGeneratedAt}
            isMutating={app.isMutating}
            onNavigate={app.navigate}
            onInsightAction={app.handleInsightAction}
            onCompleteTask={app.completeTask}
            onResolveInventoryAlert={app.resolveInventoryAlert}
            onNotifyShipment={app.markShipmentNotified}
          />
        )}

        {app.activePage === "stock" && (
          <StockPage
            products={app.state.products}
            alerts={app.state.inventoryAlerts}
            onDraft={app.draftProduct}
            disabled={app.isMutating}
          />
        )}

        {app.activePage === "inbox" && (
          <InboxPage
            threads={app.inboxThreads}
            activeThread={app.activeInboxThread}
            state={app.state}
            connectorHealth={app.connectorHealth}
            disabled={app.isMutating}
            onSelectThread={app.setActiveInboxThreadId}
            onSync={app.handleInboxSync}
            onApproveDraft={app.approveInboxDraft}
          />
        )}

        {app.activePage === "customers" && (
          <CustomersPage
            state={app.state}
            insights={app.insights}
          />
        )}

        {app.activePage === "orders" && (
          <OrdersPage
            state={app.state}
            filter={app.ordersFilter}
            onFilterChange={app.setOrdersFilter}
          />
        )}

        {app.activePage === "memory" && (
          <MemoryPage
            insights={app.insights}
            records={app.memoryRecords}
            memoryStatus={app.memoryStatus}
            llmMode={app.llmMode}
            search={app.memorySearch}
            onSearchChange={app.setMemorySearch}
            memoryInput={app.memoryInput}
            onMemoryInputChange={app.setMemoryInput}
            onMemoryIngest={app.handleMemoryIngest}
            isMutating={app.isMutating}
            actions={app.actions}
          />
        )}
      </div>

      <FloatingAssistant
        chatState={app.chatState}
        mockComposer={app.mockComposer}
        customers={app.state.customers}
        messages={app.messages}
        chatInput={app.chatInput}
        isMutating={app.isMutating}
        chatLogRef={app.chatLogRef}
        onOpenMockComposer={app.openMockComposer}
        onMockComposerChange={app.updateMockComposer}
        onCloseMockComposer={app.closeMockComposer}
        onSendMockComposer={app.sendMockComposerMessage}
        onChatStateChange={app.setChatState}
        onChatInputChange={app.setChatInput}
        onChatSubmit={app.handleChatSubmit}
      />

      {app.draftModal && (
        <DraftDrawer
          draft={app.draftModal}
          notice={app.draftNotice}
          onClose={app.closeDraft}
          onBodyChange={app.updateDraftBody}
          onMockSend={app.mockSendDraft}
          onCopy={app.copyDraft}
        />
      )}
    </div>
  );
}
