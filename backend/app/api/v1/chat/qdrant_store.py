"""
Qdrant RAG store for text-to-SQL examples.
Phase 2 — prepared but not yet called from the main pipeline.
"""

from typing import Any

from app.config import settings


class Text2SqlStore:
    """Qdrant vector store for text-to-SQL example pairs."""

    COLLECTION = settings.QDRANT_COLLECTION
    VECTOR_DIM = 768  # nomic-embed-text dimension

    def __init__(self) -> None:
        from qdrant_client import QdrantClient

        self._client = QdrantClient(url=settings.QDRANT_URL)

    async def ensure_collection(self) -> None:
        """Create the collection if it doesn't exist."""
        from qdrant_client.models import Distance, VectorParams

        collections = self._client.get_collections().collections
        if not any(c.name == self.COLLECTION for c in collections):
            self._client.create_collection(
                collection_name=self.COLLECTION,
                vectors_config=VectorParams(
                    size=self.VECTOR_DIM,
                    distance=Distance.COSINE,
                ),
            )

    async def store_example(
        self,
        question: str,
        sql: str,
        embedding: list[float],
        point_id: int | None = None,
    ) -> None:
        """Store a successful question→SQL pair with its embedding."""
        import uuid

        from qdrant_client.models import PointStruct

        pid = point_id or abs(hash(question)) % (2**63)
        self._client.upsert(
            collection_name=self.COLLECTION,
            points=[
                PointStruct(
                    id=pid,
                    vector=embedding,
                    payload={"question": question, "sql": sql},
                )
            ],
        )

    async def find_similar(
        self,
        embedding: list[float],
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """Find the most similar question→SQL examples."""
        results = self._client.search(
            collection_name=self.COLLECTION,
            query_vector=embedding,
            limit=top_k,
        )
        return [
            {"question": r.payload["question"], "sql": r.payload["sql"], "score": r.score}
            for r in results
        ]
