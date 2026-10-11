from fastapi import APIRouter

from backend.core.monitoring import metrics_payload

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def metrics_endpoint():
    payload, content_type = metrics_payload()
    return payload
