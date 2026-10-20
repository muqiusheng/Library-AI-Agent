import re
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import chromadb

import threading

from app.core.config import get_settings
from app.integrations.embeddings.base import EmbeddingProvider

_chroma_lock = threading.Lock()
_shared_client = None


@dataclass(frozen=True)
class VectorHit:
    book_id: UUID
    score: float


class ChromaVectorStore:
    def __init__(
        self, embedding_provider: EmbeddingProvider, persist_directory: Path | None = None
    ) -> None:
        global _shared_client
        settings = get_settings()
        self.embedding_provider = embedding_provider
        self.persist_directory = persist_directory or settings.chroma_persist_directory
        self.prefix = settings.chroma_collection_prefix
        
        with _chroma_lock:
            if _shared_client is None:
                self.persist_directory.mkdir(parents=True, exist_ok=True)
                _shared_client = chromadb.PersistentClient(path=str(self.persist_directory))
            self.client = _shared_client

    def collection_name(self, data_version_id: UUID) -> str:
        prefix = re.sub(r"[^a-zA-Z0-9_-]", "_", self.prefix)[:24]
        return f"{prefix}_{data_version_id.hex}"

    def upsert(
        self,
        *,
        data_version_id: UUID,
        book_ids: list[UUID],
        documents: list[str],
        metadata: list[dict],
    ) -> int:
        if not book_ids:
            return 0
        collection = self.client.get_or_create_collection(
            self.collection_name(data_version_id),
            metadata={
                "data_version": str(data_version_id),
                "model": self.embedding_provider.model_name,
            },
        )
        embeddings = self.embedding_provider.embed_documents(documents)
        collection.upsert(
            ids=[str(book_id) for book_id in book_ids],
            documents=documents,
            metadatas=metadata,
            embeddings=embeddings,
        )
        return len(book_ids)

    def query(self, *, data_version_id: UUID, text: str, limit: int = 40) -> list[VectorHit]:
        try:
            collection = self.client.get_collection(self.collection_name(data_version_id))
        except Exception:
            return []
        result = collection.query(
            query_embeddings=[self.embedding_provider.embed_query(text)],
            n_results=min(limit, max(1, collection.count())),
        )
        hits: list[VectorHit] = []
        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]
        for raw_id, distance in zip(ids, distances, strict=False):
            try:
                hits.append(VectorHit(book_id=UUID(raw_id), score=max(0.0, 1.0 - float(distance))))
            except (TypeError, ValueError):
                continue
        return hits

    def count(self, data_version_id: UUID) -> int:
        try:
            return self.client.get_collection(self.collection_name(data_version_id)).count()
        except Exception:
            return 0
