import os
from celery import Celery
from api.core.config import settings

broker_url = os.getenv("CELERY_BROKER_URL", settings.REDIS_URL)
result_backend = os.getenv("CELERY_RESULT_BACKEND", settings.REDIS_URL)

always_eager = False
if "localhost" in broker_url or "127.0.0.1" in broker_url:
    try:
        import redis
        r = redis.from_url(broker_url, socket_timeout=0.5)
        r.ping()
    except Exception:
        always_eager = True

if always_eager:
    broker_url = "memory://"
    result_backend = "cache+memory://"

celery_app = Celery(
    "university_rag_workers",
    broker=broker_url,
    backend=result_backend,
    include=[
        "workers.ingest_tasks",
        "workers.ocr_tasks",
        "workers.embed_tasks",
        "workers.index_tasks",
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    worker_concurrency=settings.MAX_CONCURRENT_INGESTION_JOBS,
    task_always_eager=always_eager,
    task_eager_propagates=True,
)
