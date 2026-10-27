import { api, connection } from "./api.js";
import { el, esc, fmt, toast } from "./ui.js";

const BLOCK_LABELS = {
  text: "текст",
  table: "таблица",
  table_row: "строка таблицы",
  paragraph: "абзац",
};

const MODE_LABELS = {
  hybrid: "по смыслу и словам",
  dense: "по смыслу",
  sparse: "по словам",
};

const refs = {};

export function initExplore() {
  refs.form = document.getElementById("search-form");
  refs.query = document.getElementById("search-query");
  refs.results = document.getElementById("search-results");
  refs.topK = document.getElementById("top-k");
  refs.topKOut = document.getElementById("top-k-out");
  refs.lang = document.getElementById("filter-lang");
  refs.block = document.getElementById("filter-block");
  refs.rerank = document.getElementById("opt-rerank");
  refs.route = document.getElementById("opt-route");
  refs.parents = document.getElementById("opt-parents");

  refs.topKOut.value = refs.topK.value;
  refs.topK.addEventListener("input", () => {
    refs.topKOut.value = refs.topK.value;
  });
  refs.form.addEventListener("submit", onSubmit);

  refs.results.replaceChildren(
    el(`<p class="empty-note">Задайте вопрос — покажем места, которые ассистент счёл подходящими.</p>`)
  );
}

async function onSubmit(event) {
  event.preventDefault();
  const question = refs.query.value.trim();
  if (!question) return;

  const mode = refs.form.querySelector('input[name="mode"]:checked')?.value || "hybrid";
  const filters = {};
  if (refs.lang.value) filters.lang = refs.lang.value;
  if (refs.block.value) filters.block_type = refs.block.value;

  refs.results.replaceChildren(el(`<p class="empty-note">Ищем…</p>`));

  try {
    await connection;
    const result = await api.search({
      question,
      mode,
      top_k: Number(refs.topK.value),
      filters,
      rerank: refs.rerank.checked,
      route: refs.route.checked,
      expand_to_parents: refs.parents.checked,
    });
    render(result);
  } catch (error) {
    refs.results.replaceChildren(el(`<p class="empty-note">Поиск не прошёл: ${esc(error.message)}</p>`));
    toast(`Ошибка поиска: ${error.message}`);
  }
}

function render(result) {
  refs.results.replaceChildren();
  refs.results.append(summary(result));

  const hits = result.hits || [];
  if (!hits.length) {
    refs.results.append(
      el(`<p class="empty-note">Подходящего не нашлось. Для вопроса не по теме это верный ответ.</p>`)
    );
    return;
  }

  const maxSparse = Math.max(...hits.map((hit) => hit.sparse_score || 0), 0.0001);
  hits.forEach((hit, index) => refs.results.append(card(hit, index + 1, maxSparse)));
}

function summary(result) {
  const items = [
    `<span class="badge badge--accent">${esc(MODE_LABELS[result.mode] || result.mode)}</span>`,
    `<span class="badge">просмотрено: ${fmt.int(result.candidates_seen)}</span>`,
    `<span class="badge">показано: ${fmt.int((result.hits || []).length)}</span>`,
    `<span class="badge">лучшее совпадение: ${fmt.score(result.best_dense_score)}</span>`,
  ];

  if (result.reranked) items.push(`<span class="badge">подбор перепроверен</span>`);
  if (result.answerable !== null && result.answerable !== undefined) {
    items.push(
      `<span class="badge badge--${result.answerable >= 0.5 ? "good" : "warn"}">хватает на ответ: ${fmt.percent(result.answerable)}</span>`
    );
  }

  const filters = Object.entries(result.filters || {});
  if (filters.length) {
    items.push(`<span class="badge">${esc(filters.map(([key, value]) => `${key}=${value}`).join(" · "))}</span>`);
  }
  if (result.search_query && result.search_query !== result.query) {
    items.push(`<span class="badge">запрос переписан</span>`);
  }

  return el(`<div class="summary-strip">${items.join("")}</div>`);
}

function card(hit, rank, maxSparse) {
  const signals = [];

  if (hit.dense_score !== null && hit.dense_score !== undefined) {
    signals.push(signal("по смыслу", hit.dense_score, hit.dense_score, hit.dense_rank, "dense"));
  }
  if (hit.sparse_score !== null && hit.sparse_score !== undefined) {
    signals.push(signal("по словам", hit.sparse_score / maxSparse, hit.sparse_score, hit.sparse_rank, "sparse"));
  }
  if (hit.rerank_score !== null && hit.rerank_score !== undefined) {
    signals.push(signal("по сути", hit.rerank_score, hit.rerank_score, null, "rerank"));
  }

  const meta = [];
  if (hit.section) meta.push(`<span class="badge">${esc(hit.section)}</span>`);
  if (hit.block_type) meta.push(`<span class="badge">${esc(BLOCK_LABELS[hit.block_type] || hit.block_type)}</span>`);
  if (hit.lang) meta.push(`<span class="badge">${esc(hit.lang)}</span>`);
  if (hit.page !== null && hit.page !== undefined) meta.push(`<span class="badge">с. ${esc(hit.page)}</span>`);

  return el(`
    <article class="result" style="animation-delay:${(rank - 1) * 40}ms">
      <div class="result__head">
        <span class="result__rank">${rank}</span>
        <span class="result__source" title="${esc(hit.source)}">${esc(hit.title || hit.source)}</span>
        ${meta.join("")}
      </div>
      <p class="result__text">${esc(hit.text)}</p>
      <div class="signals">${signals.join("")}</div>
    </article>
  `);
}

function signal(name, ratio, value, rank, kind) {
  const width = Math.max(2, Math.min(100, Math.round(ratio * 100)));
  const label = rank ? `${fmt.score(value, 3)} · #${rank}` : fmt.score(value, 3);
  return `
    <div class="signal signal--${kind}">
      <span class="signal__name">${esc(name)}</span>
      <span class="signal__track"><span class="signal__fill" style="width:${width}%"></span></span>
      <span class="signal__value">${esc(label)}</span>
    </div>
  `;
}
