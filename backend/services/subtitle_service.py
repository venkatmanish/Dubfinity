from __future__ import annotations
from typing import List, Dict
from pathlib import Path

def _fmt_ts(sec: float) -> str:
    # SRT timestamps: HH:MM:SS,mmm
    h = int(sec // 3600); m = int((sec % 3600) // 60); s = int(sec % 60)
    ms = int((sec - int(sec)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def segments_to_srt(segments: List[Dict], path: Path) -> Path:
    """
    segments: [{"start": 0.20, "end": 1.35, "text": "..."}]
    Writes a UTF-8 SRT file and returns its path.
    """
    lines = []
    for i, seg in enumerate(segments, start=1):
        start = _fmt_ts(float(seg.get("start", 0.0)))
        end = _fmt_ts(float(seg.get("end", 0.0)))
        text = str(seg.get("text", "")).strip()
        lines.append(str(i))
        lines.append(f"{start} --> {end}")
        lines.append(text or "...")
        lines.append("")  # blank line
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
