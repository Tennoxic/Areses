function dispatchDialog(detail) {
  return new Promise((resolve) => {
    function handleResult(event) {
      if (event.detail.id !== detail.id) return;
      window.removeEventListener("areses:dialog-result", handleResult);
      resolve(event.detail.value);
    }
    window.addEventListener("areses:dialog-result", handleResult);
    window.dispatchEvent(new CustomEvent("areses:dialog", { detail }));
  });
}

export function confirmDialog(message, options = {}) {
  const id = Date.now() + Math.random();
  return dispatchDialog({
    id,
    kind: "confirm",
    message,
    confirmLabel: options.confirmLabel,
    cancelLabel: options.cancelLabel,
    danger: options.danger,
  });
}

export function promptDialog(message, options = {}) {
  const id = Date.now() + Math.random();
  return dispatchDialog({
    id,
    kind: "prompt",
    message,
    defaultValue: options.defaultValue || "",
    confirmLabel: options.confirmLabel,
    cancelLabel: options.cancelLabel,
  });
}

export function alertDialog(message, options = {}) {
  const id = Date.now() + Math.random();
  return dispatchDialog({
    id,
    kind: "alert",
    message,
    confirmLabel: options.confirmLabel,
  });
}
