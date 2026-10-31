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
        "schedule": 60.0
    },
}
celery_app.conf.timezone = "UTC"