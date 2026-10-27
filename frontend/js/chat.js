import { api, connection, state, streamAnswer } from "./api.js";
import { renderMarkdown } from "./markdown.js";
import { el, esc, fmt, toast } from "./ui.js";

const SUGGESTIONS = [
  "Кто написал «В защиту прав женщин»?",
  "Чем первая волна отличалась от второй?",
  "Когда прошла Конвенция в Сенека-Фоллз?",
  "Из каких частей состоит CEDAW?",
];

const refs = {};
let sessions = [];
let activeSession = null;
let turnSeq = 0;
let pending = false;
let sessionsLoaded = false;
const citationsByTurn = new Map();

export function initChat() {
  refs.thread = document.getElementById("thread");
  refs.sessionList = document.getElementById("session-list");
  refs.marginBody = document.getElementById("margin-body");
  refs.marginCount = document.getElementById("margin-count");
  refs.form = document.getElementById("composer");
  refs.input = document.getElementById("question");
  refs.send = document.getElementById("send");
  refs.counter = document.getElementById("counter");
  refs.suggestions = document.getElementById("suggestions");

  refs.form.addEventListener("submit", onSubmit);
  refs.input.addEventListener("input", onInput);
  refs.input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      refs.form.requestSubmit();
    }
  });
  document.getElementById("new-session").addEventListener("click", startSession);

  renderSuggestions();
  showWelcome();
  renderSessions();
  syncSuggestions();
}

export async function loadSessions() {
  try {
    const payload = await api.sessions();
    sessions = payload.sessions || [];
  } catch (error) {
    toast(`Не удалось получить список диалогов: ${error.message}`);
  } finally {
    sessionsLoaded = true;
    renderSessions();
  }
}

function renderSessions() {
  refs.sessionList.replaceChildren();

  if (!sessions.length) {
    const note = sessionsLoaded
      ? "Диалогов пока нет. Задайте вопрос - он создаст первый."
      : "Загружаем диалоги…";
    refs.sessionList.append(el(`<li class="hint" style="padding:0.5rem 0.75rem">${note}</li>`));
    return;
  }

  for (const session of sessions) {
    const isActive = activeSession && session.session_id === activeSession.session_id;
    const item = el(`
      <li>
        <button class="session${isActive ? " is-active" : ""}" type="button">
          <span class="session__title">${esc(session.title)}</span>
          <span class="session__meta">${fmt.when(session.updated_at)} · ${session.messages_count} сообщ.</span>
        </button>
      </li>
    `);
    item.querySelector("button").addEventListener("click", () => openSession(session.session_id));
    refs.sessionList.append(item);
  }
}

async function startSession() {
  releaseComposer();
  activeSession = null;
  citationsByTurn.clear();
  turnSeq = 0;
  showWelcome();
  syncSuggestions();
  clearMargin();
  renderSessions();
  refs.input.focus();
}

async function openSession(id) {
  releaseComposer();
  try {
    const detail = await api.session(id);
    activeSession = detail.session;
    citationsByTurn.clear();
    turnSeq = 0;
    renderThread(detail.messages || []);
    renderSessions();
  } catch (error) {
    toast(`Диалог не открылся: ${error.message}`);
  }
}

async function ensureSession(question) {
  if (activeSession) return activeSession;
  const created = await api.createSession(question.slice(0, 60));
  activeSession = created.session_id ? created : created.session;
  sessions = [activeSession, ...sessions.filter((item) => item.session_id !== activeSession.session_id)];
  renderSessions();
  return activeSession;
}

function syncSuggestions() {
  refs.suggestions.hidden = Boolean(refs.thread.querySelector(".turn"));
}

function showWelcome() {
  refs.thread.replaceChildren(
    el(`
      <li class="welcome">
        <h2 class="welcome__title">Спросите о феминизме и его истории.</h2>
        <p class="welcome__text">Ассистент опирается на базу знаний.</p>
        <div class="welcome__rules">
          <p class="welcome__rule"><strong>Со ссылками.</strong> Каждое утверждение помечено номером - он ведет на документ справа.</p>
          <p class="welcome__rule"><strong>Без выдумок.</strong> Когда найденного не хватает на ответ, ассистент отказывается, а не досочиняет.</p>
          <p class="welcome__rule"><strong>Можно уточнять.</strong> Спросите дальше «а в каком году?» - он поймет по разговору.</p>
        </div>
      </li>
    `)
  );
}

