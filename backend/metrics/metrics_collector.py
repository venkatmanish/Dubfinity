import time
from typing import Optional
from prometheus_client import Counter, Histogram, Gauge

# ---------- Request metrics ----------
REQUEST_COUNT = Counter(
    "dubfinity_requests_total",
    "Total number of requests",
    ["endpoint", "method", "status_code"]
)

REQUEST_LATENCY = Histogram(
    "dubfinity_request_latency_seconds",
    "Request latency in seconds",
    ["endpoint", "method"]
)

CURRENT_LATENCY = Gauge(
    "dubfinity_current_latency_seconds",
    "Latest observed latency in seconds per endpoint",
    ["endpoint"]
)

# ---------- Model/usage metrics ----------
TOKEN_USAGE = Counter(
    "dubfinity_token_usage_total",
    "Total tokens used",
    ["model"]
)

INFERENCE_COST = Counter(
    "dubfinity_inference_cost_usd_total",
    "Total inference cost in USD",
    ["model"]
)

# ---------- Rolling percentiles (published by LatencyAgent snapshots) ----------
LATENCY_P50_MS = Gauge(
    "dubfinity_latency_p50_ms",
    "Rolling p50 latency (ms) per endpoint",
    ["endpoint"]
)
LATENCY_P95_MS = Gauge(
    "dubfinity_latency_p95_ms",
    "Rolling p95 latency (ms) per endpoint",
    ["endpoint"]
)

def record_request_metrics(endpoint: str, method: str, status_code: int, latency: float):
    """
    endpoint: path template like '/v1/tts'
    method: HTTP method
    latency: seconds (float)
    """
    REQUEST_COUNT.labels(endpoint=endpoint, method=method, status_code=status_code).inc()
    REQUEST_LATENCY.labels(endpoint=endpoint, method=method).observe(latency)
    CURRENT_LATENCY.labels(endpoint=endpoint).set(latency)

def publish_latency_window(endpoint: str, p50_ms: float, p95_ms: float):
    LATENCY_P50_MS.labels(endpoint=endpoint).set(p50_ms)
    LATENCY_P95_MS.labels(endpoint=endpoint).set(p95_ms)

def record_token_usage(model: str, tokens: int, cost_usd: Optional[float] = None):
    TOKEN_USAGE.labels(model=model).inc(tokens)
    if cost_usd is not None:
        INFERENCE_COST.labels(model=model).inc(cost_usd)

class Timer:
    """Context manager to measure latency in seconds."""
    def __init__(self):
        self.start_time = None
        self.elapsed = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.elapsed = time.perf_counter() - self.start_time
