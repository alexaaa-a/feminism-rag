import { api, connection, state } from "./api.js";
import { el, esc, fmt, toast } from "./ui.js";

const STATUS_LABELS = {
  indexed: ["прочитан", "good"],
  skipped: ["пропущен", "warn"],
  failed: ["ошибка", "warn"],
};

const POLL_MS = 2000;
const refs = {};
let polling = null;

export function initCorpus() {
  refs.stats = document.getElementById("stats");
  refs.documents = document.getElementById("documents");
  refs.syncLog = document.getElementById("sync-log");
  refs.sync = document.getElementById("sync");
  refs.force = document.getElementById("sync-force");

  refs.sync.addEventListener("click", startSync);
}

export async function loadCorpus(prefetchedStats) {
  try {
    const [stats, documents] = await Promise.all([
      prefetchedStats ? Promise.resolve(prefetchedStats) : api.stats(),
      api.documents(),
    ]);
    renderStats(stats);
    renderDocuments(documents);
  } catch (error) {
    toast(`Корпус не загрузился: ${error.message}`);
  }
}

function renderStats(stats) {
  const tiles = [
    ["документов", fmt.int(stats.documents), split(stats.by_lang)],
    ["фрагментов", fmt.int(stats.chunks), indexNote(stats)],
    ["форматов", fmt.int(Object.keys(stats.by_format || {}).length), split(stats.by_format)],
    ["слов прочитано", fmt.int(stats.words), stats.tables ? `<span class="badge">таблиц: ${fmt.int(stats.tables)}</span>` : ""],
  ];

  refs.stats.replaceChildren(
    ...tiles.map(([label, value, extra]) =>
      el(`
        <div class="stat">
          <span class="stat__value">${value}</span>
          <span class="stat__label">${esc(label)}</span>
          ${extra ? `<span class="stat__split">${extra}</span>` : ""}
        </div>
      `)
    )
  );
}

function indexNote(stats) {
  if (!stats.chunks) return "";
  const matches = stats.chunks === stats.points_in_index;
  return `<span class="badge badge--${matches ? "good" : "warn"}">${matches ? "все в поиске" : "поиск отстаёт"}</span>`;
}

function split(mapping) {
  return Object.entries(mapping || {})
    .map(([key, value]) => `<span class="badge">${esc(key)}: ${fmt.int(value)}</span>`)
    .join("");
}

function renderDocuments(payload) {
  const documents = payload.documents || [];
  refs.documents.replaceChildren(
    el(`
      <div class="doc-row doc-row--head">
        <span>документ</span><span>фрагментов</span><span>язык</span><span>состояние</span>
      </div>
    `)
  );

  if (!documents.length) {
    refs.documents.append(
      el(`<p class="empty-note">Пока ничего не прочитано. Нажмите «Обновить», чтобы забрать документы из источников.</p>`)
    );
    return;
  }

  for (const document of documents) {
    const [label, tone] = STATUS_LABELS[document.status] || [document.status, ""];
    refs.documents.append(
      el(`
        <div class="doc-row">
          <span class="doc__name">
            <span class="doc__title">${esc(document.title || document.source)}</span>
            <span class="doc__file">${esc(document.source)} · ${esc(document.document_format)} · ${esc(document.parser || "—")}</span>
          </span>
          <span class="doc__num">${fmt.int(document.chunks_count)}</span>
          <span class="doc__num">${esc(document.lang)}</span>
          <span>
            <span class="badge badge--${tone}">${esc(label)}</span>
            ${document.error ? `<span class="doc__file" title="${esc(document.error)}">${esc(document.error)}</span>` : ""}
          </span>
        </div>
      `)
    );
  }
}

async function startSync() {
  refs.sync.disabled = true;
  try {
    await connection;
    const run = await api.startSync({ force: refs.force.checked });
    renderRun(run);
    if (run.status === "running") pollRun(run.run_id);
    else finishSync();
  } catch (error) {
    toast(`Синхронизация не запустилась: ${error.message}`);
    refs.sync.disabled = false;
  }
}

function pollRun(runId) {
  clearInterval(polling);
  polling = setInterval(async () => {
    try {
      const run = await api.syncRun(runId);
      renderRun(run);
      if (run.status !== "running") {
        clearInterval(polling);
        finishSync();
      }
    } catch (error) {
      clearInterval(polling);
      toast(`Статус прогона не читается: ${error.message}`);
      refs.sync.disabled = false;
    }
  }, POLL_MS);
}

function finishSync() {
  refs.sync.disabled = false;
  loadCorpus();
}

function renderRun(run) {
  const running = run.status === "running";
  const tone = running ? "accent" : run.status === "succeeded" ? "good" : "warn";

  refs.syncLog.hidden = false;
  refs.syncLog.replaceChildren(
    el(`
      <div class="sync-log__head">
        <span class="sync-log__title">${running ? "Читаем документы" : run.status === "succeeded" ? "Все обновлено" : "Обновить не получилось"}</span>
        ${running ? `<span class="badge badge--${tone}">идёт</span>` : ""}
        ${run.duration_sec ? `<span class="badge">${run.duration_sec.toFixed(1)} с</span>` : ""}
        ${state.live ? "" : `<span class="badge badge--warn">демо</span>`}
      </div>
      <div class="sync-log__grid">
        <span class="badge">файлов: ${fmt.int(run.files_seen)}</span>
        <span class="badge badge--good">прочитано: ${fmt.int(run.documents_indexed)}</span>
        <span class="badge">без изменений: ${fmt.int(run.documents_skipped)}</span>
        <span class="badge${run.documents_failed ? " badge--warn" : ""}">ошибок: ${fmt.int(run.documents_failed)}</span>
        <span class="badge">удалено: ${fmt.int(run.documents_deleted)}</span>
        <span class="badge">фрагментов: ${fmt.int(run.chunks_indexed)}</span>
      </div>
      ${
        (run.errors || []).length
          ? `<ul>${run.errors.map((error) => `<li class="doc__file">${esc(error)}</li>`).join("")}</ul>`
          : ""
      }
    `)
  );
}
