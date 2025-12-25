import logging
import time
from collections import Counter
from contextlib import contextmanager
from typing import Iterator

from prometheus_client import Counter as PromCounter
from prometheus_client import Histogram
from prometheus_client import generate_latest

logger = logging.getLogger("rag-app")
RECENT_ERROR_LIMIT = 50

http_requests_total = PromCounter("rag_http_requests_total", "Total HTTP requests", ["method", "path", "status", "tenant"])
http_request_latency_ms = Histogram("rag_http_request_latency_ms", "HTTP request latency (ms)", ["method", "path", "error_code"])
ingest_latency_ms = Histogram("rag_ingest_latency_ms", "Ingestion latency (ms)")
rag_latency_ms = Histogram("rag_rag_latency_ms", "RAG total latency (ms)")


class Metrics:
    def __init__(self) -> None:
        self._counts = Counter()
        self._latency_ms: list[int] = []
        self._recent_errors: list[dict[str, object]] = []

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
            "error_recent_count": len(self._recent_errors),
        }

    def record_error(
        self,
        *,
        method: str,
        path: str,
        status: int,
        error_code: str,
        detail: str,
        correlation_id: str | None,
    ) -> None:
        record = {
            "timestamp": int(time.time() * 1000),
            "method": method,
            "path": path,
            "status": status,
            "error_code": error_code,
            "detail": detail,
            "correlation_id": correlation_id,
        }
        self._recent_errors.append(record)
        if len(self._recent_errors) > RECENT_ERROR_LIMIT:
            self._recent_errors.pop(0)

    def recent_errors(self) -> list[dict[str, object]]:
        return list(self._recent_errors)

    @contextmanager
    def timeit(self, name: str) -> Iterator[None]:
        start = time.time()
        try:
            yield
        finally:
            ms = int((time.time() - start) * 1000)
            self.observe_latency(name, ms)
            if name == "ingest_ms":
                ingest_latency_ms.observe(ms)
            if name == "rag_total_ms":
                rag_latency_ms.observe(ms)


metrics = Metrics()
