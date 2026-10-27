import { DEMO } from "./demo.js";

function withSlash(value) {
  return value.endsWith("/") ? value : `${value}/`;
}

function apiCandidates() {
  const override = new URLSearchParams(location.search).get("api");
  if (override) return [withSlash(override)];

  const candidates = [];

  if (location.pathname.includes("/ui")) {
    candidates.push(new URL("../rag/v1/", location.href).toString());
  }

  candidates.push(new URL("/rag/v1/", location.origin).toString());
  candidates.push("http://localhost:8000/rag/v1/");

  return [...new Set(candidates)];
}

export const state = {
  base: apiCandidates()[0],
  live: false,
  clientId: readClientId(),
};

let markConnected;

export const connection = new Promise((resolve) => {
  markConnected = resolve;
});

function readClientId() {
  try {
    let id = localStorage.getItem("rag-client-id");
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem("rag-client-id", id);
    }
    return id;
  } catch {
    return crypto.randomUUID();
  }
}

function headers() {
  return {
    "content-type": "application/json",
    "X-Client-Id": state.clientId,
  };
}

async function request(path, { method = "GET", body, signal } = {}) {
  const response = await fetch(state.base + path, {
    method,
    headers: headers(),
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload.detail || payload.message || detail;
    } catch { }
    throw new Error(detail);
  }
  return response.status === 204 ? null : response.json();
}

export async function probe() {
  for (const base of apiCandidates()) {
    state.base = base;
    try {
      const stats = await request("documents/stats");
      state.live = true;
      markConnected(true);
      return stats;
    } catch {
    }
  }

  state.live = false;
  markConnected(false);
  return DEMO.stats;
}

export const api = {
  stats: () => (state.live ? request("documents/stats") : Promise.resolve(DEMO.stats)),

  documents: () =>
    state.live ? request("documents?limit=200") : Promise.resolve(DEMO.documents),

  sessions: () =>
    state.live ? request("chat/sessions?limit=50") : Promise.resolve({ sessions: DEMO.sessions }),

  session: (id) =>
    state.live ? request(`chat/sessions/${id}`) : Promise.resolve(DEMO.sessionDetail(id)),

  createSession: (title) =>
    state.live
      ? request("chat/sessions", { method: "POST", body: { title } })
      : Promise.resolve(DEMO.createSession(title)),

  deleteSession: (id) =>
    state.live ? request(`chat/sessions/${id}`, { method: "DELETE" }) : Promise.resolve(null),

  ask: (body, signal) =>
    state.live ? request("chat/ask", { method: "POST", body, signal }) : DEMO.ask(body),

  search: (body) =>
    state.live ? request("search", { method: "POST", body }) : DEMO.search(body),

  startSync: (body) =>
    state.live
      ? request("documents/sync", { method: "POST", body })
      : Promise.resolve(DEMO.syncRun("running")),

  syncRun: (id) =>
    state.live ? request(`documents/sync/${id}`) : Promise.resolve(DEMO.syncRun("succeeded")),
};

export async function streamAnswer(body, onEvent, signal) {
  if (!state.live) return DEMO.stream(body, onEvent);

  const response = await fetch(state.base + "chat/stream", {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok || !response.body) throw new Error(`HTTP ${response.status}`);

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let split;
    while ((split = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, split);
      buffer = buffer.slice(split + 2);
      const parsed = parseFrame(frame);
      if (parsed) onEvent(parsed);
    }
  }
}

function parseFrame(frame) {
  let event = "message";
  const dataLines = [];

  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  if (!dataLines.length) return null;

  try {
    return { event, ...JSON.parse(dataLines.join("\n")) };
  } catch {
    return null;
  }
}
