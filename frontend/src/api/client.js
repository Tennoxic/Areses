import i18n from "../i18n";

const BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.DEV ? "http://localhost:8000" : "");
const QUEUE_KEY = "aresesOfflineQueue";

class ApiError extends Error {
  constructor(status, detail) {
    const message = ApiError.resolveMessage(status, detail);
    super(message);
    this.status = status;
    this.code = detail && typeof detail === "object" && !Array.isArray(detail) ? detail.code : undefined;
  }

  static resolveMessage(status, detail) {
    if (Array.isArray(detail)) {
      const reasons = detail
        .map((item) => (item && typeof item === "object" ? item.msg : String(item)))
        .filter(Boolean);
      if (reasons.length > 0) return reasons.join("; ");
    } else if (detail && typeof detail === "object") {
      const code = detail.code;
      const fallback = detail.message;
      if (code) return i18n.t(`errors.${code}`, { defaultValue: fallback || code });
      if (fallback) return fallback;
    } else if (typeof detail === "string" && detail) {
      return detail;
    }
    return `request failed with status ${status}`;
  }
}

function readQueue() {
  try {
    return JSON.parse(localStorage.getItem(QUEUE_KEY) || "[]");
  } catch {
    return [];
  }
}

function writeQueue(queue) {
  localStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
}

function queueMutation(path, options) {
  const queue = readQueue();
  queue.push({ path, options, queuedAt: Date.now() });
  writeQueue(queue);
}

export async function flushOfflineQueue() {
  const queue = readQueue();
  if (queue.length === 0) return;
  writeQueue([]);
  for (const item of queue) {
    try {
      await request(item.path, item.options);
    } catch {
      queueMutation(item.path, item.options);
    }
  }
}

if (typeof window !== "undefined") {
  window.addEventListener("areses:flush-queue", flushOfflineQueue);
}

async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    credentials: "include",
    headers: options.body ? { "Content-Type": "application/json" } : {},
    ...options,
  });

  if (!response.ok) {
    let detail;
    try {
      const data = await response.json();
      detail = data.detail;
    } catch {
      detail = undefined;
    }
    throw new ApiError(response.status, detail);
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

async function requestFireAndForget(path, options = {}) {
  if (typeof navigator !== "undefined" && !navigator.onLine) {
    queueMutation(path, options);
    return { status: "queued" };
  }
  try {
    return await request(path, options);
  } catch (error) {
    if (error instanceof ApiError) throw error;
    queueMutation(path, options);
    return { status: "queued" };
  }
}

export const api = {
  get: (path) => request(path),
  post: (path, body) =>
    request(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: (path, body) =>
    request(path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: (path) => request(path, { method: "DELETE" }),
  postFireAndForget: (path, body) =>
    requestFireAndForget(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
};

export { ApiError, BASE_URL };
