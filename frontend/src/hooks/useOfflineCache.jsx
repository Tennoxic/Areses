import { useEffect, useState } from "react";

export function useOfflineCache() {
  const [isOffline, setIsOffline] = useState(!navigator.onLine);

  useEffect(() => {
    function goOnline() {
      setIsOffline(false);
      window.dispatchEvent(new Event("areses:flush-queue"));
    }
    function goOffline() {
      setIsOffline(true);
    }
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, []);

  return { isOffline };
}
