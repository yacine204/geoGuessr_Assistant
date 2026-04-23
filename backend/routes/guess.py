from pathlib import Path
import sys

from fastapi import APIRouter, UploadFile
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

ASSISTANT_LOGIC_DIR = PROJECT_ROOT / "assistant_logic"
if str(ASSISTANT_LOGIC_DIR) not in sys.path:
    sys.path.append(str(ASSISTANT_LOGIC_DIR))

from assistant_logic.main import predict

router = APIRouter(prefix="/guess", tags=["guess"])

class GeolocalizationResult(BaseModel):
    YOLO_detections: dict
    sign_detection: dict
    ocr_detections: str
    language: str | None
    safe_geolocalization: dict
    candidates: list[dict]
    top_countries: list[str]


@router.post("", response_model=GeolocalizationResult)
async def guess(image: UploadFile):
    tmp_dir = PROJECT_ROOT / "backend" / "tmp_uploads"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_file = tmp_dir / image.filename

    content = await image.read()
    tmp_file.write_bytes(content)

    return await predict(str(tmp_file))