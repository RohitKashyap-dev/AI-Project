import asyncio
from pathlib import Path

from backend.services.offline_ingestion.dataset_ingestion import ingest_dataset_csv


async def main():
    root = Path(__file__).resolve().parent.parent
    csv_path = root / "data" / "raw" / "dataset.csv"
    result = await ingest_dataset_csv(csv_path)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
