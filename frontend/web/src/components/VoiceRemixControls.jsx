import { useState } from "react";

export default function VoiceRemixControls() {
  const [pitch, setPitch] = useState(0);
  const [speed, setSpeed] = useState(1.0);
  const [emotion, setEmotion] = useState("neutral");

  return (
    <div className="card">
      <h3>Voice Remix</h3>
      <div className="row">
        <label>Pitch</label>
        <input
          type="range"
          min="-6"
          max="6"
          step="1"
          value={pitch}
          onChange={(e) => setPitch(+e.target.value)}
        />
        <span>{pitch} semitones</span>
      </div>
      <div className="row">
        <label>Speed</label>
        <input
          type="range"
          min="0.5"
          max="1.5"
          step="0.01"
          value={speed}
          onChange={(e) => setSpeed(+e.target.value)}
        />
        <span>{speed.toFixed(2)}×</span>
      </div>
      <div className="row">
        <label>Emotion</label>
        <select value={emotion} onChange={(e) => setEmotion(e.target.value)}>
          <option>neutral</option>
          <option>happy</option>
          <option>sad</option>
          <option>angry</option>
        </select>
      </div>
      <p className="muted">
        These are UI-only for now. Wire to TTS params when your backend supports
        it.
      </p>
    </div>
  );
}
