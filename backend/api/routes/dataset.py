from fastapi import APIRouter, HTTPException, status

from backend.services.dataset_ingestion import ingest_dataset_csv

router = APIRouter(tags=["dataset"])


@router.post("/dataset/load")
async def load_dataset(payload: dict):
    csv_path = payload.get("csv_path")
    if not csv_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="csv_path is required")

    result = await ingest_dataset_csv(csv_path)
    return result
