from fastapi import HTTPException, status 
import cloudinary.uploader
import asyncio
import io
import time
import uuid
from pathlib import Path


def _guess_extension(image_bytes: bytes) -> str:
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if image_bytes.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "webp"
    return "jpg"


def _save_locally_and_get_url(image_bytes: bytes, user_id: int, conversation_id: int) -> str:
    backend_root = Path(__file__).resolve().parents[1]
    tmp_dir = backend_root / "tmp_uploads"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    extension = _guess_extension(image_bytes)
    filename = f"user_{user_id}_conversation_{conversation_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}.{extension}"
    file_path = tmp_dir / filename
    file_path.write_bytes(image_bytes)

    return f"http://127.0.0.1:8000/tmp_uploads/{filename}"


async def upload_image_to_cloudinary(
    image_bytes: bytes,
    user_id: int = 0,
    conversation_id: int = 0,
) -> str:
    timestamp = int(time.time())
    public_id = f"user_{user_id}/conversation_{conversation_id}/{timestamp}"
    file_like = io.BytesIO(image_bytes)
    file_like.name = "image.jpg"
    try:
        upload_result = await asyncio.to_thread(
            cloudinary.uploader.upload,
            file_like,
            public_id=public_id,
            overwrite=False,
        )
        return upload_result['secure_url']
    except Exception as e:
        # Development-friendly fallback: keep conversation flow working without Cloudinary.
        # Store image locally and return a backend-served URL.
        try:
            return _save_locally_and_get_url(image_bytes, user_id, conversation_id)
        except Exception as local_error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error uploading image to Cloudinary: {e}; local fallback failed: {local_error}"
            )
