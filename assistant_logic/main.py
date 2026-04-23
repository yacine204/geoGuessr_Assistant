"""
GeoGuessr Assistant - Main Pipeline
Detects road signs, extracts text, and predicts geolocation.
"""

from ultralytics import YOLO
from helpers.file_parsing import detect_signs
from helpers.ocr import extract_text, clean_ocr_blocks
from helpers.nominatim import search, get_top_countries_names, clear_search_cache
from helpers.location_clustering import LocationResult, cluster_locations
from helpers.country_filtering import filter_countries
from helpers.language_filtering import detect_text_language
from helpers.over_pass_query import (
    filter_qualified_detections,
    get_average_safe_coordinate,
    query_overpass_api,
    parse_overpass_results,
)
from helpers.nominatim_to_overpass import extract_overpass_tags
import os
import asyncio
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Load model once (cache it)
_model = None
MODEL_PATH = Path(__file__).resolve().parent / "yolo_pts" / "best2.pt"

def get_model():
    """Load YOLO model (singleton pattern to avoid reloading)."""
    global _model
    if _model is None:
        _model = YOLO(str(MODEL_PATH))
    return _model


# ============================================================================
# PIPELINE STAGES
# ============================================================================

def stage_1_detect_road_signs(image_path: str) -> Dict:
    """
    Stage 1: Detect road signs using YOLO.
    
    Args:
        image_path: Path to input image
        
    Returns:
        Dict with keys:
        - convention: (MUTCD, Vienna, Ambiguous)
        - boxes: [(x1, y1, x2, y2), ...]
        - detections: YOLO result object
    """
    logger.info(f"Stage 1: Detecting road signs in {image_path}")
    
    model = get_model()
    yolo_result = detect_signs(image_path, model)
    
    sign_boxes = []
    dominant_detected = "unknown"
    dominant_conf = None

    if yolo_result.detections and len(yolo_result.detections) > 0:
        best_conf = -1.0
        for detection in yolo_result.detections:
            boxes = detection.boxes
            class_names = getattr(detection, "names", {})
            for box in boxes:
                x1, y1, x2, y2 = map(float, box.xyxy[0])
                sign_boxes.append((x1, y1, x2, y2))

                conf = float(box.conf[0]) if hasattr(box.conf, "__len__") else float(box.conf)
                if conf > best_conf:
                    best_conf = conf
                    cls_id = int(box.cls[0]) if hasattr(box.cls, "__len__") else int(box.cls)
                    class_name = str(class_names.get(cls_id, "unknown")).lower()
                    if "vienna" in class_name:
                        dominant_detected = "vienna"
                    elif "mutcd" in class_name:
                        dominant_detected = "mutcd"
                    else:
                        dominant_detected = class_name
                    dominant_conf = conf

        logger.info(f"  ✓ Found {len(sign_boxes)} road signs")
    else:
        logger.warning("  ⚠ No road signs detected")
    
    return {
        "convention": yolo_result.convention,
        "bias": yolo_result.bias,
        "boxes": sign_boxes,
        "sign_detection": {
            "detected": dominant_detected,
            "conf": dominant_conf,
        },
        "detections": yolo_result.detections,
        "image_path": image_path,
    }


def stage_2_extract_text(image_path: str, sign_boxes: List[Tuple]) -> Dict:
    """
    Stage 2: Extract text from image using OCR (inside and outside sign boxes).
    
    Args:
        image_path: Path to input image
        sign_boxes: List of sign bounding boxes from stage 1
        
    Returns:
        Dict with keys:
        - text_inside_signs: Text detected inside road signs
        - text_outside_signs: Text detected outside signs (shops, street names, etc.)
        - language: Detected language
        - speed_limits: Extracted speed limit values
        - success: Whether OCR succeeded
    """
    logger.info("Stage 2: Extracting text via OCR")
    
    ocr_result = extract_text(
        image_path,
        yolo_road_sign_boxes=sign_boxes if sign_boxes else None
    )
    
    speed_limits = []
    if ocr_result.road_sign_classification and ocr_result.road_sign_classification.speedlimit_values:
        speed_limits = ocr_result.road_sign_classification.speedlimit_values
        logger.info(f"  ✓ Speed limits detected: {speed_limits}")
    
    search_queries = clean_ocr_blocks(ocr_result.other_text_blocks) if ocr_result.success else []
    logger.info(f"  ✓ Found {len(search_queries)} search term(s)")
    if ocr_result.success:
        logger.info(f"  ✓ OCR text (inside signs): {ocr_result.text}")
        logger.info(f"  ✓ OCR text blocks (outside signs): {ocr_result.other_text_blocks}")

    detected_language = None
    if ocr_result.success and ocr_result.text:
        lang_code, _ = detect_text_language(ocr_result.text)
        detected_language = lang_code if lang_code != "unknown" else None
    
    return {
        "text_inside_signs": ocr_result.text if ocr_result.success else "",
        "text_outside_signs": ocr_result.other_text_blocks if ocr_result.success else [],
        "language": detected_language,
        "speed_limits": speed_limits,
        "search_queries": search_queries,
        "success": ocr_result.success,
    }


