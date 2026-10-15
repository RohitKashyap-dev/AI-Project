from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.services.online_ingestion.retrieval_service import RetrievalService

router = APIRouter(tags=["vector"])


@router.post("/index")
async def index_document(payload: dict, db: AsyncSession = Depends(get_db)):
    text = payload.get("text")
    metadata = payload.get("metadata")
    if not text or not isinstance(text, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="text is required")
    service = RetrievalService(db)
    chunk_id = await service.index_text(text, metadata=metadata)
    return {"chunk_id": chunk_id, "status": "indexed"}


@router.post("/search")
async def search_vector(payload: dict, db: AsyncSession = Depends(get_db)):
    query = payload.get("query")
    if not query or not isinstance(query, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="query is required")
    service = RetrievalService(db)
    matches = await service.search_similar(query, limit=payload.get("limit", 5))
    return {
        "results": [
            {"id": item.id, "text": item.text, "metadata": item.metadata} for item in matches
        ]
    }
