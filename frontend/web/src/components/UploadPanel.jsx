import React, { useEffect, useState } from "react";

export default function UploadPanel({ actors = [], lang = "te" }) {
  const [actor, setActor] = useState("");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [audioUrl, setAudioUrl] = useState("");

  useEffect(() => {
    if (!actor && actors.length) setActor(actors[0].actor);
  }, [actors]);

  async function handleDub() {
    if (!file) return alert("Choose a Hindi WAV/MP3/M4A first");
    setBusy(true);
    setAudioUrl("");

    try {
      const form = new FormData();
      form.append("file", file); // <-- must be "file"
      form.append("target_lang", lang); // backend reads Form(...)
      form.append("actor", actor);

      const res = await fetch("/v1/dub-audio", {
        method: "POST",
        body: form,
      });
      if (!res.ok) throw new Error(await res.text());

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      setAudioUrl(url);

      // optional auto-play
      const a = new Audio(url);
      a.play().catch(() => {});
    } catch (e) {
      alert(`Dub failed: ${e?.message || e}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <div className="row">
        <label>Speaker</label>
        <select value={actor} onChange={(e) => setActor(e.target.value)}>
          {actors.map((v) => (
            <option key={v.voice_id} value={v.actor}>
              {v.actor}
            </option>
          ))}
        </select>
      </div>

      <div className="row">
        <label>Upload Hindi WAV</label>
        <input
          type="file"
          accept=".wav,.mp3,.m4a,audio/*"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
      </div>

      <button onClick={handleDub} disabled={busy || !file}>
        {busy ? "Dubbing..." : "Dub"}
      </button>

      {audioUrl && (
        <div className="row">
          <audio controls preload="metadata" src={audioUrl}></audio>
          <a href={audioUrl} download="dub.wav" style={{ marginLeft: 12 }}>
            Download
          </a>
        </div>
      )}
    </div>
  );
}
