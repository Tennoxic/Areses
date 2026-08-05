import { useTranslation } from "react-i18next";
import { api } from "../../../api/client";

export function DataExportPanel() {
  const { t } = useTranslation();

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

  return (
    <div>
      <h3>{t("settings.dataExport")}</h3>
      <button className="pill-button" onClick={exportData}>{t("settings.exportMyData")}</button>
    </div>
  );
}
