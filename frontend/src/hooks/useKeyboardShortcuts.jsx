import { useEffect } from "react";

const STORAGE_KEY = "aresesShortcuts";

export function getShortcuts() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

export function setShortcut(action, combo) {
  const shortcuts = getShortcuts();
  shortcuts[action] = combo;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(shortcuts));
}

export function clearShortcut(action) {
  const shortcuts = getShortcuts();
  delete shortcuts[action];
  localStorage.setItem(STORAGE_KEY, JSON.stringify(shortcuts));
}

function comboFromEvent(event) {
  const parts = [];
  if (event.ctrlKey) parts.push("Ctrl");
  if (event.metaKey) parts.push("Meta");
  if (event.altKey) parts.push("Alt");
  if (event.shiftKey) parts.push("Shift");
  parts.push(event.key.length === 1 ? event.key.toUpperCase() : event.key);
  return parts.join("+");
}

export { comboFromEvent };

export function useKeyboardShortcuts(actionHandlers) {
  useEffect(() => {
    function handleKeyDown(event) {
      const target = event.target;
      const isEditable =
        target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable;
      if (isEditable) return;

      const shortcuts = getShortcuts();
      const combo = comboFromEvent(event);
      const action = Object.keys(shortcuts).find((key) => shortcuts[key] === combo);
      if (action && actionHandlers[action]) {
        event.preventDefault();
        actionHandlers[action]();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [actionHandlers]);
}
