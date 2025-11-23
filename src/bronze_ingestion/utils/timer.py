"""
Timing helper for capturing durations.
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class Timer:
    start: float | None = None
    end: float | None = None
    duration: float | None = None

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end = time.perf_counter()
        self.duration = (self.end - self.start) if self.start else None
