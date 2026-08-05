import { useTranslation } from "react-i18next";
import { useReadingPreferences } from "../../hooks/useReadingPreferences";
import { setLanguage } from "../../i18n";
import { Select, Slider } from "../Ui/Ui";

const THEMES = ["sepia", "light", "nocturne", "dark"];
const LANGUAGES = [
  { code: "en", key: "appearance.languageNameEn" },
  { code: "tr", key: "appearance.languageNameTr" },
];

export function AppearanceMenu({ onClose }) {
  const { t, i18n } = useTranslation();
  const { prefs, update } = useReadingPreferences();

  return (
    <div className="appearance-menu-overlay" onClick={onClose}>
      <div className="appearance-menu" onClick={(e) => e.stopPropagation()}>
        <div className="appearance-menu-title">{t("readingPane.displaySettings")}</div>

        <label className="appearance-menu-field-label">
          {t("appearance.language")}
          <Select value={i18n.language} onChange={(e) => setLanguage(e.target.value)}>
            {LANGUAGES.map(({ code, key }) => (
              <option key={code} value={code}>{t(key)}</option>
            ))}
          </Select>
        </label>

        <div className="reading-theme-switch">
          {THEMES.map((theme) => (
            <button
              key={theme}
              className={`pill-button ${prefs.theme === theme ? "active" : ""}`}
              onClick={() => update({ theme })}
            >
              {t(`readingPane.theme.${theme}`)}
            </button>
          ))}
        </div>

        <label className="appearance-menu-field-label">
          {t("readingPane.fontSize")}
          <Slider
            min={14}
            max={26}
            value={prefs.fontSize}
            unit="px"
            onChange={(e) => update({ fontSize: Number(e.target.value) })}
          />
        </label>

        <label className="appearance-menu-field-label">
          {t("readingPane.fontFamily")}
          <Select value={prefs.fontFamily} onChange={(e) => update({ fontFamily: e.target.value })}>
            <option value="sans">{t("readingPane.fontSansSerif")}</option>
            <option value="serif">{t("readingPane.fontSerif")}</option>
            <option value="mono">{t("readingPane.fontMono")}</option>
            <option value="retro">{t("readingPane.fontRetro")}</option>
          </Select>
        </label>

        <label className="appearance-menu-field-label">
          {t("readingPane.lineHeight")}
          <Slider
            min={1.2}
            max={2.2}
            step={0.1}
            value={prefs.lineHeight}
            onChange={(e) => update({ lineHeight: Number(e.target.value) })}
          />
        </label>

        <label className="appearance-menu-field-label">
          {t("readingPane.nightLight")}
          <Slider
            min={0}
            max={100}
            value={prefs.nightLight}
            unit="%"
            onChange={(e) => update({ nightLight: Number(e.target.value) })}
          />
        </label>
      </div>
    </div>
  );
}
