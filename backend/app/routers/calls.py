import asyncio
import base64
import io
import json
import logging
import re
import time
import wave
from typing import Optional

try:
    import audioop
except ModuleNotFoundError:
    import audioop_lts as audioop  # Python 3.13+ replacement

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from twilio.rest import Client as TwilioClient
from twilio.twiml.voice_response import Connect, VoiceResponse as TwiML

logger = logging.getLogger(__name__)
router = APIRouter()

# Voice activity detection thresholds
# Phone audio is noisier than browser mic — higher thresholds prevent
# background noise triggering a false pipeline run.
_SILENCE_RMS = 600      # mulaw RMS — below this = silence (phone noise ~200-400)
_SILENCE_CHUNKS = 60    # ~1.2 s at 20 ms/chunk before auto-stop (was 1.6 s)
_MIN_CHUNKS = 25        # ignore utterances shorter than ~500 ms

_GREETING_EN = "Hello! Welcome to Reid and Taylor. How can I help you today?"
_GREETING_HI = "Namaste! Reid aur Taylor mein aapka swagat hai. Aap ki kya help kar sakta hoon?"


# ── Audio conversion helpers ──────────────────────────────────────────────────

def _mulaw_to_wav16k(mulaw: bytes) -> bytes:
    """Twilio mulaw 8 kHz mono → PCM-16 WAV 16 kHz (Sarvam ASR format)."""
    pcm8k = audioop.ulaw2lin(mulaw, 2)
    pcm16k, _ = audioop.ratecv(pcm8k, 2, 1, 8000, 16000, None)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(pcm16k)
    return buf.getvalue()


def _wav_to_mulaw8k(wav: bytes) -> bytes:
    """Sarvam TTS WAV (any rate/channels) → mulaw 8 kHz mono (Twilio format)."""
    buf = io.BytesIO(wav)
    with wave.open(buf, "rb") as wf:
        rate = wf.getframerate()
        ch = wf.getnchannels()
        sw = wf.getsampwidth()
        pcm = wf.readframes(wf.getnframes())
    if ch == 2:
        pcm = audioop.tomono(pcm, sw, 0.5, 0.5)
    if sw != 2:
        pcm = audioop.lin2lin(pcm, sw, 2)
    if rate != 8000:
        pcm, _ = audioop.ratecv(pcm, 2, 1, rate, 8000, None)
    return audioop.lin2ulaw(pcm, 2)


def _build_twiml(ws_url: str) -> str:
    resp = TwiML()
    connect = Connect()
    connect.stream(url=ws_url)
    resp.append(connect)
    return str(resp)


async def _send_post_call_sms(settings, call_sid: str, history: list[dict]) -> None:
    """Send a post-call SMS to the caller with a conversation summary."""
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        return
    # Retrieve the caller's number from Twilio call details
    try:
        import asyncio
        from twilio.rest import Client as TwilioClient
        twilio = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
        call = await asyncio.to_thread(twilio.calls(call_sid).fetch)
        to_number = call.to
        if not to_number or to_number == settings.twilio_phone_number:
            return  # outbound: "to" is the customer

        # Build a brief summary from the last assistant turn
        if not history:
            body = (
                "Thank you for calling Reid & Taylor!\n\n"
                "Shop online: www.reidandtaylor.in\n"
                "Support: support@rtil.in | 1800-203-0571 (Mon–Fri 10:30–18:30 IST)"
            )
        else:
            lines = ["Thank you for calling Reid & Taylor! Here's a summary of our conversation:\n"]
            exchanges = [
                (history[i], history[i + 1])
                for i in range(0, len(history) - 1, 2)
                if history[i]["role"] == "user" and history[i + 1]["role"] == "assistant"
            ]
            for i, (user_msg, bot_msg) in enumerate(exchanges, 1):
                q = user_msg["content"][:80].rstrip()
                a = bot_msg["content"][:100].rstrip()
                lines.append(f"Q{i}: {q}")
                lines.append(f"A{i}: {a}\n")
            lines.append("Shop online: www.reidandtaylor.in")
            lines.append("Support: support@rtil.in | 1800-203-0571 (Mon–Fri 10:30–18:30 IST)")
            body = "\n".join(lines)

        await asyncio.to_thread(
            twilio.messages.create,
            to=to_number,
            from_=settings.twilio_phone_number,
            body=body,
        )
        logger.info("Post-call SMS sent to %s for call %s", to_number, call_sid)
    except Exception:
        logger.exception("Post-call SMS failed for call %s", call_sid)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/api/calls/inbound")