function renderThread(messages) {
  refs.thread.replaceChildren();
  clearMargin();

  let lastCitations = null;
  let lastTurnId = null;

  for (let index = 0; index < messages.length; index += 1) {
    const message = messages[index];
    if (message.role !== "user") continue;

    const answer = messages[index + 1]?.role === "assistant" ? messages[index + 1] : null;
    const turn = appendTurn(message.content);

    if (answer) {
      const citations = answer.citations || [];
      citationsByTurn.set(turn.id, citations);
      paintAnswer(turn, {
        answer: answer.content,
        citations,
        refused: answer.refused,
        diagnostics: answer.diagnostics,
      });
      lastCitations = citations;
      lastTurnId = turn.id;
    }
  }

  if (lastCitations) renderMargin(lastCitations, lastTurnId);
  syncSuggestions();
  scrollThread();
}

function appendTurn(question) {
  turnSeq += 1;
  const id = `turn-${turnSeq}`;
  const node = el(`
    <li class="turn" id="${id}">
      <div class="turn__question">
        <span class="eyebrow">вопрос</span>
        <p>${esc(question)}</p>
      </div>
      <div class="turn__answer">
        <div class="answer-body answer-body--streaming"><p class="typing"><span></span><span></span><span></span></p></div>
      </div>
    </li>
  `);

  if (refs.thread.querySelector(".welcome")) refs.thread.replaceChildren();
  refs.thread.append(node);
  syncSuggestions();
  scrollThread();

  return { id, node, answer: node.querySelector(".turn__answer"), body: node.querySelector(".answer-body") };
}

function paintAnswer(turn, payload) {
  const citations = payload.citations || [];
  turn.body.classList.remove("answer-body--streaming");
  turn.body.classList.toggle("answer-body--refused", Boolean(payload.refused));
  turn.body.innerHTML = answerHtml(payload.answer, citations.length);
  wireCites(turn);

  turn.answer.querySelector(".turn__badges")?.remove();
  turn.answer.querySelector(".diag")?.remove();

  const diagnostics = payload.diagnostics;
  if (!diagnostics) return;

  turn.answer.append(badges(diagnostics, payload.refused, citations.length));
  turn.answer.append(diagnosticsBlock(diagnostics));
}

function answerHtml(text, citationsCount) {
  return renderMarkdown(text, (part) => citeMarkup(part, citationsCount));
}

function citeMarkup(part, citationsCount) {
  return part.replace(/( ?)((?:\[\d{1,2}\])+)([.,;:!?»)\]]*)/g, (match, space, markers, tail) => {
    const chips = markers.match(/\[(\d{1,2})\]/g).map((marker) => {
      const number = Number(marker.slice(1, -1));
      return number <= citationsCount
        ? `<button class="cite" type="button" data-cite="${number}" aria-label="Источник ${number}">${number}</button>`
        : marker;
    });
    if (!chips.some((chip) => chip.startsWith("<button"))) return match;
    return `${space ? "&nbsp;" : ""}<span class="cite-run">${chips.join("")}${tail}</span>`;
  });
}

function wireCites(turn) {
  for (const button of turn.body.querySelectorAll(".cite")) {
    button.addEventListener("click", () => {
      const citations = citationsByTurn.get(turn.id) || [];
      renderMargin(citations, turn.id, Number(button.dataset.cite));
    });
  }
}

const MODE_LABELS = {
  hybrid: "по смыслу и словам",
  dense: "по смыслу",
  sparse: "по словам",
};

function badges(diagnostics, refused, citationsCount) {
  const items = [];

  if (refused) items.push(`<span class="badge badge--warn">ответа в документах нет</span>`);
  else items.push(`<span class="badge badge--good">${citationsCount} ${plural(citationsCount, ["документ", "документа", "документов"])}</span>`);

  if (diagnostics.answerable !== null && diagnostics.answerable !== undefined) {
    items.push(`<span class="badge">уверенность ${fmt.percent(diagnostics.answerable)}</span>`);
  }
  if (diagnostics.latency_ms) items.push(`<span class="badge">${fmt.ms(diagnostics.latency_ms)}</span>`);

  return el(`<div class="turn__badges">${items.join("")}</div>`);
}

