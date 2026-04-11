import io
from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_list_fridge_items_empty(auth_client):
    response = await auth_client.get("/api/fridge/items")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_add_fridge_item(auth_client):
    payload = {"item_name": "butter", "quantity": 1, "unit": "block", "source": "manual"}
    response = await auth_client.post("/api/fridge/items", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["item_name"] == "butter"
    assert data["source"] == "manual"


@pytest.mark.asyncio
async def test_add_fridge_item_deduplicates(auth_client):
    payload = {"item_name": "milk", "quantity": 1, "unit": "bottle", "source": "manual"}
    await auth_client.post("/api/fridge/items", json=payload)
    payload["quantity"] = 2
    response = await auth_client.post("/api/fridge/items", json=payload)
    assert response.status_code == 201

    items_response = await auth_client.get("/api/fridge/items")
    milk_items = [i for i in items_response.json() if i["item_name"] == "milk"]
    assert len(milk_items) == 1
    assert milk_items[0]["quantity"] == 2.0


@pytest.mark.asyncio
async def test_update_fridge_item(auth_client):
    add_response = await auth_client.post(
        "/api/fridge/items",
        json={"item_name": "cheese", "quantity": 100, "unit": "g", "source": "manual"},
    )
    item_id = add_response.json()["id"]

    update_response = await auth_client.patch(
        f"/api/fridge/items/{item_id}", json={"quantity": 200}
    )
    assert update_response.status_code == 200
    assert update_response.json()["quantity"] == 200.0


@pytest.mark.asyncio
async def test_delete_fridge_item(auth_client):
    add_response = await auth_client.post(
        "/api/fridge/items",
        json={"item_name": "yogurt", "quantity": 1, "unit": "cup", "source": "manual"},
    )
    item_id = add_response.json()["id"]

    delete_response = await auth_client.delete(f"/api/fridge/items/{item_id}")
    assert delete_response.status_code == 204

    items_response = await auth_client.get("/api/fridge/items")
    ids = [i["id"] for i in items_response.json()]
    assert item_id not in ids


@pytest.mark.asyncio
async def test_scan_requires_auth(client):
    response = await client.post("/api/fridge/scan")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_scan_fridge(auth_client, mock_anthropic):
    with patch("app.services.vision.storage.upload_image", return_value="key"):
        response = await auth_client.post(
            "/api/fridge/scan",
            files={"file": ("fridge.jpg", io.BytesIO(b"fake-image"), "image/jpeg")},
        )
    assert response.status_code == 200
    data = response.json()
    assert "detected" in data
    assert "saved_count" in data
