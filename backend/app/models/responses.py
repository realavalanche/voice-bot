from typing import Literal, Optional
from pydantic import BaseModel


class DiskInfo(BaseModel):
    path: str
    used_gb: float
    total_gb: float
    percent: float


class ChromaInfo(BaseModel):
    initialized: bool
    faq_docs: int
    product_docs: int


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    disk: DiskInfo
    chroma: ChromaInfo
    timestamp: str


class VoiceChatResponse(BaseModel):
    transcript: str
    response_text: str
    audio_base64: str
    language: str
    intent: str
    processing_time_ms: Optional[int] = None


class ChatResponse(BaseModel):
    response: str
    intent: str
    sources: list[str] = []


class ProductResponse(BaseModel):
    id: str
    name: str
    category: str
    price: int
    colors: list[str]
    sizes: list[str | int]
    fit: Optional[str] = None
    fabric: Optional[str] = None
    description: str
    in_stock: bool
    collection: Optional[str] = None
    image_url: Optional[str] = None


class ProductListResponse(BaseModel):
    products: list[ProductResponse]
    total: int
