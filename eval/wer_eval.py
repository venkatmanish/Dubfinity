#!/usr/bin/env python3
"""
Compute Word Error Rate (WER) between reference and hypothesis.
Usage:
  1) Text mode:
     python eval/wer_eval.py --ref ref.txt --hyp hyp.txt

  2) Audio mode (requires faster-whisper):
     python eval/wer_eval.py --ref-audio ref.wav --hyp-audio hyp.wav --lang hi
"""

from __future__ import annotations
import argparse
import re
from typing import List

# Optional ASR
try:
    from faster_whisper import WhisperModel  # type: ignore
    HAS_WHISPER = True
except Exception:
    HAS_WHISPER = False

def _normalize(s: str) -> List[str]:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9\u0900-\u097F\s]", " ", s)  # keep latin digits + Devanagari
    s = re.sub(r"\s+", " ", s)
    return s.split()

def _edit_distance(a: List[str], b: List[str]) -> int:
    # classic Levenshtein
    dp = [[0]*(len(b)+1) for _ in range(len(a)+1)]
    for i in range(len(a)+1): dp[i][0] = i
    for j in range(len(b)+1): dp[0][j] = j
    for i in range(1, len(a)+1):
        for j in range(1, len(b)+1):
            cost = 0 if a[i-1] == b[j-1] else 1
            dp[i][j] = min(dp[i-1][j] + 1,      # deletion
                           dp[i][j-1] + 1,      # insertion
                           dp[i-1][j-1] + cost) # substitution
    return dp[-1][-1]

def wer(ref: str, hyp: str) -> float:
    r = _normalize(ref)
    h = _normalize(hyp)
    if not r:
        return 0.0 if not h else 1.0
    return _edit_distance(r, h) / float(len(r))

def transcribe(path: str, lang: str = "hi", model_size: str = "small") -> str:
    if not HAS_WHISPER:
        raise RuntimeError("faster-whisper not installed. Provide text files instead.")
    model = WhisperModel(model_size, compute_type="int8")
    segments, _ = model.transcribe(path, language=lang, vad_filter=True)
    out = []
    for s in segments:
        out.append(s.text.strip())
    return " ".join(out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", type=str, help="reference text file")
    ap.add_argument("--hyp", type=str, help="hypothesis text file")
    ap.add_argument("--ref-audio", type=str, help="reference audio wav")
    ap.add_argument("--hyp-audio", type=str, help="hypothesis audio wav")
    ap.add_argument("--lang", type=str, default="hi")
    args = ap.parse_args()

    if args.ref and args.hyp:
        ref_txt = open(args.ref, "r", encoding="utf-8").read()
        hyp_txt = open(args.hyp, "r", encoding="utf-8").read()
    elif args.ref_audio and args.hyp_audio:
        ref_txt = transcribe(args.ref_audio, lang=args.lang)
        hyp_txt = transcribe(args.hyp_audio, lang=args.lang)
    else:
        ap.error("Provide (--ref and --hyp) OR (--ref-audio and --hyp-audio).")

    score = wer(ref_txt, hyp_txt)
    print(f"WER: {score:.3f}")

if __name__ == "__main__":
    main()
