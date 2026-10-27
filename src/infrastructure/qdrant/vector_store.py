import logging
import uuid

from qdrant_client import AsyncQdrantClient, models

from src.application.interfaces.services.vector_store import VectorPoint, VectorStoreInterface
from src.config import Settings
from src.domain.entities.retrieval import RetrievalFilters, ScoredChunk

DENSE_VECTOR = "dense"
SPARSE_VECTOR = "bm25"
POINT_NAMESPACE = uuid.UUID("6f0f6f3a-1f4d-4a6b-9c2e-5a1f0c7d8e91")
INDEXED_PAYLOAD_FIELDS = ("source", "lang", "block_type", "format", "document_id")


def point_id_for(chunk_id: str) -> str:
    return str(uuid.uuid5(POINT_NAMESPACE, chunk_id))


class QdrantVectorStore(VectorStoreInterface):
    def __init__(
            self,
            client: AsyncQdrantClient,
            logger: logging.Logger,
            settings: Settings,
    ) -> None:
        self._client = client
        self._logger = logger
        self._settings = settings
        self._collection = settings.qdrant_settings.collection
        self._batch_size = settings.qdrant_settings.upsert_batch_size
        self._server_mode = bool(settings.qdrant_settings.url)

    async def ensure_collection(self, vector_size: int) -> bool:
        try:
            if not await self._client.collection_exists(self._collection):
                await self._client.create_collection(
                    collection_name=self._collection,
                    vectors_config={
                        DENSE_VECTOR: models.VectorParams(
                            size=vector_size,
                            distance=models.Distance.COSINE,
                        )
                    },
                    sparse_vectors_config={
                        SPARSE_VECTOR: models.SparseVectorParams(
                            modifier=models.Modifier.IDF,
                        )
                    },
                )
                self._logger.info(
                    "Created Qdrant collection %s with vector size %s",
                    self._collection,
                    vector_size,
                )
            await self._ensure_payload_indexes()
            return True
        except Exception:
            self._logger.exception("Failed to ensure Qdrant collection %s", self._collection)
            return False

    async def _ensure_payload_indexes(self) -> None:
        if not self._server_mode:
            self._logger.debug("Local Qdrant mode: payload indexes skipped")
            return

        for field_name in INDEXED_PAYLOAD_FIELDS:
            try:
                await self._client.create_payload_index(
                    collection_name=self._collection,
                    field_name=field_name,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
            except Exception:
                self._logger.debug("Payload index for %s already exists", field_name)

    async def upsert_points(self, points: list[VectorPoint]) -> bool:
        if not points:
            return True
        try:
            for start in range(0, len(points), self._batch_size):
                batch = points[start: start + self._batch_size]
                await self._client.upsert(
                    collection_name=self._collection,
                    points=[self._to_point_struct(point) for point in batch],
                    wait=True,
                )
            return True
        except Exception:
            self._logger.exception("Failed to upsert %s points", len(points))
            return False

    def _to_point_struct(self, point: VectorPoint) -> models.PointStruct:
        vector: dict[str, object] = {DENSE_VECTOR: point.dense}
        if point.sparse_indices:
            vector[SPARSE_VECTOR] = models.SparseVector(
                indices=point.sparse_indices,
                values=point.sparse_values,
            )
        return models.PointStruct(
            id=point_id_for(point.point_id),
            vector=vector,
            payload=point.payload,
        )

    async def search_dense(
            self,
            vector: list[float],
            limit: int,
            filters: RetrievalFilters | None = None,
            score_threshold: float | None = None,
            with_vectors: bool = False,
    ) -> list[ScoredChunk]:
        try:
            response = await self._client.query_points(
                collection_name=self._collection,
                query=vector,
                using=DENSE_VECTOR,
                query_filter=build_filter(filters),
                score_threshold=score_threshold,
                limit=max(limit, 1),
                with_payload=True,
                with_vectors=[DENSE_VECTOR] if with_vectors else False,
            )
            return [self._to_scored_chunk(point, dense=True) for point in response.points]
        except Exception:
            self._logger.exception("Dense search failed")
            return []

    async def search_sparse(
            self,
            indices: list[int],
            values: list[float],
            limit: int,
            filters: RetrievalFilters | None = None,
    ) -> list[ScoredChunk]:
        if not indices:
            return []
        try:
            response = await self._client.query_points(
                collection_name=self._collection,
                query=models.SparseVector(indices=indices, values=values),
                using=SPARSE_VECTOR,
                query_filter=build_filter(filters),
                limit=max(limit, 1),
                with_payload=True,
            )
            return [self._to_scored_chunk(point, dense=False) for point in response.points]
        except Exception:
            self._logger.exception("Sparse search failed")
            return []

    def _to_scored_chunk(self, point: models.ScoredPoint, dense: bool) -> ScoredChunk:
        payload = dict(point.payload or {})
        score = float(point.score)
        vector: list[float] = []
        if isinstance(point.vector, dict):
            raw_vector = point.vector.get(DENSE_VECTOR) or []
            if isinstance(raw_vector, list):
                vector = [float(value) for value in raw_vector]

        return ScoredChunk(
            chunk_id=str(payload.get("chunk_id") or point.id),
            text=str(payload.get("text") or ""),
            payload=payload,
            score=score,
            dense_score=score if dense else None,
            sparse_score=None if dense else score,
            vector=vector,
        )

    async def delete_by_document(self, document_id: str) -> bool:
        try:
            await self._client.delete(
                collection_name=self._collection,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="document_id",
                                match=models.MatchValue(value=document_id),
                            )
                        ]
                    )
                ),
                wait=True,
            )
            return True
        except Exception:
            self._logger.exception("Failed to delete points of document %s", document_id)
            return False

    async def count_points(self) -> int:
        try:
            if not await self._client.collection_exists(self._collection):
                return 0
            result = await self._client.count(
                collection_name=self._collection,
                exact=True,
            )
            return int(result.count)
        except Exception:
            self._logger.exception("Failed to count points")
            return 0

    async def health(self) -> bool:
        try:
            await self._client.get_collections()
            return True
        except Exception:
            self._logger.exception("Qdrant health check failed")
            return False


def build_filter(filters: RetrievalFilters | None) -> models.Filter | None:
    if filters is None or filters.empty:
        return None
    return models.Filter(
        must=[
            models.FieldCondition(key=key, match=models.MatchValue(value=value))
            for key, value in filters.as_dict().items()
        ]
    )
