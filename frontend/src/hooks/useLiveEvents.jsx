import { useEffect } from "react";
import { BASE_URL } from "../api/client";

export function useLiveEvents(onNewArticle) {
  useEffect(() => {
    const source = new EventSource(`${BASE_URL}/api/events`, { withCredentials: true });

    source.onmessage = (event) => {
      let message;
      try {
        message = JSON.parse(event.data);
      } catch {
        return;
      }
      if (message.type === "newArticle") {
        onNewArticle(message.data);
      }
    };

    return () => source.close();
  }, [onNewArticle]);
}
