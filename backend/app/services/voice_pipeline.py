import logging
from dataclasses import dataclass, field

from app.services.rag_service import RAGService
from app.services.sarvam_client import SarvamClient

logger = logging.getLogger(__name__)

_FALLBACK_HINDI = "Kuch samajh nahi aaya. Kripya dobara bolein."
_FALLBACK_ENGLISH = "I could not understand that. Please try again."


@dataclass
class VoiceResponse:
    transcript: str
    response_text: str
    audio_bytes: bytes
    language: str
    intent: str
    rag_debug: str = field(default="")


class VoicePipeline:
    """Orchestrates: audio → ASR → RAG → LLM → TTS → audio."""

    def __init__(self, sarvam_client: SarvamClient, rag_service: RAGService):
        self._sarvam = sarvam_client
        self._rag = rag_service

    async def process(
        self,
        audio_bytes: bytes,
        conversation_history: list[dict] | None = None,
        preferred_language: str = "auto",
    ) -> VoiceResponse:
        # Step 1: ASR — tell Sarvam which language to transcribe in.
        # "unknown" triggers Sarvam's own auto-detection.
        asr_lang = "unknown" if preferred_language == "auto" else preferred_language
        asr_result = await self._sarvam.transcribe(audio_bytes, language_code=asr_lang)
        transcript = asr_result.get("transcript", "").strip()
        detected_lang = asr_result.get("language_code", "hi-IN")
        # Response language = explicit user choice, or fall back to what ASR detected.
        response_lang = detected_lang if preferred_language == "auto" else preferred_language

        if not transcript:
            fallback_text = (
                _FALLBACK_HINDI if "hi" in response_lang else _FALLBACK_ENGLISH
            )
            fallback_audio = await self._sarvam.synthesize_speech(
                fallback_text, response_lang
            )
            return VoiceResponse(
                transcript="",
                response_text=fallback_text,
                audio_bytes=fallback_audio,
                language=detected_lang,
                intent="unknown",
            )

        # Step 2: RAG context
        context = await self._rag.get_context(transcript)

        # Step 3: LLM
        system_prompt = self._rag.build_system_prompt(context, response_lang)
        messages = (conversation_history or []) + [
            {"role": "user", "content": transcript}
        ]
        response_text = await self._sarvam.generate_response(messages, system_prompt)

        # Step 4: TTS
        lang_code = response_lang if response_lang in ("hi-IN", "en-IN") else "hi-IN"
        audio_out = await self._sarvam.synthesize_speech(response_text, lang_code)

        return VoiceResponse(
            transcript=transcript,
            response_text=response_text,
            audio_bytes=audio_out,
            language=lang_code,
            intent=context["intent"],
            rag_debug=context.get("faq_context", "")[:200],
        )
