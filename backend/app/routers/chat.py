import logging

from fastapi import APIRouter, Request
from app.models.requests import ChatRequest
from app.models.responses import ChatResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/chat", response_model=ChatResponse)
async def text_chat(request: Request, body: ChatRequest) -> ChatResponse:
    """Text-only fallback — skips ASR and TTS."""
    rag_service = request.app.state.rag_service
    sarvam_client = request.app.state.sarvam_client

    context = await rag_service.get_context(body.message)
    lang = body.language if body.language != "auto" else "hi-IN"
    system_prompt = rag_service.build_system_prompt(context, lang)
    messages = list(body.history) + [{"role": "user", "content": body.message}]
    response_text = await sarvam_client.generate_response(messages, system_prompt)

    return ChatResponse(
        response=response_text,
        intent=context["intent"],
        sources=[],
    )
