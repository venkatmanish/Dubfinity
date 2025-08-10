from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

def enable_otel_if_configured(app, enabled: bool) -> None:
    """
    If enabled=True, instrument FastAPI with OpenTelemetry.
    Safe to call even if OTEL packages are missing; it will just log a hint.
    """
    if not enabled:
        logger.info("OpenTelemetry disabled by config.")
        return

    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry import trace
        tracer_provider = trace.get_tracer_provider()  # use default unless you wire exporters
        FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
        logger.info("OpenTelemetry FastAPI instrumentation enabled.")
    except Exception as e:
        logger.warning("OpenTelemetry not enabled (missing deps or init error): %s", e)