async def inbound_call(request: Request) -> Response:
    """
    Twilio webhook — called when a call arrives on the Twilio number.
    Returns TwiML that opens a bidirectional Media Stream to our WebSocket.
    """
    settings = request.app.state.settings
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    logger.info("Inbound call %s", call_sid)
    ws_url = f"wss://{settings.public_host}/api/calls/ws/{call_sid}"
    return Response(content=_build_twiml(ws_url), media_type="application/xml")


@router.post("/api/calls/outbound")
async def outbound_call(request: Request) -> dict:
    """
    Trigger an outbound call to a given E.164 phone number.
    Body: { "phone_number": "+91XXXXXXXXXX", "language": "en-IN" }
    """
    settings = request.app.state.settings
    body = await request.json()
    phone_number: str = body.get("phone_number", "").strip()

    if not phone_number:
        raise HTTPException(status_code=400, detail="phone_number required")
    if not phone_number.startswith("+"):
        raise HTTPException(status_code=400, detail="Use E.164 format: +91XXXXXXXXXX")
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        raise HTTPException(status_code=503, detail="Twilio credentials not configured")

    twilio = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
    twiml_url = f"https://{settings.public_host}/api/calls/inbound"
    try:
        call = twilio.calls.create(
            to=phone_number,
            from_=settings.twilio_phone_number,
            url=twiml_url,
        )
    except Exception as e:
        logger.error("Twilio outbound error: %s", e)
        raise HTTPException(status_code=502, detail=str(e))

    logger.info("Outbound call %s → %s", call.sid, phone_number)
    return {"call_sid": call.sid, "status": call.status}


