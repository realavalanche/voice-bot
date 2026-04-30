import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import Settings
from app.utils.pdf_loader import extract_faq_chunks

logger = logging.getLogger(__name__)


class ChromaService:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._client: Optional[chromadb.ClientAPI] = None
        self._faq_collection = None
        self._products_collection = None
        self._initialized = False

    async def initialize(self) -> None:
        if self._initialized:
            return

        persist_dir = self._settings.chroma_persist_dir
        Path(persist_dir).mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        self._faq_collection = self._client.get_or_create_collection(
            name=self._settings.chroma_faq_collection,
            metadata={"hnsw:space": "cosine"},
        )
        self._products_collection = self._client.get_or_create_collection(
            name=self._settings.chroma_products_collection,
            metadata={"hnsw:space": "cosine"},
        )

        if self._faq_collection.count() == 0:
            await asyncio.to_thread(self._ingest_faq)
            logger.info("FAQ ingestion complete: %d chunks", self._faq_collection.count())

        if self._products_collection.count() == 0:
            await asyncio.to_thread(self._ingest_products)
            logger.info("Products ingestion complete: %d items", self._products_collection.count())

        self._initialized = True
        logger.info(
            "ChromaDB ready — faq=%d, products=%d",
            self._faq_collection.count(),
            self._products_collection.count(),
        )

    def _ingest_faq(self) -> None:
        chunks = extract_faq_chunks(self._settings.faq_pdf_path)
        if not chunks:
            logger.warning("No FAQ chunks extracted from PDF")
            return

        documents = [c["text"] for c in chunks]
        ids = [f"faq_{i}" for i in range(len(chunks))]
        metadatas = [
            {"section": c["section"], "question": c.get("question", "")}
            for c in chunks
        ]
        self._faq_collection.upsert(documents=documents, ids=ids, metadatas=metadatas)

    def _ingest_products(self) -> None:
        products_path = self._settings.products_json_path
        if not Path(products_path).exists():
            logger.warning("products.json not found at %s", products_path)
            return

        with open(products_path) as f:
            products = json.load(f)

        documents, ids, metadatas = [], [], []
        for p in products:
            sizes_str = ", ".join(str(s) for s in p.get("sizes", []))
            colors_str = ", ".join(p.get("colors", []))
            doc_text = (
                f"Product: {p['name']}. Category: {p['category']}. "
                f"Price: Rs.{p['price']}. Colors: {colors_str}. "
                f"Sizes: {sizes_str}. Fit: {p.get('fit', 'N/A')}. "
                f"Description: {p.get('description', '')}."
            )
            documents.append(doc_text)
            ids.append(f"product_{p['id']}")
            metadatas.append({
                "id": p["id"],
                "name": p["name"],
                "category": p["category"],
                "price": p["price"],
                "in_stock": p.get("in_stock", True),
            })

        self._products_collection.upsert(documents=documents, ids=ids, metadatas=metadatas)

    def query_faq(self, query_text: str, n_results: int = 3) -> list[dict]:
        if not self._initialized:
            return []
        results = self._faq_collection.query(
            query_texts=[query_text],
            n_results=min(n_results, self._faq_collection.count()),
            include=["documents", "distances", "metadatas"],
        )
        return self._format_results(results)

    def query_products(self, query_text: str, n_results: int = 5) -> list[dict]:
        if not self._initialized:
            return []
        results = self._products_collection.query(
            query_texts=[query_text],
            n_results=min(n_results, self._products_collection.count()),
            include=["documents", "distances", "metadatas"],
        )
        return self._format_results(results)

    def _format_results(self, results) -> list[dict]:
        out = []
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        for doc, meta, dist in zip(docs, metas, distances):
            out.append({"text": doc, "metadata": meta, "distance": dist})
        return out

    def is_initialized(self) -> bool:
        return self._initialized

    def faq_count(self) -> int:
        if self._faq_collection is None:
            return 0
        return self._faq_collection.count()

    def product_count(self) -> int:
        if self._products_collection is None:
            return 0
        return self._products_collection.count()
