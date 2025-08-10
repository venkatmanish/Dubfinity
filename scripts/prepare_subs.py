#!/usr/bin/env python3
"""
Create SRT subtitles from a WAV by running ASR (if faster-whisper available).
Fallback: write a single full-duration cue with placeholder text.
Usage:
  python scripts/prepare_subs.py --input dataset/test/scenes_hi/scene_01.wav --out scene_01.srt --lang hi
"""
from __future__ import annotations
import argparse, io, wave, numpy as np
from pathlib import Path

try:
    from faster_whisper import WhisperModel  # type: ignore
    HAS_WHISPER = True
except Exception:
    HAS_WHISPER = False

def fmt_ts(sec: float) -> str:
    h = int(sec // 3600); m = int((sec % 3600) // 60); s = int(sec % 60)
    ms = int((sec - int(sec)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / float(wf.getframerate())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--lang", default="hi")
    ap.add_argument("--model", default="small")
    args = ap.parse_args()

    infile = Path(args.input)
    outfile = Path(args.out)

    if HAS_WHISPER:
        model = WhisperModel(args.model, compute_type="int8")
        segs, _ = model.transcribe(str(infile), language=args.lang, vad_filter=True)
        lines = []
        for i, s in enumerate(segs, start=1):
            lines.append(str(i))
            lines.append(f"{fmt_ts(float(s.start))} --> {fmt_ts(float(s.end))}")
            lines.append(s.text.strip())
            lines.append("")
        outfile.write_text("\n".join(lines), encoding="utf-8")
        print(f"[ok] wrote SRT: {outfile}")
    else:
        dur = wav_duration(infile)
        text = "(transcript unavailable — install faster-whisper to generate real subtitles)"
        srt = f"1\n00:00:00,000 --> {fmt_ts(dur)}\n{text}\n\n"
        outfile.write_text(srt, encoding="utf-8")
        print(f"[stub] wrote placeholder SRT: {outfile}")

if __name__ == "__main__":
    main()
