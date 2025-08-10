/* Minimal TS client for Dubfinity backend (audio-only). */
export type Lang = "te" | "en" | "kn";

export interface DubfinityClientOptions {
  baseUrl?: string; // default http://localhost:8000
}

export class DubfinityClient {
  baseUrl: string;

  constructor(opts: DubfinityClientOptions = {}) {
    this.baseUrl = (opts.baseUrl || "http://localhost:8000").replace(
      /\/+$/,
      ""
    );
  }

  async health(): Promise<any> {
    const r = await fetch(`${this.baseUrl}/health`);
    if (!r.ok) throw new Error(`/health failed: ${r.status}`);
    return r.json();
  }

  async listVoices(): Promise<Array<{ actor: string; voice_id: string }>> {
    const r = await fetch(`${this.baseUrl}/v1/voices`);
    if (!r.ok) throw new Error(`/v1/voices failed: ${r.status}`);
    return r.json();
  }

  async translate(text: string | string[], target_lang: Lang): Promise<any> {
    const r = await fetch(`${this.baseUrl}/v1/translate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, target_lang }),
    });
    if (!r.ok) throw new Error(`/v1/translate failed: ${r.status}`);
    return r.json();
  }

  /** Returns ArrayBuffer for audio/wav */
  async tts(
    text: string,
    actor: string,
    lang: Lang = "te"
  ): Promise<ArrayBuffer> {
    const r = await fetch(`${this.baseUrl}/v1/tts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, actor, lang }),
    });
    if (!r.ok) throw new Error(`/v1/tts failed: ${r.status}`);
    return r.arrayBuffer();
  }

  /** Upload a WAV and receive dubbed WAV as ArrayBuffer */
  async dubAudio(
    file: File | Blob,
    target_lang: Lang = "te",
    actor?: string
  ): Promise<ArrayBuffer> {
    const fd = new FormData();
    fd.append("file", file);
    const q = new URLSearchParams({ target_lang, ...(actor ? { actor } : {}) });
    const r = await fetch(`${this.baseUrl}/v1/dub-audio?${q.toString()}`, {
      method: "POST",
      body: fd,
    });
    if (!r.ok) throw new Error(`/v1/dub-audio failed: ${r.status}`);
    return r.arrayBuffer();
  }

  /** Stream TTS over WebSocket; onChunk gets binary audio chunks */
  wsTTS(
    params: { text: string; actor: string; lang?: Lang },
    onChunk: (chunk: ArrayBuffer) => void,
    onDone?: (meta: any) => void,
    onError?: (err: any) => void
  ): WebSocket {
    const url = this.baseUrl.replace(/^http/, "ws") + "/ws/tts";
    const ws = new WebSocket(url);
    ws.binaryType = "arraybuffer";
    ws.onopen = () =>
      ws.send(
        JSON.stringify({
          text: params.text,
          actor: params.actor,
          lang: params.lang || "te",
        })
      );
    ws.onmessage = (evt: MessageEvent) => {
      // server sends both binary audio and a final JSON {"event":"done",...}
      if (evt.data instanceof ArrayBuffer) onChunk(evt.data);
      else {
        try {
          const meta = JSON.parse(String(evt.data));
          if (onDone) onDone(meta);
        } catch {
          /* ignore */
        }
      }
    };
    ws.onerror = (e) => onError && onError(e);
    return ws;
  }

  /** LLM→speech streaming demo */
  wsLLMTTS(
    params: { provider?: string; model?: string; prompt: string },
    onChunk: (chunk: ArrayBuffer) => void,
    onDone?: (meta: any) => void,
    onError?: (err: any) => void
  ): WebSocket {
    const url = this.baseUrl.replace(/^http/, "ws") + "/ws/llm_tts";
    const ws = new WebSocket(url);
    ws.binaryType = "arraybuffer";
    ws.onopen = () =>
      ws.send(
        JSON.stringify({
          provider: params.provider || "groq",
          model: params.model || "llama3-8b-8192",
          prompt: params.prompt,
        })
      );
    ws.onmessage = (evt: MessageEvent) => {
      if (evt.data instanceof ArrayBuffer) onChunk(evt.data);
      else {
        try {
          const meta = JSON.parse(String(evt.data));
          if (onDone) onDone(meta);
        } catch {
          /* ignore */
        }
      }
    };
    ws.onerror = (e) => onError && onError(e);
    return ws;
  }
}
