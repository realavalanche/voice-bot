from datetime import datetime, timezone
from fastapi import APIRouter, Request
from app.models.responses import ChromaInfo, DiskInfo, HealthResponse
from app.utils.disk_utils import get_disk_info

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    chroma_service = request.app.state.chroma_service
    disk = get_disk_info(request.app.state.settings.chroma_persist_dir)

    initialized = chroma_service.is_initialized()
    faq_count = chroma_service.faq_count() if initialized else 0
    product_count = chroma_service.product_count() if initialized else 0

    degraded = not initialized or disk["percent"] >= 90.0
    status = "degraded" if degraded else "healthy"

    return HealthResponse(
        status=status,
        disk=DiskInfo(**disk),
        chroma=ChromaInfo(
            initialized=initialized,
            faq_docs=faq_count,
            product_docs=product_count,
        ),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
