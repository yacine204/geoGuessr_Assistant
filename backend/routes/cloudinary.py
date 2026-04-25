from fastapi import APIRouter, UploadFile, File, HTTPException, status
from service.cloudinary import upload_image_to_cloudinary


router = APIRouter(prefix="/upload", tags=["images"])

@router.post(
    "/",
    summary="Upload image to Cloudinary",
    description="Uploads a single image file and returns a hosted URL.",
)
async def upload_image_upload(file: UploadFile = File(..., description="Image file to upload")):
    try:
        image_bytes = await file.read()
        image_url = await upload_image_to_cloudinary(image_bytes)
        return {"status": "success", "url": image_url}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occured: {e}"
        )