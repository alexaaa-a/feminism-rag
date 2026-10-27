from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, HTTPException, status

from src.application.dto.search import SearchRequest
from src.application.use_case.search.search_chunks import SearchChunksUseCase
from src.domain.entities.retrieval import RetrievalResult, ScoredChunk, SearchMode
from src.presentation.api.v1.search.schema import SearchHitOut, SearchIn, SearchOut

router = APIRouter(route_class=DishkaRoute)


def _hit_to_response(chunk: ScoredChunk) -> SearchHitOut:
    payload = chunk.payload
    return SearchHitOut(
        chunk_id=chunk.chunk_id,
        source=chunk.source,
        text=chunk.text,
        score=chunk.score,
        dense_score=chunk.dense_score,
        sparse_score=chunk.sparse_score,
        dense_rank=chunk.dense_rank,
        sparse_rank=chunk.sparse_rank,
        rerank_score=chunk.rerank_score,
        section=chunk.section,
        page=payload.get("page"),
        block_type=payload.get("block_type"),
        lang=payload.get("lang"),
        title=payload.get("title"),
        source_url=payload.get("source_url"),
    )


def _result_to_response(result: RetrievalResult) -> SearchOut:
    return SearchOut(
        query=result.query,
        search_query=result.search_query,
        mode=str(result.mode),
        filters=result.filters.as_dict(),
        candidates_seen=result.candidates_seen,
        best_dense_score=result.best_dense_score,
        answerable=result.answerable,
        reranked=result.reranked,
        route_intent=result.route.intent if result.route.used else None,
        route_in_domain=result.route.in_domain if result.route.used else None,
        hits=[_hit_to_response(chunk) for chunk in result.chunks],
        context=result.context,
    )


@router.post(
    "/search",
    status_code=status.HTTP_200_OK,
    response_model=SearchOut,
    description="Поиск по корпусу без генерации: фрагменты, скоры и собранный контекст",
)
async def search(
        body: SearchIn,
        uc: FromDishka[SearchChunksUseCase],
):
    mode: SearchMode | None = None
    if body.mode:
        try:
            mode = SearchMode(body.mode)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="mode может быть dense, sparse или hybrid",
            )

    result = await uc(
        SearchRequest(
            question=body.question,
            top_k=body.top_k,
            mode=mode,
            filters=body.filters.to_entity(),
            score_threshold=body.score_threshold,
            rerank=body.rerank,
            route=body.route,
            expand_to_parents=body.expand_to_parents,
        )
    )

    if result.retrieval is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message or "Не удалось выполнить поиск",
        )
    return _result_to_response(result.retrieval)
