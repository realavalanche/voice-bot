import base64
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport


def make_wav_bytes() -> bytes:
    """Minimal valid WAV header (44 bytes) for testing."""
    import struct
    data_size = 0
    return struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, 1, 16000, 32000, 2, 16,
        b"data", data_size,
    )


@pytest.fixture
def sample_wav():
    return make_wav_bytes()


@pytest.fixture
def mock_sarvam():
    client = MagicMock()
    client.transcribe = AsyncMock(return_value={
        "transcript": "formal shirts dikhao under 3000",
        "language_code": "hi-IN",
    })
    client.generate_response = AsyncMock(
        return_value="Aapke liye hamare paas kuch behtareen formal shirts hain."
    )
    client.synthesize_speech = AsyncMock(
        return_value=base64.b64decode(
            "UklGRiQAAABXQVZFZm10IBAAAA"  # tiny base64 stub
            "EAAQAAgD4AAAQACAABACAAAA=="
        )
    )
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_chroma():
    svc = MagicMock()
    svc.is_initialized.return_value = True
    svc.faq_count.return_value = 42
    svc.product_count.return_value = 50
    svc.query_faq.return_value = [
        {"text": "Q: Return policy?\nA: 15 days, unworn with tags.", "metadata": {}, "distance": 0.1}
    ]
    svc.query_products.return_value = [
        {
            "text": "Product: Oxford Formal Shirt. Category: formal_shirt. Price: Rs.2999.",
            "metadata": {"id": "fs_001", "name": "Oxford Formal Shirt", "category": "formal_shirt", "price": 2999, "in_stock": True},
            "distance": 0.05,
        }
    ]
    return svc


@pytest_asyncio.fixture
async def client(mock_sarvam, mock_chroma):
    from app.main import app
    from app.services.rag_service import RAGService
    from app.services.voice_pipeline import VoicePipeline
    from app.config import get_settings

    app.state.settings = get_settings()
    app.state.chroma_service = mock_chroma
    app.state.sarvam_client = mock_sarvam
    app.state.rag_service = RAGService(mock_chroma)
    app.state.voice_pipeline = VoicePipeline(mock_sarvam, RAGService(mock_chroma))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
