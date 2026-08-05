import { useEffect, useState } from "react";

export function ToastHost() {
  const [toasts, setToasts] = useState([]);

  useEffect(() => {
    function handleToast(event) {
      const toast = event.detail;
      setToasts((current) => [...current, toast]);
      setTimeout(() => {
        setToasts((current) => current.filter((t) => t.id !== toast.id));
      }, 4000);
    }
    window.addEventListener("areses:toast", handleToast);
    return () => window.removeEventListener("areses:toast", handleToast);
  }, []);

  if (toasts.length === 0) return null;

  return (
    <div className="toast-host">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast toast-${toast.variant}`}>
          {toast.message}
        </div>
      ))}
    </div>
  );
}