def stage_3_filter_countries(convention: str, ocr_text: str) -> Dict:
    """
    Stage 3: Filter countries based on road sign convention and OCR language.
    
    Args:
        convention: Road sign convention (MUTCD, Vienna, Ambiguous)
        ocr_text: OCR extracted text for language detection
        
    Returns:
        Dict with keys:
        - filtered_countries: List of (country_code, score) tuples
        - top_3: List of top 3 country names
    """
    logger.info("Stage 3: Filtering countries by convention & language")
    
    country_result = filter_countries(
        convention=convention,
        ocr_text=ocr_text,
        boost_multiplier=3.0,
        show_details=False,
    )
    
    top_countries = [c.country for c in country_result.filtered_countries[:10]]
    logger.info(f"  ✓ Top countries: {', '.join(top_countries[:3])}")
    
    return {
        "filtered_countries": country_result.filtered_countries,
        "top_countries": top_countries,
    }


async def stage_4_nominatim_search(
    search_queries: List[str],
    top_countries: List[str]
) -> Dict:
    """
    Stage 4: Search for locations using Nominatim.
    
    Args:
        search_queries: List of text queries from OCR
        top_countries: List of top countries to filter results
        
    Returns:
        Dict with keys:
        - nominatim_results: Raw Nominatim results
        - location_results: Clusterable LocationResult objects
    """
    logger.info("Stage 4: Searching Nominatim for locations")
    
    if not search_queries:
        logger.warning("  ⚠ No search queries provided")
        return {"nominatim_results": [], "location_results": []}
    
    clear_search_cache()
    nominatim_results = []
    location_results = []
    
    for query in search_queries:
        try:
            results = await search(
                query,
                language='en',
                top_countries=top_countries if top_countries else None
            )
            if results:
                result = results[0]
                logger.info(f"  ✓ Found: {result.address}")
                nominatim_results.append(result)
                location_results.append(LocationResult(
                    query=query,
                    latitude=result.latitude,
                    longitude=result.longitude,
                    address=result.address
                ))
            else:
                logger.warning(f"  ✗ No results for: {query}")
        except Exception as e:
            logger.error(f"  ✗ Error searching '{query}': {str(e)}")
        
        await asyncio.sleep(0.5)  # Rate limiting
    
    logger.info(f"  ✓ Found {len(location_results)} location(s)")
    
    return {
        "nominatim_results": nominatim_results,
        "location_results": location_results,
    }