function diagnosticsBlock(diagnostics) {
  const rows = [
    ["как искали", MODE_LABELS[diagnostics.mode] || diagnostics.mode],
    ["просмотрено мест", fmt.int(diagnostics.candidates_seen)],
    ["взято в ответ", fmt.int(diagnostics.chunks_used)],
    ["лучшее совпадение", fmt.score(diagnostics.best_dense_score)],
    ["уверенность", fmt.percent(diagnostics.answerable)],
    ["подбор перепроверен", diagnostics.reranked ? "да" : "нет"],
    ["ответ сверен с документами", fmt.percent(diagnostics.groundedness)],
    ["модель", diagnostics.llm_model || "—"],
    ["слов отправлено", fmt.int(diagnostics.prompt_tokens)],
    ["слов в ответе", fmt.int(diagnostics.completion_tokens)],
  ];

  if (diagnostics.search_query) rows.push(["вопрос для поиска", diagnostics.search_query]);
  const filters = Object.entries(diagnostics.filters || {});
  if (filters.length) rows.push(["ограничения", filters.map(([key, value]) => `${key}=${value}`).join(", ")]);

  return el(`
    <details class="diag">
      <summary>как собран этот ответ</summary>
      <div class="diag__grid">
        ${rows
          .map(
            ([key, value]) => `
          <div class="diag__item">
            <span class="diag__key">${esc(key)}</span>
            <span class="diag__value">${esc(value)}</span>
          </div>`
          )
          .join("")}
      </div>
    </details>
  `);
}

function clearMargin() {
  refs.marginCount.textContent = "";
  refs.marginBody.replaceChildren(
    el(`<p class="margin__empty">Здесь появятся документы, на которые опирается ответ. Номер&nbsp;[1] в тексте ведёт на нужное место.</p>`)
  );
}

