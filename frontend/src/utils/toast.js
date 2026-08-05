export function showToast(message, variant = "info") {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent("areses:toast", { detail: { message, variant, id: Date.now() + Math.random() } })
  );
}