def stage_5_overpass_query(
    location_results: List[LocationResult],
    nominatim_results: List,
    speed_limits: List[str]
) -> Dict:
    """
    Stage 5: Query Overpass API to validate and refine geolocation.
    
    Args:
        location_results: Clustered location results
        nominatim_results: Raw Nominatim results for OSM tag extraction
        speed_limits: Speed limit clues from road signs
        
    Returns:
        Dict with keys:
        - overpass_data: Raw Overpass API response
        - parsed_results: Parsed Overpass results
        - center_latitude: Average latitude
        - center_longitude: Average longitude
    """
    logger.info("Stage 5: Querying Overpass API for validation")
    
    if not location_results:
        logger.warning("  ⚠ No locations to query")
        return {
            "overpass_data": None,
            "parsed_results": [],
            "center_latitude": None,
            "center_longitude": None,
        }
    
    # Cluster and filter
    clustered = cluster_locations(location_results)
    qualified = filter_qualified_detections(clustered)
    
    if not qualified:
        logger.warning("  ⚠ No qualified detections after filtering")
        return {
            "overpass_data": None,
            "parsed_results": [],
            "center_latitude": None,
            "center_longitude": None,
        }
    
    # Extract OSM tags and compute center
    smart_tags = extract_overpass_tags(nominatim_results)
    avg_lat, avg_lon = get_average_safe_coordinate(qualified)
    
    logger.info(f"  ✓ Query center: ({avg_lat}, {avg_lon})")
    logger.info(f"  ✓ OSM tags: {smart_tags}")
    
    if speed_limits:
        logger.info(f"  ✓ Speed limit hints: {', '.join(speed_limits)} km/h")
    
    try:
        overpass_data = query_overpass_api(
            latitude=avg_lat,
            longitude=avg_lon,
            search_radius_m=5000,
            tags=smart_tags,
            timeout=30,
            retries=2
        )
        
        parsed_results = []
        if overpass_data and overpass_data.get('elements'):
            parsed_results = parse_overpass_results(overpass_data)
            logger.info(f"  ✓ Found {len(parsed_results)} OSM features")
        else:
            logger.info("  ⚠ No OSM features found in area")
        
        return {
            "overpass_data": overpass_data,
            "parsed_results": parsed_results,
            "center_latitude": avg_lat,
            "center_longitude": avg_lon,
        }
    except Exception as e:
        logger.error(f"  ✗ Overpass API error: {str(e)}")
        return {
            "overpass_data": None,
            "parsed_results": [],
            "center_latitude": avg_lat,
            "center_longitude": avg_lon,
        }


# ============================================================================
# ORCHESTRATION
# ============================================================================

async def predict(image_path: str) -> Dict:
    """
    Full prediction pipeline: detect signs → extract text → filter countries → 
    search → validate with Overpass.
    
    Args:
        image_path: Path to input image
        
    Returns:
        Dict with compact output:
        {
            "safe_geolocalization": {"lon": float | None, "lat": float | None},
            "candidates": [{"lat": float, "lon": float}, ...],  # max 5
            "top_countries": [str, ...]  # max 10
        }
    """
    logger.info(f"Starting prediction pipeline for {image_path}")
    
    try:
        # Stage 1: Detect signs
        signs = stage_1_detect_road_signs(image_path)
        
        # Stage 2: Extract text
        text = stage_2_extract_text(image_path, signs["boxes"])
        
        # Stage 3: Filter countries
        countries = stage_3_filter_countries(signs["convention"], text["text_inside_signs"])
        
        # Stage 4: Search Nominatim (async)
        nominatim = await stage_4_nominatim_search(
            text["search_queries"],
            countries["top_countries"]
        )
        
        # Stage 5: Query Overpass
        overpass = stage_5_overpass_query(
            nominatim["location_results"],
            nominatim["nominatim_results"],
            text["speed_limits"]
        )
        
        # Build candidates (max 5)
        candidates = [
            {"lat": loc.latitude, "lon": loc.longitude}
            for loc in nominatim["location_results"][:5]
        ]

        # Safe geolocalization from Overpass center (if available)
        result = {
            "YOLO_detections": {
                "dominant_convention": signs["convention"],
                "bias": signs["bias"],
            },
            "sign_detection": signs["sign_detection"],
            "ocr_detections": text["text_inside_signs"],
            "language": text["language"],
            "safe_geolocalization": {
                "lon": overpass["center_longitude"],
                "lat": overpass["center_latitude"],
            },
            "candidates": candidates,
            "top_countries": countries["top_countries"][:10],
        }
        
        logger.info("Prediction pipeline completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
        raise


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import argparse
    import json
    
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="GeoGuessr Assistant Prediction")
    parser.add_argument("image", help="Path to image file")
    parser.add_argument("--output", "-o", help="Save results to JSON file")
    args = parser.parse_args()
    
    # Run prediction
    result = asyncio.run(predict(args.image))
    
    # Print summary
    print("\n" + "=" * 70)
    print("PREDICTION RESULT")
    print("=" * 70)
    print(result)
    print("=" * 70)
    
    # Save if requested
    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Results saved to {args.output}")