import { probe, state } from "./api.js";
import { initChat, loadSessions } from "./chat.js";
import { initExplore } from "./explore.js";
import { initCorpus, loadCorpus } from "./corpus.js";
import { toast } from "./ui.js";

const THEME_KEY = "rag-theme";
let corpusLoaded = false;
let firstStats = null;
let connected = false;
let activeView = "chat";

function initTheme() {
  const toggle = document.getElementById("theme-toggle");
  const system = window.matchMedia("(prefers-color-scheme: dark)");

  let stored = null;
  try {
    stored = localStorage.getItem(THEME_KEY);
  } catch { }
  apply(stored);

  toggle.addEventListener("click", () => {
    const next = effective() === "dark" ? "light" : "dark";
    apply(next);
    try {
      localStorage.setItem(THEME_KEY, next);
    } catch { }
  });

  system.addEventListener("change", () => {
    if (!document.documentElement.dataset.theme) syncLabel();
  });

  function effective() {
    return document.documentElement.dataset.theme || (system.matches ? "dark" : "light");
  }

  function apply(theme) {
    if (theme === "dark" || theme === "light") document.documentElement.dataset.theme = theme;
    else delete document.documentElement.dataset.theme;
    syncLabel();
  }

  function syncLabel() {
    const dark = effective() === "dark";
    toggle.setAttribute("aria-pressed", String(dark));
    toggle.setAttribute("aria-label", dark ? "Включить светлую тему" : "Включить темную тему");
  }
}

function initNav() {
  const buttons = [...document.querySelectorAll(".nav__item")];
  const views = {
    chat: document.getElementById("view-chat"),
    explore: document.getElementById("view-explore"),
    corpus: document.getElementById("view-corpus"),
  };

  function show(name) {
    activeView = name;
    for (const button of buttons) button.classList.toggle("is-active", button.dataset.view === name);
    for (const [key, node] of Object.entries(views)) node.classList.toggle("is-active", key === name);

    if (name === "corpus") loadCorpusOnce();
    if (location.hash.slice(1) !== name) history.replaceState(null, "", `#${name}`);
  }

  for (const button of buttons) button.addEventListener("click", () => show(button.dataset.view));

  const fromHash = location.hash.slice(1);
  show(fromHash in views ? fromHash : "chat");
}

function loadCorpusOnce() {
  if (corpusLoaded || !connected) return;
  corpusLoaded = true;
  loadCorpus(firstStats);
}

async function initConnection() {
  const node = document.getElementById("connection");
  const text = node.querySelector(".status__text");

  firstStats = await probe();

  if (state.live) {
    node.dataset.state = "live";
    text.textContent = "на связи";
  } else {
    node.dataset.state = "demo";
    text.textContent = "демо-данные";
    toast("Сервер не отвечает.");
  }
}

async function boot() {
  initTheme();
  initChat();
  initExplore();
  initCorpus();
  initNav();

  await initConnection();
  connected = true;

  loadSessions();
  if (activeView === "corpus") loadCorpusOnce();
}

boot();
