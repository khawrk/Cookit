import logging
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.db import Recipe, User
from app.models.schemas import RecommendResponse, RecipeOut, TranslatedRecipeOut
from app.services import recommend
from app.services.translate import translate_recipe

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("/recommend", response_model=RecommendResponse)
async def get_recommendations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecommendResponse:
    return await recommend.get_recommendations(current_user.id, db)


@router.get("/search", response_model=list[RecipeOut])
async def search_recipes(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[RecipeOut]:
    from sqlalchemy import or_

    result = await db.execute(
        select(Recipe)
        .where(
            or_(
                Recipe.title.ilike(f"%{q}%"),
                Recipe.cuisine.ilike(f"%{q}%"),
            )
        )
        .limit(20)
    )
    recipes = result.scalars().all()
    return [RecipeOut.model_validate(r) for r in recipes]


@router.get("/{recipe_id}/translate", response_model=TranslatedRecipeOut)
async def translate_recipe_endpoint(
    recipe_id: uuid.UUID,
    lang: str = Query("th"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TranslatedRecipeOut:
    result = await db.execute(select(Recipe).where(Recipe.id == recipe_id))
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")

    # Strip bare header entries ("STEP 1", "1", "2") before translating
    real_steps = [
        s for s in recipe.steps
        if not re.fullmatch(r'step\s*\d+', str(s.get("instruction", "")).strip(), re.IGNORECASE)
        and not re.fullmatch(r'\d+', str(s.get("instruction", "")).strip())
    ]

    translated = await translate_recipe(
        title=recipe.title,
        ingredients=recipe.ingredients,
        steps=real_steps,
        target_lang=lang,
    )
    return TranslatedRecipeOut(**translated)


@router.get("/{recipe_id}", response_model=RecipeOut)
async def get_recipe(
    recipe_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> RecipeOut:
    result = await db.execute(select(Recipe).where(Recipe.id == recipe_id))
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    return RecipeOut.model_validate(recipe)
