import pytest
from unittest.mock import MagicMock
from app.services.rag_service import RAGService


def make_rag():
    chroma = MagicMock()
    chroma.query_faq.return_value = [
        {"text": "Returns within 15 days.", "metadata": {}, "distance": 0.1}
    ]
    chroma.query_products.return_value = [
        {"text": "Product: Oxford Shirt. Price: Rs.2999.", "metadata": {}, "distance": 0.05}
    ]
    return RAGService(chroma)


def test_intent_product_search():
    rag = make_rag()
    assert rag._detect_intent("formal shirts dikhao under 3000") == "product_search"


def test_intent_product_search_english():
    rag = make_rag()
    assert rag._detect_intent("show me blazers") == "product_search"


def test_intent_sizing():
    rag = make_rag()
    assert rag._detect_intent("what size should I choose") == "sizing"


def test_intent_sizing_hindi():
    rag = make_rag()
    assert rag._detect_intent("mera chest 42 inches hai") == "sizing"


def test_intent_order_support():
    rag = make_rag()
    assert rag._detect_intent("I want to return my order") == "order_support"


def test_intent_order_support_hindi():
    rag = make_rag()
    assert rag._detect_intent("return karna hai") == "order_support"


def test_intent_faq_fallback():
    rag = make_rag()
    assert rag._detect_intent("tell me about your brand") == "faq"


def test_intent_price_digit_triggers_product_search():
    rag = make_rag()
    assert rag._detect_intent("kuch 2000 mein dena") == "product_search"


@pytest.mark.asyncio
async def test_get_context_returns_all_keys():
    rag = make_rag()
    context = await rag.get_context("formal shirts dikhao")
    assert "intent" in context
    assert "faq_context" in context
    assert "product_context" in context
    assert "has_faq" in context
    assert "has_products" in context


def test_system_prompt_contains_faq_context():
    rag = make_rag()
    context = {
        "intent": "faq",
        "faq_context": "Returns within 15 days.",
        "product_context": "",
        "has_faq": True,
        "has_products": False,
    }
    prompt = rag.build_system_prompt(context, "en-IN")
    assert "Returns within 15 days." in prompt


def test_system_prompt_hindi_instruction():
    rag = make_rag()
    context = {
        "intent": "faq",
        "faq_context": "",
        "product_context": "",
        "has_faq": False,
        "has_products": False,
    }
    prompt = rag.build_system_prompt(context, "hi-IN")
    assert "Hindi" in prompt
