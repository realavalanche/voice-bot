import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import get_settings
from app.services.chroma_service import ChromaService
from app.services.rag_service import RAGService
from app.services.sarvam_client import SarvamClient
from app.services.voice_pipeline import VoicePipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings

    chroma_service = ChromaService(settings)
    await chroma_service.initialize()
    app.state.chroma_service = chroma_service

    sarvam_client = SarvamClient(settings)
    app.state.sarvam_client = sarvam_client

    rag_service = RAGService(chroma_service)
    app.state.rag_service = rag_service

    voice_pipeline = VoicePipeline(sarvam_client, rag_service)
    app.state.voice_pipeline = voice_pipeline

    # Warm up ChromaDB collections so the first real query isn't slow.
    # Without this the first call takes ~2.4s just for RAG; after warmup it's ~0.14s.
    logger.info("Warming up ChromaDB collections…")
    try:
        await rag_service.get_context("shirts")
        logger.info("ChromaDB warmup complete")
    except Exception as e:
        logger.warning("ChromaDB warmup failed (non-fatal): %s", e)

    logger.info("Reid & Taylor Voice Bot backend ready")
    yield

    await sarvam_client.close()
    logger.info("Backend shutdown complete")


app = FastAPI(
    title="Reid & Taylor Voice Bot",
    description="Bilingual (Hindi/English) voice assistant for premium menswear",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import health, voice, chat, products, calls  # noqa: E402

app.include_router(health.router)
app.include_router(voice.router)
app.include_router(chat.router)
app.include_router(products.router)
app.include_router(calls.router)

# Serve React frontend — must come after API routers
_FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"
if _FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        file = _FRONTEND_DIST / full_path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(_FRONTEND_DIST / "index.html")
