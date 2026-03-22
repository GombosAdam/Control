"""
Generalized Qdrant vector store manager.
Handles all 4 collections, embedding generation via Ollama.
"""

import logging
import uuid
from typing import Any

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from common.config import settings

logger = logging.getLogger(__name__)

COLLECTIONS = {
    "invoice_fingerprints": {
        "dim": 768,
        "distance": Distance.COSINE,
    },
    "partner_embeddings": {
        "dim": 768,
        "distance": Distance.COSINE,
    },
    "text2sql_examples": {
        "dim": 768,
        "distance": Distance.COSINE,
    },
    "supplier_templates": {
        "dim": 768,
        "distance": Distance.COSINE,
    },
}

# Thresholds
PARTNER_MATCH_THRESHOLD = 0.85
DUPLICATE_THRESHOLD = 0.92
RAG_MIN_SCORE = 0.7
RAG_DEDUP_THRESHOLD = 0.95


class VectorStoreManager:
    """Manages all Qdrant collections and embedding generation."""

    def __init__(
        self,
        qdrant_url: str | None = None,
        ollama_url: str | None = None,
        embed_model: str = "nomic-embed-text",
    ):
        self._qdrant_url = qdrant_url or settings.QDRANT_URL
        self._ollama_url = ollama_url or settings.OLLAMA_URL
        self._embed_model = embed_model
        self._client: QdrantClient | None = None

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(url=self._qdrant_url, timeout=30)
        return self._client

    def ensure_collections(self) -> None:
        """Create all collections if they don't exist."""
        existing = {c.name for c in self.client.get_collections().collections}
        for name, cfg in COLLECTIONS.items():
            if name not in existing:
                self.client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(
                        size=cfg["dim"],
                        distance=cfg["distance"],
                    ),
                )
                logger.info("Created Qdrant collection: %s", name)

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding via Ollama /api/embed endpoint."""
        response = httpx.post(
            f"{self._ollama_url}/api/embed",
            json={"model": self._embed_model, "input": text},
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()
        embeddings = data.get("embeddings")
        if embeddings and len(embeddings) > 0:
            return embeddings[0]
        raise ValueError(f"No embeddings returned from Ollama: {data}")

    def store(
        self,
        collection: str,
        point_id: str,
        text: str,
        payload: dict[str, Any],
    ) -> None:
        """Embed text and store in the given collection."""
        vector = self.embed_text(text)
        self.client.upsert(
            collection_name=collection,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                ),
            ],
        )

    def store_with_vector(
        self,
        collection: str,
        point_id: str,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None:
        """Store a pre-computed vector in the given collection."""
        self.client.upsert(
            collection_name=collection,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                ),
            ],
        )

    def search(
        self,
        collection: str,
        text: str,
        top_k: int = 3,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Embed text and search the collection."""
        vector = self.embed_text(text)
        return self.search_by_vector(collection, vector, top_k, min_score)

    def search_by_vector(
        self,
        collection: str,
        vector: list[float],
        top_k: int = 3,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Search using a pre-computed vector."""
        results = self.client.search(
            collection_name=collection,
            query_vector=vector,
            limit=top_k,
            score_threshold=min_score,
        )
        return [
            {
                "id": str(r.id),
                "score": r.score,
                "payload": r.payload,
            }
            for r in results
        ]

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
