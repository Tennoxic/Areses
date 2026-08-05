import { createContext, useCallback, useContext, useEffect, useState } from "react";

const STORAGE_KEY = "aresesReadingPrefs";

const DEFAULTS = {
  fontSize: 18,
  fontFamily: "sans",
  lineHeight: 1.6,
  theme: "sepia",
  nightLight: 0,
};

const NIGHT_LIGHT_MAX_OPACITY = 0.32;

const FONT_STACKS = {
  sans:  "'IBM Plex Sans', system-ui, sans-serif",
  serif: "Georgia, 'Times New Roman', serif",
  mono:  "'IBM Plex Mono', ui-monospace, monospace",
  retro: "'Share Tech Mono', 'IBM Plex Mono', monospace",
};

function readStored() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULTS;
    const stored = JSON.parse(raw);
    if (stored.fontFamily === "system") stored.fontFamily = "sans";
    if (stored.fontFamily === "original") stored.fontFamily = "retro";
    return { ...DEFAULTS, ...stored };
  } catch {
    return DEFAULTS;
  }
}

function applyToDocument(prefs) {
  const root = document.documentElement;
  root.style.setProperty("--reading-font-size", `${prefs.fontSize}px`);
  root.style.setProperty("--reading-font-family", FONT_STACKS[prefs.fontFamily] || FONT_STACKS.sans);
  root.style.setProperty("--reading-line-height", String(prefs.lineHeight));
  root.style.setProperty(
    "--night-light-opacity",
    String((prefs.nightLight / 100) * NIGHT_LIGHT_MAX_OPACITY)
  );
  root.setAttribute("data-app-theme", prefs.theme);
}

const ReadingPreferencesContext = createContext(null);

export function ReadingPreferencesProvider({ children }) {
  const [prefs, setPrefs] = useState(readStored);

  useEffect(() => {
    applyToDocument(prefs);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
    } catch {
    }
  }, [prefs]);

  const update = useCallback((patch) => {
    setPrefs((current) => ({ ...current, ...patch }));
  }, []);

  return (
    <ReadingPreferencesContext.Provider value={{ prefs, update, fontStacks: FONT_STACKS }}>
      {children}
    </ReadingPreferencesContext.Provider>
  );
}

export function useReadingPreferences() {
  const context = useContext(ReadingPreferencesContext);
  if (!context) {
    throw new Error("useReadingPreferences must be used within ReadingPreferencesProvider");
  }
  return context;
}
