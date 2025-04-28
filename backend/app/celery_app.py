from celery import Celery
from app.core.config import settings

# Create Celery instance
celery_app = Celery(
    "app",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.services.payment_tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max task runtime
)

# Optional: Configure scheduled tasks
celery_app.conf.beat_schedule = {
    'check-pending-payments-every-5-minutes': {
        'task': 'app.services.payment_tasks.check_pending_payments',
        'schedule': 300.0,  # 5 minutes
    },
}