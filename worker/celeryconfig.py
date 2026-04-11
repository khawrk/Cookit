import os

from celery.schedules import crontab

broker_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
result_backend = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]
timezone = "UTC"
enable_utc = True

beat_schedule = {
    "scrape-recipes-nightly": {
        "task": "worker.tasks.scraper.crawl_all_sources",
        "schedule": crontab(hour=2, minute=0),
    },
    "generate-embeddings": {
        "task": "worker.tasks.embedder.embed_pending",
        "schedule": crontab(minute="*/30"),
    },
}

imports = [
    "worker.tasks.scraper",
    "worker.tasks.embedder",
]
