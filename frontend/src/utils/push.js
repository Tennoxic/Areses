import { api } from "../api/client";

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)));
}

export async function isPushSupported() {
  return "serviceWorker" in navigator && "PushManager" in window;
}

export async function getPushSubscriptionStatus() {
  if (!(await isPushSupported())) return "unsupported";
  const registration = await navigator.serviceWorker.ready;
  const subscription = await registration.pushManager.getSubscription();
  return subscription ? "subscribed" : "unsubscribed";
}

export async function subscribeToPush() {
  const registration = await navigator.serviceWorker.ready;
  const { publicKey } = await api.get("/api/push/vapid-public-key");
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(publicKey),
  });
  const json = subscription.toJSON();
  await api.post("/api/push/subscribe", { endpoint: json.endpoint, keys: json.keys });
  return subscription;
}

export async function unsubscribeFromPush() {
  const registration = await navigator.serviceWorker.ready;
  const subscription = await registration.pushManager.getSubscription();
  if (!subscription) return;
  await api.post("/api/push/unsubscribe", { endpoint: subscription.endpoint });
  await subscription.unsubscribe();
}
