const BASE_URL = (
  import.meta.env.VITE_API_BASE || "http://localhost:8000"
).replace(/\/+$/, "");

export async function getVoices() {
  const res = await fetch("/v1/voices");
  if (!res.ok) throw new Error("Failed to fetch voices");
  return res.json();
}

export async function tts({ text, actor, language, format = "wav" }) {
  const res = await fetch("/v1/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, actor, language, format }),
  });
  if (!res.ok) {
    const msg = await res.text().catch(() => "TTS request failed");
    throw new Error(msg);
  }
  return res.arrayBuffer();
}

export async function dubAudio({ file, target_lang, actor }) {
  const fd = new FormData();
  fd.append("file", file);
  const qs = new URLSearchParams({ target_lang, ...(actor ? { actor } : {}) });
  const r = await fetch(`${BASE_URL}/v1/dub-audio?${qs.toString()}`, {
    method: "POST",
    body: fd,
  });
  if (!r.ok) throw new Error(`dub-audio: ${r.status}`);
  return await r.arrayBuffer();
}

export async function translate({ text, target_lang }) {
  const r = await fetch(`${BASE_URL}/v1/translate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, target_lang }),
  });
  if (!r.ok) throw new Error(`translate: ${r.status}`);
  return r.json();
}

export async function translateText(text, targetLang) {
  const res = await fetch("/v1/translate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text,
      source_lang: "auto",
      target_lang: targetLang,
    }),
  });
  if (!res.ok) throw new Error(`Translate failed: ${res.status}`);
  const data = await res.json();
  return data.translated_text;
}
