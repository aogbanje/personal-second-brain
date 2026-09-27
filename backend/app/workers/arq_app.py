"""Arq worker entrypoint.

    arq app.workers.arq_app.WorkerSettings
"""

import logging

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.workers.tasks import ingest_document, startup

logging.basicConfig(level=logging.INFO)


class WorkerSettings:
    functions = [ingest_document]
    on_startup = startup
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    # Embedding is CPU-bound and the extraction calls fan out internally, so a
    # high concurrency here mostly buys contention.
    max_jobs = 2
    job_timeout = 900
    keep_result = 3600
