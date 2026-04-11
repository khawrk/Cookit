from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.schemas import NormalizedIngredient


def _make_mock_client(response_text: str) -> MagicMock:
    mock = MagicMock()
    mock.messages.create = AsyncMock(
        return_value=MagicMock(content=[MagicMock(text=response_text)])
    )
    return mock


@pytest.mark.asyncio
async def test_normalize_single_ingredient(monkeypatch):
    from app.services import normalize

    monkeypatch.setattr(
        "app.services.normalize.client",
        _make_mock_client('[{"canonical_name":"fish sauce","category":"condiment","default_unit":"tbsp"}]'),
    )

    result = await normalize.normalize_ingredient("Fish Sauce")
    assert isinstance(result, NormalizedIngredient)
    assert result.canonical_name == "fish sauce"
    assert result.category == "condiment"


@pytest.mark.asyncio
async def test_normalize_batch_caps_at_20(monkeypatch):
    from app.services import normalize

    call_count = 0
    call_sizes = []

    async def mock_create(**kwargs):
        nonlocal call_count
        call_count += 1
        content = kwargs.get("messages", [{}])[0].get("content", "")
        import json
        # extract the list from the prompt
        import re
        match = re.search(r"\[.*?\]", content, re.DOTALL)
        names = json.loads(match.group()) if match else []
        call_sizes.append(len(names))
        results = [
            {"canonical_name": n.lower(), "category": "other", "default_unit": "count"} for n in names
        ]
        return MagicMock(content=[MagicMock(text=json.dumps(results))])

    mock_client = MagicMock()
    mock_client.messages.create = mock_create
    monkeypatch.setattr("app.services.normalize.client", mock_client)

    names = [f"ingredient_{i}" for i in range(45)]
    results = await normalize.normalize_batch(names)

    assert len(results) == 45
    assert call_count == 3  # 20 + 20 + 5
    assert call_sizes == [20, 20, 5]


@pytest.mark.asyncio
async def test_normalize_strips_markdown(monkeypatch):
    from app.services import normalize

    monkeypatch.setattr(
        "app.services.normalize.client",
        _make_mock_client('```json\n[{"canonical_name":"garlic","category":"produce","default_unit":"count"}]\n```'),
    )

    result = await normalize.normalize_ingredient("Garlic Cloves")
    assert result.canonical_name == "garlic"
