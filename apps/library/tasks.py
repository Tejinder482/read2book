from celery import shared_task
from django.conf import settings
from django.db import close_old_connections, transaction
import logging
import threading

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def process_book_task(self, book_id: int):
    from .services import process_book

    try:
        process_book(book_id)
    except Exception as exc:
        logger.exception("Failed processing book %s", book_id)
        raise self.retry(exc=exc, countdown=5)


def _run_process_in_thread(book_id: int) -> None:
    """Background processing for local/eager mode so upload returns immediately."""
    close_old_connections()
    try:
        from .services import process_book

        process_book(book_id)
    except Exception:
        logger.exception("Background processing failed for book %s", book_id)
    finally:
        close_old_connections()


def enqueue_book_processing(book_id: int) -> None:
    """
    Schedule PDF processing without blocking the HTTP response.
    - Celery worker mode: .delay()
    - Eager/local mode: daemon thread (upload stays fast)
    """

    def _enqueue():
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", True):
            threading.Thread(
                target=_run_process_in_thread,
                args=(book_id,),
                daemon=True,
                name=f"process-book-{book_id}",
            ).start()
        else:
            process_book_task.delay(book_id)

    transaction.on_commit(_enqueue)
