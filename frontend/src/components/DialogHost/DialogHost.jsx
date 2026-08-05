import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Input } from "../Ui/Ui";

export function DialogHost() {
  const { t } = useTranslation();
  const [dialog, setDialog] = useState(null);
  const [value, setValue] = useState("");

  useEffect(() => {
    function handleDialog(event) {
      setDialog(event.detail);
      setValue(event.detail.defaultValue || "");
    }
    window.addEventListener("areses:dialog", handleDialog);
    return () => window.removeEventListener("areses:dialog", handleDialog);
  }, []);

  function resolve(resultValue) {
    window.dispatchEvent(
      new CustomEvent("areses:dialog-result", { detail: { id: dialog.id, value: resultValue } })
    );
    setDialog(null);
  }

  if (!dialog) return null;

  return (
    <div className="dialog-overlay" onClick={() => resolve(dialog.kind === "prompt" ? null : false)}>
      <div className="dialog-box" onClick={(e) => e.stopPropagation()}>
        <p className="dialog-message">{dialog.message}</p>

        {dialog.kind === "prompt" && (
          <Input
            autoFocus
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && resolve(value)}
            className="dialog-input"
          />
        )}

        <div className="dialog-actions">
          {dialog.kind !== "alert" && (
            <button className="pill-button" onClick={() => resolve(dialog.kind === "prompt" ? null : false)}>
              {dialog.cancelLabel || t("dialog.cancel")}
            </button>
          )}
          <button
            className={`pill-button active ${dialog.danger ? "pill-button-danger" : ""}`}
            onClick={() => resolve(dialog.kind === "prompt" ? value : true)}
            autoFocus={dialog.kind !== "prompt"}
          >
            {dialog.confirmLabel || (dialog.kind === "alert" ? t("dialog.ok") : t("dialog.confirm"))}
          </button>
        </div>
      </div>
    </div>
  );
}
