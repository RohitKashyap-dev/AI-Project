from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models.knowledge_chunk import KnowledgeChunk

try:
    from pinecone import Pinecone
except ImportError:  # pragma: no cover - handled at runtime when Pinecone is disabled
    Pinecone = None


class VectorStore:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.use_pinecone = str(getattr(settings, "VECTOR_BACKEND", "pgvector")).lower() == "pinecone"
        self._pinecone_index = None
        self._pinecone_documents: dict[str, dict[str, Any]] = {}

    @property
    def pinecone_index(self):
        if not self.use_pinecone:
            return None
        if Pinecone is None:
            raise RuntimeError("pinecone package is not installed")
        if self._pinecone_index is None:
            api_key = getattr(settings, "PINECONE_API_KEY", None)
            if not api_key:
                raise RuntimeError("PINECONE_API_KEY is not set")
            self._pinecone_index = Pinecone(api_key=api_key).Index(getattr(settings, "PINECONE_INDEX_NAME", "scam-detector"))
        return self._pinecone_index

    async def add_document(self, text: str, metadata: dict[str, Any] | None = None) -> Any:
        if self.use_pinecone:
            document_metadata = dict(metadata or {})
            document_metadata.setdefault("text", text)
            chunk_id = str(document_metadata.get("id") or uuid.uuid4())
            self._pinecone_documents[chunk_id] = document_metadata
            return SimpleNamespace(
                id=chunk_id,
                text=text,
                metadata=document_metadata,
                source=document_metadata.get("source"),
            )

        chunk = KnowledgeChunk(
            text=text,
            metadata=metadata or {},
            source=metadata.get("source") if isinstance(metadata, dict) else None,
        )
        self.session.add(chunk)
        await self.session.commit()
        await self.session.refresh(chunk)
        return chunk

    async def add_embedding(self, chunk_id: int | str, embedding: list[float], metadata: dict[str, Any] | None = None) -> None:
        if self.use_pinecone:
            document_metadata = self._pinecone_documents.get(str(chunk_id), {})
            if metadata is not None:
                document_metadata = {**document_metadata, **metadata}
            record = {"id": str(chunk_id), "values": embedding, "metadata": {"text": document_metadata.get("text", ""), **document_metadata}}
            self.pinecone_index.upsert(vectors=[record])
            return

        chunk = await self.session.get(KnowledgeChunk, chunk_id)
        if chunk is None:
            raise ValueError(f"Chunk {chunk_id} not found")
        chunk.embedding = embedding
        await self.session.commit()

    async def search(self, query_embedding: list[float], limit: int = 5):
        if self.use_pinecone:
            results = self.pinecone_index.query(vector=query_embedding, top_k=limit, include_metadata=True)
            matches = []
            for item in results.get("matches", []):
                metadata = dict(item.get("metadata") or {})
                text = metadata.get("text")
                matches.append(
                    SimpleNamespace(
                        id=item.get("id"),
                        text=text,
                        metadata=metadata,
                        score=item.get("score"),
                    )
                )
            return matches

        stmt = (
            select(KnowledgeChunk)
            .where(KnowledgeChunk.embedding.is_not(None))
            .order_by(KnowledgeChunk.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
