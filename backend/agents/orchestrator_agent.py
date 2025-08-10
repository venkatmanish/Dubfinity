from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Optional

from backend.config import settings
from backend.agents.latency_agent import LatencyAgent

cfg = settings()

TTSModel = Literal["lightning", "lightning-large"]

@dataclass
class OrchestratorDecision:
    # model / mode
    tts_model: TTSModel
    streaming: bool
    reason: str

    # budgets/limits
    budget_ms: int
    max_chars_per_chunk: int

    # synthesis controls (safe defaults; wire to SDK when supported)
    speed: float = 1.0
    similarity: float = 0.0
    enhancement: bool = False

    # routing hint (optional)
    voice_id: Optional[str] = None


class OrchestratorAgent:
    """
    Chooses quality vs speed based on:
      - latency budget (ms)
      - real-time flag
      - observed p95 latency (via LatencyAgent)
      - input length (very long text → chunk + stream)
    Exposes a small API to update observed latency and re-evaluate decisions.
    """

    def __init__(
        self,
        latency_target_ms: Optional[int] = None,
        max_chars_fast: int = 220,
        max_chars_steady: int = 480,
    ):
        self.latency_target_ms = int(
            latency_target_ms
            or cfg.thresholds.get("latency_ms_target", 450)
        )
        self.max_chars_fast = max_chars_fast
        self.max_chars_steady = max_chars_steady

        # Track observed latencies (seconds internally)
        self._lat = LatencyAgent(budget_ms=self.latency_target_ms)

    # ---- public API --------------------------------------------------------

    def observe_latency_seconds(self, seconds: float) -> None:
        """Record an observed end-to-end TTS latency (seconds)."""
        self._lat.record(seconds)

    def snapshot_ms(self) -> float:
        """Return current p95 in milliseconds."""
        return self._lat.snapshot().p95_ms

    def decide(
        self,
        text_len: int,
        realtime: bool = False,
        desired_quality: Literal["auto", "high", "fast"] = "auto",
        voice_id: Optional[str] = None,
    ) -> OrchestratorDecision:
        """
        Compute a routing decision for the next synthesis call.
        """
        p95_ms = self._lat.snapshot().p95_ms
        over = p95_ms > 0 and p95_ms > self.latency_target_ms

        # 1) Decide model
        #    - Real-time or over-budget → "lightning" (fast)
        #    - Explicit "high" quality → "lightning-large" (unless realtime)
        #    - Auto: short text prefers large, long text prefers fast
        if realtime:
            model: TTSModel = "lightning"
            reason = "realtime"
        elif desired_quality == "high":
            model = "lightning-large"
            reason = "user_pref_high"
        elif desired_quality == "fast":
            model = "lightning"
            reason = "user_pref_fast"
        elif over:
            model = "lightning"
            reason = "over_budget_p95"
        else:
            model = "lightning-large" if text_len <= self.max_chars_fast else "lightning"
            reason = "auto_quality" if model == "lightning-large" else "auto_speed"

        # 2) Chunking / streaming strategy
        if realtime or model == "lightning" or text_len > self.max_chars_steady:
            streaming = True
            max_chars_per_chunk = min(self.max_chars_steady, max(text_len // 3, self.max_chars_fast))
        else:
            streaming = False
            max_chars_per_chunk = self.max_chars_steady

        # 3) Simple prosody defaults (can be overridden by voice_style_agent)
        speed = 1.0 if model == "lightning-large" else 1.02
        enhancement = (model == "lightning-large")  # pretend higher quality path enables enhancement

        return OrchestratorDecision(
            tts_model=model,
            streaming=streaming,
            reason=reason,
            budget_ms=self.latency_target_ms,
            max_chars_per_chunk=max_chars_per_chunk,
            speed=speed,
            similarity=0.0,
            enhancement=enhancement,
            voice_id=voice_id,
        )

    # ---- convenience -------------------------------------------------------

    def time_and_observe(self):
        """
        Context manager to time a block and record the latency.
        Usage:
            with orch.time_and_observe():
                do_tts_call()
        """
        from contextlib import contextmanager
        import time

        @contextmanager
        def _cm():
            t0 = time.perf_counter()
            try:
                yield
            finally:
                dt = time.perf_counter() - t0
                self.observe_latency_seconds(dt)
        return _cm()
