import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, BASE_URL } from "../../api/client";
import { alertDialog, confirmDialog } from "../../utils/dialog";
import { Input, Textarea } from "../Ui/Ui";
import { FeedRow } from "../Settings/panels/FeedRow";

export function ManageFeeds({ onClose, onFeedsChanged }) {
  const { t } = useTranslation();
  const [feeds, setFeeds] = useState([]);
  const [folders, setFolders] = useState([]);
  const [opmlText, setOpmlText] = useState("");
  const [newFolderName, setNewFolderName] = useState("");

  function loadFeeds() {
    api.get("/api/feeds").then(setFeeds);
  }

  useEffect(() => {
    loadFeeds();
    api.get("/api/folders").then(setFolders);
  }, []);

  async function deleteFeed(subscriptionId) {
    await api.delete(`/api/feeds/${subscriptionId}`);
    setFeeds(feeds.filter((f) => f.subscriptionId !== subscriptionId));
    onFeedsChanged();
  }

  async function refreshFeed(subscriptionId) {
    await api.post(`/api/feeds/${subscriptionId}/refresh`);
  }

  async function createFolder(event) {
    event.preventDefault();
    if (!newFolderName) return;
    const folder = await api.post("/api/folders", { name: newFolderName });
    setFolders([...folders, folder]);
    setNewFolderName("");
  }

  async function deleteFolder(folderId) {
    if (!(await confirmDialog(t("settings.confirmDeleteFolder"), { danger: true }))) return;
    await api.delete(`/api/folders/${folderId}`);
    setFolders(folders.filter((f) => f.id !== folderId));
    onFeedsChanged();
  }

  async function importOpml() {
    const result = await api.post("/api/feeds/import-opml", { opml: opmlText });
    onFeedsChanged();
    await alertDialog(t("settings.opmlImported", { count: result.imported }));
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
        <h2>{t("manage.title")}</h2>

        <h3>{t("settings.feeds")}</h3>
        {feeds.map((feed) => (
          <FeedRow
            key={feed.subscriptionId}
            feed={feed}
            onDelete={deleteFeed}
            onRefresh={refreshFeed}
            onUpdated={loadFeeds}
          />
        ))}

        <h3>{t("settings.folders")}</h3>
        <p style={{ fontSize: 16, color: "var(--muted)" }}>{t("settings.foldersHint")}</p>
        {folders.map((folder) => (
          <div
            key={folder.id}
            style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 15, padding: "4px 0", color: "var(--ink)" }}
          >
            <span>{folder.name}</span>
            <button className="pill-button pill-button-icon" onClick={() => deleteFolder(folder.id)}>✕</button>
          </div>
        ))}
        <form onSubmit={createFolder} className="inline-add-row" style={{ marginTop: 8 }}>
          <Input
            value={newFolderName}
            onChange={(e) => setNewFolderName(e.target.value)}
            placeholder={t("sidebar.addFolder")}
            style={{ flex: 1 }}
          />
          <button className="pill-button pill-button-icon" type="submit">+</button>
        </form>

        <h3>OPML</h3>
        <Textarea
          rows={3}
          placeholder="<opml>...</opml>"
          value={opmlText}
          onChange={(e) => setOpmlText(e.target.value)}
        />
        <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
          <button className="pill-button" onClick={importOpml}>{t("settings.importOpml")}</button>
          <a className="pill-button" href={`${BASE_URL}/api/feeds/export-opml`} target="_blank" rel="noreferrer">
            {t("settings.exportOpml")}
          </a>
        </div>

        <div className="modal-actions">
          <button className="pill-button" onClick={onClose}>{t("common.close")}</button>
        </div>
      </div>
    </div>
  );
}
