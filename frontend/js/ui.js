export function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

export function el(html) {
  const template = document.createElement("template");
  template.innerHTML = html.trim();
  return template.content.firstElementChild;
}

export const fmt = {
  int(value) {
    return new Intl.NumberFormat("ru-RU").format(Number(value || 0));
  },
  score(value, digits = 3) {
    return value === null || value === undefined ? "—" : Number(value).toFixed(digits);
  },
  percent(value) {
    return value === null || value === undefined ? "—" : `${Math.round(Number(value) * 100)}%`;
  },
  ms(value) {
    if (!value) return "—";
    return value < 1000 ? `${value} мс` : `${(value / 1000).toFixed(1)} с`;
  },
  when(value) {
    if (!value) return "—";
    const date = new Date(value);
    const sameDay = new Date().toDateString() === date.toDateString();
    return date.toLocaleString("ru-RU", sameDay
      ? { hour: "2-digit", minute: "2-digit" }
      : { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  },
};

let toastTimer = null;

export function toast(message) {
  const node = document.getElementById("toast");
  node.textContent = message;
  node.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { node.hidden = true; }, 4200);
}
