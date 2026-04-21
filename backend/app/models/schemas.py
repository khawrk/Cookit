import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, model_validator


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Fridge ────────────────────────────────────────────────────────────────────

class DetectedItem(BaseModel):
    item_name: str
    category: str
    quantity: float
    unit: str
    confidence: float


class ScanResponse(BaseModel):
    detected: list[DetectedItem]
    saved_count: int


class FridgeItemIn(BaseModel):
    item_name: str
    category: str | None = None
    quantity: float | None = None
    unit: str | None = None
    source: str = "manual"


class FridgeItemUpdate(BaseModel):
    quantity: float | None = None
    unit: str | None = None
    category: str | None = None


class FridgeItemOut(BaseModel):
    id: uuid.UUID
    item_name: str
    category: str | None
    quantity: float | None
    unit: str | None
    source: str
    confidence: float | None
    updated_at: datetime

    model_config = {"from_attributes": True}


class CondimentCatalogItem(BaseModel):
    id: uuid.UUID
    name: str
    category: str | None
    default_unit: str | None

    model_config = {"from_attributes": True}


# ── Recipes ───────────────────────────────────────────────────────────────────

class RecipeIngredientSchema(BaseModel):
    name: str
    quantity: float | None = None
    unit: str | None = None


class RecipeStepSchema(BaseModel):
    step_number: int
    instruction: str


class TranslatedRecipeOut(BaseModel):
    title: str
    ingredients: list[dict]
    steps: list[dict]


class RecipeOut(BaseModel):
    id: uuid.UUID
    title: str
    source_url: str
    ingredients: list[dict]
    steps: list[dict]
    cuisine: str | None
    tags: list[str] | None
    scraped_at: datetime

    model_config = {"from_attributes": True}


class RecommendationItem(BaseModel):
    recipe_id: uuid.UUID
    title: str
    match_score: float
    matched_ingredients: list[str]
    missing_ingredients: list[str]
    cuisine: str | None
    source_url: str


class RecommendResponse(BaseModel):
    recommendations: list[RecommendationItem]


# ── Scan Corrections ──────────────────────────────────────────────────────────

class CorrectionEntry(BaseModel):
    original_name: str
    original_quantity: float | None = None
    original_unit: str | None = None
    corrected_name: str
    corrected_quantity: float | None = None
    corrected_unit: str | None = None

    @model_validator(mode="after")
    def must_differ(self) -> "CorrectionEntry":
        if (
            self.original_name == self.corrected_name
            and self.original_quantity == self.corrected_quantity
            and self.original_unit == self.corrected_unit
        ):
            raise ValueError("Correction must change at least one field")
        return self


class CorrectionsRequest(BaseModel):
    corrections: list[CorrectionEntry]

    @model_validator(mode="after")
    def must_be_non_empty(self) -> "CorrectionsRequest":
        if not self.corrections:
            raise ValueError("corrections list must not be empty")
        return self


class CorrectionsResponse(BaseModel):
    saved_count: int


# ── Normalisation ─────────────────────────────────────────────────────────────

class NormalizedIngredient(BaseModel):
    canonical_name: str
    category: str
    default_unit: str
