import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile

from app.models.schemas import ScanResponse


@pytest.mark.asyncio
async def test_detect_items_returns_scan_response(db_session, mock_anthropic):
    from app.services import vision

    file_bytes = b"fake-image-bytes"
    upload_file = UploadFile(filename="test.jpg", file=io.BytesIO(file_bytes))
    upload_file.content_type = "image/jpeg"

    user_id = uuid.uuid4()

    with patch("app.services.vision.storage.upload_image", return_value="test-key"):
        result = await vision.detect_items(upload_file, db_session, user_id)

    assert isinstance(result, ScanResponse)
    assert result.saved_count >= 0
    assert len(result.detected) > 0
    assert result.detected[0].item_name == "chicken breast"


@pytest.mark.asyncio
async def test_detect_items_drops_low_confidence(db_session, monkeypatch):
    from app.services import vision

    low_conf_response = MagicMock()
    low_conf_response.content = [
        MagicMock(
            text='[{"item_name":"mystery","category":"other","quantity":1,"unit":"count","confidence":0.3}]'
        )
    ]
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=low_conf_response)
    monkeypatch.setattr("app.services.vision.client", mock_client)

    file_bytes = b"fake"
    upload_file = UploadFile(filename="test.jpg", file=io.BytesIO(file_bytes))
    upload_file.content_type = "image/jpeg"
    user_id = uuid.uuid4()

    with patch("app.services.vision.storage.upload_image", return_value="key"):
        result = await vision.detect_items(upload_file, db_session, user_id)

    assert result.saved_count == 0
    assert len(result.detected) == 0


@pytest.mark.asyncio
async def test_detect_items_strips_markdown_fences(db_session, monkeypatch):
    from app.services import vision

    fenced_response = MagicMock()
    fenced_response.content = [
        MagicMock(
            text='```json\n[{"item_name":"eggs","category":"protein","quantity":6,"unit":"count","confidence":0.9}]\n```'
        )
    ]
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=fenced_response)
    monkeypatch.setattr("app.services.vision.client", mock_client)

    upload_file = UploadFile(filename="test.jpg", file=io.BytesIO(b"x"))
    upload_file.content_type = "image/jpeg"

    with patch("app.services.vision.storage.upload_image", return_value="key"):
        result = await vision.detect_items(upload_file, db_session, uuid.uuid4())

    assert result.detected[0].item_name == "eggs"
