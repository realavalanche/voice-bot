import base64
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.services.sarvam_client import SarvamClient, ResponseCache
from app.config import Settings


def make_settings(**overrides) -> Settings:
    defaults = {
        "sarvam_api_key": "test-key",
        "sarvam_base_url": "https://api.sarvam.ai",
        "cache_ttl_seconds": 3600,
    }
    return Settings(**{**defaults, **overrides})


@pytest.mark.asyncio
async def test_response_cache_miss_then_hit():
    cache = ResponseCache(ttl_seconds=60)
    assert await cache.get("k1") is None
    await cache.set("k1", "hello")
    assert await cache.get("k1") == "hello"


@pytest.mark.asyncio
async def test_response_cache_expired():
    import time
    cache = ResponseCache(ttl_seconds=0)
    await cache.set("k2", "value")
    # TTL=0 means immediately expired
    result = await cache.get("k2")
    assert result is None


@pytest.mark.asyncio
async def test_tts_cache_hit():
    settings = make_settings()
    client = SarvamClient(settings)

    audio_b64 = base64.b64encode(b"FAKE_WAV").decode()
    mock_response = MagicMock()
    mock_response.json.return_value = {"audios": [audio_b64]}
    mock_response.raise_for_status = MagicMock()

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(return_value=mock_response)
    client._http_client = mock_http

    audio1 = await client.synthesize_speech("Hello", "en-IN")
    audio2 = await client.synthesize_speech("Hello", "en-IN")

    assert audio1 == audio2
    assert mock_http.post.call_count == 1  # second call used cache


@pytest.mark.asyncio
async def test_llm_cache_hit():
    settings = make_settings()
    client = SarvamClient(settings)

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Test response"}}]
    }
    mock_response.raise_for_status = MagicMock()

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(return_value=mock_response)
    client._http_client = mock_http

    messages = [{"role": "user", "content": "What is return policy?"}]
    r1 = await client.generate_response(messages, system_prompt="You are helpful.")
    r2 = await client.generate_response(messages, system_prompt="You are helpful.")

    assert r1 == r2
    assert mock_http.post.call_count == 1


@pytest.mark.asyncio
async def test_asr_not_cached():
    """ASR should call API on every invocation (audio is unique)."""
    settings = make_settings()
    client = SarvamClient(settings)

    mock_response = MagicMock()
    mock_response.json.return_value = {"transcript": "hello", "language_code": "en-IN"}
    mock_response.raise_for_status = MagicMock()

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(return_value=mock_response)
    client._http_client = mock_http

    await client.transcribe(b"audio1")
    await client.transcribe(b"audio2")

    assert mock_http.post.call_count == 2
