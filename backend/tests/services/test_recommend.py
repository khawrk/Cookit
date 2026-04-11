import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.schemas import RecommendResponse


@pytest.mark.asyncio
async def test_empty_fridge_returns_empty(db_session, test_user):
    from app.services import recommend

    result = await recommend.get_recommendations(test_user.id, db_session)
    assert isinstance(result, RecommendResponse)
    assert result.recommendations == []


def test_merge_and_rank_deduplicates():
    from app.services.recommend import _merge_and_rank

    recipe_id = str(uuid.uuid4())
    strategy_a = [
        {
            "recipe_id": recipe_id,
            "title": "Stir Fry",
            "source_url": "http://example.com",
            "cuisine": "Asian",
            "overlap_score": 0.8,
            "cosine_score": 0.0,
            "ai_score": 0.0,
            "matched_ingredients": ["chicken", "garlic"],
            "missing_ingredients": ["soy sauce"],
        }
    ]
    strategy_b = [
        {
            "recipe_id": recipe_id,
            "title": "Stir Fry",
            "source_url": "http://example.com",
            "cuisine": "Asian",
            "overlap_score": 0.0,
            "cosine_score": 0.75,
            "ai_score": 0.0,
            "matched_ingredients": ["chicken"],
            "missing_ingredients": [],
        }
    ]
    results = _merge_and_rank(strategy_a, strategy_b, [])
    assert len(results) == 1
    # 0.4*0.8 + 0.35*0.75 = 0.32 + 0.2625 = 0.5825
    assert abs(results[0].match_score - 0.5825) < 0.001


def test_merge_and_rank_sorts_descending():
    from app.services.recommend import _merge_and_rank

    a_results = [
        {
            "recipe_id": str(uuid.uuid4()),
            "title": f"Recipe {i}",
            "source_url": "",
            "cuisine": None,
            "overlap_score": i * 0.1,
            "cosine_score": 0.0,
            "ai_score": 0.0,
            "matched_ingredients": [],
            "missing_ingredients": [],
        }
        for i in range(5)
    ]
    results = _merge_and_rank(a_results, [], [])
    scores = [r.match_score for r in results]
    assert scores == sorted(scores, reverse=True)
