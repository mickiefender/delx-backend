from __future__ import annotations

import logging
import os

from celery import Celery
from celery.exceptions import MaxRetriesExceededError
from celery.utils.log import get_task_logger

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

logger = get_task_logger(__name__)


class CeleryApp:
    """Celery application instance."""

    def __init__(self):
        self.app = Celery("config")
        # Load Celery config from Django settings, using the `CELERY_` namespace
        self.app.config_from_object("django.conf:settings", namespace="CELERY")
        # Auto-discover tasks.py modules in installed apps
        self.app.autodiscover_tasks()

    @property
    def config(self):
        return self.app.conf


app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


class BaseTaskWithRetry(app.Task):
    """
    Base task class with retry logic and error handling.
    
    Provides common retry patterns for tasks that may fail temporarily.
    """

    # Default retry settings
    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 600  # 10 minutes max backoff
    retry_jitter = True
    max_retries = 3

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails after all retries exhausted."""
        logger.error(
            f"Task {self.name}[{task_id}] failed permanently: {exc}",
            exc_info=exc,
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)

    def retry_with_backoff(self, exc, args=None, kwargs=None, countdown=None):
        """
        Retry with exponential backoff.
        
        Args:
            exc: The exception that caused the retry
            args: Positional args for the task
            kwargs: Keyword args for the task
            countdown: Custom countdown (overrides automatic backoff)
        """
        try:
            return self.retry(
                exc=exc,
                args=args,
                kwargs=kwargs,
                countdown=countdown,
                max_retries=self.max_retries,
            )
        except MaxRetriesExceededError:
            logger.error(
                f"Task {self.name} exceeded max retries ({self.max_retries})",
                exc_info=exc,
            )
            raise


@app.task(bind=True, base=BaseTaskWithRetry, max_retries=3)
def debug_task(self):
    """Debug task to test Celery connectivity."""
    logger.info(f"Debug task executed at {self.request.id}")
    return {"status": "ok", "task_id": self.request.id}
