import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../api/client";
import { useAppDispatch, useAppState } from "../../context/AppContext";
import { showToast } from "../../utils/toast";
import { confirmDialog } from "../../utils/dialog";
import { Checkbox, Select } from "../Ui/Ui";

const EMPTY_FILTER = { sourceId: null, folderId: null, unreadOnly: false, starredOnly: false, readLaterOnly: false, summariesOnly: false, query: "" };
const COLLAPSED_FOLDERS_KEY = "areses.collapsedFolderIds";

function loadCollapsedFolderIds() {
  try {
    const raw = localStorage.getItem(COLLAPSED_FOLDERS_KEY);
    return raw ? new Set(JSON.parse(raw)) : new Set();
  } catch {
    return new Set();
  }
}

function saveCollapsedFolderIds(ids) {
  try {
    localStorage.setItem(COLLAPSED_FOLDERS_KEY, JSON.stringify([...ids]));
  } catch {
    /* localStorage unavailable, collapse state just won't persist */
  }
}

export function Sidebar({ onAddFeed, onOpenManageFeeds, onOpenSettings, refreshSignal, unreadRefreshSignal }) {
  const { t } = useTranslation();
  const state = useAppState();
  const dispatch = useAppDispatch();
  const [feeds, setFeeds] = useState([]);
  const [folders, setFolders] = useState([]);
  const [savedSearches, setSavedSearches] = useState([]);
  const [bulkMode, setBulkMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [collapsedFolderIds, setCollapsedFolderIds] = useState(loadCollapsedFolderIds);
  const [draggingSubscriptionId, setDraggingSubscriptionId] = useState(null);
  const [dropTargetFolderId, setDropTargetFolderId] = useState(undefined);

  useEffect(() => {
    api.get("/api/feeds").then(setFeeds).catch(() => showToast(t("sidebar.loadFeedsError"), "error"));
    api.get("/api/folders").then(setFolders).catch(() => showToast(t("sidebar.loadFoldersError"), "error"));
    api.get("/api/saved-searches").then(setSavedSearches).catch(() => showToast(t("sidebar.loadSavedSearchesError"), "error"));
  }, [refreshSignal]);

  useEffect(() => {
    if (unreadRefreshSignal === 0) return;
    api.get("/api/feeds").then(setFeeds).catch(() => showToast(t("sidebar.loadFeedsError"), "error"));
  }, [unreadRefreshSignal]);

  function selectFilter(payload) {
    dispatch({ type: "SET_FILTER", payload: { ...EMPTY_FILTER, ...payload } });
  }

  function isActive(predicate) {
    return predicate(state.activeFilter) ? "active" : "";
  }

  function toggleSelected(subscriptionId, event) {
    event.stopPropagation();
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(subscriptionId)) next.delete(subscriptionId);
      else next.add(subscriptionId);
      return next;
    });
  }

  async function bulkDelete() {
    if (selectedIds.size === 0) return;
    if (!(await confirmDialog(t("sidebar.confirmBulkDelete", { count: selectedIds.size }), { danger: true }))) return;
    await api.post("/api/feeds/bulk-delete", { subscriptionIds: [...selectedIds] });
    showToast(t("sidebar.bulkDeleted", { count: selectedIds.size }));
    setSelectedIds(new Set());
    setBulkMode(false);
    api.get("/api/feeds").then(setFeeds);
  }

  async function deleteSavedSearch(event, savedSearchId) {
    event.stopPropagation();
    if (!(await confirmDialog(t("sidebar.confirmDeleteSavedSearch"), { danger: true }))) return;
    await api.delete(`/api/saved-searches/${savedSearchId}`);
    setSavedSearches((current) => current.filter((s) => s.id !== savedSearchId));
  }

  async function bulkMoveTo(folderId) {
    if (selectedIds.size === 0) return;
    await api.post("/api/feeds/bulk-move", { subscriptionIds: [...selectedIds], folderId: folderId });
    showToast(t("sidebar.bulkMoved", { count: selectedIds.size }));
    setSelectedIds(new Set());
    setBulkMode(false);
    api.get("/api/feeds").then(setFeeds);
  }

  async function toggleHidden(event, subscriptionId, currentlyHidden) {
    event.stopPropagation();
    await api.patch(`/api/feeds/${subscriptionId}`, { hidden: !currentlyHidden });
    setFeeds(feeds.map((f) => (f.subscriptionId === subscriptionId ? { ...f, hidden: !currentlyHidden } : f)));
  }

  async function moveFeedToFolder(subscriptionId, folderId) {
    await api.post("/api/feeds/bulk-move", { subscriptionIds: [subscriptionId], folderId });
    setFeeds(feeds.map((f) => (f.subscriptionId === subscriptionId ? { ...f, folderId } : f)));
    const folderName = folderId ? folders.find((f) => f.id === folderId)?.name : null;
    showToast(folderName ? t("sidebar.feedMovedToFolder", { folder: folderName }) : t("sidebar.feedMovedToRoot"));
  }

  function handleFeedDragStart(event, subscriptionId) {
    event.dataTransfer.setData("text/plain", String(subscriptionId));
    event.dataTransfer.effectAllowed = "move";
    setDraggingSubscriptionId(subscriptionId);
  }

  function handleFeedDragEnd() {
    setDraggingSubscriptionId(null);
    setDropTargetFolderId(undefined);
  }

  function handleFolderDragEnter(event, folderId) {
    event.preventDefault();
    setDropTargetFolderId(folderId);
  }

  function handleFolderDragLeave(event, folderId) {
    if (event.currentTarget.contains(event.relatedTarget)) return;
    setDropTargetFolderId((current) => (current === folderId ? undefined : current));
  }

  function handleFolderDrop(event, folderId) {
    event.preventDefault();
    setDropTargetFolderId(undefined);
    setDraggingSubscriptionId(null);
    const subscriptionId = Number(event.dataTransfer.getData("text/plain"));
    if (!subscriptionId) return;
    moveFeedToFolder(subscriptionId, folderId);
  }

  function toggleFolderCollapsed(folderId) {
    setCollapsedFolderIds((current) => {
      const next = new Set(current);
      if (next.has(folderId)) next.delete(folderId);
      else next.add(folderId);
      saveCollapsedFolderIds(next);
      return next;
    });
  }

  function renderFeedItem(feed, indent) {
    return (
      <div
        key={feed.subscriptionId}
        className={`sidebar-item ${feed.isBroken ? "broken" : ""} ${draggingSubscriptionId === feed.subscriptionId ? "dragging" : ""} ${isActive((f) => f.sourceId === feed.sourceId)}`}
        style={{ ...(indent ? { paddingLeft: 32 } : undefined), opacity: feed.hidden ? 0.5 : 1 }}
        onClick={() => (bulkMode ? null : selectFilter({ sourceId: feed.sourceId }))}
        title={feed.lastErrorMessage || undefined}
        draggable
        onDragStart={(e) => handleFeedDragStart(e, feed.subscriptionId)}
        onDragEnd={handleFeedDragEnd}
      >
        {bulkMode && (
          <Checkbox
            checked={selectedIds.has(feed.subscriptionId)}
            onChange={(e) => toggleSelected(feed.subscriptionId, e)}
          />
        )}
        <span className="drag-handle" title={t("sidebar.dragToMove")} aria-hidden="true">⠿</span>
        <span>{feed.customName || feed.url}</span>
        {feed.unreadCount > 0 && <span className="count">{feed.unreadCount}</span>}
        <button
          className="pill-button pill-button-icon"
          onClick={(e) => toggleHidden(e, feed.subscriptionId, feed.hidden)}
          title={feed.hidden ? t("sidebar.showFeed") : t("sidebar.hideFeed")}
        >
          {feed.hidden ? "🙈" : "👁"}
        </button>
      </div>
    );
  }

  const rootFeeds = feeds.filter((f) => !f.folderId);
  const feedsBySourceFolder = new Map();
  for (const feed of feeds) {
    if (!feed.folderId) continue;
    if (!feedsBySourceFolder.has(feed.folderId)) feedsBySourceFolder.set(feed.folderId, []);
    feedsBySourceFolder.get(feed.folderId).push(feed);
  }
  const childFoldersByParent = new Map();
  for (const folder of folders) {
    const key = folder.parentId ?? null;
    if (!childFoldersByParent.has(key)) childFoldersByParent.set(key, []);
    childFoldersByParent.get(key).push(folder);
  }

  function renderFolder(folder, depth, visited) {
    if (visited.has(folder.id)) return null;
    const nextVisited = new Set(visited).add(folder.id);
    const children = childFoldersByParent.get(folder.id) || [];
    const folderFeeds = feedsBySourceFolder.get(folder.id) || [];
    const isCollapsed = collapsedFolderIds.has(folder.id);
    const hasChildren = children.length > 0 || folderFeeds.length > 0;
    return (
      <div key={folder.id}>
        <div
          className={`sidebar-item folder-row ${isActive((f) => f.folderId === folder.id)} ${dropTargetFolderId === folder.id ? "drop-target" : ""}`}
          style={{ paddingLeft: 16 + depth * 16 }}
          onClick={() => (bulkMode ? null : selectFilter({ folderId: folder.id }))}
          onDragEnter={(e) => handleFolderDragEnter(e, folder.id)}
          onDragOver={(e) => e.preventDefault()}
          onDragLeave={(e) => handleFolderDragLeave(e, folder.id)}
          onDrop={(e) => handleFolderDrop(e, folder.id)}
        >
          <span
            className={`folder-twisty ${isCollapsed ? "collapsed" : ""}`}
            onClick={(e) => {
              e.stopPropagation();
              if (hasChildren) toggleFolderCollapsed(folder.id);
            }}
            aria-hidden="true"
          >
            {hasChildren ? "▾" : ""}
          </span>
          <span className="folder-name">{folder.name}</span>
        </div>
        {!isCollapsed && folderFeeds.map((feed) => (
          <div key={feed.subscriptionId} style={{ paddingLeft: depth * 16 }}>
            {renderFeedItem(feed, true)}
          </div>
        ))}
        {!isCollapsed && children.map((child) => renderFolder(child, depth + 1, nextVisited))}
      </div>
    );
  }

  const rootFolders = childFoldersByParent.get(null) || [];

  return (
    <div className="sidebar pane">
      <div className="sidebar-brand">{t("app.name")}</div>

      <div className="sidebar-section">
        <div
          className={`sidebar-item ${isActive((f) => !f.sourceId && !f.folderId && !f.unreadOnly && !f.starredOnly && !f.readLaterOnly && !f.summariesOnly)}`}
          onClick={() => selectFilter({})}
        >
          <span>{t("sidebar.all")}</span>
        </div>
        <div className={`sidebar-item ${isActive((f) => f.unreadOnly)}`} onClick={() => selectFilter({ unreadOnly: true })}>
          <span>{t("sidebar.unread")}</span>
        </div>
        <div className={`sidebar-item ${isActive((f) => f.starredOnly)}`} onClick={() => selectFilter({ starredOnly: true })}>
          <span>{t("sidebar.starred")}</span>
        </div>
        <div className={`sidebar-item ${isActive((f) => f.readLaterOnly)}`} onClick={() => selectFilter({ readLaterOnly: true })}>
          <span>{t("sidebar.readLater")}</span>
        </div>
        <div className={`sidebar-item ${isActive((f) => f.summariesOnly)}`} onClick={() => selectFilter({ summariesOnly: true })}>
          <span>{t("sidebar.summaries")}</span>
        </div>
      </div>

      <div className="sidebar-section">
        <div
          className={`sidebar-section-title ${dropTargetFolderId === null ? "drop-target" : ""}`}
          style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}
          onDragEnter={(e) => handleFolderDragEnter(e, null)}
          onDragOver={(e) => e.preventDefault()}
          onDragLeave={(e) => handleFolderDragLeave(e, null)}
          onDrop={(e) => handleFolderDrop(e, null)}
        >
          <span>{t("settings.feeds")}</span>
          <button
            className="pill-button"
            onClick={() => { setBulkMode(!bulkMode); setSelectedIds(new Set()); }}
          >
            {bulkMode ? t("sidebar.cancel") : t("sidebar.select")}
          </button>
        </div>

        {bulkMode && (
          <div className="bulk-toolbar">
            <span>{t("sidebar.selectedCount", { count: selectedIds.size })}</span>
            <Select
              value=""
              onChange={(e) => {
                if (!e.target.value) return;
                bulkMoveTo(e.target.value === "none" ? null : Number(e.target.value));
              }}
            >
              <option value="" disabled>{t("sidebar.bulkMoveTo")}</option>
              <option value="none">{t("sidebar.noFolder")}</option>
              {folders.map((folder) => (
                <option key={folder.id} value={folder.id}>{folder.name}</option>
              ))}
            </Select>
            <button className="pill-button" onClick={bulkDelete}>{t("sidebar.bulkDelete")}</button>
          </div>
        )}

        {rootFeeds.map((feed) => renderFeedItem(feed, false))}
        {rootFolders.map((folder) => renderFolder(folder, 0, new Set()))}
      </div>

      <div className="sidebar-section">
        <div className="sidebar-item" onClick={onAddFeed}>
          <span>+ {t("sidebar.addFeed")}</span>
        </div>
        <div className="sidebar-item" onClick={onOpenManageFeeds}>
          <span>{t("manage.title")}</span>
        </div>
        <div className="sidebar-item" onClick={onOpenSettings}>
          <span>{t("sidebar.settings")}</span>
        </div>
      </div>

      {savedSearches.length > 0 && (
        <div className="sidebar-section">
          <div className="sidebar-section-title">{t("sidebar.savedSearches")}</div>
          {savedSearches.map((saved) => (
            <div
              key={saved.id}
              className={`sidebar-item ${isActive((f) => f.query === saved.query)}`}
              onClick={() => selectFilter({ query: saved.query })}
              style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}
            >
              <span>{saved.name}</span>
              <button
                className="pill-button pill-button-icon"
                onClick={(e) => deleteSavedSearch(e, saved.id)}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
