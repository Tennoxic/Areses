import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../../api/client";
import { showToast } from "../../../utils/toast";
import { Input, Select } from "../../Ui/Ui";

const AI_PROVIDERS = ["anthropic", "openai", "gemini", "groq", "ollama"];
const AI_MODEL_EXAMPLES = {
  anthropic: "claude-sonnet-5",
  openai: "gpt-5",
  gemini: "gemini-2.5-flash",
  groq: "llama-3.3-70b-versatile",
  ollama: "llama3",
};

export function AIProviderPanel() {
  const { t } = useTranslation();
  const [provider, setProvider] = useState("anthropic");
  const [model, setModel] = useState("");
  const [savedModel, setSavedModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    Promise.all([
      api.get("/api/admin/settings/aiProvider"),
      api.get("/api/admin/settings/aiModel"),
      api.get("/api/admin/settings/aiBaseUrl"),
    ]).then(([p, m, b]) => {
      if (p.value) setProvider(p.value);
      if (m.value) { setModel(m.value); setSavedModel(m.value); }
      if (b.value) setBaseUrl(b.value);
    });
  }, []);

  async function save() {
    setSaving(true);
    try {
      await api.post("/api/admin/settings", { key: "aiProvider", value: provider });
      await api.post("/api/admin/settings", { key: "aiModel", value: model });
      await api.post("/api/admin/settings", { key: "aiBaseUrl", value: baseUrl });
      if (apiKey) {
        await api.post("/api/admin/settings", { key: "aiApiKey", value: apiKey });
        setApiKey("");
      }
      setSavedModel(model);
      showToast(t("settings.aiSettingsSaved"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <h3>{t("settings.aiSummary")}</h3>
      <p style={{ fontSize: 16, color: "var(--muted)", marginTop: -4, marginBottom: 12 }}>
        {t("settings.aiSummaryHint")}
      </p>
      <label className="settings-field-label">
        {t("settings.aiProvider")}
        <Select value={provider} onChange={(e) => setProvider(e.target.value)}>
          {AI_PROVIDERS.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </Select>
      </label>
      <label className="settings-field-label">
        {t("settings.aiModel")}
        <Input value={model} onChange={(e) => setModel(e.target.value)} placeholder={AI_MODEL_EXAMPLES[provider]} />
      </label>
      {savedModel && (
        <p style={{ fontSize: 15, color: "var(--muted)", marginTop: -8, marginBottom: 0 }}>
          {t("settings.aiUsedModel", { model: savedModel })}
        </p>
      )}
      <label className="settings-field-label">
        {t("settings.aiApiKey")}
        <Input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder={t("settings.aiApiKeyPlaceholder")}
        />
      </label>
      {provider === "ollama" && (
        <label className="settings-field-label">
          {t("settings.aiBaseUrl")}
          <Input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="http://localhost:11434" />
        </label>
      )}
      <button className="pill-button" onClick={save} disabled={saving} style={{ marginTop: 8 }}>
        {t("settings.aiSaveSettings")}
      </button>
    </div>
  );
}
