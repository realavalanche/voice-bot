import asyncio
import base64
import hashlib
import json
import logging
import re
import time
from typing import AsyncGenerator, Optional

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


class ResponseCache:
    """In-memory TTL cache. No Redis dependency; sufficient for 50 concurrent users."""

    def __init__(self, ttl_seconds: int = 3600):
        self._store: dict[str, tuple[object, float]] = {}
        self._ttl = ttl_seconds
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[object]:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    async def set(self, key: str, value: object) -> None:
        async with self._lock:
            self._store[key] = (value, time.monotonic() + self._ttl)
            # Evict stale entries periodically (every 100 sets)
            if len(self._store) % 100 == 0:
                self._evict_expired()

    def _evict_expired(self) -> None:
        now = time.monotonic()
        stale = [k for k, (_, exp) in self._store.items() if now > exp]
        for k in stale:
            del self._store[k]


class SarvamClient:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._cache = ResponseCache(ttl_seconds=settings.cache_ttl_seconds)
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self._settings.sarvam_base_url,
                headers={"api-subscription-key": self._settings.sarvam_api_key},
                timeout=httpx.Timeout(15.0, connect=5.0),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )
        return self._http_client

    async def transcribe(
        self,
        audio_bytes: bytes,
        language_code: str = "hi-IN",
    ) -> dict:
        """
        POST /speech-to-text — ASR not cached (audio is unique per call).
        Returns {"transcript": str, "language_code": str}
        """
        client = await self._get_client()
        files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
        data = {"model": "saarika:v2.5", "language_code": language_code}
        try:
            response = await client.post("/speech-to-text", files=files, data=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error("Sarvam ASR error %s: %s", e.response.status_code, e.response.text)
            raise

    async def generate_response(
        self,
        messages: list[dict],
        system_prompt: str,
        temperature: float = 0.3,
    ) -> str:
        """
        POST /v1/chat/completions — OpenAI-compatible.
        Cached by hash of system_prompt + last user message.
        Returns assistant message string.
        """
        last_user_msg = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"), ""
        )
        cache_key = _sha256("llm", system_prompt, last_user_msg)
        cached = await self._cache.get(cache_key)
        if cached is not None:
            logger.debug("LLM cache hit")
            return cached  # type: ignore[return-value]

        payload = {
            "model": "sarvam-m",
            "messages": [{"role": "system", "content": system_prompt}] + messages,
            "temperature": temperature,
            "max_tokens": 500,
        }
        client = await self._get_client()
        try:
            response = await client.post("/v1/chat/completions", json=payload)
            response.raise_for_status()
            result: str = response.json()["choices"][0]["message"]["content"]
            # sarvam-m is a reasoning model — strip <think>…</think> blocks.
            # Also handles unclosed <think> tags (response truncated by max_tokens).
            result = re.sub(r"<think>.*?</think>", "", result, flags=re.DOTALL)
            if "<think>" in result:
                result = result[:result.index("<think>")]
            result = result.strip()
        except httpx.HTTPStatusError as e:
            logger.error("Sarvam LLM error %s: %s", e.response.status_code, e.response.text)
            raise

        await self._cache.set(cache_key, result)
        return result

    async def generate_response_stream(
        self,
        messages: list[dict],
        system_prompt: str,
        temperature: float = 0.3,
    ) -> AsyncGenerator[str, None]:
        """
        Streaming version of generate_response.
        Yields complete sentences as they arrive from the LLM.
        Strips <think>...</think> reasoning blocks.
        Used by the phone pipeline for low-latency sentence-level TTS.
        """
        payload = {
            "model": "sarvam-m",
            "messages": [{"role": "system", "content": system_prompt}] + messages,
            "temperature": temperature,
            "max_tokens": 300,
            "stream": True,
        }
        client = await self._get_client()
        buffer = ""
        in_think = False

        try:
            async with client.stream("POST", "/v1/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        delta = json.loads(data)["choices"][0]["delta"].get("content", "")
                        if not delta:
                            continue
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

                    buffer += delta

                    # Track and strip <think>...</think> blocks
                    while True:
                        if not in_think and "<think>" in buffer:
                            in_think = True
                            buffer = buffer[buffer.index("<think>") + len("<think>"):]
                        if in_think:
                            if "</think>" in buffer:
                                buffer = buffer[buffer.index("</think>") + len("</think>"):]
                                in_think = False
                            else:
                                buffer = ""  # discard think content still accumulating
                                break
                        else:
                            break

                    if in_think:
                        continue

                    # Yield complete sentences (split on . ! ? । followed by space/end)
                    while True:
                        match = re.search(r'[.!?।](?:\s+|$)', buffer)
                        if not match:
                            break
                        sentence = buffer[:match.end()].strip()
                        buffer = buffer[match.end():]
                        if sentence:
                            yield sentence
        except httpx.HTTPStatusError as e:
            logger.error("Sarvam streaming LLM error %s: %s",
                         e.response.status_code, e.response.text)
            raise

        # Yield any remaining text that didn't end with punctuation
        buffer = buffer.strip()
        if buffer:
            yield buffer

    async def synthesize_speech(
        self,
        text: str,
        target_language_code: str = "hi-IN",
        speaker: str = "anushka",
    ) -> bytes:
        """
        POST /text-to-speech.
        Cached by hash of (text, language_code, speaker).
        Returns raw WAV bytes.
        """
        cache_key = _sha256("tts", text, target_language_code, speaker)
        cached = await self._cache.get(cache_key)
        if cached is not None:
            logger.debug("TTS cache hit")
            return cached  # type: ignore[return-value]

        payload = {
            "inputs": [text],
            "target_language_code": target_language_code,
            "speaker": speaker,
            "model": "bulbul:v2",
            "pitch": 0,
            "pace": 1.0,
            "loudness": 1.5,
            "enable_preprocessing": True,
        }
        client = await self._get_client()
        try:
            response = await client.post("/text-to-speech", json=payload)
            response.raise_for_status()
            audio_b64: str = response.json()["audios"][0]
            audio_bytes = base64.b64decode(audio_b64)
        except httpx.HTTPStatusError as e:
            logger.error("Sarvam TTS error %s: %s", e.response.status_code, e.response.text)
            raise

        await self._cache.set(cache_key, audio_bytes)
        return audio_bytes

    async def close(self) -> None:
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


def _sha256(*parts: str) -> str:
    combined = "|".join(parts)
    return hashlib.sha256(combined.encode()).hexdigest()
