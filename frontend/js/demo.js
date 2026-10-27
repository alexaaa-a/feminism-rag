const CITATIONS = [
  {
    chunk_id: "local:12_ru_Интерсекциональность.txt::0003",
    source: "12_ru_Интерсекциональность.txt",
    title: "Интерсекциональность",
    section: "Происхождение термина",
    page: null,
    lang: "ru",
    score: 0.871,
    source_url: "https://ru.wikipedia.org/wiki/Интерсекциональность",
    text:
      "Термин «интерсекциональность» предложила американская исследовательница права Кимберли Креншоу " +
      "в 1989 году в работе о дискриминации чернокожих женщин: её положение нельзя описать ни через расовую, " +
      "ни через гендерную дискриминацию по отдельности.",
  },
  {
    chunk_id: "local:12_ru_Интерсекциональность.txt::0007",
    source: "12_ru_Интерсекциональность.txt",
    title: "Интерсекциональность",
    section: "Критика единого субъекта",
    page: null,
    lang: "ru",
    score: 0.804,
    source_url: "https://ru.wikipedia.org/wiki/Интерсекциональность",
    text:
      "Подход показывает, что формы неравенства не складываются, а пересекаются: класс, раса, " +
      "гражданство и инвалидность меняют то, как именно работает гендерное неравенство.",
  },
  {
    chunk_id: "local:04_ru_Третья_волна_феминизма.txt::0011",
    source: "04_ru_Третья_волна_феминизма.txt",
    title: "Третья волна феминизма",
    section: "Теоретические основания",
    page: null,
    lang: "ru",
    score: 0.642,
    source_url: "https://ru.wikipedia.org/wiki/Третья_волна_феминизма",
    text:
      "Третья волна опиралась на критику универсальной «женщины» как субъекта движения, " +
      "и интерсекциональный подход стал для неё одним из опорных.",
  },
];

const ANSWER_TEXT =
  "Интерсекциональность — подход, согласно которому формы дискриминации не существуют по отдельности, " +
  "а пересекаются и меняют друг друга: положение человека определяется одновременно гендером, расой, " +
  "классом и другими признаками [1][2].\n\n" +
  "Термин ввела американская исследовательница права Кимберли Креншоу в 1989 году, разбирая случаи " +
  "дискриминации чернокожих женщин: суды рассматривали расовую и гендерную дискриминацию отдельно, " +
  "и положение, возникающее на их пересечении, оказывалось юридически невидимым [1].\n\n" +
  "Для третьей волны феминизма этот подход стал одним из опорных: он подорвал представление об " +
  "универсальной «женщине» как едином субъекте движения [3].";

const DIAGNOSTICS = {
  mode: "hybrid",
  candidates_seen: 38,
  chunks_used: 3,
  best_dense_score: 0.871,
  answerable: 0.94,
  groundedness: null,
  reranked: true,
  route_intent: "overview",
  route_in_domain: 0.98,
  filters: {},
  search_query: null,
  latency_ms: 2140,
  llm_model: "openai/gpt-6-luna",
  prompt_tokens: 1284,
  completion_tokens: 176,
};

