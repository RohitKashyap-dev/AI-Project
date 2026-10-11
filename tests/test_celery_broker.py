from celery.app import trace as celery_trace

from backend.core.celery_app import celery_app
from backend.tasks.classify_task import classify_message_task


def test_task_uses_project_celery_app():
    assert classify_message_task.app is celery_app
    assert classify_message_task.app.connection().as_uri() == "redis://localhost:6379/0"
    assert len(celery_trace._localized) == 3
