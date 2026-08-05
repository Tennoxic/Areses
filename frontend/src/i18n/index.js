import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./en.json";
import tr from "./tr.json";

const LANGUAGE_STORAGE_KEY = "aresesLanguage";

function readStoredLanguage() {
  try {
    const stored = localStorage.getItem(LANGUAGE_STORAGE_KEY);
    return stored === "en" || stored === "tr" ? stored : "en";
  } catch {
    return "en";
  }
}

i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, tr: { translation: tr } },
  lng: readStoredLanguage(),
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

function syncDocumentLang(lng) {
  if (typeof document !== "undefined") {
    document.documentElement.lang = lng;
  }
}
i18n.on("languageChanged", syncDocumentLang);
syncDocumentLang(i18n.language);

export function setLanguage(lng) {
  try {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, lng);
  } catch {
  }
  i18n.changeLanguage(lng);
}

export default i18n;
