"""
Qdrant RAG store for text-to-SQL examples.
Now integrated with the main chat pipeline via VectorStoreManager.
"""

from typing import Any

import httpx

from common.config import settings


class Text2SqlStore:
    """Qdrant vector store for text-to-SQL example pairs."""

    COLLECTION = settings.QDRANT_COLLECTION
    VECTOR_DIM = 768  # nomic-embed-text dimension

    def __init__(self) -> None:
        from qdrant_client import QdrantClient

        self._client = QdrantClient(url=settings.QDRANT_URL)

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding via Ollama /api/embed endpoint."""
        response = httpx.post(
            f"{settings.OLLAMA_URL}/api/embed",
            json={"model": settings.EMBEDDING_MODEL, "input": text},
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()
        embeddings = data.get("embeddings")
        if embeddings and len(embeddings) > 0:
            return embeddings[0]
        raise ValueError(f"No embeddings returned from Ollama: {data}")

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
        """Store a successful question→SQL pair with its embedding.
        Includes dedup: skips if a very similar example already exists.
        """
        from qdrant_client.models import PointStruct

        # Dedup check
        existing = self._client.search(
            collection_name=self.COLLECTION,
            query_vector=embedding,
            limit=1,
            score_threshold=settings.RAG_DEDUP_THRESHOLD,
        )
        if existing:
            return  # Similar example already exists

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
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Find the most similar question→SQL examples."""
        results = self._client.search(
            collection_name=self.COLLECTION,
            query_vector=embedding,
            limit=top_k,
            score_threshold=min_score,
        )
        return [
            {"question": r.payload["question"], "sql": r.payload["sql"], "score": r.score}
            for r in results
        ]