@router.websocket("/api/calls/ws/{call_sid}")
async def call_media_stream(websocket: WebSocket, call_sid: str) -> None:
    """
    Twilio Media Streams WebSocket handler.
    Receives inbound mulaw audio, runs the full voice pipeline, streams
    synthesised audio back — creating a real-time phone conversation.
    """
    await websocket.accept()
    logger.info("WS accepted for call %s", call_sid)

    try:
        pipeline = websocket.app.state.voice_pipeline  # noqa: F841 — kept for greeting
        sarvam = websocket.app.state.sarvam_client
        rag_service = websocket.app.state.rag_service
    except AttributeError as e:
        logger.error("App state not ready for call %s: %s", call_sid, e)
        return

    stream_sid: Optional[str] = None
    audio_buffer: list[bytes] = []
    silence_count: int = 0
    speech_active: bool = False
    history: list[dict] = []
    ws_lock = asyncio.Lock()  # Starlette WS does not allow concurrent sends

    async def send_audio(mulaw: bytes) -> None:
        """Stream mulaw audio back to Twilio in 20 ms chunks."""
        if not stream_sid:
            return
        chunk_size = 160  # 20 ms at 8 kHz
        async with ws_lock:
            for i in range(0, len(mulaw), chunk_size):
                try:
                    await websocket.send_text(json.dumps({
                        "event": "media",
                        "streamSid": stream_sid,
                        "media": {"payload": base64.b64encode(mulaw[i:i + chunk_size]).decode()},
                    }))
                except Exception as e:
                    logger.warning("send_audio chunk failed on call %s: %s", call_sid, e)
                    return

    async def run_pipeline(chunks: list[bytes]) -> None:
        nonlocal history
        t0 = time.monotonic()
        try:
            wav = _mulaw_to_wav16k(b"".join(chunks))

            # Step 1: ASR
            asr_result = await sarvam.transcribe(wav, language_code="unknown")
            transcript = asr_result.get("transcript", "").strip()
            if not transcript:
                return  # noise — stay silent
            detected_lang = asr_result.get("language_code", "hi-IN")
            lang_code = detected_lang if detected_lang in ("hi-IN", "en-IN") else "hi-IN"
            logger.info("Call %s — [%.2fs] ASR done: %r lang: %s",
                        call_sid, time.monotonic() - t0, transcript[:80], lang_code)

            # Step 2: RAG (parallel FAQ + product lookup)
            context = await rag_service.get_context(transcript)
            system_prompt = rag_service.build_system_prompt(context, lang_code)
            messages = history + [{"role": "user", "content": transcript}]
            logger.info("Call %s — [%.2fs] RAG done, intent=%s",
                        call_sid, time.monotonic() - t0, context["intent"])

            # Step 3: LLM — full response (sarvam-m returns in ~0.15s)
            response_text = await sarvam.generate_response(messages, system_prompt)
            logger.info("Call %s — [%.2fs] LLM done: %r",
                        call_sid, time.monotonic() - t0, response_text[:80])

            # Step 4: Split into sentences and TTS all in parallel
            # Cap at 3 sentences max — voice responses must be concise.
            sentences = [s.strip() for s in re.split(r'(?<=[.!?।])\s+', response_text.strip()) if s.strip()]
            if not sentences:
                sentences = [response_text.strip()]
            sentences = sentences[:3]  # never TTS more than 3 sentences on a phone call

            tts_results = await asyncio.gather(
                *[sarvam.synthesize_speech(s, lang_code) for s in sentences],
                return_exceptions=True,
            )
            logger.info("Call %s — [%.2fs] TTS done (%d sentences)",
                        call_sid, time.monotonic() - t0, len(sentences))

            # Send audio in order
            for audio in tts_results:
                if isinstance(audio, Exception):
                    logger.warning("Call %s — TTS sentence failed: %s", call_sid, audio)
                    continue
                await send_audio(_wav_to_mulaw8k(audio))

            history = (history + [
                {"role": "user", "content": transcript},
                {"role": "assistant", "content": response_text},
            ])[-10:]
            logger.info("Call %s — [%.2fs] pipeline complete",
                        call_sid, time.monotonic() - t0)
        except Exception:
            logger.exception("Pipeline error on call %s", call_sid)

    try:
        while True:
            # Isolate receive so a single bad frame doesn't kill the call
            try:
                raw = await websocket.receive_text()
            except WebSocketDisconnect:
                logger.info("Call %s WebSocket disconnected", call_sid)
                break

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Call %s — invalid JSON: %r", call_sid, raw[:100])
                continue

            event = msg.get("event")
            # media events are very frequent — log at DEBUG only
            if event != "media":
                logger.info("Call %s — event: %s", call_sid, event)
            else:
                logger.debug("Call %s — event: media", call_sid)

            if event == "connected":
                # Twilio sends this before "start" — acknowledge and continue
                pass

            elif event == "start":
                # streamSid lives at top-level AND inside the nested "start" dict
                stream_sid = (
                    msg.get("streamSid")
                    or msg.get("start", {}).get("streamSid", "unknown")
                )
                logger.info("Call %s — stream started, streamSid=%s", call_sid, stream_sid)
                try:
                    wav = await sarvam.synthesize_speech(_GREETING_EN, "en-IN")
                    await send_audio(_wav_to_mulaw8k(wav))
                    logger.info("Call %s — greeting sent", call_sid)
                except Exception:
                    logger.exception("Greeting TTS failed for call %s", call_sid)

            elif event == "media":
                if msg.get("media", {}).get("track") != "inbound":
                    continue
                try:
                    payload = base64.b64decode(msg["media"]["payload"])
                except Exception:
                    continue
                audio_buffer.append(payload)

                try:
                    rms = audioop.rms(audioop.ulaw2lin(payload, 2), 2)
                except Exception:
                    rms = 0

                if rms > _SILENCE_RMS:
                    speech_active = True
                    silence_count = 0
                elif speech_active:
                    silence_count += 1
                    if silence_count >= _SILENCE_CHUNKS:
                        if len(audio_buffer) >= _MIN_CHUNKS:
                            asyncio.create_task(run_pipeline(list(audio_buffer)))
                        audio_buffer.clear()
                        speech_active = False
                        silence_count = 0

            elif event == "stop":
                logger.info("Call %s — stream stopped", call_sid)
                await _send_post_call_sms(websocket.app.state.settings, call_sid, history)
                break

            else:
                logger.info("Call %s — unhandled event type: %s", call_sid, event)

    except Exception:
        logger.exception("Unexpected error on call %s", call_sid)
