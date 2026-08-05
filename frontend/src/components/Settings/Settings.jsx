import { useTranslation } from "react-i18next";
import { useAuth } from "../../hooks/useAuth";
import { ShortcutRow } from "./panels/ShortcutRow";
import { NotificationsPanel } from "./panels/NotificationsPanel";
import { DataExportPanel } from "./panels/DataExportPanel";
import { AdminPanel } from "./panels/AdminPanel";
import { AIProviderPanel } from "./panels/AIProviderPanel";
import { SmtpSettingsPanel } from "./panels/SmtpSettingsPanel";
import { BackupPanel } from "./panels/BackupPanel";

const SHORTCUT_ACTIONS = ["markRead", "nextArticle", "previousArticle", "toggleStar", "openOriginal"];

export function Settings({ onClose }) {
  const { t } = useTranslation();
  const { user } = useAuth();

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
        <h2>{t("settings.title")}</h2>

        <h3>{t("settings.shortcuts")}</h3>
        <p style={{ fontSize: 16, color: "var(--muted)" }}>{t("settings.shortcutsHint")}</p>
        {SHORTCUT_ACTIONS.map((action) => (
          <ShortcutRow key={action} action={action} />
        ))}

        <NotificationsPanel />
        <DataExportPanel />

        {user?.isAdmin && <AdminPanel />}
        {user?.isAdmin && <AIProviderPanel />}
        {user?.isAdmin && <SmtpSettingsPanel />}
        {user?.isAdmin && <BackupPanel />}

        <div className="modal-actions">
          <button className="pill-button" onClick={onClose}>{t("common.close")}</button>
        </div>
      </div>
    </div>
  );
}
