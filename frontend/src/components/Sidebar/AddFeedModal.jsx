import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../api/client";
import { showToast } from "../../utils/toast";
import { Input } from "../Ui/Ui";

export function AddFeedModal({ onClose, onAdded }) {
  const { t } = useTranslation();
  const [url, setUrl] = useState("");
  const [showAuth, setShowAuth] = useState(false);
  const [httpUsername, setHttpUsername] = useState("");
  const [httpPassword, setHttpPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [preview, setPreview] = useState(null);

  async function handlePreview() {
    if (!url) return;
    setPreviewing(true);
    setError("");
    setPreview(null);
    try {
      const result = await api.post("/api/feeds/preview", {
        url,
        httpUsername: httpUsername || undefined,
        httpPassword: httpPassword || undefined,
      });
      setPreview(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setPreviewing(false);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const result = await api.post("/api/feeds", {
        url,
        httpUsername: httpUsername || undefined,
        httpPassword: httpPassword || undefined,
      });
      if (result.alreadyInCatalog) {
        showToast(t("sidebar.feedAlreadyKnownToast"), "info");
      }
      onAdded(result);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>{t("sidebar.addFeed")}</h2>
        <form onSubmit={handleSubmit}>
          <label className="settings-field-label">
            Feed URL
            <Input
              type="url"
              required
              value={url}
              onChange={(e) => {
                setUrl(e.target.value);
                setPreview(null);
              }}
              placeholder="https://example.com/feed.xml"
            />
          </label>

          <button
            type="button"
            className="switch-mode"
            style={{ marginTop: 12, display: "block" }}
            onClick={() => setShowAuth(!showAuth)}
          >
            {t("sidebar.protectedFeed")}
          </button>

          {showAuth && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 8 }}>
              <label className="settings-field-label">
                {t("auth.username")}
                <Input value={httpUsername} onChange={(e) => setHttpUsername(e.target.value)} />
              </label>
              <label className="settings-field-label">
                {t("auth.password")}
                <Input
                  type="password"
                  value={httpPassword}
                  onChange={(e) => setHttpPassword(e.target.value)}
                />
              </label>
            </div>
          )}

          <button
            type="button"
            className="pill-button"
            style={{ marginTop: 12 }}
            onClick={handlePreview}
            disabled={!url || previewing}
          >
            {previewing ? t("sidebar.previewLoading") : t("sidebar.previewFeed")}
          </button>

          {preview && (
            <div className="feed-preview">
              {preview.alreadyInCatalog && (
                <div className="feed-preview-warning">{t("sidebar.feedAlreadyKnown")}</div>
              )}
              <div className="feed-preview-title">{preview.feedTitle || preview.resolvedUrl}</div>
              <ul className="feed-preview-entries">
                {preview.entries.map((entry, index) => (
                  <li key={index}>{entry.title}</li>
                ))}
              </ul>
            </div>
          )}

          {error && <div className="auth-error">{error}</div>}
          <div className="modal-actions">
            <button type="button" className="pill-button" onClick={onClose}>{t("sidebar.cancel")}</button>
            <button type="submit" className="pill-button active" disabled={submitting}>
              {t("sidebar.addFeed")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
