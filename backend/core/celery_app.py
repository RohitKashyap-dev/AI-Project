from celery import Celery
from celery.app import trace as celery_trace
from celery.app.trace import prepare_accept_content

from backend.core.config import settings

celery_app = Celery(
    "scam_detector_worker",
    include=["backend.tasks.classify_task"],
)

celery_app.conf.update(
    broker_url=settings.REDIS_URL,
    result_backend=settings.REDIS_URL,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

celery_app.set_current()
celery_app.set_default()
celery_app.finalize()
celery_trace._localized[:] = [
    celery_app._tasks,
    prepare_accept_content(celery_app.conf.accept_content),
    celery_trace.gethostname(),
]
celery_app.use_fast_trace_task = True
