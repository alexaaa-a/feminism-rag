import asyncio
import contextlib
import logging
import time

from src.application.dto.search import SearchRequest
from src.application.interfaces.db.parent_db import ParentChunkDBInterface
from src.application.interfaces.services.decider import (
    AnswerJudgeInterface,
    QueryRouterInterface,
    RerankerInterface,
)
from src.application.interfaces.services.embedder import EmbedderInterface
from src.application.interfaces.services.vector_store import VectorStoreInterface
from src.config import Settings
from src.domain.entities.retrieval import (
    QueryRoute,
    RetrievalFilters,
    RetrievalResult,
    ScoredChunk,
    SearchMode,
)
from src.domain.services.fusion import (
    blend_rerank_scores,
    maximal_marginal_relevance,
    reciprocal_rank_fusion,
)
from src.domain.services.prompting import ContextBlock, build_context
from src.domain.services.tokenization import Bm25Encoder

TABLE_SPARSE_BOOST = 1.6


class RetrievalPipeline:
    def __init__(
            self,
            embedder: EmbedderInterface,
            vector_store: VectorStoreInterface,
            parent_db: ParentChunkDBInterface,
            query_router: QueryRouterInterface,
            reranker: RerankerInterface,
            answer_judge: AnswerJudgeInterface,
            bm25: Bm25Encoder,
            logger: logging.Logger,
            settings: Settings,
    ) -> None:
        self._embedder = embedder
        self._vector_store = vector_store
        self._parent_db = parent_db
        self._query_router = query_router
        self._reranker = reranker
        self._answer_judge = answer_judge
        self._bm25 = bm25
        self._logger = logger
        self._settings = settings.retrieval_settings
        self._jev_settings = settings.jev_settings

    async def retrieve(self, request: SearchRequest) -> RetrievalResult:
        question = request.question.strip()
        top_k = request.top_k or self._settings.top_k
        mode = request.mode or (
            SearchMode.HYBRID if self._settings.hybrid else SearchMode.DENSE
        )

        stage = _Stopwatch()
        embedding = (
            asyncio.create_task(self._embedder.embed_query(question))
            if mode in {SearchMode.DENSE, SearchMode.HYBRID}
            else None
        )

        try:
            route = await self._route(question, request)
        except BaseException:
            await _discard(embedding)
            raise

        filters = self._apply_route(request.filters, route)
        stage.mark("route")

        result = RetrievalResult(
            query=question,
            search_query=question,
            mode=mode,
            filters=filters,
            route=route,
        )

        if route.out_of_domain:
            await _discard(embedding)
            self._logger.info("Query routed as out of domain: in_domain=%s", route.in_domain)
            return result

        dense, sparse = await self._search(question, mode, filters, embedding)
        stage.mark("search")
        result.candidates_seen = len({chunk.chunk_id for chunk in dense + sparse})
        result.best_dense_score = max((chunk.dense_score or 0.0 for chunk in dense), default=None)

        candidates = self._merge(dense, sparse, mode, route)
        if not candidates:
            return result

        threshold = (
            request.score_threshold
            if request.score_threshold is not None
            else self._settings.dense_score_threshold
        )
        if not self._passes_threshold(result.best_dense_score, threshold):
            self._logger.info(
                "All candidates below dense threshold: best=%s threshold=%s",
                result.best_dense_score,
                threshold,
            )
            return result

        candidates, reranked = await self._rerank(question, candidates, request)
        result.reranked = reranked
        stage.mark("rerank")

        selected = self._select(candidates, top_k)
        result.chunks = selected

        blocks = await self._context_blocks(selected, request)
        result.context = build_context(blocks, self._settings.max_context_chars)
        stage.mark("parents")

        result.answerable = await self._answer_judge.is_answerable(question, result.context)
        stage.mark("gate")

        self._logger.info("Retrieval stages, мс: %s", stage.report())
        return result

    async def _route(self, question: str, request: SearchRequest) -> QueryRoute:
        if request.route is False:
            return QueryRoute()
        route = await self._query_router.route(question)
        return route or QueryRoute()

    def _apply_route(
            self,
            filters: RetrievalFilters,
            route: QueryRoute,
    ) -> RetrievalFilters:
        if filters.lang or not route.used or not route.lang_preference:
            return filters
        return RetrievalFilters(
            source=filters.source,
            lang=route.lang_preference,
            block_type=filters.block_type,
            document_format=filters.document_format,
            document_id=filters.document_id,
        )

    async def _search(
            self,
            question: str,
            mode: SearchMode,
            filters: RetrievalFilters,
            embedding: asyncio.Task[list[float]] | None = None,
    ) -> tuple[list[ScoredChunk], list[ScoredChunk]]:
        tasks = []
        want_dense = mode in {SearchMode.DENSE, SearchMode.HYBRID}
        want_sparse = mode in {SearchMode.SPARSE, SearchMode.HYBRID}

        if want_dense:
            tasks.append(self._dense_search(question, filters, embedding))
        if want_sparse:
            tasks.append(self._sparse_search(question, filters))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        collected: list[list[ScoredChunk]] = []
        for item in results:
            if isinstance(item, BaseException):
                self._logger.exception("Search leg failed", exc_info=item)
                collected.append([])
            else:
                collected.append(item)

        dense = collected.pop(0) if want_dense else []
        sparse = collected.pop(0) if want_sparse else []
        return dense, sparse

    async def _dense_search(
            self,
            question: str,
            filters: RetrievalFilters,
            embedding: asyncio.Task[list[float]] | None = None,
    ) -> list[ScoredChunk]:
        vector = (
            await embedding
            if embedding is not None
            else await self._embedder.embed_query(question)
        )
        return await self._vector_store.search_dense(
            vector=vector,
            limit=self._settings.candidates_dense,
            filters=filters,
            with_vectors=self._settings.use_mmr,
        )

    async def _sparse_search(
            self,
            question: str,
            filters: RetrievalFilters,
    ) -> list[ScoredChunk]:
        indices, values = self._bm25.encode_query(question)
        return await self._vector_store.search_sparse(
            indices=indices,
            values=values,
            limit=self._settings.candidates_sparse,
            filters=filters,
        )

    def _merge(
            self,
            dense: list[ScoredChunk],
            sparse: list[ScoredChunk],
            mode: SearchMode,
            route: QueryRoute,
    ) -> list[ScoredChunk]:
        if mode is SearchMode.DENSE:
            return dense
        if mode is SearchMode.SPARSE:
            return sparse

        sparse_weight = self._settings.sparse_weight
        if route.used and route.needs_table > 0.5:
            sparse_weight *= TABLE_SPARSE_BOOST

        return reciprocal_rank_fusion(
            dense=dense,
            sparse=sparse,
            dense_weight=self._settings.dense_weight,
            sparse_weight=sparse_weight,
            rrf_k=self._settings.rrf_k,
        )

    def _passes_threshold(self, best_dense_score: float | None, threshold: float) -> bool:
        if threshold <= 0 or best_dense_score is None:
            return True
        return best_dense_score >= threshold

    async def _rerank(
            self,
            question: str,
            candidates: list[ScoredChunk],
            request: SearchRequest,
    ) -> tuple[list[ScoredChunk], bool]:
        if request.rerank is False:
            return candidates, False

        limit = self._jev_settings.rerank_candidates
        head = candidates[:limit]
        tail = candidates[limit:]
        scores = await self._reranker.score_candidates(
            question,
            [chunk.text for chunk in head],
        )
        if scores is None or len(scores) != len(head):
            return candidates, False

        for chunk, score in zip(head, scores):
            chunk.rerank_score = round(float(score), 6)

        relevant = [
            chunk
            for chunk in head
            if (chunk.rerank_score or 0.0) >= self._jev_settings.relevant_threshold
        ]
        ordered = blend_rerank_scores(
            relevant or head,
            self._jev_settings.rerank_weight,
        )
        return ordered + tail, True

    def _select(self, candidates: list[ScoredChunk], top_k: int) -> list[ScoredChunk]:
        best_by_parent: dict[str, ScoredChunk] = {}
        unique: list[ScoredChunk] = []

        for chunk in candidates:
            parent_id = chunk.parent_id
            if not parent_id:
                unique.append(chunk)
                continue
            current = best_by_parent.get(parent_id)
            if current is None or chunk.score > current.score:
                best_by_parent[parent_id] = chunk

        unique.extend(best_by_parent.values())
        unique.sort(key=lambda item: item.score, reverse=True)

        if self._settings.use_mmr and len(unique) > top_k:
            return maximal_marginal_relevance(
                unique,
                top_k=top_k,
                lambda_mult=self._settings.mmr_lambda,
            )
        return unique[:top_k]

    async def _context_blocks(
            self,
            chunks: list[ScoredChunk],
            request: SearchRequest,
    ) -> list[ContextBlock]:
        expand = (
            self._settings.expand_to_parents
            if request.expand_to_parents is None
            else request.expand_to_parents
        )
        parents = {}
        if expand:
            parent_ids = [chunk.parent_id for chunk in chunks if chunk.parent_id]
            parents = await self._parent_db.get_parents(parent_ids)

        blocks: list[ContextBlock] = []
        for index, chunk in enumerate(chunks, start=1):
            parent = parents.get(chunk.parent_id or "")
            text = parent.text if parent is not None else chunk.text
            blocks.append(
                ContextBlock(
                    index=index,
                    text=text,
                    source=chunk.source,
                    section=chunk.section,
                    page=chunk.payload.get("page"),
                    title=chunk.payload.get("title"),
                )
            )
        return blocks


class _Stopwatch:
    def __init__(self) -> None:
        self._last = time.perf_counter()
        self._stages: list[tuple[str, int]] = []

    def mark(self, name: str) -> None:
        now = time.perf_counter()
        self._stages.append((name, int((now - self._last) * 1000)))
        self._last = now

    def report(self) -> str:
        return ", ".join(f"{name}={value}" for name, value in self._stages)


async def _discard(task: asyncio.Task | None) -> None:
    if task is None:
        return
    task.cancel()
    with contextlib.suppress(BaseException):
        await task
