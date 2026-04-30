import pytest


@pytest.mark.asyncio
async def test_voice_chat_success(client, sample_wav):
    response = await client.post(
        "/api/voice-chat",
        files={"audio": ("test.wav", sample_wav, "audio/wav")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "transcript" in data
    assert "response_text" in data
    assert "audio_base64" in data
    assert "language" in data
    assert "intent" in data


@pytest.mark.asyncio
async def test_voice_chat_has_processing_time(client, sample_wav):
    data = (
        await client.post(
            "/api/voice-chat",
            files={"audio": ("test.wav", sample_wav, "audio/wav")},
        )
    ).json()
    assert data["processing_time_ms"] >= 0


@pytest.mark.asyncio
async def test_voice_chat_rejects_oversized_audio(client):
    big_audio = b"X" * (11 * 1024 * 1024)
    response = await client.post(
        "/api/voice-chat",
        files={"audio": ("big.wav", big_audio, "audio/wav")},
    )
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_voice_chat_rejects_empty_audio(client):
    response = await client.post(
        "/api/voice-chat",
        files={"audio": ("empty.wav", b"", "audio/wav")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_voice_chat_empty_transcript_fallback(client, mock_sarvam, sample_wav):
    from unittest.mock import AsyncMock
    mock_sarvam.transcribe = AsyncMock(return_value={"transcript": "", "language_code": "hi-IN"})
    response = await client.post(
        "/api/voice-chat",
        files={"audio": ("test.wav", sample_wav, "audio/wav")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["transcript"] == ""
    assert data["response_text"] != ""
