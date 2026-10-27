import math
from collections.abc import Sequence

from src.domain.entities.retrieval import ScoredChunk


def reciprocal_rank_fusion(
        dense: Sequence[ScoredChunk],
        sparse: Sequence[ScoredChunk],
        dense_weight: float = 1.0,
        sparse_weight: float = 0.7,
        rrf_k: int = 60,
) -> list[ScoredChunk]:
    merged: dict[str, ScoredChunk] = {}
    scores: dict[str, float] = {}

    for rank, chunk in enumerate(dense, start=1):
        merged[chunk.chunk_id] = chunk
        chunk.dense_rank = rank
        scores[chunk.chunk_id] = dense_weight / (rrf_k + rank)

    for rank, chunk in enumerate(sparse, start=1):
        existing = merged.get(chunk.chunk_id)
        if existing is None:
            merged[chunk.chunk_id] = chunk
            existing = chunk
        else:
            existing.sparse_score = chunk.sparse_score
        existing.sparse_rank = rank
        scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + sparse_weight / (rrf_k + rank)

    for chunk_id, chunk in merged.items():
        chunk.score = round(scores[chunk_id], 6)

    return sorted(merged.values(), key=lambda item: item.score, reverse=True)


def blend_rerank_scores(
        chunks: Sequence[ScoredChunk],
        rerank_weight: float,
) -> list[ScoredChunk]:
    ranked = sorted(chunks, key=lambda item: item.score, reverse=True)
    total = len(ranked)
    if total == 0:
        return []

    weight = min(max(rerank_weight, 0.0), 1.0)
    for rank, chunk in enumerate(ranked, start=1):
        retrieval_part = (total - rank + 1) / total
        rerank_part = chunk.rerank_score if chunk.rerank_score is not None else retrieval_part
        chunk.score = round(weight * rerank_part + (1.0 - weight) * retrieval_part, 6)

    return sorted(ranked, key=lambda item: item.score, reverse=True)


def maximal_marginal_relevance(
        chunks: Sequence[ScoredChunk],
        top_k: int,
        lambda_mult: float = 0.7,
) -> list[ScoredChunk]:
    candidates = [chunk for chunk in chunks if chunk.vector]
    without_vectors = [chunk for chunk in chunks if not chunk.vector]
    if not candidates:
        return list(chunks)[:top_k]

    selected: list[ScoredChunk] = []
    pool = list(candidates)

    while pool and len(selected) < top_k:
        best_chunk = pool[0]
        best_value = -math.inf
        for chunk in pool:
            penalty = max(
                (_cosine(chunk.vector, picked.vector) for picked in selected),
                default=0.0,
            )
            value = lambda_mult * chunk.score - (1.0 - lambda_mult) * penalty
            if value > best_value:
                best_value = value
                best_chunk = chunk
        selected.append(best_chunk)
        pool.remove(best_chunk)

    if len(selected) < top_k:
        selected.extend(without_vectors[: top_k - len(selected)])
    return selected


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)
