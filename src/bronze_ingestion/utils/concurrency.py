"""
Concurrency utilities for orchestrating per-table ingestion tasks.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, Future
from contextlib import contextmanager
from typing import Callable, Iterable, Iterator, Tuple


class CancellationToken:
    def __init__(self):
        self._event = threading.Event()

    def cancel(self):
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()


def submit_weighted(
    items: Iterable[Tuple[int, Callable[[], object]]],
    max_concurrency: int,
) -> Iterator[Future]:
    """
    Submits callables respecting a simple weight-based concurrency heuristic.
    """

    executor = ThreadPoolExecutor(max_workers=max_concurrency)
    try:
        for weight, func in sorted(items, key=lambda entry: entry[0], reverse=True):
            yield executor.submit(func)
    finally:
        executor.shutdown(wait=True)


@contextmanager
def cancellable_executor(max_workers: int) -> Iterator[Tuple[ThreadPoolExecutor, CancellationToken]]:
    token = CancellationToken()
    executor = ThreadPoolExecutor(max_workers=max_workers)
    try:
        yield executor, token
    finally:
        token.cancel()
        executor.shutdown(wait=True)
