import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../../api/client";
import { showToast } from "../../../utils/toast";
import { Input, Checkbox } from "../../Ui/Ui";

export function SmtpSettingsPanel() {
  const { t } = useTranslation();
  const [registrationEnabled, setRegistrationEnabled] = useState(true);
  const [baseUrl, setBaseUrl] = useState("");
  const [smtpHost, setSmtpHost] = useState("");
  const [smtpPort, setSmtpPort] = useState("587");
  const [smtpUser, setSmtpUser] = useState("");
  const [smtpPassword, setSmtpPassword] = useState("");
  const [smtpFrom, setSmtpFrom] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    Promise.all([
      api.get("/api/admin/settings/registrationEnabled"),
      api.get("/api/admin/settings/baseUrl"),
      api.get("/api/admin/settings/smtpHost"),
      api.get("/api/admin/settings/smtpPort"),
      api.get("/api/admin/settings/smtpUser"),
      api.get("/api/admin/settings/smtpFrom"),
    ]).then(([reg, url, host, port, smtpUsr, from]) => {
      setRegistrationEnabled(reg.value !== "false");
      if (url.value) setBaseUrl(url.value);
      if (host.value) setSmtpHost(host.value);
      if (port.value) setSmtpPort(port.value);
      if (smtpUsr.value) setSmtpUser(smtpUsr.value);
      if (from.value) setSmtpFrom(from.value);
    });
  }, []);

  async function save() {
    setSaving(true);
    try {
      await api.post("/api/admin/settings", { key: "registrationEnabled", value: registrationEnabled ? "true" : "false" });
      await api.post("/api/admin/settings", { key: "baseUrl", value: baseUrl });
      await api.post("/api/admin/settings", { key: "smtpHost", value: smtpHost });
      await api.post("/api/admin/settings", { key: "smtpPort", value: smtpPort });
      await api.post("/api/admin/settings", { key: "smtpUser", value: smtpUser });
      await api.post("/api/admin/settings", { key: "smtpFrom", value: smtpFrom });
      if (smtpPassword) {
        await api.post("/api/admin/settings", { key: "smtpPassword", value: smtpPassword });
        setSmtpPassword("");
      }
      showToast(t("settings.smtpSettingsSaved"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <h3>{t("settings.smtp")}</h3>
      <p style={{ fontSize: 16, color: "var(--muted)", marginTop: -4, marginBottom: 12 }}>
        {t("settings.smtpHint")}
      </p>
      <Checkbox checked={registrationEnabled} onChange={(e) => setRegistrationEnabled(e.target.checked)}>
        {t("settings.registrationEnabled")}
      </Checkbox>
      <label className="settings-field-label">
        {t("settings.baseUrl")}
        <Input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="http://localhost:8000" />
      </label>
      <label className="settings-field-label">
        {t("settings.smtpHost")}
        <Input value={smtpHost} onChange={(e) => setSmtpHost(e.target.value)} placeholder="smtp.example.com" />
      </label>
      <label className="settings-field-label">
        {t("settings.smtpPort")}
        <Input value={smtpPort} onChange={(e) => setSmtpPort(e.target.value)} placeholder="587" />
      </label>
      <label className="settings-field-label">
        {t("settings.smtpUser")}
        <Input value={smtpUser} onChange={(e) => setSmtpUser(e.target.value)} />
      </label>
      <label className="settings-field-label">
        {t("settings.smtpPassword")}
        <Input
          type="password"
          value={smtpPassword}
          onChange={(e) => setSmtpPassword(e.target.value)}
          placeholder={t("settings.smtpPasswordPlaceholder")}
        />
      </label>
      <label className="settings-field-label">
        {t("settings.smtpFrom")}
        <Input value={smtpFrom} onChange={(e) => setSmtpFrom(e.target.value)} placeholder="areses@example.com" />
      </label>
      <button className="pill-button" onClick={save} disabled={saving} style={{ marginTop: 8 }}>
        {t("settings.smtpSaveSettings")}
      </button>
    </div>
  );
}
