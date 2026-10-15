from __future__ import annotations

import asyncio
from pathlib import Path

from backend.core.migration_runner import create_all_tables
from backend.services.offline_ingestion.dataset_ingestion import ingest_dataset_csv


async def bootstrap_application() -> dict:
    await create_all_tables()
    dataset_path = Path(__file__).resolve().parent.parent / "data" / "raw" / "dataset.csv"
    if dataset_path.exists():
        result = await ingest_dataset_csv(dataset_path)
        return {"status": "ok", "database_initialized": True, "dataset_ingested": result}
    return {"status": "ok", "database_initialized": True, "dataset_ingested": {"status": "skipped", "reason": "dataset missing"}}


if __name__ == "__main__":
    print(asyncio.run(bootstrap_application()))
