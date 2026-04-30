import pytest


@pytest.mark.asyncio
async def test_health_returns_200(client):
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_shape(client):
    data = (await client.get("/health")).json()
    assert data["status"] in ("healthy", "degraded", "unhealthy")
    assert "disk" in data
    assert "chroma" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_health_disk_fields(client):
    disk = (await client.get("/health")).json()["disk"]
    assert "used_gb" in disk
    assert "total_gb" in disk
    assert "percent" in disk
    assert disk["percent"] >= 0


@pytest.mark.asyncio
async def test_health_chroma_initialized(client):
    chroma = (await client.get("/health")).json()["chroma"]
    assert chroma["initialized"] is True
    assert chroma["faq_docs"] == 42
    assert chroma["product_docs"] == 50


@pytest.mark.asyncio
async def test_health_degraded_when_chroma_not_ready(client, mock_chroma):
    mock_chroma.is_initialized.return_value = False
    response = await client.get("/health")
    assert response.json()["status"] == "degraded"
