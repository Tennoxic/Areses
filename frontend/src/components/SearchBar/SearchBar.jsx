import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Input } from "../Ui/Ui";

const HISTORY_KEY = "aresesSearchHistory";
const MAX_HISTORY = 8;
const OPERATOR_HINTS = ["f:", "c:", "author:", "intitle:", "intext:", "inurl:", "date:", "pubdate:", "mdate:", "userdate:"];

function readHistory() {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
  } catch {
    return [];
  }
}

function pushHistory(query) {
  if (!query || query.trim().length < 2) return;
  const current = readHistory().filter((entry) => entry !== query);
  current.unshift(query);
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(current.slice(0, MAX_HISTORY)));
  } catch {
  }
}

export function SearchBar({ value, onChange }) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState(value);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [history, setHistory] = useState(readHistory);

  useEffect(() => setDraft(value), [value]);

  function commit(query) {
    onChange(query);
    pushHistory(query);
    setHistory(readHistory());
    setShowSuggestions(false);
  }

  function handleKeyDown(event) {
    if (event.key === "Enter") {
      commit(draft);
    } else if (event.key === "Escape") {
      setShowSuggestions(false);
    }
  }

  const lastToken = draft.split(" ").pop() || "";
  const operatorSuggestions = lastToken.length > 0
    ? OPERATOR_HINTS.filter((hint) => hint.startsWith(lastToken.toLowerCase()) && hint !== lastToken)
    : [];

  const historySuggestions = draft.length === 0 ? history : [];
  const suggestions = [...operatorSuggestions.map((s) => ({ type: "operator", value: s })), ...historySuggestions.map((s) => ({ type: "history", value: s }))];

  return (
    <div className="search-bar-wrapper">
      <Input
        className="search-input ui-input"
        placeholder={t("search.placeholder")}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={handleKeyDown}
        onFocus={() => setShowSuggestions(true)}
        onBlur={() => {
          setTimeout(() => setShowSuggestions(false), 150);
          commit(draft);
        }}
      />
      {showSuggestions && suggestions.length > 0 && (
        <div className="search-suggestions">
          {suggestions.map((suggestion, index) => (
            <div
              key={index}
              className="search-suggestion-item"
              onMouseDown={(event) => {
                event.preventDefault();
                if (suggestion.type === "operator") {
                  const withoutLast = draft.split(" ").slice(0, -1).join(" ");
                  const next = `${withoutLast ? withoutLast + " " : ""}${suggestion.value}`;
                  setDraft(next);
                } else {
                  commit(suggestion.value);
                }
              }}
            >
              {suggestion.type === "history" ? "🕘 " : ""}
              {suggestion.value}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
