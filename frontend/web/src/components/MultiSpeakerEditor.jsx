import { useState, useEffect } from "react";

export default function MultiSpeakerEditor({ actors }) {
  const [mapping, setMapping] = useState({
    spk1: actors[0]?.actor,
    spk2: actors[1]?.actor,
  });

  useEffect(() => {}, [mapping]);

  function set(spk, actor) {
    setMapping((m) => ({ ...m, [spk]: actor }));
  }

  return (
    <div className="card">
      <h3>Multi-Speaker Mapping</h3>
      {["spk1", "spk2", "spk3"].map((spk) => (
        <div className="row" key={spk}>
          <label>{spk}</label>
          <select
            value={mapping[spk] || ""}
            onChange={(e) => set(spk, e.target.value)}
          >
            <option value="">-- select voice --</option>
            {actors.map((v) => (
              <option key={v.voice_id} value={v.actor}>
                {v.actor}
              </option>
            ))}
          </select>
        </div>
      ))}
      <p className="muted">
        This mapping would be sent with diarization results when you enable
        multi-speaker dubbing.
      </p>
    </div>
  );
}
