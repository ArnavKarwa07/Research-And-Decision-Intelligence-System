"""Qdrant client wrapper supporting collection creation, point upsert, dense vector search, and deletion."""
import logging
from typing import Any
import uuid

from app.config import settings

logger = logging.getLogger(__name__)


class QdrantService:
    """Wrapper around Qdrant client with fallback in-memory store for dev/testing."""

    def __init__(self, url: str | None = None, api_key: str | None = None):
        self.url = url or getattr(settings, "qdrant_url", "http://localhost:6333")
        self.api_key = api_key or getattr(settings, "qdrant_api_key", None)
        self._client = None
        self._mock_collections: dict[str, dict[str, Any]] = {}
        self._init_client()

    def _init_client(self) -> None:
        try:
            from qdrant_client import QdrantClient
            self._client = QdrantClient(url=self.url, api_key=self.api_key, timeout=5.0)
        except Exception as e:
            logger.warning(f"Could not connect to Qdrant at {self.url}. Using in-memory vector store fallback. Error: {e}")
            self._client = None

    def ensure_collection(
        self,
        collection_name: str,
        dimension: int = 1536,
        distance_metric: str = "Cosine",
    ) -> bool:
        """Ensure vector collection exists in Qdrant, creating it if necessary."""
        if self._client is not None:
            try:
                from qdrant_client.http import models as qmodels
                
                # Check if collection exists
                collections = self._client.get_collections().collections
                exists = any(c.name == collection_name for c in collections)
                
                if not exists:
                    metric = qmodels.Distance.COSINE
                    if distance_metric.lower() == "euclidean":
                        metric = qmodels.Distance.EUCLID
                    elif distance_metric.lower() == "dot":
                        metric = qmodels.Distance.DOT

                    self._client.create_collection(
                        collection_name=collection_name,
                        vectors_config=qmodels.VectorParams(
                            size=dimension,
                            distance=metric,
                        ),
                    )
                return True
            except Exception as e:
                logger.warning(f"Qdrant ensure_collection failed, falling back to mock store: {e}")
                self._client = None

        # Fallback mock store
        if collection_name not in self._mock_collections:
            self._mock_collections[collection_name] = {
                "dimension": dimension,
                "distance": distance_metric,
                "points": {},
            }
        return True

    def upsert_points(self, collection_name: str, points: list[dict[str, Any]]) -> bool:
        """Upsert points into Qdrant collection.

        Each point dict should contain:
        - 'id': str or UUID
        - 'vector': list[float]
        - 'payload': dict
        """
        if not points:
            return True

        if self._client is not None:
            try:
                from qdrant_client.http import models as qmodels

                q_points = []
                for pt in points:
                    pt_id = str(pt["id"])
                    # Ensure valid UUID string for Qdrant
                    try:
                        pt_id = str(uuid.UUID(pt_id))
                    except ValueError:
                        pt_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, pt_id))

                    q_points.append(
                        qmodels.PointStruct(
                            id=pt_id,
                            vector=pt["vector"],
                            payload=pt.get("payload", {}),
                        )
                    )

                self._client.upsert(
                    collection_name=collection_name,
                    points=q_points,
                )
                return True
            except Exception as e:
                logger.warning(f"Qdrant upsert_points failed, falling back to mock store: {e}")
                self._client = None

        # Fallback mock store
        self.ensure_collection(collection_name)
        coll = self._mock_collections[collection_name]["points"]
        for pt in points:
            pt_id = str(pt["id"])
            coll[pt_id] = {
                "id": pt_id,
                "vector": pt["vector"],
                "payload": pt.get("payload", {}),
            }
        return True

    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search vector collection with query vector."""
        if self._client is not None:
            try:
                from qdrant_client.http import models as qmodels

                q_filter = None
                if filter_dict:
                    must_conditions = []
                    for k, v in filter_dict.items():
                        must_conditions.append(
                            qmodels.FieldCondition(
                                key=k,
                                match=qmodels.MatchValue(value=v),
                            )
                        )
                    q_filter = qmodels.Filter(must=must_conditions)

                search_result = self._client.search(
                    collection_name=collection_name,
                    query_vector=query_vector,
                    query_filter=q_filter,
                    limit=limit,
                )

                results = []
                for res in search_result:
                    results.append({
                        "id": str(res.id),
                        "score": float(res.score),
                        "payload": res.payload or {},
                    })
                return results
            except Exception as e:
                logger.warning(f"Qdrant search failed, falling back to mock store: {e}")
                self._client = None

        # Fallback mock search
        if collection_name not in self._mock_collections:
            return []

        coll_points = self._mock_collections[collection_name]["points"]
        results = []

        import math
        norm_q = math.sqrt(sum(x * x for x in query_vector))

        for pt_id, pt in coll_points.items():
            payload = pt["payload"]
            p_vec = pt.get("vector", [])

            # Validate vector dimension match between query vector and point vectors
            if len(p_vec) != len(query_vector):
                logger.warning(
                    f"Vector dimension mismatch in search for point {pt_id}: "
                    f"query dim {len(query_vector)} vs point dim {len(p_vec)}"
                )
                continue

            # Apply basic filter check if present
            if filter_dict:
                match = True
                for k, v in filter_dict.items():
                    if payload.get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            dot = sum(a * b for a, b in zip(query_vector, p_vec))
            norm_p = math.sqrt(sum(x * x for x in p_vec))
            score = float(dot / (norm_q * norm_p)) if norm_q > 0 and norm_p > 0 else 0.0

            results.append({
                "id": pt_id,
                "score": score,
                "payload": payload,
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def delete_points(self, collection_name: str, point_ids: list[str]) -> bool:
        """Delete specific points from collection."""
        if not point_ids:
            return True

        if self._client is not None:
            try:
                from qdrant_client.http import models as qmodels
                formatted_ids = []
                for pid in point_ids:
                    try:
                        formatted_ids.append(str(uuid.UUID(pid)))
                    except ValueError:
                        formatted_ids.append(str(uuid.uuid5(uuid.NAMESPACE_DNS, pid)))

                self._client.delete(
                    collection_name=collection_name,
                    points_selector=qmodels.PointIdsList(points=formatted_ids),
                )
                return True
            except Exception as e:
                logger.warning(f"Qdrant delete_points failed: {e}")

        if collection_name in self._mock_collections:
            for pid in point_ids:
                self._mock_collections[collection_name]["points"].pop(pid, None)
        return True

    def delete_collection(self, collection_name: str) -> bool:
        """Delete an entire collection."""
        if self._client is not None:
            try:
                self._client.delete_collection(collection_name=collection_name)
                return True
            except Exception as e:
                logger.warning(f"Qdrant delete_collection failed: {e}")

        self._mock_collections.pop(collection_name, None)
        return True


# Singleton Qdrant service instance
qdrant_service = QdrantService()
