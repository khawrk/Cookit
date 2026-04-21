import logging
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.db import CondimentsCatalog, FridgeItem, User
from app.models.schemas import (
    CondimentCatalogItem,
    CorrectionsRequest,
    CorrectionsResponse,
    FridgeItemIn,
    FridgeItemOut,
    FridgeItemUpdate,
    ScanResponse,
)
from app.services import vision

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/fridge", tags=["fridge"])

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/scan", response_model=ScanResponse)
async def scan_fridge(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScanResponse:
    if file.size and file.size > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image must be ≤10 MB")

    return await vision.detect_items(file, db, current_user.id)


@router.get("/items", response_model=list[FridgeItemOut])
async def list_fridge_items(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[FridgeItemOut]:
    result = await db.execute(
        select(FridgeItem).where(FridgeItem.user_id == current_user.id).order_by(FridgeItem.updated_at.desc())
    )
    items = result.scalars().all()
    return [FridgeItemOut.model_validate(i) for i in items]


@router.post("/items", response_model=FridgeItemOut, status_code=status.HTTP_201_CREATED)
async def add_fridge_item(
    payload: FridgeItemIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FridgeItemOut:
    from sqlalchemy import text

    await db.execute(
        text(
            """
            INSERT INTO fridge_items (user_id, item_name, category, quantity, unit, source)
            VALUES (:user_id, :item_name, :category, :quantity, :unit, :source)
            ON CONFLICT (user_id, item_name) DO UPDATE
                SET quantity   = EXCLUDED.quantity,
                    category   = COALESCE(EXCLUDED.category, fridge_items.category),
                    source     = EXCLUDED.source,
                    updated_at = now()
            """
        ),
        {
            "user_id": str(current_user.id),
            "item_name": payload.item_name,
            "category": payload.category,
            "quantity": payload.quantity,
            "unit": payload.unit,
            "source": payload.source,
        },
    )
    await db.commit()

    result = await db.execute(
        select(FridgeItem).where(
            FridgeItem.user_id == current_user.id,
            FridgeItem.item_name == payload.item_name,
        )
    )
    item = result.scalar_one()
    return FridgeItemOut.model_validate(item)


@router.patch("/items/{item_id}", response_model=FridgeItemOut)
async def update_fridge_item(
    item_id: uuid.UUID,
    payload: FridgeItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FridgeItemOut:
    result = await db.execute(
        select(FridgeItem).where(FridgeItem.id == item_id, FridgeItem.user_id == current_user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    await db.commit()
    await db.refresh(item)
    return FridgeItemOut.model_validate(item)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fridge_item(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    result = await db.execute(
        select(FridgeItem).where(FridgeItem.id == item_id, FridgeItem.user_id == current_user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    await db.delete(item)
    await db.commit()


@router.post("/corrections", response_model=CorrectionsResponse, status_code=status.HTTP_201_CREATED)
async def submit_corrections(
    payload: CorrectionsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CorrectionsResponse:
    count = await vision.save_corrections(db, current_user.id, payload.corrections)
    return CorrectionsResponse(saved_count=count)


@router.get("/catalog", response_model=list[CondimentCatalogItem])
async def list_catalog(db: AsyncSession = Depends(get_db)) -> list[CondimentCatalogItem]:
    result = await db.execute(select(CondimentsCatalog).order_by(CondimentsCatalog.name))
    items = result.scalars().all()
    return [CondimentCatalogItem.model_validate(i) for i in items]
