from datetime import timedelta

from celery import Celery

celery_app = Celery(
    "cinema_worker",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0",
    include=["src.celery.tasks"]
)


celery_app.conf.beat_schedule = {
    "send-daily-digest-every-morning": {
        "task": "src.celery.tasks.cleanup_tokens_task",
        "schedule": 60000.0
    },
    "check-expired-orders": {
        "task": "src.celery.tasks.check_status_order_task",
        "schedule": timedelta(minutes=10)
    }
}
celery_app.conf.timezone = "UTC"