import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query, Request
from app.models.responses import ProductListResponse, ProductResponse

logger = logging.getLogger(__name__)
router = APIRouter()


def _load_all_products(products_json_path: str) -> list[dict]:
    path = Path(products_json_path)
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


@router.get("/api/products", response_model=ProductListResponse)
async def search_products(
    request: Request,
    q: str = Query(default="", description="Semantic search query"),
    category: Optional[str] = Query(default=None),
    max_price: Optional[int] = Query(default=None, ge=0),
    color: Optional[str] = Query(default=None),
    in_stock_only: bool = Query(default=False),
    limit: int = Query(default=10, ge=1, le=50),
) -> ProductListResponse:
    settings = request.app.state.settings
    chroma_service = request.app.state.chroma_service

    if q:
        raw_results = chroma_service.query_products(q, n_results=limit * 2)
        # Semantic results come as text docs; re-load full product data by id
        all_products = _load_all_products(settings.products_json_path)
        product_map = {p["id"]: p for p in all_products}
        products = []
        for r in raw_results:
            pid = r.get("metadata", {}).get("id")
            if pid and pid in product_map:
                products.append(product_map[pid])
    else:
        products = _load_all_products(settings.products_json_path)

    # Apply filters
    if category:
        products = [p for p in products if p.get("category") == category]
    if max_price is not None:
        products = [p for p in products if p.get("price", 0) <= max_price]
    if color:
        color_lower = color.lower()
        products = [
            p for p in products
            if any(color_lower in c.lower() for c in p.get("colors", []))
        ]
    if in_stock_only:
        products = [p for p in products if p.get("in_stock", True)]

    products = products[:limit]
    parsed = [ProductResponse(**p) for p in products]
    return ProductListResponse(products=parsed, total=len(parsed))
