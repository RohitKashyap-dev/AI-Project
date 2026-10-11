from fastapi import APIRouter

from backend.core.migration_runner import create_all_tables

router = APIRouter(tags=["bootstrap"])


@router.post("/bootstrap")
async def bootstrap_database():
    await create_all_tables()
    return {"status": "ok", "message": "Database tables initialized."}
