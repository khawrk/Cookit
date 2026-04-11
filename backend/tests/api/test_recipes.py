import uuid

import pytest


@pytest.mark.asyncio
async def test_get_recommendations_empty_fridge(auth_client):
    response = await auth_client.get("/api/recipes/recommend")
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    assert isinstance(data["recommendations"], list)


@pytest.mark.asyncio
async def test_get_recipe_not_found(auth_client):
    fake_id = uuid.uuid4()
    response = await auth_client.get(f"/api/recipes/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_search_recipes(auth_client):
    response = await auth_client.get("/api/recipes/search?q=chicken")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_search_requires_query(auth_client):
    response = await auth_client.get("/api/recipes/search")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_recipes_require_auth(client):
    response = await client.get("/api/recipes/recommend")
    assert response.status_code == 401
