from fastapi import HTTPException, status 
import cloudinary.uploader
import asyncio
import io
import time


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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading image to Cloudinary: {e}"
        )
