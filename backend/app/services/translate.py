import asyncio
import logging

from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)


def _translate_batch(texts: list[str], target: str) -> list[str]:
    translator = GoogleTranslator(source="en", target=target)
    return [translator.translate(t) or t for t in texts]


async def translate_recipe(
    title: str,
    ingredients: list[dict],
    steps: list[dict],
    target_lang: str,
) -> dict:
    """
    Translate recipe title, ingredient names, measures, and step instructions.
    Numeric-only values (e.g. "150ml", "2") are passed through Google Translate
    which preserves them as-is. step_number values are never touched.
    """
    ingredient_names = [ing.get("name", "") for ing in ingredients]
    ingredient_measures = [ing.get("measure", "") or "" for ing in ingredients]
    step_instructions = [s.get("instruction", "") for s in steps]

    all_texts = [title] + ingredient_names + ingredient_measures + step_instructions

    loop = asyncio.get_event_loop()
    translated = await loop.run_in_executor(None, _translate_batch, all_texts, target_lang)

    t_title = translated[0]
    offset = 1
    t_names = translated[offset : offset + len(ingredient_names)]
    offset += len(ingredient_names)
    t_measures = translated[offset : offset + len(ingredient_measures)]
    offset += len(ingredient_measures)
    t_instructions = translated[offset:]

    return {
        "title": t_title,
        "ingredients": [
            {**ing, "name": t_names[i], "measure": t_measures[i]}
            for i, ing in enumerate(ingredients)
        ],
        "steps": [
            {**step, "instruction": t_instructions[i]}
            for i, step in enumerate(steps)
        ],
    }
