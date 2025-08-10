const BASE_URL = (
  import.meta.env.VITE_API_BASE || "http://localhost:8000"
).replace(/\/+$/, "");

export function wsTTS({ text, actor, lang = "te", onChunk, onDone, onError }) {
  const url = BASE_URL.replace(/^http/, "ws") + "/ws/tts";
  const ws = new WebSocket(url);
  ws.binaryType = "arraybuffer";
  ws.onopen = () => ws.send(JSON.stringify({ text, actor, lang }));
  ws.onmessage = (evt) => {
    if (evt.data instanceof ArrayBuffer) {
      onChunk?.(evt.data);
    } else {
      try {
        const meta = JSON.parse(String(evt.data));
        onDone?.(meta);
      } catch (_) {}
    }
  };
  ws.onerror = (e) => onError?.(e);
  return ws;
}