const SEARCH_HITS = [
  {
    chunk_id: "local:25_ru_Статистика_и_CEDAW.docx::0042",
    source: "25_ru_Статистика_и_CEDAW.docx",
    title: "Статистика и CEDAW",
    text: "Country: Albania | Year: 1920",
    section: "Избирательное право по странам",
    block_type: "table_row",
    lang: "ru",
    page: null,
    score: 0.0271,
    dense_score: 0.412,
    sparse_score: 7.84,
    dense_rank: 9,
    sparse_rank: 1,
    rerank_score: 0.96,
    source_url: null,
  },
  {
    chunk_id: "local:28_ru_волны_и_суфражизм_layout.pdf::0018",
    source: "28_ru_волны_и_суфражизм_layout.pdf",
    title: null,
    text:
      "Албания — 1920 | Австрия — 1918 | Бельгия — 1948 | Канада — 1917 | " +
      "Дания — 1915 | Финляндия — 1906",
    section: null,
    block_type: "table",
    lang: "ru",
    page: 3,
    score: 0.0193,
    dense_score: 0.455,
    sparse_score: 5.12,
    dense_rank: 5,
    sparse_rank: 3,
    rerank_score: 0.88,
    source_url: null,
  },
  {
    chunk_id: "local:13_ru_Женское_избирательное_право.txt::0006",
    source: "13_ru_Женское_избирательное_право.txt",
    title: "Женское избирательное право",
    text:
      "В межвоенный период избирательное право для женщин было введено в большинстве стран Европы: " +
      "в Австрии и Германии в 1918 году, в Албании в 1920-м, в Испании в 1931-м.",
    section: "Межвоенный период",
    block_type: "text",
    lang: "ru",
    page: null,
    score: 0.0164,
    dense_score: 0.598,
    sparse_score: 3.41,
    dense_rank: 1,
    sparse_rank: 6,
    rerank_score: 0.74,
    source_url: "https://ru.wikipedia.org/wiki/Женское_избирательное_право",
  },
];

const DOCUMENTS = [
  ["local:01_ru_Феминизм.txt", "01_ru_Феминизм.txt", "Феминизм", "ru", ".txt", 164, 58, "indexed"],
  ["local:02_ru_Первая_волна_феминизма.txt", "02_ru_Первая_волна_феминизма.txt", "Первая волна феминизма", "ru", ".txt", 97, 34, "indexed"],
  ["local:04_ru_Третья_волна_феминизма.txt", "04_ru_Третья_волна_феминизма.txt", "Третья волна феминизма", "ru", ".txt", 24, 9, "indexed"],
  ["local:12_ru_Интерсекциональность.txt", "12_ru_Интерсекциональность.txt", "Интерсекциональность", "ru", ".txt", 31, 11, "indexed"],
  ["local:18_en_Seneca_Falls_Convention.txt", "18_en_Seneca_Falls_Convention.txt", "Seneca Falls Convention", "en", ".txt", 42, 15, "indexed"],
  ["local:25_ru_Статистика_и_CEDAW.docx", "25_ru_Статистика_и_CEDAW.docx", "Статистика и CEDAW", "ru", ".docx", 88, 31, "indexed"],
  ["local:26_ru_волны_феминизма.md", "26_ru_волны_феминизма.md", "Волны феминизма", "ru", ".md", 19, 7, "indexed"],
  ["local:27_ru_Декларация_чувств_scan.pdf", "27_ru_Декларация_чувств_scan.pdf", "Декларация чувств (скан)", "ru", ".pdf", 0, 0, "skipped"],
  ["local:28_ru_волны_и_суфражизм_layout.pdf", "28_ru_волны_и_суфражизм_layout.pdf", "Волны и суфражизм", "ru", ".pdf", 56, 20, "indexed"],
];

const SESSIONS = [
  { session_id: "demo-1", title: "Что такое интерсекциональность и кто ввёл этот термин?", created_at: iso(-2), updated_at: iso(-2), messages_count: 2 },
  { session_id: "demo-2", title: "Чем цели первой волны отличались от второй?", created_at: iso(-26), updated_at: iso(-25), messages_count: 4 },
];

