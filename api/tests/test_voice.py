import io
import pytest
from fastapi.testclient import TestClient

from main import app
from voice.service import get_voice_service


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def voice():
    return get_voice_service()


def test_voice_transcribe_offline_english(voice):
    """Test voice transcription in English."""
    sample_wav = b"RIFF....WAVEfmt ...." + b"\x00" * 200
    res = voice.transcribe(sample_wav, mime_type="audio/wav", lang="en")
    assert res["is_empty"] is False
    assert len(res["text"]) > 5
    assert res["lang"] == "en"
    assert res["confidence"] >= 0.70


def test_voice_transcribe_offline_hindi(voice):
    """Test voice transcription in Hindi."""
    sample_webm = b"webm...." + b"\x00" * 300
    res = voice.transcribe(sample_webm, mime_type="audio/webm", lang="hi")
    assert res["is_empty"] is False
    assert len(res["text"]) > 5
    assert res["lang"] == "hi"


def test_api_voice_transcribe_endpoint(client):
    """Test POST /voice/transcribe endpoint."""
    fake_audio = io.BytesIO(b"AUDIO_BYTES_SAMPLE" * 10)
    resp = client.post(
        "/voice/transcribe",
        files={"file": ("recording.webm", fake_audio, "audio/webm")},
        data={"lang": "en"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "text" in data
    assert data["confidence"] > 0.5


def test_api_voice_turn_interview(client):
    """Test POST /voice/turn in conversational interview mode."""
    fake_audio = io.BytesIO(b"AUDIO_BYTES_SAMPLE_TURN" * 15)
    resp = client.post(
        "/voice/turn",
        files={"file": ("turn.webm", fake_audio, "audio/webm")},
        data={"lang": "en", "mode": "interview", "profile_json": "{}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "transcription" in data
    assert "reply_text" in data
    assert "interview" in data


def test_voice_missing_gemini_api_key(monkeypatch):
    """Test that voice returns clear error when GEMINI_API_KEY is missing outside test mock."""
    from voice.service import VoiceService
    from rag.gemini import GeminiClient

    client_no_key = GeminiClient(api_key="")
    voice_no_key = VoiceService(gemini_client=client_no_key)

    # Temporarily clear PYTEST_CURRENT_TEST to simulate live production invocation
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("TESTING", raising=False)

    res = voice_no_key.transcribe(b"SAMPLE_BYTES_FOR_LIVE_MODE", lang="en")
    assert res["is_empty"] is True
    assert "GEMINI_API_KEY" in res.get("error", "")
