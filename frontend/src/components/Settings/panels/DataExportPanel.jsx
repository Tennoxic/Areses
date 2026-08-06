import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../../../api/client";
import { showToast } from "../../../utils/toast";
import { confirmDialog } from "../../../utils/dialog";
import { Select } from "../../Ui/Ui";

export function DataExportPanel() {
  const { t } = useTranslation();
  const [importMode, setImportMode] = useState("merge");
  const [importing, setImporting] = useState(false);
  const fileInputRef = useRef(null);

  async function exportData() {
    const data = await api.get("/api/export/my-data");
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `areses-export-${new Date().toISOString().slice(0, 10)}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  function triggerFilePicker() {
    fileInputRef.current?.click();
  }

  async function handleFileSelected(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    let text;
    try {
      text = await file.text();
    } catch {
      showToast(t("settings.importReadError"), "error");
      return;
    }

    let parsed;
    try {
      parsed = JSON.parse(text);
    } catch {
      showToast(t("settings.importInvalidJson"), "error");
      return;
    }

    if (typeof parsed !== "object" || parsed === null || !Array.isArray(parsed.subscriptions)) {
      showToast(t("settings.importInvalidFormat"), "error");
      return;
    }

    if (importMode === "overwrite") {
      const confirmed = await confirmDialog(t("settings.confirmImportOverwrite"), { danger: true });
      if (!confirmed) return;
    }

    setImporting(true);
    try {
      const result = await api.post("/api/import/my-data", { ...parsed, mode: importMode });
      showToast(
        t("settings.importDone", {
          subscriptions: result.subscriptionsCreated,
          folders: result.foldersCreated,
          states: result.articleStatesApplied,
          searches: result.savedSearchesCreated,
        })
      );
      if (result.articleStatesSkipped > 0) {
        showToast(t("settings.importStatesSkipped", { count: result.articleStatesSkipped }), "info");
      }
    } catch (error) {
      showToast(error instanceof ApiError ? error.message : t("settings.importFailed"), "error");
    } finally {
      setImporting(false);
    }
  }

  return (
    <div>
      <h3>{t("settings.dataExport")}</h3>
      <button className="pill-button" onClick={exportData}>{t("settings.exportMyData")}</button>

      <h3 style={{ marginTop: 16 }}>{t("settings.dataImport")}</h3>
      <p style={{ fontSize: 15, color: "var(--muted)", marginTop: -4, marginBottom: 8 }}>
        {t("settings.dataImportHint")}
      </p>
      <label className="settings-field-label" style={{ maxWidth: 220 }}>
        {t("settings.importMode")}
        <Select value={importMode} onChange={(e) => setImportMode(e.target.value)}>
          <option value="merge">{t("settings.importModeMerge")}</option>
          <option value="overwrite">{t("settings.importModeOverwrite")}</option>
        </Select>
      </label>
      <input
        ref={fileInputRef}
        type="file"
        accept="application/json"
        style={{ display: "none" }}
        onChange={handleFileSelected}
      />
      <button className="pill-button" onClick={triggerFilePicker} disabled={importing} style={{ marginTop: 8 }}>
        {importing ? t("settings.importing") : t("settings.importMyData")}
      </button>
    </div>
  );
}
