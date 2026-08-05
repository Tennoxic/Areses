import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../../api/client";
import { showToast } from "../../../utils/toast";
import { confirmDialog } from "../../../utils/dialog";

export function AdminPanel() {
  const { t } = useTranslation();
  const [users, setUsers] = useState([]);

  useEffect(() => {
    api.get("/api/admin/users").then(setUsers);
  }, []);

  async function removeUser(user) {
    if (!(await confirmDialog(t("settings.confirmDeleteUser", { username: user.username }), { danger: true }))) return;
    try {
      await api.delete(`/api/admin/users/${user.id}`);
      setUsers((current) => current.filter((u) => u.id !== user.id));
    } catch (err) {
      showToast(err.message, "error");
    }
  }

  async function toggleRole(user) {
    if (user.isAdmin) {
      if (!(await confirmDialog(t("settings.confirmDemoteAdmin", { username: user.username }), { danger: true }))) return;
    }
    try {
      const updated = await api.patch(`/api/admin/users/${user.id}/role`, { isAdmin: !user.isAdmin });
      setUsers((current) => current.map((u) => (u.id === updated.id ? updated : u)));
    } catch (err) {
      showToast(err.message, "error");
    }
  }

  return (
    <div>
      <h3>{t("settings.admin")}</h3>
      {users.map((u) => (
        <div key={u.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 15, padding: "4px 0", color: "var(--ink)" }}>
          <span>{u.username} {u.isAdmin ? t("common.adminBadge") : ""}</span>
          <span style={{ display: "flex", gap: 8 }}>
            <button className="pill-button" onClick={() => toggleRole(u)}>
              {u.isAdmin ? t("settings.demoteAdmin") : t("settings.promoteAdmin")}
            </button>
            {!u.isAdmin && <button className="pill-button pill-button-icon" onClick={() => removeUser(u)}>✕</button>}
          </span>
        </div>
      ))}
    </div>
  );
}