function renderMargin(citations, turnId, focusIndex = null) {
  if (!citations.length) {
    clearMargin();
    return;
  }

  refs.marginCount.textContent = `${citations.length} ${plural(citations.length, ["место", "места", "мест"])}`;
  refs.marginBody.replaceChildren();

  citations.forEach((citation, index) => {
    const number = index + 1;
    const card = el(`
      <article class="source" id="source-${turnId}-${number}" style="animation-delay:${index * 45}ms">
        <div class="source__head">
          <span class="source__index">${number}</span>
          <span class="source__name" title="${esc(citation.source)}">${esc(citation.title || citation.source)}</span>
        </div>
        ${citation.section ? `<p class="source__section">Раздел: ${esc(citation.section)}</p>` : ""}
        ${citation.page !== null && citation.page !== undefined ? `<p class="source__section">Страница ${esc(citation.page)}</p>` : ""}
        <p class="source__text">${esc(citation.text)}</p>
        <div class="source__foot">
          ${citation.lang ? `<span class="badge">${esc(citation.lang)}</span>` : ""}
          ${citation.source_url ? `<a class="source__link" href="${esc(citation.source_url)}" target="_blank" rel="noopener">источник</a>` : ""}
        </div>
      </article>
    `);
    refs.marginBody.append(card);
  });

  if (focusIndex) {
    const card = document.getElementById(`source-${turnId}-${focusIndex}`);
    if (card) {
      for (const node of refs.marginBody.querySelectorAll(".source")) node.classList.remove("is-active");
      card.classList.add("is-active");
      card.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }
}

async function onSubmit(event) {
  event.preventDefault();
  if (pending) return;

  const question = refs.input.value.trim();
  if (!question) return;

  refs.input.value = "";
  onInput();
  await ask(question);
}

async function ask(question) {
  pending = true;
  refs.send.disabled = true;

  const turn = appendTurn(question);
  clearMargin();
  setProgress(turn, "ищу подходящие места в документах…");
  let streamed = "";
  let completed = false;

  const alive = () => turn.node.isConnected;

  try {
    await connection;
    const session = await ensureSession(question);
    const body = { question, session_id: session.session_id };

    try {
      await streamAnswer(body, (event) => {
        if (!alive()) return;
        if (event.event === "meta" && event.answer) {
          citationsByTurn.set(turn.id, event.answer.citations || []);
          renderMargin(event.answer.citations || [], turn.id);
          setProgress(turn, "нашла, пишу ответ…");
        } else if (event.event === "delta") {
          streamed += event.text || "";
          writeStream(turn, streamed);
          scrollThread();
        } else if (event.event === "done" && event.answer) {
          completed = true;
          citationsByTurn.set(turn.id, event.answer.citations || []);
          paintAnswer(turn, event.answer);
          renderMargin(event.answer.citations || [], turn.id);
        } else if (event.event === "error") {
          throw new Error(event.message || event.error);
        }
      });
    } catch (streamError) {
      console.warn("поток оборвался", streamError);
      if (!streamed && !citationsByTurn.has(turn.id)) {
        const answer = await api.ask(body);
        if (alive()) {
          completed = true;
          citationsByTurn.set(turn.id, answer.citations || []);
          paintAnswer(turn, answer);
          renderMargin(answer.citations || [], turn.id);
        }
      }
    }

    if (alive() && !completed) {
      await showSaved(turn, session.session_id, 1, streamed);
    }

    if (alive()) await refreshSession();
  } catch (error) {
    if (!alive()) return;
    turn.body.classList.remove("answer-body--streaming");
    turn.body.innerHTML = `<p>Запрос не прошёл: ${esc(error.message)}</p>`;
    toast(`Ошибка: ${error.message}`);
  } finally {
    if (alive()) releaseComposer();
    scrollThread();
  }
}

function releaseComposer() {
  pending = false;
  refs.send.disabled = false;
}

const SAVED_ATTEMPTS = 4;
const SAVED_DELAY_MS = 2500;

async function showSaved(turn, sessionId, attempt = 1, partial = "") {
  const detail = await api.session(sessionId).catch(() => null);
  const messages = detail?.messages || [];
  const last = messages[messages.length - 1];

  if (!turn.node.isConnected) return;

  if (last && last.role === "assistant") {
    citationsByTurn.set(turn.id, last.citations || []);
    paintAnswer(turn, {
      answer: last.content,
      citations: last.citations || [],
      refused: last.refused,
      diagnostics: last.diagnostics,
    });
    renderMargin(last.citations || [], turn.id);
    return;
  }

  if (attempt >= SAVED_ATTEMPTS) {
    if (partial) {
      paintAnswer(turn, {
        answer: `${partial}…\n\nСвязь оборвалась на этом месте. Откройте диалог заново через полминуты - ответ дописывается на сервере.`,
        citations: citationsByTurn.get(turn.id) || [],
      });
    } else {
      turn.body.classList.remove("answer-body--streaming");
      turn.body.innerHTML = `<p>Связь оборвалась. Ассистент дописывает ответ - откройте диалог заново через полминуты.</p>`;
    }
    return;
  }

  setProgress(turn, "связь оборвалась, жду ответ с сервера…");
  await new Promise((resolve) => setTimeout(resolve, SAVED_DELAY_MS));
  if (turn.node.isConnected) await showSaved(turn, sessionId, attempt + 1, partial);
}

function setProgress(turn, note) {
  let node = turn.body.querySelector(".typing-note");
  if (!node) {
    node = el(`<p class="typing-note"></p>`);
    turn.body.append(node);
  }
  node.textContent = note;
}

function writeStream(turn, text) {
  let node = turn.body.querySelector(".stream-text");
  if (!node) {
    node = el(`<div class="stream-text"></div>`);
    turn.body.replaceChildren(node);
  }
  const count = (citationsByTurn.get(turn.id) || []).length;
  node.innerHTML = answerHtml(text, count);
}

async function refreshSession() {
  if (!activeSession) return;
  activeSession = { ...activeSession, messages_count: (activeSession.messages_count || 0) + 2, updated_at: new Date().toISOString() };
  sessions = sessions.map((item) => (item.session_id === activeSession.session_id ? activeSession : item));
  renderSessions();
}

function onInput() {
  const value = refs.input.value;
  refs.input.style.height = "auto";
  refs.input.style.height = `${Math.min(refs.input.scrollHeight, 144)}px`;
  refs.counter.textContent = value.length > 1600 ? `${value.length} / 2000` : "";
}

function renderSuggestions() {
  refs.suggestions.replaceChildren();
  for (const text of SUGGESTIONS) {
    const button = el(`<button class="suggestion" type="button">${esc(text)}</button>`);
    button.addEventListener("click", () => {
      if (pending) return;
      ask(text);
    });
    refs.suggestions.append(button);
  }
}

function scrollThread() {
  refs.thread.scrollTop = refs.thread.scrollHeight;
}

function plural(count, forms) {
  const mod100 = count % 100;
  const mod10 = count % 10;
  if (mod100 >= 11 && mod100 <= 14) return forms[2];
  if (mod10 === 1) return forms[0];
  if (mod10 >= 2 && mod10 <= 4) return forms[1];
  return forms[2];
}
