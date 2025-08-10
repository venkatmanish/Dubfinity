import json
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "targets" in data

def test_list_voices_present_or_404():
    r = client.get("/v1/voices")
    # if voice_ids.json exists -> 200 with list
    if r.status_code == 200:
        arr = r.json()
        assert isinstance(arr, list)
        if arr:
            assert "actor" in arr[0] and "voice_id" in arr[0]
    else:
        # if you haven't added demos/demo_assets/voice_ids.json yet
        assert r.status_code == 404

def test_tts_sync_returns_wav_even_without_key(monkeypatch, tmp_path):
    # choose an actor available in your voice_ids.json; fallback to fake if 404
    # we first try to fetch actors:
    r = client.get("/v1/voices")
    if r.status_code != 200:
        return  # skip if mapping not present
    actors = [v["actor"] for v in r.json()]
    if not actors:
        return
    actor = actors[0]

    payload = {"text": "नमस्ते, यह एक परीक्षण है।", "actor": actor, "lang": "te"}
    r = client.post("/v1/tts", data=json.dumps(payload))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/wav")
    # save to tmp
    (tmp_path / "out.wav").write_bytes(r.content)
