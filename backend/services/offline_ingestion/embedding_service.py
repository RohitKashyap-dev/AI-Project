from __future__ import annotations

import math
from typing import Iterable


class EmbeddingService:
    """Minimal production-ready embedding abstraction.

    In production, this should use a hosted embedding model such as Gemini
    embeddings, OpenAI embeddings, or a sentence-transformers model run in a
    dedicated service. This scaffold keeps it explicit and lightweight.
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name

    def embed_text(self, text: str) -> list[float]:
        try:
            from sentence_transformers import SentenceTransformer
        except Exception:
            return self._fallback_embedding(text)

        if not hasattr(self, "_model"):
            self._model = SentenceTransformer(self.model_name)
        vector = self._model.encode(text)
        return [float(v) for v in vector]

    def embed_many(self, texts: Iterable[str]) -> list[list[float]]:
        return [self.embed_text(text) for text in texts]

    @staticmethod
    def _fallback_embedding(text: str) -> list[float]:
        tokens = [token.lower() for token in text.replace("\n", " ").split() if token]
        if not tokens:
            return [0.0] * 384

        vector = [0.0] * 384
        for i, token in enumerate(tokens[:384]):
            score = 1.0 + (len(token) / 10.0)
            vector[i % 384] = score * (1.0 if i % 2 == 0 else -1.0)
        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0:
            return [0.0] * 384
        return [v / norm for v in vector]
