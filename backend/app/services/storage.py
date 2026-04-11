import logging
import uuid

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_s3_client = None


def _get_s3():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
    return _s3_client


def upload_image(file_bytes: bytes, content_type: str) -> str:
    """Upload image bytes to S3 and return the object key."""
    key = f"fridge-scans/{uuid.uuid4()}.jpg"
    try:
        _get_s3().put_object(
            Bucket=settings.aws_s3_bucket,
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
        )
        logger.info("Uploaded image to S3: %s", key)
        return key
    except (BotoCoreError, ClientError) as exc:
        logger.error("S3 upload failed: %s", exc)
        raise


def get_presigned_url(key: str, expires_in: int = 3600) -> str:
    """Return a presigned GET URL for the given S3 key."""
    try:
        return _get_s3().generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.aws_s3_bucket, "Key": key},
            ExpiresIn=expires_in,
        )
    except (BotoCoreError, ClientError) as exc:
        logger.error("Failed to generate presigned URL: %s", exc)
        raise
