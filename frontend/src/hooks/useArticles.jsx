import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/client";

const PAGE_SIZE = 30;

function buildQuery(filter, beforeId) {
  const params = new URLSearchParams();
  if (filter.sourceId) params.set("sourceId", filter.sourceId);
  if (filter.folderId) params.set("folderId", filter.folderId);
  if (filter.unreadOnly) params.set("unreadOnly", "true");
  if (filter.starredOnly) params.set("starredOnly", "true");
  if (filter.readLaterOnly) params.set("readLaterOnly", "true");
  if (filter.summariesOnly) params.set("hasSummaryOnly", "true");
  if (filter.query) params.set("q", filter.query);
  if (beforeId) params.set("beforeId", beforeId);
  params.set("limit", String(PAGE_SIZE));
  return params.toString();
}

function matchesFilter(article, filter) {
  if (filter.unreadOnly && article.isRead) return false;
  if (filter.starredOnly && !article.starred) return false;
  if (filter.readLaterOnly && !article.readLater) return false;
  if (filter.summariesOnly && !article.aiSummary) return false;
  return true;
}

export function useArticles(filter) {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const cacheRef = useRef(new Map());

  const filterKey = JSON.stringify(filter);

  const load = useCallback(
    async (beforeId) => {
      setLoading(true);
      try {
        const query = buildQuery(filter, beforeId);
        const data = await api.get(`/api/articles?${query}`);
        setArticles((prev) => {
          const next = beforeId ? [...prev, ...data] : data;
          cacheRef.current.set(filterKey, { articles: next, hasMore: data.length === PAGE_SIZE });
          return next;
        });
        setHasMore(data.length === PAGE_SIZE);
      } finally {
        setLoading(false);
      }
    },
    [filter, filterKey]
  );

  useEffect(() => {
    const cached = cacheRef.current.get(filterKey);
    if (cached) {
      setArticles(cached.articles);
      setHasMore(cached.hasMore);
    } else {
      load(null);
    }
  }, [filterKey]);

  const loadMore = useCallback(() => {
    if (loading || !hasMore || articles.length === 0) return;
    load(articles[articles.length - 1].id);
  }, [loading, hasMore, articles, load]);

  const refetch = useCallback(() => {
    cacheRef.current.clear();
    load(null);
  }, [load]);

  const patchArticle = useCallback(
    (articleId, patch) => {
      setArticles((prev) => {
        const next = prev
          .map((article) => (article.id === articleId ? { ...article, ...patch } : article))
          .filter((article) => matchesFilter(article, filter));
        cacheRef.current.set(filterKey, { articles: next, hasMore });
        return next;
      });
      for (const [key, entry] of cacheRef.current.entries()) {
        if (key === filterKey) continue;
        let entryFilter;
        try {
          entryFilter = JSON.parse(key);
        } catch {
          continue;
        }
        const patchedArticles = entry.articles
          .map((article) => (article.id === articleId ? { ...article, ...patch } : article))
          .filter((article) => matchesFilter(article, entryFilter));
        cacheRef.current.set(key, { articles: patchedArticles, hasMore: entry.hasMore });
      }
    },
    [filterKey, filter, hasMore]
  );

  return { articles, loading, hasMore, loadMore, refetch, patchArticle };
}
