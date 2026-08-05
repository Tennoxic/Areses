import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import hljs from "highlight.js";
import "highlight.js/styles/github.css";
import { api } from "../../api/client";
import { useAppState } from "../../context/AppContext";
import { extractHighlightTerms } from "../../utils/highlight";
import { ImageLightbox } from "./ImageLightbox";

const SCROLL_DEBOUNCE_MS = 2000;

export function ReadingPane({ onArticleChanged, onNextUnread, hasNextUnread, searchQuery, onOpenAppearance, onBackToList }) {
  const { t } = useTranslation();
  const state = useAppState();
  const [article, setArticle] = useState(null);
  const [showSummary, setShowSummary] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [showTranslateMenu, setShowTranslateMenu] = useState(false);
  const [translating, setTranslating] = useState(false);
  const [translatedContent, setTranslatedContent] = useState(null);
  const [translatedLanguage, setTranslatedLanguage] = useState(null);
  const [lightboxSrc, setLightboxSrc] = useState(null);
  const contentRef = useRef(null);
  const contentHtmlRef = useRef(null);
  const scrollTimerRef = useRef(null);

  useEffect(() => {
    clearTimeout(scrollTimerRef.current);
    setTranslatedContent(null);
    setTranslatedLanguage(null);
    setShowTranslateMenu(false);
    if (!state.activeArticleId) {
      setArticle(null);
      return;
    }
    api.get(`/api/articles/${state.activeArticleId}`).then((data) => {
      setArticle(data);
      setShowSummary(Boolean(data.aiSummary));
      requestAnimationFrame(() => {
        if (contentRef.current) {
          contentRef.current.scrollTop = data.scrollPosition * contentRef.current.scrollHeight;
        }
      });
    });
  }, [state.activeArticleId]);

  useEffect(() => {
    const container = contentHtmlRef.current;
    if (!container) return;

    container.querySelectorAll("pre code").forEach((block) => {
      hljs.highlightElement(block);
    });

    function handleClick(event) {
      if (event.target.tagName === "IMG") {
        setLightboxSrc(event.target.src);
      }
    }
    container.addEventListener("click", handleClick);
    return () => container.removeEventListener("click", handleClick);
  }, [article?.content, showSummary]);

  function handleScroll() {
    if (!article || !contentRef.current) return;
    clearTimeout(scrollTimerRef.current);
    scrollTimerRef.current = setTimeout(() => {
      const el = contentRef.current;
      const position = el.scrollHeight > el.clientHeight ? el.scrollTop / el.scrollHeight : 0;
      api.postFireAndForget(`/api/articles/${article.id}/scroll-position`, { position });
    }, SCROLL_DEBOUNCE_MS);
  }

  async function toggleStar() {
    const nextStarred = !article.starred;
    setArticle({ ...article, starred: nextStarred });
    onArticleChanged(article.id, { starred: nextStarred });
    await api.postFireAndForget(`/api/articles/${article.id}/star`);
  }

  async function toggleReadLater() {
    const nextValue = !article.readLater;
    setArticle({ ...article, readLater: nextValue });
    onArticleChanged(article.id, { readLater: nextValue });
    await api.postFireAndForget(`/api/articles/${article.id}/read-later`);
  }

  async function markUnread() {
    await api.postFireAndForget(`/api/articles/${article.id}/unread`);
    setArticle({ ...article, isRead: false });
    onArticleChanged(article.id, { isRead: false });
  }

  async function generateSummary() {
    setGenerating(true);
    try {
      const updated = await api.post(`/api/articles/${article.id}/generate-summary`);
      setArticle(updated);
      setShowSummary(true);
      onArticleChanged(article.id, { aiSummary: updated.aiSummary });
    } finally {
      setGenerating(false);
    }
  }

  const TRANSLATE_LANGUAGES = [
    "Turkish", "English", "Spanish", "German", "French",
    "Portuguese", "Italian", "Russian", "Arabic", "Japanese",
  ];

  async function translateArticle(language) {
    setShowTranslateMenu(false);
    setTranslating(true);
    try {
      const result = await api.post(`/api/articles/${article.id}/translate`, {
        targetLanguage: language,
      });
      setTranslatedContent(result.translatedContent);
      setTranslatedLanguage(language);
    } finally {
      setTranslating(false);
    }
  }

  if (!article) {
    return (
      <div className="reading-pane pane">
        <div className="reading-pane-empty">{t("readingPane.selectPrompt")}</div>
      </div>
    );
  }

  const highlightTerms = extractHighlightTerms(searchQuery);
  const highlightedTitle = highlightTitleHtml(article.title, highlightTerms);

  return (
    <div className="reading-pane pane" ref={contentRef} onScroll={handleScroll}>
      <ImageLightbox src={lightboxSrc} onClose={() => setLightboxSrc(null)} />

      <h1 className="reading-pane-title" dangerouslySetInnerHTML={{ __html: highlightedTitle }} />
      <button className="pill-button mobile-back-button" onClick={onBackToList}>
        ← {t("articleList.backToList")}
      </button>
      <div className="reading-pane-meta">
        <span>{new Date(article.publishedAt || article.fetchedAt).toLocaleString()}</span>
        {article.readingTimeMinutes && (
          <span>{t("readingPane.minuteRead", { count: article.readingTimeMinutes })}</span>
        )}
        <a href={article.url} target="_blank" rel="noreferrer">
          {t("readingPane.openOriginal")}
        </a>
        <button className="pill-button" onClick={onNextUnread} disabled={!hasNextUnread}>
          {t("readingPane.nextUnread")} →
        </button>
        <div className="reading-pane-actions">
          <button className={`pill-button ${article.starred ? "active" : ""}`} onClick={toggleStar}>
            {article.starred ? t("readingPane.unstar") : t("readingPane.star")}
          </button>
          <button className={`pill-button ${article.readLater ? "active" : ""}`} onClick={toggleReadLater}>
            {article.readLater ? t("readingPane.removeReadLater") : t("readingPane.readLater")}
          </button>
          <button className="pill-button" onClick={markUnread}>
            {t("readingPane.markUnread")}
          </button>
          {article.aiSummary ? (
            <button className="pill-button" onClick={() => setShowSummary(!showSummary)}>
              {showSummary ? t("readingPane.fullText") : t("readingPane.summary")}
            </button>
          ) : (
            !article.extractionFailed && (
              <button className="pill-button" onClick={generateSummary} disabled={generating}>
                {t("readingPane.generateSummary")}
              </button>
            )
          )}
          <div style={{ position: "relative", display: "inline-block" }}>
            <button
              className="pill-button"
              onClick={() => setShowTranslateMenu(!showTranslateMenu)}
              disabled={translating}
            >
              {translating ? t("readingPane.translating") : t("readingPane.translateTo")}
            </button>
            {showTranslateMenu && (
              <div className="translate-menu">
                {TRANSLATE_LANGUAGES.map((language) => (
                  <button
                    key={language}
                    className="translate-menu-item"
                    onClick={() => translateArticle(language)}
                  >
                    {t(`languages.${language}`)}
                  </button>
                ))}
              </div>
            )}
          </div>
          {translatedContent && (
            <button className="pill-button" onClick={() => setTranslatedContent(null)}>
              {t("readingPane.showOriginal")}
            </button>
          )}
          <button className="pill-button" onClick={onOpenAppearance}>
            {t("readingPane.displaySettings")}
          </button>
        </div>
      </div>

      {article.enclosureUrl && (
        <div className="reading-pane-enclosure">
          {article.enclosureType?.startsWith("video/") ? (
            <video controls src={article.enclosureUrl} style={{ width: "100%" }} />
          ) : (
            <audio controls src={article.enclosureUrl} style={{ width: "100%" }} />
          )}
        </div>
      )}

      <div className="reading-pane-content" ref={contentHtmlRef}>
        {translatedContent ? (
          <>
            <p className="reading-pane-translate-note">{t("readingPane.translatedTo", { language: t(`languages.${translatedLanguage}`) })}</p>
            <p>{translatedContent}</p>
          </>
        ) : showSummary && article.aiSummary ? (
          <p>{article.aiSummary}</p>
        ) : article.content ? (
          <div dangerouslySetInnerHTML={{ __html: article.content }} />
        ) : (
          <div className="reading-pane-extraction-failed">
            <p>{t("readingPane.extractionFailed")}</p>
            <a className="pill-button active" href={article.url} target="_blank" rel="noreferrer">
              {t("readingPane.openOriginal")}
            </a>
          </div>
        )}
      </div>
    </div>
  );
}

function highlightTitleHtml(title, terms) {
  const escaped = (title ?? "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  if (!terms || terms.length === 0) {
    return escaped;
  }
  const pattern = new RegExp(`(${terms.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "gi");
  return escaped.replace(pattern, "<mark>$1</mark>");
}
