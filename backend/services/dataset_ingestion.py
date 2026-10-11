from __future__ import annotations

import pandas as pd
from pathlib import Path

from backend.core.monitoring import track_dataset_ingestion
from backend.db.session import AsyncSessionLocal
from backend.services.chunking_service import chunk_text
from backend.services.embedding_service import EmbeddingService
from backend.services.vector_store import VectorStore


async def ingest_dataset_csv(csv_path: str | Path, source_name: str = "dataset") -> dict:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    df = pd.read_csv(path)
    records = df.to_dict("records")

    if not records:
        track_dataset_ingestion(0, 0)
        return {"status": "ok", "chunks_created": 0, "source": str(path)}

    async with AsyncSessionLocal() as session:
        store = VectorStore(session)
        embedding_service = EmbeddingService()
        created = 0

        for row in records:
            message = str(row.get("message_text") or "").strip()
            if not message:
                continue

            labels = {
                "label": row.get("label"),
                "intent_type": row.get("intent_type"),
                "flag_reason": row.get("flag_reason"),
                "source": source_name,
            }

            for index, chunk in enumerate(chunk_text(message, chunk_size=500, overlap=50)):
                stored = await store.add_document(chunk, metadata={**labels, "chunk_index": index})
                embedding = embedding_service.embed_text(chunk)
                await store.add_embedding(stored.id, embedding)
                created += 1

        await session.commit()

    track_dataset_ingestion(len(records), created)
    return {"status": "ok", "chunks_created": created, "source": str(path)}
