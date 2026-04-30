import base64
import time
import logging

import httpx
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from app.models.responses import VoiceChatResponse

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10MB


@router.post("/api/voice-chat", response_model=VoiceChatResponse)
async def voice_chat(
    request: Request,
    audio: UploadFile = File(..., description="Audio file (WAV, MP3, OGG, WebM)"),
    language: str = Form(default="auto"),
) -> VoiceChatResponse:
    audio_bytes = await audio.read()
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio file too large (max 10MB)")
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    pipeline = request.app.state.voice_pipeline
    t0 = time.monotonic()
    try:
        result = await pipeline.process(audio_bytes, preferred_language=language)
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Sarvam API error {e.response.status_code}: {e.response.text[:200]}",
        )
    except Exception as e:
        logger.exception("Voice pipeline failed")
        raise HTTPException(status_code=500, detail=str(e))
    elapsed_ms = int((time.monotonic() - t0) * 1000)

    return VoiceChatResponse(
        transcript=result.transcript,
        response_text=result.response_text,
        audio_base64=base64.b64encode(result.audio_bytes).decode(),
        language=result.language,
        intent=result.intent,
        processing_time_ms=elapsed_ms,
    )
