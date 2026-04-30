import pytest


@pytest.mark.asyncio
async def test_chat_hindi(client):
    response = await client.post(
        "/api/chat",
        json={"message": "Aapka return policy kya hai?", "language": "hi-IN"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "intent" in data


@pytest.mark.asyncio
async def test_chat_english(client):
    response = await client.post(
        "/api/chat",
        json={"message": "What is your return policy?", "language": "en-IN"},
    )
    assert response.status_code == 200
    assert response.json()["response"]


@pytest.mark.asyncio
async def test_chat_with_history(client):
    response = await client.post(
        "/api/chat",
        json={
            "message": "And for shipping?",
            "language": "en-IN",
            "history": [
                {"role": "user", "content": "What is the return policy?"},
                {"role": "assistant", "content": "Returns within 15 days."},
            ],
        },
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_chat_rejects_empty_message(client):
    response = await client.post(
        "/api/chat",
        json={"message": "", "language": "hi-IN"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_intent_returned(client):
    response = await client.post(
        "/api/chat",
        json={"message": "formal shirts dikhao under 3000", "language": "hi-IN"},
    )
    assert response.json()["intent"] in (
        "product_search", "sizing", "order_support", "faq"
    )
