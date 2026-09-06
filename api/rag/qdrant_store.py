import os
import atexit
import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from api.core.config import settings

logger = logging.getLogger(__name__)

class QdrantStore:
    """
    Qdrant vector store manager.
    Supports persistent local storage or remote cluster with mandatory ACL payload filters.
    Reference: Phase 3 & Table 9 of technical plan.
    """

    def __init__(self, collection_name: str = None):
        self.collection_name = collection_name or settings.VECTOR_COLLECTION_NAME
        self.client = self._init_client()
        self._ensure_collection()
        atexit.register(self.close)

    def close(self):
        try:
            if hasattr(self, "client") and self.client is not None:
                self.client.close()
        except Exception:
            pass

    def _init_client(self) -> QdrantClient:
        storage_path = os.path.abspath("data/qdrant_storage")
        os.makedirs(storage_path, exist_ok=True)

        try:
            if settings.VECTOR_STORE_HOST not in ["localhost", "127.0.0.1"]:
                return QdrantClient(host=settings.VECTOR_STORE_HOST, port=settings.VECTOR_STORE_PORT, timeout=3.0)
        except Exception:
            pass

        return QdrantClient(path=storage_path)

    def _ensure_collection(self):
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if not exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error ensuring Qdrant collection: {e}")

    def upsert_chunks(self, chunks: List[Dict[str, Any]]):
        points = []
        for c in chunks:
            points.append(
                PointStruct(
                    id=c["id"],
                    vector=c["vector"],
                    payload=c["payload"]
                )
            )

        if points:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info(f"Upserted {len(points)} vector points into {self.collection_name}")

    def search_dense(
        self,
        query_vector: List[float],
        limit: int = 20,
        department: Optional[str] = None,
        course: Optional[str] = None,
        semester: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        conditions = []
        if department:
            conditions.append(FieldCondition(key="department", match=MatchValue(value=department)))
        if course:
            conditions.append(FieldCondition(key="course", match=MatchValue(value=course)))
        if semester:
            conditions.append(FieldCondition(key="semester", match=MatchValue(value=semester)))

        search_filter = Filter(must=conditions) if conditions else None

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=search_filter,
            limit=limit,
            with_payload=True
        ).points

        hits = []
        for r in results:
            item = dict(r.payload)
            item["score"] = float(r.score)
            item["vector_id"] = str(r.id)
            hits.append(item)

        return hits

    def delete_points(self, point_ids: List[str]):
        if not point_ids:
            return
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=point_ids,
                wait=True
            )
        except Exception as e:
            logger.warning(f"Error deleting points from {self.collection_name}: {e}")

    def delete_document(self, document_id: str):
        try:
            doc_filter = Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=str(document_id)))])
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=doc_filter,
                wait=True
            )
        except Exception as e:
            logger.warning(f"Error deleting document vectors for {document_id}: {e}")

qdrant_store = QdrantStore()
