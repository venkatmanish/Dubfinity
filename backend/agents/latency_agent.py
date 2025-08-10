from __future__ import annotations
from dataclasses import dataclass
from collections import deque
from contextlib import contextmanager
from typing import Deque, Iterable

@dataclass
class LatencyWindow:
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    count: int = 0

class LatencyAgent:
    """
    Tracks latency samples (stored in SECONDS), reports percentiles in ms,
    and can advise switching models if p95 exceeds a millisecond budget.
    """
    def __init__(self, budget_ms: int = 450, max_samples: int = 500):
        self.budget_ms = float(budget_ms)
        self._samples_sec: Deque[float] = deque(maxlen=max_samples)

    # --- recording --- #
    def record(self, seconds: float) -> None:
        """Record a sample in SECONDS."""
        if seconds is None:
            return
        self._samples_sec.append(float(seconds))

    def record_ms(self, ms: float) -> None:
        """Record a sample in MILLISECONDS."""
        self.record(ms / 1000.0)

    def extend(self, seconds_iter: Iterable[float]) -> None:
        for s in seconds_iter:
            self.record(s)

    def reset(self) -> None:
        self._samples_sec.clear()

    # --- stats --- #
    def snapshot(self) -> LatencyWindow:
        if not self._samples_sec:
            return LatencyWindow(0.0, 0.0, 0)
        arr = sorted(self._samples_sec)
        n = len(arr)
        def percentile(p: float) -> float:
            # nearest-rank on 0..1, returns seconds
            if n == 1:
                return arr[0]
            idx = max(0, min(n - 1, int(round(p * (n - 1)))))
            return arr[idx]
        p50_s = percentile(0.50)
        p95_s = percentile(0.95)
        return LatencyWindow(p50_ms=p50_s * 1000.0, p95_ms=p95_s * 1000.0, count=n)

    def over_budget(self) -> bool:
        return self.snapshot().p95_ms > self.budget_ms

    # --- convenience timing helper --- #
    @contextmanager
    def timeit(self):
        import time
        t0 = time.perf_counter()
        try:
            yield
        finally:
            dt = time.perf_counter() - t0
            self.record(dt)
