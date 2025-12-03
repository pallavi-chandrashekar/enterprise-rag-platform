import logging
import time
from collections import Counter
from contextlib import contextmanager
from typing import Iterator

logger = logging.getLogger("rag-app")


class Metrics:
    def __init__(self) -> None:
        self._counts = Counter()
        self._latency_ms: list[int] = []

    def inc(self, name: str) -> None:
        self._counts[name] += 1

    def observe_latency(self, name: str, value_ms: int) -> None:
        self._counts[f"{name}_count"] += 1
        self._latency_ms.append(value_ms)

    def snapshot(self) -> dict[str, int | float]:
        # Expose basic counts and simple latency stats for debugging.
        if self._latency_ms:
            avg_latency = sum(self._latency_ms) / len(self._latency_ms)
            p95 = sorted(self._latency_ms)[max(int(len(self._latency_ms) * 0.95) - 1, 0)]
        else:
            avg_latency = 0.0
            p95 = 0
        return {
            "counts": dict(self._counts),
            "latency_avg_ms": avg_latency,
            "latency_p95_ms": p95,
        }

    @contextmanager
    def timeit(self, name: str) -> Iterator[None]:
        start = time.time()
        try:
            yield
        finally:
            ms = int((time.time() - start) * 1000)
            self.observe_latency(name, ms)


metrics = Metrics()
