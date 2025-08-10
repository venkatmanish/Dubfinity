import { useEffect, useRef, useState } from "react";
import { getVoices, tts, translateText } from "./api/apiClient";
import UploadPanel from "./components/UploadPanel";
import RealTimeMic from "./components/RealTimeMic";
import MultiSpeakerEditor from "./components/MultiSpeakerEditor";
import VoiceRemixControls from "./components/VoiceRemixControls";
import MetricsDashboard from "./components/MetricsDashboard";
import "./styles.css";

const LANGS = [
  { code: "te", label: "Telugu" },
  { code: "en", label: "English" },
  { code: "kn", label: "Kannada" },
  { code: "hi", label: "Hindi" },
];

function Section({ title, children }) {
  return (
    <section className="section">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

export default function App() {
  const [voices, setVoices] = useState([]);
  const [actor, setActor] = useState("");
  const [lang, setLang] = useState("te");
  const [text, setText] = useState("नमस्ते, यह एक परीक्षण है।");
  const [audioUrl, setAudioUrl] = useState("");
  const [translating, setTranslating] = useState(false);
  const audioRef = useRef(null);
  const lastUrlRef = useRef("");

  useEffect(() => {
    (async () => {
      try {
        const v = await getVoices(); // [{actor, voice_id}]
        setVoices(v);
        if (!actor && v.length) setActor(v[0].actor); // pick first voice
      } catch (e) {
        console.error(e);
        setVoices([]);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleLangChange(newLang) {
    if (lang === newLang) return;
    setLang(newLang);

    // keep currently chosen actor; if empty, default to first
    if (!actor && voices.length) setActor(voices[0].actor);

    if (text.trim()) {
      setTranslating(true);
      try {
        const translated = await translateText(text, newLang);
        if (translated) setText(translated);
      } catch (e) {
        console.error(e);
        alert("Translation failed — keeping original text.");
      } finally {
        setTranslating(false);
      }
    }
  }

  async function handleSpeak() {
    // cleanup any prior URL
    if (lastUrlRef.current) {
      URL.revokeObjectURL(lastUrlRef.current);
      lastUrlRef.current = "";
    }
    setAudioUrl("");

    try {
      const buf = await tts({ text, actor, lang });
      const blob = new Blob([buf], { type: "audio/wav" });
      const url = URL.createObjectURL(blob);
      lastUrlRef.current = url;
      setAudioUrl(url);

      // try to play immediately once the element gets the new src
      requestAnimationFrame(() => {
        const el = audioRef.current;
        if (el) {
          el.load(); // ensure metadata parse
          el.onloadedmetadata = () => {
            // if metadata parsed correctly, duration should be > 0
            // auto-play (user already clicked a button)
            el.play().catch(() => {});
          };
        }
      });
    } catch (e) {
      alert(`TTS failed: ${e.message || e}`);
    }
  }

  return (
    <div className="container">
      <header className="header">
        <h1>Dubfinity — Audio Dubbing (Smallest.ai)</h1>
      </header>

      <div className="grid">
        <Section title="Controls">
          <div className="row">
            <label>Language</label>
            <select
              value={lang}
              onChange={(e) => handleLangChange(e.target.value)}
              disabled={translating}
            >
              {LANGS.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.label}
                </option>
              ))}
            </select>
          </div>

          <div className="row">
            <label>Voice</label>
            <select value={actor} onChange={(e) => setActor(e.target.value)}>
              {voices.map((v) => (
                <option key={v.voice_id} value={v.actor}>
                  {v.actor}
                </option>
              ))}
            </select>
          </div>

          <textarea
            rows={4}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />

          <div className="row">
            <button onClick={handleSpeak} disabled={translating}>
              {translating ? "Translating..." : "Synthesize"}
            </button>
          </div>

          {audioUrl && (
            <div className="row">
              <audio
                ref={audioRef}
                controls
                preload="metadata"
                src={audioUrl}
              />
              <a download="tts.wav" href={audioUrl} style={{ marginLeft: 12 }}>
                Download
              </a>
            </div>
          )}
        </Section>

        <Section title="Upload & Dub (Audio → Audio)">
          <UploadPanel actors={voices} lang={lang} />
        </Section>

        <Section title="Real-time WS TTS (Demo)">
          <RealTimeMic actor={actor} lang={lang} />
        </Section>

        <Section title="Multi-speaker Mapping">
          <MultiSpeakerEditor actors={voices} />
        </Section>

        <Section title="Voice Remix">
          <VoiceRemixControls />
        </Section>

        <Section title="Metrics">
          <MetricsDashboard />
        </Section>

        <Section title="Embed">
          <EmbedWidget />
        </Section>
      </div>

      <footer className="footer">
        <span>Built for the Smallest.ai Hackathon • Audio-only</span>
      </footer>
    </div>
  );
}

function EmbedWidget() {
  return (
    <div className="card">
      <h3>Partner Embed</h3>
      <p className="muted">Drop-in widget via the JS client.</p>
      <code>&lt;div id="dubfinity-widget"&gt;&lt;/div&gt;</code>
    </div>
  );
}
