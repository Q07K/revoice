import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class JobRunner:
    """Runs long-lived jobs (training, cover rendering) off the request thread.

    Job functions own their error handling and persist failures to the DB;
    this wrapper only guards against bugs escaping a job silently.
    """

    def __init__(self, max_workers: int) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="revoice-job"
        )

    def submit(self, task: Callable[[], None]) -> None:
        self._executor.submit(_run_safely, task)


def _run_safely(task: Callable[[], None]) -> None:
    try:
        task()
    except Exception:
        logger.exception("Background job crashed without persisting its failure state.")


@lru_cache
def get_job_runner() -> JobRunner:
    return JobRunner(max_workers=get_settings().job_workers)
