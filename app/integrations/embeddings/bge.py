import hashlib
import math
from collections.abc import Iterable

from app.core.config import get_settings


class BGEEmbeddingProvider:
    """Lazy BGE provider with an explicit deterministic offline fallback."""

    def __init__(self, model_name: str | None = None, *, dimension: int = 384) -> None:
        self._model_name = model_name or get_settings().embedding_model
        self.dimension = dimension
        self._model = None
        self._load_attempted = False

    @property
    def model_name(self) -> str:
        return self._model_name if self._model is not None else f"{self._model_name}:hash-fallback"

    def _load(self):
        if self._load_attempted:
            return self._model
        self._load_attempted = True
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name, local_files_only=True)
        except (ImportError, OSError):
            self._model = None
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        if model is not None:
            values = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
            return [value.tolist() for value in values]
        return [self._hash_embedding(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def _hash_embedding(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        normalized = "".join(text.casefold().split())
        tokens = list(self._ngrams(normalized, 2)) + list(self._ngrams(normalized, 3))
        for token in tokens or [normalized]:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    @staticmethod
    def _ngrams(text: str, size: int) -> Iterable[str]:
        return (text[index : index + size] for index in range(max(0, len(text) - size + 1)))
