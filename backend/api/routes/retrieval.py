from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.services.offline_ingestion.chunking_service import chunk_text
from backend.services.offline_ingestion.embedding_service import EmbeddingService
from backend.services.offline_ingestion.vector_store import VectorStore

router = APIRouter(tags=["retrieval"])


@router.post("/ingest")
async def ingest_document(payload: dict, db: AsyncSession = Depends(get_db)):
    text = payload.get("text")
    if not text or not isinstance(text, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="text is required")

    chunks = chunk_text(text)
    store = VectorStore(db)
    embedding_service = EmbeddingService()
    created = []

    for idx, chunk in enumerate(chunks):
        chunk_record = await store.add_document(chunk, metadata={"chunk_index": idx})
        embedding = embedding_service.embed_text(chunk)
        await store.add_embedding(chunk_record.id, embedding)
        created.append({"id": chunk_record.id, "chunk_index": idx})

    return {"status": "ok", "chunks_created": len(created), "records": created}


@router.post("/retrieve")
async def retrieve_similar(payload: dict, db: AsyncSession = Depends(get_db)):
    query = payload.get("query")
    if not query or not isinstance(query, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="query is required")

    embedding_service = EmbeddingService()
    query_embedding = embedding_service.embed_text(query)
    store = VectorStore(db)
    matches = await store.search(query_embedding, limit=payload.get("limit", 5))
    return {
        "results": [
            {"id": item.id, "text": item.text, "metadata": item.metadata or {}} for item in matches
        ]
    }
