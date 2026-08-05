import { useCallback, useEffect, useMemo, useState } from "react";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import { AppStateProvider, useAppDispatch, useAppState } from "./context/AppContext";
import { Sidebar } from "./components/Sidebar/Sidebar";
import { AddFeedModal } from "./components/Sidebar/AddFeedModal";
import { ArticleList } from "./components/ArticleList/ArticleList";
import { ReadingPane } from "./components/ReadingPane/ReadingPane";
import { Settings } from "./components/Settings/Settings";
import { ManageFeeds } from "./components/ManageFeeds/ManageFeeds";
import { AppearanceMenu } from "./components/Appearance/AppearanceMenu";
import { ToastHost } from "./components/ToastHost/ToastHost";
import { DialogHost } from "./components/DialogHost/DialogHost";
import { AuthScreen } from "./components/Auth/AuthScreen";
import { GlobalView } from "./views/GlobalView";
import { useArticles } from "./hooks/useArticles";
import { useKeyboardShortcuts } from "./hooks/useKeyboardShortcuts";
import { useOfflineCache } from "./hooks/useOfflineCache";
import { ReadingPreferencesProvider } from "./hooks/useReadingPreferences";
import { useLiveEvents } from "./hooks/useLiveEvents";
import { showToast } from "./utils/toast";
import { useTranslation } from "react-i18next";
import { api } from "./api/client";
import "./i18n";

const VIEWS = ["normal", "reader", "global"];

function ViewSwitcher({ view, onChange, onToggleSidebar, onOpenAppearance }) {
  const { t } = useTranslation();
  return (
    <div className="top-toolbar">
      <button className="pill-button sidebar-toggle-btn" onClick={onToggleSidebar} title={t("sidebar.toggle")}>
        ☰
      </button>
      <div className="view-switcher-group">
        {VIEWS.map((v) => (
          <button
            key={v}
            className={`pill-button ${view === v ? "active" : ""}`}
            onClick={() => onChange(v)}
          >
            {t(`views.${v}`)}
          </button>
        ))}
      </div>
      <button className="pill-button" onClick={onOpenAppearance} title={t("readingPane.displaySettings")}>
        🎨
      </button>
    </div>
  );
}

