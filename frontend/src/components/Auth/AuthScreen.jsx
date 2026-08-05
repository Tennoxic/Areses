import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../hooks/useAuth";
import { api } from "../../api/client";
import { Input, Checkbox } from "../Ui/Ui";

function ForgotPasswordForm({ onBack }) {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    const result = await api.post("/api/auth/forgot-password", { email });
    setStatus(result.status);
  }

  return (
    <div className="auth-card">
      <h1>{t("auth.forgotPassword")}</h1>
      {status ? (
        <p style={{ fontSize: 13 }}>{t(`errors.${status}`, { defaultValue: status })}</p>
      ) : (
        <form onSubmit={handleSubmit}>
          <Input
            type="email"
            placeholder={t("auth.email")}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <button type="submit">{t("auth.sendResetLink")}</button>
        </form>
      )}
      <button className="switch-mode" onClick={onBack}>
        {t("auth.backToLogin")}
      </button>
    </div>
  );
}

function ResetPasswordForm({ token, onDone }) {
  const { t } = useTranslation();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    try {
      await api.post("/api/auth/reset-password", { token, newPassword: password });
      setDone(true);
    } catch (err) {
      setError(err.message);
    }
  }

  if (done) {
    return (
      <div className="auth-card">
        <h1>{t("auth.passwordReset")}</h1>
        <button className="switch-mode" onClick={onDone}>{t("auth.backToLogin")}</button>
      </div>
    );
  }

  return (
    <div className="auth-card">
      <h1>{t("auth.resetPassword")}</h1>
      <form onSubmit={handleSubmit}>
        <Input
          type="password"
          placeholder={t("auth.newPassword")}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error && <div className="auth-error">{error}</div>}
        <button type="submit">{t("auth.resetPassword")}</button>
      </form>
    </div>
  );
}

export function AuthScreen() {
  const { t } = useTranslation();
  const { login, register } = useAuth();
  const urlToken = new URLSearchParams(window.location.search).get("token");
  const [mode, setMode] = useState(urlToken ? "reset" : "login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      if (mode === "login") {
        await login(username, password, rememberMe);
      } else {
        await register(username, email, password);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (mode === "forgot") {
    return (
      <div className="auth-screen">
        <ForgotPasswordForm onBack={() => setMode("login")} />
      </div>
    );
  }

  if (mode === "reset") {
    return (
      <div className="auth-screen">
        <ResetPasswordForm
          token={urlToken}
          onDone={() => {
            window.history.replaceState({}, "", window.location.pathname);
            setMode("login");
          }}
        />
      </div>
    );
  }

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <h1>{mode === "login" ? t("auth.login") : t("auth.register")}</h1>
        <form onSubmit={handleSubmit}>
          <Input
            placeholder={t("auth.username")}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
          {mode === "register" && (
            <Input
              type="email"
              placeholder={t("auth.email")}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          )}
          <Input
            type="password"
            placeholder={t("auth.password")}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {mode === "login" && (
            <div style={{ marginTop: 8, marginBottom: 4 }}>
              <Checkbox
                id="remember-me"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
              >
                {t("auth.rememberMe")}
              </Checkbox>
            </div>
          )}
          {error && <div className="auth-error">{error}</div>}
          <button type="submit" disabled={submitting}>
            {mode === "login" ? t("auth.login") : t("auth.register")}
          </button>
        </form>
        <button className="switch-mode" onClick={() => setMode(mode === "login" ? "register" : "login")}>
          {mode === "login" ? t("auth.noAccount") : t("auth.haveAccount")}
        </button>
        {mode === "login" && (
          <button className="switch-mode" onClick={() => setMode("forgot")}>
            {t("auth.forgotPassword")}
          </button>
        )}
      </div>
    </div>
  );
}
