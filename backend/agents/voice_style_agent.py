from __future__ import annotations
from typing import List, Dict, Optional
import logging
import numpy as np

logger = logging.getLogger(__name__)

class VoiceStyleAgent:
    """
    Lightweight prosody extractor that produces sane defaults for TTS params.
    You can wire these into Smallest TTS once the SDK exposes them.

    Outputs two levels:
      - global map: {"speed": float, "similarity": float, "enhancement": bool}
      - per-segment list (optional) with segment-local speed hints

    Current heuristic:
      - speed is slightly higher for longer segments (text length proxy)
      - clamp speed to [0.9, 1.15] for stability
    """

    def __init__(self, min_speed: float = 0.90, max_speed: float = 1.15):
        self.min_speed = float(min_speed)
        self.max_speed = float(max_speed)

    # --------- core features --------- #
    def _speed_from_textlen(self, text: str) -> float:
        L = len(text or "")
        # map 0..800 chars roughly to +0.00..+0.15
        inc = min(0.15, max(0.0, L / 800.0))
        return float(np.clip(0.95 + inc, self.min_speed, self.max_speed))

    # --------- public APIs --------- #
    def extract_prosody(self, segments: List[Dict]) -> Dict:
        """
        Returns:
          {
            "global": {"speed": float, "similarity": 0.0, "enhancement": False},
            "per_segment": [{"speed": float}, ...]  # aligned with input segments
          }
        """
        if not segments:
            return {"global": {"speed": 1.0, "similarity": 0.0, "enhancement": False}, "per_segment": []}

        per_seg = []
        speeds = []
        for s in segments:
            spd = self._speed_from_textlen(s.get("text", "") or "")
            speeds.append(spd)
            per_seg.append({"speed": spd})

        # global defaults: average segment speed, neutral similarity, no enhancement
        global_speed = float(np.mean(speeds)) if speeds else 1.0
        prosody = {
            "global": {
                "speed": round(global_speed, 3),
                "similarity": 0.0,
                "enhancement": False,
            },
            "per_segment": per_seg,
        }
        return prosody

    # Backward-compat alias (older snippets called .estimate())
    def estimate(self, segments: List[Dict]) -> Dict:
        return self.extract_prosody(segments)
