import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { getPushSubscriptionStatus, isPushSupported, isSecureContextForPush, subscribeToPush, unsubscribeFromPush } from "../../../utils/push";
import { showToast } from "../../../utils/toast";

export function NotificationsPanel() {
  const { t } = useTranslation();
  const [status, setStatus] = useState("checking");
  const secureContext = isSecureContextForPush();

  useEffect(() => {
    isPushSupported().then((supported) => {
      if (!supported) {
        setStatus("unsupported");
      } else {
        getPushSubscriptionStatus().then(setStatus);
      }
    });
  }, []);

  async function toggle() {
    try {
      if (status === "subscribed") {
        await unsubscribeFromPush();
        setStatus("unsubscribed");
      } else {
        await subscribeToPush();
        setStatus("subscribed");
      }
    } catch (err) {
      showToast(err.code === "insecure_context" ? t("settings.pushInsecureContext") : err.message, "info");
    }
  }

  return (
    <div>
      <h3>{t("settings.notifications")}</h3>
      {!secureContext && status !== "unsupported" && (
        <p style={{ fontSize: 15, color: "var(--danger)", marginBottom: 8 }}>{t("settings.pushInsecureContext")}</p>
      )}
      {status === "unsupported" ? (
        <p style={{ fontSize: 16, color: "var(--muted)" }}>{t("settings.pushUnsupported")}</p>
      ) : (
        <button className={`pill-button ${status === "subscribed" ? "active" : ""}`} onClick={toggle} disabled={status === "checking"}>
          {status === "subscribed" ? t("settings.pushEnabled") : t("settings.pushDisabled")}
        </button>
      )}
      <p style={{ fontSize: 15, color: "var(--muted)", marginTop: 8 }}>{t("settings.notifyPerFeedHint")}</p>
    </div>
  );
}
