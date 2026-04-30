import asyncio
import logging

from app.services.chroma_service import ChromaService

logger = logging.getLogger(__name__)

_PRODUCT_KEYWORDS = {
    "dikhao", "show", "shirt", "trouser", "jacket", "blazer", "jeans",
    "chino", "shorts", "belt", "under", "price", "buy", "collection",
    "available", "colors", "colour", "size", "style", "track", "polo",
    "tshirt", "t-shirt", "denim", "formal", "casual", "linen",
}
_SIZING_KEYWORDS = {
    "size", "fit", "chest", "waist", "measurement", "inches", "fitting",
    "measurements", "slim", "regular", "tailor", "naap",
}
_ORDER_KEYWORDS = {
    "return", "refund", "cancel", "track", "order", "deliver", "delivery",
    "shipping", "exchange", "wapas", "vapas", "bhejo",
}


class RAGService:
    def __init__(self, chroma_service: ChromaService):
        self._chroma = chroma_service

    async def get_context(self, user_query: str, n_faq: int = 3, n_products: int = 5) -> dict:
        """Parallel FAQ + product query. Returns structured context for LLM prompt."""
        faq_task = asyncio.to_thread(self._chroma.query_faq, user_query, n_faq)
        product_task = asyncio.to_thread(self._chroma.query_products, user_query, n_products)
        faq_results, product_results = await asyncio.gather(faq_task, product_task)

        intent = self._detect_intent(user_query)
        return {
            "intent": intent,
            "faq_context": self._format_faq_context(faq_results),
            "product_context": self._format_product_context(product_results),
            "has_faq": bool(faq_results),
            "has_products": bool(product_results),
        }

    def _detect_intent(self, query: str) -> str:
        words = set(query.lower().split())
        if words & _SIZING_KEYWORDS:
            return "sizing"
        if words & _ORDER_KEYWORDS:
            return "order_support"
        if words & _PRODUCT_KEYWORDS:
            return "product_search"
        # Heuristic: contains price digits → product search
        if any(char.isdigit() for char in query):
            return "product_search"
        return "faq"

    def _format_faq_context(self, results: list[dict]) -> str:
        if not results:
            return ""
        lines = []
        for r in results:
            text = r.get("text", "").strip()
            if text:
                lines.append(text)
        return "\n\n".join(lines)

    def _format_product_context(self, results: list[dict]) -> str:
        if not results:
            return ""
        lines = []
        for r in results:
            text = r.get("text", "").strip()
            if text:
                lines.append(f"- {text}")
        return "\n".join(lines)

    def build_system_prompt(self, context: dict, detected_language: str = "hi-IN") -> str:
        lang_instruction = (
            "Respond in Hindi (Devanagari script or Roman Hindi is fine)."
            if "hi" in detected_language
            else "Respond in English."
        )

        prompt = f"""You are a helpful voice assistant for Reid & Taylor, a premium Indian menswear brand.

IMPORTANT RULES:
- Keep responses to 2-3 sentences maximum — your answer will be spoken aloud.
- Do NOT use markdown, bullet points, or numbered lists.
- Do NOT use <think> or any internal reasoning — reply directly.
- {lang_instruction}
- Be warm, professional, and helpful.
- If you don't know, politely say so and suggest contacting support.

BRAND INFO:
Reid & Taylor — premium menswear since the 1830s. Website: www.reidandtaylor.in
Support: support@rtil.in | 1800-203-0571 (Mon–Fri 10:30–18:30 IST)
Returns: 15 days, unworn with tags. Refund in 2–7 business days.
Shipping: Standard 1–7 days, Express 2–5 days. India only.
"""

        if context["has_faq"]:
            prompt += f"\nRELEVANT FAQ INFORMATION:\n{context['faq_context']}\n"

        if context["has_products"] and context["intent"] in ("product_search", "sizing"):
            prompt += f"\nRELEVANT PRODUCTS:\n{context['product_context']}\n"

        prompt += "\nAnswer only from the information above. Keep it brief and conversational."
        return prompt
