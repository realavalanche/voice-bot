import pytest


@pytest.mark.asyncio
async def test_products_no_filter(client):
    response = await client.get("/api/products")
    assert response.status_code == 200
    data = response.json()
    assert "products" in data
    assert "total" in data
    assert isinstance(data["products"], list)


@pytest.mark.asyncio
async def test_products_category_filter(client):
    response = await client.get("/api/products?category=formal_shirt")
    assert response.status_code == 200
    for p in response.json()["products"]:
        assert p["category"] == "formal_shirt"


@pytest.mark.asyncio
async def test_products_max_price_filter(client):
    response = await client.get("/api/products?max_price=2999")
    assert response.status_code == 200
    for p in response.json()["products"]:
        assert p["price"] <= 2999


@pytest.mark.asyncio
async def test_products_combined_filters(client):
    response = await client.get(
        "/api/products?category=formal_shirt&max_price=3000&in_stock_only=true"
    )
    assert response.status_code == 200
    for p in response.json()["products"]:
        assert p["category"] == "formal_shirt"
        assert p["price"] <= 3000
        assert p["in_stock"] is True


@pytest.mark.asyncio
async def test_products_limit(client):
    response = await client.get("/api/products?limit=3")
    assert response.status_code == 200
    assert len(response.json()["products"]) <= 3


@pytest.mark.asyncio
async def test_products_semantic_search(client, mock_chroma):
    response = await client.get("/api/products?q=formal+shirts+under+3000")
    assert response.status_code == 200
