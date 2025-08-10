from __future__ import annotations
import base64
import io
import json
import pathlib
import typing as t

import requests
import websockets
import asyncio

class DubfinityClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")

    # ---------- REST ---------- #
    def health(self) -> dict:
        r = requests.get(f"{self.base_url}/health", timeout=30)
        r.raise_for_status()
        return r.json()

    def list_voices(self) -> list[dict]:
        r = requests.get(f"{self.base_url}/v1/voices", timeout=30)
        if r.status_code == 404:
            return []
        r.raise_for_status()
        return r.json()

    def translate(self, text: t.Union[str, list[str]], target_lang: str) -> dict:
        r = requests.post(f"{self.base_url}/v1/translate",
                          json={"text": text, "target_lang": target_lang},
                          timeout=60)
        r.raise_for_status()
        return r.json()

    def tts(self, text: str, actor: str, lang: str = "te") -> bytes:
        r = requests.post(f"{self.base_url}/v1/tts",
                          json={"text": text, "actor": actor, "lang": lang},
                          timeout=120)
        r.raise_for_status()
        return r.content  # WAV bytes

    def dub_audio(self, wav_path: t.Union[str, pathlib.Path], target_lang: str = "te", actor: str | None = None) -> bytes:
        files = {"file": open(wav_path, "rb")}
        params = {"target_lang": target_lang}
        if actor:
            params["actor"] = actor
        r = requests.post(f"{self.base_url}/v1/dub-audio", files=files, params=params, timeout=300)
        r.raise_for_status()
        return r.content

    # ---------- WebSockets ---------- #
    async def ws_tts(self, text: str, actor: str, lang: str = "te",
                     on_chunk: t.Callable[[bytes], t.Awaitable[None] | None] | None = None) -> dict:
        url = self.base_url.replace("http", "ws") + "/ws/tts"
        async with websockets.connect(url, ping_interval=None) as ws:
            await ws.send(json.dumps({"text": text, "actor": actor, "lang": lang}))
            meta = {}
            while True:
                msg = await ws.recv()
                if isinstance(msg, bytes):
                    if on_chunk:
                        res = on_chunk(msg)
                        if asyncio.iscoroutine(res):
                            await res
                else:
                    try:
                        meta = json.loads(msg)
                        break
                    except Exception:
                        pass
            return meta

    async def ws_llm_tts(self, prompt: str,
                         provider: str = "groq",
                         model: str = "llama3-8b-8192",
                         on_chunk: t.Callable[[bytes], t.Awaitable[None] | None] | None = None) -> dict:
        url = self.base_url.replace("http", "ws") + "/ws/llm_tts"
        async with websockets.connect(url, ping_interval=None) as ws:
            await ws.send(json.dumps({"provider": provider, "model": model, "prompt": prompt}))
            meta = {}
            while True:
                msg = await ws.recv()
                if isinstance(msg, bytes):
                    if on_chunk:
                        res = on_chunk(msg)
                        if asyncio.iscoroutine(res):
                            await res
                else:
                    try:
                        meta = json.loads(msg)
                        break
                    except Exception:
                        pass
            return meta


# ----- quick manual test -----
if __name__ == "__main__":
    c = DubfinityClient()
    print("Health:", c.health())
    voices = c.list_voices()
    print("Voices:", voices[:2])
    if voices:
        actor = voices[0]["actor"]
        wav = c.tts("नमस्ते, यह एक परीक्षण है।", actor=actor, lang="te")
        pathlib.Path("out_te.wav").write_bytes(wav)
        print("Saved out_te.wav")
