"""In-process cancellation for background jobs.

A job requests cancellation by id; the worker thread running that job polls
`is_cancel_requested` at safe points (e.g. between subprocess output lines) and
tears down its child process tree when it sees the flag.
"""

import threading

_lock = threading.Lock()
_cancel_requested: set[int] = set()


def request_cancel(job_id: int) -> None:
    with _lock:
        _cancel_requested.add(job_id)


def is_cancel_requested(job_id: int) -> bool:
    with _lock:
        return job_id in _cancel_requested


def clear(job_id: int) -> None:
    with _lock:
        _cancel_requested.discard(job_id)
