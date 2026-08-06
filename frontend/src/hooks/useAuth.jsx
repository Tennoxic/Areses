import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const session = await api.get("/api/auth/session");
      setUser(session.authenticated ? session.user : null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(
    async (username, password, rememberMe) => {
      await api.post("/api/auth/login", {
        username,
        password,
        rememberMe: rememberMe,
      });
      await refresh();
    },
    [refresh]
  );

  const register = useCallback(
    async (username, email, password) => {
      await api.post("/api/auth/register", { username, email, password });
      await login(username, password, false);
    },
    [login]
  );

  const logout = useCallback(async () => {
    await api.post("/api/auth/logout");
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