function Workspace() {
  const { t } = useTranslation();
  const { logout } = useAuth();
  const state = useAppState();
  const dispatch = useAppDispatch();
  const { isOffline } = useOfflineCache();
  const [showAddFeed, setShowAddFeed] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showManageFeeds, setShowManageFeeds] = useState(false);
  const [showAppearance, setShowAppearance] = useState(false);
  const [mobilePane, setMobilePane] = useState("list");
  const [feedsRefreshSignal, setFeedsRefreshSignal] = useState(0);
  const [unreadRefreshSignal, setUnreadRefreshSignal] = useState(0);

  const articlesHook = useArticles(state.activeFilter);

  const bumpFeedsRefresh = useCallback(() => setFeedsRefreshSignal((n) => n + 1), []);
  const bumpUnreadRefresh = useCallback(() => setUnreadRefreshSignal((n) => n + 1), []);

  const handleNewArticle = useCallback(
    (data) => {
      showToast(t("liveEvents.newArticle", { title: data.title }));
      bumpUnreadRefresh();
      const filter = state.activeFilter;
      const noNarrowing =
        !filter.query && !filter.starredOnly && !filter.readLaterOnly && !filter.summariesOnly && !filter.folderId;
      const matchesActiveFeed = filter.sourceId ? filter.sourceId === data.sourceId : true;
      if (noNarrowing && matchesActiveFeed) {
        articlesHook.refetch();
      }
    },
    [bumpUnreadRefresh, t, state.activeFilter, articlesHook]
  );
  useLiveEvents(handleNewArticle);

  useEffect(() => {
    if (state.activeArticleId) setMobilePane("reading");
  }, [state.activeArticleId]);

  function handleArticleChanged(articleId, patch) {
    articlesHook.patchArticle(articleId, patch);
  }

  function findNextUnread() {
    const idx = articlesHook.articles.findIndex((a) => a.id === state.activeArticleId);
    const rest = articlesHook.articles.slice(idx + 1);
    return rest.find((a) => !a.isRead);
  }

  function goToNextUnread() {
    const next = findNextUnread();
    if (next) {
      dispatch({ type: "SET_ACTIVE_ARTICLE", payload: next.id });
      if (!next.isRead) {
        api.postFireAndForget(`/api/articles/${next.id}/read`);
        articlesHook.patchArticle(next.id, { isRead: true });
        bumpUnreadRefresh();
      }
    }
  }

  const shortcutHandlers = useMemo(
    () => ({
      markRead: () => {
        if (state.activeArticleId) {
          api.postFireAndForget(`/api/articles/${state.activeArticleId}/read`);
          articlesHook.patchArticle(state.activeArticleId, { isRead: true });
        }
      },
      toggleStar: () => {
        if (state.activeArticleId) {
          const current = articlesHook.articles.find((a) => a.id === state.activeArticleId);
          if (current) {
            articlesHook.patchArticle(state.activeArticleId, { starred: !current.starred });
          }
          api.postFireAndForget(`/api/articles/${state.activeArticleId}/star`);
        }
      },
      nextArticle: () => {
        const idx = articlesHook.articles.findIndex((a) => a.id === state.activeArticleId);
        const next = articlesHook.articles[idx + 1];
        if (next) dispatch({ type: "SET_ACTIVE_ARTICLE", payload: next.id });
      },
      previousArticle: () => {
        const idx = articlesHook.articles.findIndex((a) => a.id === state.activeArticleId);
        const prev = articlesHook.articles[idx - 1];
        if (prev) dispatch({ type: "SET_ACTIVE_ARTICLE", payload: prev.id });
      },
      openOriginal: () => {
        const current = articlesHook.articles.find((a) => a.id === state.activeArticleId);
        if (current) window.open(current.url, "_blank");
      },
    }),
    [state.activeArticleId, articlesHook, dispatch]
  );
  useKeyboardShortcuts(shortcutHandlers);

  if (state.view === "global") {
    return (
      <div>
        <ViewSwitcher
          view={state.view}
          onChange={(v) => dispatch({ type: "SET_VIEW", payload: v })}
          onToggleSidebar={() => dispatch({ type: "TOGGLE_SIDEBAR" })}
          onOpenAppearance={() => setShowAppearance(true)}
        />
        <GlobalView />
        {showAppearance && <AppearanceMenu onClose={() => setShowAppearance(false)} />}
      </div>
    );
  }

  const isReaderMode = state.view === "reader";

  return (
    <div>
      <ViewSwitcher
        view={state.view}
        onChange={(v) => dispatch({ type: "SET_VIEW", payload: v })}
        onToggleSidebar={() => dispatch({ type: "TOGGLE_SIDEBAR" })}
        onOpenAppearance={() => setShowAppearance(true)}
      />
      {isOffline && <div className="offline-banner">{t("offline.banner")}</div>}
      <div
        className={[
          "app-shell",
          state.sidebarOpen ? "" : "sidebar-collapsed",
          `mobile-pane-${mobilePane}`,
        ].join(" ")}
        style={isReaderMode ? { gridTemplateColumns: "0px 0px 1fr" } : undefined}
      >
        {state.sidebarOpen && (
          <div className="sidebar-overlay-backdrop" onClick={() => dispatch({ type: "TOGGLE_SIDEBAR" })} />
        )}
        <Sidebar
          onAddFeed={() => setShowAddFeed(true)}
          onOpenManageFeeds={() => setShowManageFeeds(true)}
          onOpenSettings={() => setShowSettings(true)}
          refreshSignal={feedsRefreshSignal}
          unreadRefreshSignal={unreadRefreshSignal}
        />
        <ArticleList
          articlesHook={articlesHook}
          onFeedsChanged={bumpFeedsRefresh}
          onUnreadChanged={bumpUnreadRefresh}
        />
        <ReadingPane
          onArticleChanged={handleArticleChanged}
          onNextUnread={goToNextUnread}
          hasNextUnread={Boolean(findNextUnread())}
          searchQuery={state.activeFilter.query}
          onOpenAppearance={() => setShowAppearance(true)}
          onBackToList={() => setMobilePane("list")}
        />
      </div>
      {showAddFeed && (
        <AddFeedModal onClose={() => setShowAddFeed(false)} onAdded={bumpFeedsRefresh} />
      )}
      {showManageFeeds && (
        <ManageFeeds onClose={() => setShowManageFeeds(false)} onFeedsChanged={bumpFeedsRefresh} />
      )}
      {showSettings && (
        <Settings onClose={() => setShowSettings(false)} />
      )}
      {showAppearance && <AppearanceMenu onClose={() => setShowAppearance(false)} />}
      <ToastHost />
      <button
        className="pill-button"
        style={{ position: "fixed", bottom: 12, right: 12 }}
        onClick={logout}
      >
        {t("auth.logout")}
      </button>
    </div>
  );
}

function Gate() {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <AuthScreen />;
  return (
    <AppStateProvider>
      <Workspace />
    </AppStateProvider>
  );
}

export default function App() {
  return (
    <ReadingPreferencesProvider>
      <AuthProvider>
        <Gate />
        <DialogHost />
        <div className="night-light-overlay" />
      </AuthProvider>
    </ReadingPreferencesProvider>
  );
}
