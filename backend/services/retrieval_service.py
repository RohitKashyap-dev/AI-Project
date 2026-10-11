from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.embedding_service import EmbeddingService
from backend.services.vector_store import VectorStore


class RetrievalService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore(session)

    async def index_text(self, text: str, metadata: dict | None = None) -> int:
        chunk = await self.vector_store.add_document(text, metadata=metadata)
        embedding = self.embedding_service.embed_text(text)
        await self.vector_store.add_embedding(chunk.id, embedding)
        return chunk.id

    async def search_similar(self, text: str, limit: int = 5):
        embedding = self.embedding_service.embed_text(text)
        return await self.vector_store.search(embedding, limit=limit)
