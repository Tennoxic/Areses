import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../../api/client";
import { showToast } from "../../../utils/toast";
import { Input, Checkbox, Slider } from "../../Ui/Ui";

export function FeedRow({ feed, onDelete, onRefresh, onUpdated }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const [autoReadPattern, setAutoReadPattern] = useState(feed.autoReadPattern || "");
  const [notifyEnabled, setNotifyEnabled] = useState(feed.notifyEnabled);
  const [summarizeEnabled, setSummarizeEnabled] = useState(feed.summarizeEnabled);
  const [fetchIntervalMinutes, setFetchIntervalMinutes] = useState(feed.fetchIntervalMinutes || 60);
  const [saving, setSaving] = useState(false);
  const [patternError, setPatternError] = useState("");

  async function save() {
    setSaving(true);
    setPatternError("");
    try {
      await api.patch(`/api/feeds/${feed.subscriptionId}`, {
        autoReadPattern: autoReadPattern,
        notifyEnabled: notifyEnabled,
        summarizeEnabled: summarizeEnabled,
        fetchIntervalMinutes: fetchIntervalMinutes,
      });
      onUpdated();
      showToast(t("settings.feedUpdated"));
    } catch (err) {
      setPatternError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{ borderBottom: "1px solid var(--line)", padding: "4px 0" }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 15 }}>
        <span onClick={() => setExpanded(!expanded)} style={{ cursor: "pointer", color: "var(--ink)" }}>
          {feed.customName || feed.url} {feed.isBroken && <span className="feed-health-error">⚠</span>}
        </span>
        <span>
          <button className="pill-button pill-button-icon" onClick={() => setExpanded(!expanded)}>⚙</button>{" "}
          <button className="pill-button pill-button-icon" onClick={() => onRefresh(feed.subscriptionId)}>
            <span className="icon-glyph-refresh">↻</span>
          </button>{" "}
          <button className="pill-button pill-button-icon" onClick={() => onDelete(feed.subscriptionId)}>✕</button>
        </span>
      </div>
      {feed.lastErrorMessage && (
        <div className="feed-health-error">{feed.lastErrorMessage}</div>
      )}
      {expanded && (
        <div style={{ padding: "12px 0", display: "flex", flexDirection: "column", gap: 12 }}>
          <label className="settings-field-label">
            {t("settings.autoReadPattern")}
            <Input
              value={autoReadPattern}
              onChange={(e) => setAutoReadPattern(e.target.value)}
              placeholder={t("settings.autoReadPatternPlaceholder")}
            />
          </label>
          <label className="settings-field-label">
            {t("settings.fetchInterval")}
            <Slider
              min={5}
              max={360}
              step={5}
              value={fetchIntervalMinutes}
              unit={t("settings.minutesUnit")}
              onChange={(e) => setFetchIntervalMinutes(Number(e.target.value))}
            />
          </label>
          <Checkbox
            checked={notifyEnabled}
            onChange={(e) => setNotifyEnabled(e.target.checked)}
          >
            {t("settings.notifyEnabled")}
          </Checkbox>
          <Checkbox
            checked={summarizeEnabled}
            onChange={(e) => setSummarizeEnabled(e.target.checked)}
          >
            {t("settings.summarizeEnabled")}
          </Checkbox>
          {patternError && <div className="auth-error">{patternError}</div>}
          <button className="pill-button active" onClick={save} disabled={saving} style={{ alignSelf: "flex-start" }}>
            {t("common.save")}
          </button>
        </div>
      )}
    </div>
  );
}
