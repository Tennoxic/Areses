import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../../api/client";
import { showToast } from "../../../utils/toast";
import { confirmDialog } from "../../../utils/dialog";

export function BackupPanel() {
  const { t } = useTranslation();
  const [info, setInfo] = useState(null);

  useEffect(() => {
    api.get("/api/admin/backups").then(setInfo).catch(() => setInfo(null));
  }, []);

  async function toggleEnabled() {
    await api.patch("/api/admin/backups/settings", { backupEnabled: !info.backupEnabled });
    setInfo(await api.get("/api/admin/backups"));
  }

  async function runNow() {
    await api.post("/api/admin/backups/run-now");
    showToast(t("settings.backupDone"));
    setInfo(await api.get("/api/admin/backups"));
  }

  async function deleteBackup(filename) {
    if (!(await confirmDialog(t("settings.confirmDeleteBackup"), { danger: true }))) return;
    await api.delete(`/api/admin/backups/${filename}`);
    setInfo(await api.get("/api/admin/backups"));
  }

  if (!info) return null;

  return (
    <div>
      <h3>{t("settings.backups")}</h3>
      <button className={`pill-button ${info.backupEnabled ? "active" : ""}`} onClick={toggleEnabled}>
        {info.backupEnabled ? t("settings.backupAutoOn") : t("settings.backupAutoOff")}
      </button>{" "}
      <button className="pill-button" onClick={runNow}>{t("settings.backupRunNow")}</button>
      <ul style={{ fontSize: 14, marginTop: 8, color: "var(--ink)", listStyle: "none", padding: 0 }}>
        {info.backups.slice(0, 5).map((backup) => (
          <li key={backup.filename} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "4px 0" }}>
            <span>{backup.filename} · {(backup.sizeBytes / 1024).toFixed(0)} KB</span>
            <button className="pill-button pill-button-icon" onClick={() => deleteBackup(backup.filename)}>✕</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
