import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from settings import Settings

logger = logging.getLogger(__name__)


def _client(settings: "Settings"):
    import boto3
    return boto3.client(
        "s3",
        aws_access_key_id=settings.app_aws_access_key_id,
        aws_secret_access_key=settings.app_aws_secret_access_key,
        region_name=settings.app_aws_region,
    )


def upload_bytes(data: bytes, key: str, content_type: str, settings: "Settings") -> str:
    _client(settings).put_object(
        Bucket=settings.aws_storage_bucket_name,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    return key


def generate_presigned_url(key: str, settings: "Settings", expires: int = 3600) -> str:
    return _client(settings).generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.aws_storage_bucket_name, "Key": key},
        ExpiresIn=expires,
    )


async def upload_bytes_async(data: bytes, key: str, content_type: str, settings: "Settings") -> str:
    return await asyncio.to_thread(upload_bytes, data, key, content_type, settings)


async def generate_presigned_url_async(key: str, settings: "Settings", expires: int = 3600) -> str:
    return await asyncio.to_thread(generate_presigned_url, key, settings, expires)