function iso(hoursAgo) {
  return new Date(Date.now() + hoursAgo * 3600_000).toISOString();
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function answerFor(question) {
  return {
    question,
    answer: ANSWER_TEXT,
    refused: false,
    citations: CITATIONS,
    diagnostics: { ...DIAGNOSTICS },
  };
}

export const DEMO = {
  stats: {
    documents: 25,
    chunks: 1184,
    parents: 412,
    points_in_index: 1184,
    chars: 742_318,
    words: 98_441,
    tables: 7,
    by_lang: { ru: 20, en: 5 },
    by_format: { ".txt": 21, ".pdf": 2, ".docx": 1, ".md": 1 },
    by_origin: { local: 25 },
  },

  documents: {
    total: DOCUMENTS.length,
    documents: DOCUMENTS.map(([document_id, source, title, lang, format, chunks_count, parents_count, status]) => ({
      document_id,
      source,
      title,
      lang,
      document_format: format,
      chunks_count,
      parents_count,
      status,
      origin: "local",
      chars: chunks_count * 1180,
      words: chunks_count * 164,
      tables: format === ".docx" ? 2 : 0,
      pages: format === ".pdf" ? 4 : null,
      parser: format === ".pdf" ? "pymupdf" : "pathlib",
      ocr_needed: status === "skipped",
      error: status === "skipped" ? "нет извлекаемого текста, нужен OCR" : null,
      indexed_at: iso(-5),
    })),
  },

  sessions: SESSIONS,

  sessionDetail(id) {
    const session = SESSIONS.find((item) => item.session_id === id) || SESSIONS[0];
    return {
      session,
      messages: [
        {
          message_id: "m1",
          role: "user",
          content: session.title,
          created_at: session.created_at,
          refused: false,
          citations: [],
          diagnostics: null,
        },
        {
          message_id: "m2",
          role: "assistant",
          content: ANSWER_TEXT,
          created_at: session.updated_at,
          refused: false,
          citations: CITATIONS,
          diagnostics: { ...DIAGNOSTICS },
        },
      ],
    };
  },

  createSession(title) {
    const session = {
      session_id: `demo-${Date.now()}`,
      title: title || "Новый диалог",
      created_at: iso(0),
      updated_at: iso(0),
      messages_count: 0,
    };
    SESSIONS.unshift(session);
    return session;
  },

  async ask(body) {
    await sleep(600);
    return answerFor(body.question);
  },

  async stream(body, onEvent) {
    const answer = answerFor(body.question);
    await sleep(380);
    onEvent({ event: "meta", answer: { ...answer, answer: "" } });

    const words = ANSWER_TEXT.split(/(\s+)/);
    for (let index = 0; index < words.length; index += 6) {
      await sleep(28);
      onEvent({ event: "delta", text: words.slice(index, index + 6).join("") });
    }
    onEvent({ event: "done", answer });
  },

  async search(body) {
    await sleep(420);
    const limit = body.top_k || 5;
    const mode = body.mode || "hybrid";
    let hits = SEARCH_HITS.map((hit) => ({ ...hit }));

    if (mode === "dense") {
      hits.sort((a, b) => b.dense_score - a.dense_score);
      hits = hits.map((hit) => ({ ...hit, sparse_score: null, sparse_rank: null, score: hit.dense_score }));
    } else if (mode === "sparse") {
      hits.sort((a, b) => b.sparse_score - a.sparse_score);
      hits = hits.map((hit) => ({ ...hit, dense_score: null, dense_rank: null, score: hit.sparse_score }));
    }
    if (body.filters?.lang) hits = hits.filter((hit) => hit.lang === body.filters.lang);
    if (body.filters?.block_type) hits = hits.filter((hit) => hit.block_type === body.filters.block_type);
    if (body.rerank === false) hits = hits.map((hit) => ({ ...hit, rerank_score: null }));

    return {
      query: body.question,
      search_query: body.question,
      mode,
      filters: body.filters || {},
      candidates_seen: 38,
      best_dense_score: 0.598,
      answerable: 0.91,
      reranked: body.rerank !== false,
      route_intent: "factual",
      route_in_domain: 0.97,
      hits: hits.slice(0, limit),
      context: "",
    };
  },

  syncRun(status) {
    return {
      run_id: "demo-run",
      status,
      origin: "local",
      started_at: iso(0),
      finished_at: status === "running" ? null : iso(0),
      duration_sec: status === "running" ? null : 41.6,
      files_seen: 28,
      documents_indexed: status === "running" ? 6 : 25,
      documents_skipped: status === "running" ? 0 : 3,
      documents_failed: 0,
      documents_deleted: 0,
      chunks_indexed: status === "running" ? 284 : 1184,
      force: false,
      errors: [],
    };
  },
};
