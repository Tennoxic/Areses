import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";

export function GlobalView() {
  const { t } = useTranslation();
  const [feeds, setFeeds] = useState([]);

  useEffect(() => {
    api.get("/api/feeds").then(setFeeds);
  }, []);

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ fontFamily: "var(--font-display)" }}>{t("globalView.title")}</h2>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "1px solid var(--line)" }}>
            <th>{t("globalView.feed")}</th>
            <th>{t("globalView.unread")}</th>
            <th>{t("globalView.status")}</th>
            <th>{t("globalView.interval")}</th>
          </tr>
        </thead>
        <tbody>
          {feeds.map((feed) => (
            <tr key={feed.subscriptionId} style={{ borderBottom: "1px solid var(--line)" }}>
              <td style={{ padding: "8px 0" }}>{feed.customName || feed.url}</td>
              <td>{feed.unreadCount}</td>
              <td style={{ color: feed.isBroken ? "var(--danger)" : "inherit" }}>
                {feed.isBroken ? t("globalView.broken") : t("globalView.ok")}
              </td>
              <td>{feed.fetchIntervalMinutes}m</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
