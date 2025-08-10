import { useEffect, useRef, useState } from "react";
import { wsTTS } from "../api/wsClient";

export default function RealTimeMic({ actor, lang }) {
  const [text, setText] = useState("नमस्ते, यह एक परीक्षण है।");
  const [status, setStatus] = useState("idle");
  const audioRef = useRef(null);
  const mediaSourceRef = useRef(null);
  const sourceBufferRef = useRef(null);
  const queueRef = useRef([]);

  function startStream() {
    // MediaSource to append PCM WAV chunks (simple approach: concatenate into one blob)
    setStatus("connecting");
    let chunks = [];
    const ws = wsTTS({
      text,
      actor,
      lang,
      onChunk: (buf) => chunks.push(new Uint8Array(buf)),
      onDone: () => {
        setStatus("done");
        const blob = new Blob(chunks, { type: "audio/wav" });
        const url = URL.createObjectURL(blob);
        if (audioRef.current) {
          audioRef.current.src = url;
          audioRef.current.play().catch(() => {});
        }
      },
      onError: (e) => setStatus(`error: ${e?.message || e}`),
    });
  }

  return (
    <div className="card">
      <h3>Real-time WS TTS (demo)</h3>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={3}
      />
      <div className="row">
        <button onClick={startStream}>Speak</button>
        <span className="muted">{status}</span>
      </div>
      <audio ref={audioRef} controls />
    </div>
  );
}
