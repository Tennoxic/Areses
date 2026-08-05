import { useState } from "react";
import { useTranslation } from "react-i18next";
import { clearShortcut, comboFromEvent, getShortcuts, setShortcut } from "../../../hooks/useKeyboardShortcuts";

export function ShortcutRow({ action }) {
  const { t } = useTranslation();
  const [combo, setCombo] = useState(getShortcuts()[action] || "");
  const [capturing, setCapturing] = useState(false);

  function handleKeyDown(event) {
    event.preventDefault();
    if (event.key === "Escape") {
      clearShortcut(action);
      setCombo("");
      setCapturing(false);
      return;
    }
    const value = comboFromEvent(event);
    setShortcut(action, value);
    setCombo(value);
    setCapturing(false);
  }

  function handleClear(e) {
    e.stopPropagation();
    clearShortcut(action);
    setCombo("");
  }

  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid var(--stone)" }}>
      <span style={{ fontFamily: "var(--font-mono)", fontSize: 14, color: "var(--ink)" }}>{t(`settings.shortcutAction.${action}`)}</span>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <input
          readOnly
          value={capturing ? "…" : combo}
          placeholder="—"
          onFocus={() => setCapturing(true)}
          onKeyDown={handleKeyDown}
          className="shortcut-input"
        />
        <button
          onClick={handleClear}
          title={t("common.clearShortcut")}
          style={{
            width: 18, height: 18, borderRadius: 0,
            background: combo ? "var(--danger)" : "var(--stone-dark)",
            border: "none", color: "white", fontSize: 11,
            display: "flex", alignItems: "center", justifyContent: "center",
            cursor: "pointer", flexShrink: 0, lineHeight: 1,
            opacity: combo ? 1 : 0.35,
            transition: "opacity 0.12s ease, background 0.12s ease",
          }}
          aria-label={t("common.clearShortcut")}
        >
          ✕
        </button>
      </div>
    </div>
  );
}
