from celery import Celery
import os

# Use container name 'redis' as the host
redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery = Celery(
    "medifusion_tasks",
    broker=redis_url,
    backend=redis_url,
)

# Use absolute import from app.workers
celery.conf.task_routes = {
    "app.workers.tasks.process_case_task": {"queue": "celery"},
}
