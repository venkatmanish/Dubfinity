# backend/app.py
from __future__ import annotations

import time
import logging
from collections import defaultdict
from pathlib import Path
import json

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response

# --- Config / Logging / OTEL (defensive imports) ---
try:
    from backend.config import settings
    cfg = settings()
except Exception:
    cfg = None

try:
    from backend.logging import setup_logging
    setup_logging(level="INFO")
except Exception:
    logging.basicConfig(level=logging.INFO)

try:
    from backend.otel_middleware import enable_otel_if_configured
except Exception:
    def enable_otel_if_configured(app, enabled=False):  # no-op
        return

logger = logging.getLogger("dubfinity.app")

# --- Services & Agents (singletons) ---
from backend.services.smallest_service import SmallestClient
from backend.agents.transcriber_agent import TranscriberAgent
from backend.agents.translator_agent import TranslatorAgent
from backend.agents.voice_style_agent import VoiceStyleAgent
from backend.agents.dubbing_agent import DubbingAgent
from backend.agents.quality_agent import QualityAgent
from backend.agents.orchestrator_agent import OrchestratorAgent
from backend.pipeline.audio_dub_pipeline import AudioDubPipeline

sdk = SmallestClient()
asr = TranscriberAgent(src_lang="hi")
tr = TranslatorAgent(client=sdk, source_lang="hi")
style = VoiceStyleAgent()
dub = DubbingAgent(sdk=sdk)
qa = QualityAgent()
orc = OrchestratorAgent()

# Expose singleton pipeline for routes that import it
audio_pipeline = AudioDubPipeline(
    asr=asr, translator=tr, style=style, dubber=dub, qa=qa, orchestrator=orc
)

# --- FastAPI app ---
app = FastAPI(
    title="Dubfinity AI Backend (audio-only)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Optional OpenTelemetry
enable_otel_if_configured(app, enabled=bool(getattr(cfg, "telemetry", {}).get("otel_enabled", False)) if cfg else False)

# --- Root meta route (keep inline) ---
@app.get("/", tags=["meta"])
def root():
    env = getattr(cfg, "ENV", "dev") if cfg else "dev"
    return {"ok": True, "service": "dubfinity-backend", "env": env}

# --- Prometheus /metrics ---
from backend.metrics.prometheus_exports import router as metrics_router
app.include_router(metrics_router)

# --- Feature routers (now includes the new health router) ---
from backend.routes import health, voices, translate, tts, llm_tts, dub_audio
app.include_router(health.router)                 # /health
app.include_router(voices.router, tags=["voices"])
app.include_router(translate.router, tags=["translate"])
app.include_router(tts.router, tags=["tts"])
app.include_router(llm_tts.router, tags=["tts"])  # optional WS demo
app.include_router(dub_audio.router, tags=["dub"])

# --- Latency → Prometheus middleware ---
from backend.agents.latency_agent import LatencyAgent
from backend.metrics.metrics_collector import (
    record_request_metrics,
    publish_latency_window,
)

_latency_agents: dict[str, LatencyAgent] = defaultdict(
    lambda: LatencyAgent(
        budget_ms=int(getattr(getattr(cfg, "thresholds", {}), "get", lambda *_: 450)("latency_ms_target", 450))
        if cfg else 450
    )
)

@app.middleware("http")
async def latency_prom_mw(request: Request, call_next):
    method = request.method.upper()
    # Use the resolved route template if available; fallback to raw path
    route_template = getattr(request.scope.get("route"), "path", request.url.path)
    label = f"{method} {route_template}"
    t0 = time.perf_counter()
    status = 500
    try:
        response: Response = await call_next(request)
        status = response.status_code
        return response
    finally:
        dt = time.perf_counter() - t0  # seconds
        # Standard metrics
        record_request_metrics(endpoint=route_template, method=method, status_code=status, latency=dt)
        # Rolling p50/p95 → Prometheus gauges
        la = _latency_agents[label]
        la.record(dt)
        snap = la.snapshot()  # ms
        publish_latency_window(endpoint=label, p50_ms=snap.p50_ms, p95_ms=snap.p95_ms)
