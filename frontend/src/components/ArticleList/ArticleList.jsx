import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../api/client";
import { useAppDispatch, useAppState } from "../../context/AppContext";
import { SearchBar } from "../SearchBar/SearchBar";
import { extractHighlightTerms, highlightText } from "../../utils/highlight";
import { promptDialog } from "../../utils/dialog";

const PULL_THRESHOLD = 70;

export function ArticleList({ articlesHook, onFeedsChanged, onUnreadChanged }) {
  const { t } = useTranslation();
  const state = useAppState();
  const dispatch = useAppDispatch();
  const { articles, loading, loadMore, refetch, patchArticle } = articlesHook;
  const sentinelRef = useRef(null);
  const listRef = useRef(null);
  const [pullDistance, setPullDistance] = useState(0);
  const touchStartRef = useRef(null);
  const swipeStateRef = useRef({});

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) loadMore();
      },
      { threshold: 0.1 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [loadMore]);

  function selectArticle(article) {
    dispatch({ type: "SET_ACTIVE_ARTICLE", payload: article.id });
    if (!article.isRead) {
      api.postFireAndForget(`/api/articles/${article.id}/read`);
      patchArticle(article.id, { isRead: true });
      onUnreadChanged();
    }
  }

  async function markAllRead() {
    await api.post("/api/articles/mark-all-read", {
      sourceId: state.activeFilter.sourceId,
      folderId: state.activeFilter.folderId,
    });
    refetch();
    onUnreadChanged();
  }

  async function saveCurrentSearch() {
    const name = await promptDialog(t("sidebar.saveSearchPrompt"));
    if (!name) return;
    await api.post("/api/saved-searches", { name, query: state.activeFilter.query });
    onFeedsChanged();
  }

  async function toggleStarQuick(article, event) {
    event.stopPropagation();
    const nextStarred = !article.starred;
    patchArticle(article.id, { starred: nextStarred });
    await api.postFireAndForget(`/api/articles/${article.id}/star`);
  }

  async function toggleReadLaterFor(articleId) {
    patchArticle(articleId, {
      readLater: !articles.find((a) => a.id === articleId)?.readLater,
    });
    await api.postFireAndForget(`/api/articles/${articleId}/read-later`);
  }

  async function markReadFor(articleId) {
    patchArticle(articleId, { isRead: true });
    await api.postFireAndForget(`/api/articles/${articleId}/read`);
    onUnreadChanged();
  }

  function handleTouchStart(event) {
    if (listRef.current && listRef.current.scrollTop === 0) {
      touchStartRef.current = event.touches[0].clientY;
    } else {
      touchStartRef.current = null;
    }
  }

  function handleTouchMove(event) {
    if (touchStartRef.current === null) return;
    const delta = event.touches[0].clientY - touchStartRef.current;
    if (delta > 0) {
      setPullDistance(Math.min(delta, 120));
    }
  }

  function handleTouchEnd() {
    if (pullDistance > PULL_THRESHOLD) {
      refetch();
    }
    setPullDistance(0);
    touchStartRef.current = null;
  }

  function handleItemTouchStart(articleId, event) {
    swipeStateRef.current[articleId] = event.touches[0].clientX;
  }

  function handleItemTouchEnd(articleId, event) {
    const startX = swipeStateRef.current[articleId];
    if (startX === undefined) return;
    const deltaX = event.changedTouches[0].clientX - startX;
    delete swipeStateRef.current[articleId];
    if (Math.abs(deltaX) < 60) return;
    if (deltaX > 0) {
      markReadFor(articleId);
    } else {
      toggleReadLaterFor(articleId);
    }
  }

  const highlightTerms = extractHighlightTerms(state.activeFilter.query);

  return (
    <div className="article-list pane">
      <div className="article-list-header">
        <SearchBar
          value={state.activeFilter.query}
          onChange={(query) => dispatch({ type: "SET_FILTER", payload: { query } })}
        />
        {state.activeFilter.query && (
          <button className="pill-button" onClick={saveCurrentSearch}>
            ☆
          </button>
        )}
        <button className="pill-button" onClick={markAllRead}>
          {t("articleList.markAllRead")}
        </button>
      </div>

      <div
        className="article-list-scroll"
        ref={listRef}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {pullDistance > 0 && (
          <div className="pull-to-refresh-indicator" style={{ height: pullDistance }}>
            {pullDistance > PULL_THRESHOLD ? t("articleList.releaseToRefresh") : t("articleList.pullToRefresh")}
          </div>
        )}

        {articles.length === 0 && !loading && (
          <div style={{ padding: 24, fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--muted)" }}>
            {t("articleList.empty")}
          </div>
        )}

        {articles.map((article) => (
          <div
            key={article.id}
            className={`article-item ${article.isRead ? "read" : ""} ${state.activeArticleId === article.id ? "active" : ""}`}
            onClick={() => selectArticle(article)}
            onTouchStart={(e) => handleItemTouchStart(article.id, e)}
            onTouchEnd={(e) => handleItemTouchEnd(article.id, e)}
          >
            <p className="article-item-title">
              {highlightTerms.length > 0 ? highlightText(article.title, highlightTerms) : article.title}
            </p>
            <div className="article-item-meta">
              {article.starred && <span>★</span>}
              {article.readLater && <span title={t("readingPane.readLater")}>🕓</span>}
              {article.aiSummary && <span title={t("readingPane.summary")}>✦</span>}
              {article.enclosureUrl && <span title={t("common.podcastBadge")}>🎧</span>}
              {article.readingTimeMinutes && <span>{t("common.readingTimeMinutes", { count: article.readingTimeMinutes })}</span>}
              <span>{new Date(article.publishedAt || article.fetchedAt).toLocaleDateString()}</span>
              <button className="article-item-star" onClick={(e) => toggleStarQuick(article, e)}>
                {article.starred ? "★" : "☆"}
              </button>
            </div>
          </div>
        ))}

        <div ref={sentinelRef} style={{ height: 1 }} />
      </div>
    </div>
  );
}
