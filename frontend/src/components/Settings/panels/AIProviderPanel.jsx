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
  const [apiKeyIsSet, setApiKeyIsSet] = useState(false);
  const [baseUrl, setBaseUrl] = useState("");
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    Promise.all([
      api.get("/api/admin/settings/aiProvider"),
      api.get("/api/admin/settings/aiModel"),
      api.get("/api/admin/settings/aiBaseUrl"),
      api.get("/api/admin/settings/aiApiKey"),
    ]).then(([p, m, b, k]) => {
      if (p.value) setProvider(p.value);
      if (m.value) { setModel(m.value); setSavedModel(m.value); }
      if (b.value) setBaseUrl(b.value);
      setApiKeyIsSet(Boolean(k.isSet));
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
        setApiKeyIsSet(true);
      }
      setSavedModel(model);
      showToast(t("settings.aiSettingsSaved"));
    } finally {
      setSaving(false);
    }
  }

  async function clearApiKey() {
    await api.post("/api/admin/settings", { key: "aiApiKey", value: "" });
    setApiKeyIsSet(false);
    setApiKey("");
    showToast(t("settings.aiApiKeyCleared"));
  }

  async function testConnection() {
    setTesting(true);
    try {
      const result = await api.post("/api/admin/ai/test", {
        provider,
        model,
        apiKey: apiKey || undefined,
        baseUrl: baseUrl || undefined,
      });
      showToast(
        result.success ? t("settings.aiTestSuccess") : t("settings.aiTestFailed", { message: result.message }),
        result.success ? "success" : "error"
      );
    } finally {
      setTesting(false);
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
          placeholder={apiKeyIsSet ? t("settings.aiApiKeySetPlaceholder") : t("settings.aiApiKeyPlaceholder")}
        />
      </label>
      {apiKeyIsSet && (
        <p style={{ fontSize: 15, color: "var(--muted)", marginTop: -8, marginBottom: 0, display: "flex", alignItems: "center", gap: 8 }}>
          {t("settings.aiApiKeyIsSet")}
          <button className="pill-button pill-button-icon" onClick={clearApiKey} title={t("settings.aiApiKeyClear")}>✕</button>
        </p>
      )}
      {provider === "ollama" && (
        <label className="settings-field-label">
          {t("settings.aiBaseUrl")}
          <Input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="http://localhost:11434" />
        </label>
      )}
      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        <button className="pill-button" onClick={save} disabled={saving}>
          {t("settings.aiSaveSettings")}
        </button>
        <button className="pill-button" onClick={testConnection} disabled={testing || (!apiKeyIsSet && !apiKey && provider !== "ollama")}>
          {testing ? t("settings.aiTesting") : t("settings.aiTestConnection")}
        </button>
      </div>
    </div>
  );
}
