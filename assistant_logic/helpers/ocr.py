"""
Simple EasyOCR Text Extraction
- Uses ONLY EasyOCR (no Tesseract)
- Separates road sign text into dedicated variable
- Road sign text is determined by YOLO bounding boxes (external input)
- Road sign text is further categorized: speed limits vs word matching
"""

import easyocr
from paddleocr import PaddleOCR
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
import numpy as np
import re

@dataclass
class RoadSignClassification:
    """Classification of road sign text"""
    speedlimit_values: List[str]  # Numeric values found (e.g., ['50', '90', '110'])
    word_matches: List[str]  # Text words found (e.g., ['STOP', 'YIELD', 'ONE WAY'])
    raw_text: str  # Original text


@dataclass
class OCRResult:
    """OCR extraction result"""
    text: str  # All detected text
    text_blocks: List[str]  # Individual text blocks/lines
    confidence: float  # Average confidence (0.0-1.0)
    success: bool  # Whether OCR succeeded
    image_path: str  # Source image path
    
    # Road sign specific text (from YOLO boxes)
    road_signs_detections_text: str  # Text detected within road sign boxes
    road_sign_blocks: List[str]  # Individual road sign text blocks
    
    # Other text (NOT in road sign boxes)
    other_text: str  # Text NOT in road sign boxes
    other_text_blocks: List[str]  # Individual other text blocks
    
    # Optional fields with defaults
    road_sign_classification: Optional[RoadSignClassification] = None  # Categorized road sign text
    error: str = ""  # Error message if failed


_easyocr_reader: Optional[easyocr.Reader] = None
_paddle_reader: Optional[PaddleOCR] = None


def _get_easyocr_reader():
    """Get or create EasyOCR reader instance."""
    global _easyocr_reader
    if _easyocr_reader is None:
        print("Loading EasyOCR model (first time only)...")
        _easyocr_reader = easyocr.Reader(['en'], gpu=False)
    return _easyocr_reader


def _get_paddle_reader():
    """Get or create PaddleOCR reader instance."""
    global _paddle_reader
    if _paddle_reader is None:
        print("Loading PaddleOCR model (first time only)...")
        # Disable ONNX conversion to avoid compatibility issues
        import os
        os.environ['PADDLE_DISABLE_OPERATORS_PASS'] = '1'
        _paddle_reader = PaddleOCR(
            use_angle_cls=False,  # Disable angle classification
            lang='en',
            use_onnx=False,  # Disable ONNX conversion
            gpu=False  # CPU only for stability
        )
    return _paddle_reader


def _text_in_box(text_bbox: List[List[float]], yolo_box: Tuple[float, float, float, float],
                 overlap_threshold: float = 0.5) -> bool:
    """
    Check if text bbox overlaps with YOLO box.
    
    Args:
        text_bbox: EasyOCR bbox format [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        yolo_box: YOLO box format (x1, y1, x2, y2)
        overlap_threshold: Percentage overlap to consider as "in box"
    
    Returns:
        True if text overlaps with YOLO box
    """
    try:
        # Convert EasyOCR bbox to rectangle
        text_bbox_array = np.array(text_bbox)
        text_x_min, text_y_min = text_bbox_array.min(axis=0)
        text_x_max, text_y_max = text_bbox_array.max(axis=0)
        
        # YOLO box
        yolo_x1, yolo_y1, yolo_x2, yolo_y2 = yolo_box
        
        # Calculate overlap area
        overlap_x_min = max(text_x_min, yolo_x1)
        overlap_y_min = max(text_y_min, yolo_y1)
        overlap_x_max = min(text_x_max, yolo_x2)
        overlap_y_max = min(text_y_max, yolo_y2)
        
        if overlap_x_max < overlap_x_min or overlap_y_max < overlap_y_min:
            return False  # No overlap
        
        overlap_area = (overlap_x_max - overlap_x_min) * (overlap_y_max - overlap_y_min)
        text_area = (text_x_max - text_x_min) * (text_y_max - text_y_min)
        
        if text_area == 0:
            return False
        
        overlap_ratio = overlap_area / text_area
        return overlap_ratio > overlap_threshold
    
    except Exception as e:
        print(f"Error checking overlap: {e}")
        return False


def extract_text(image_path: str, 
                yolo_road_sign_boxes: Optional[List[Tuple[float, float, float, float]]] = None) -> OCRResult:
    """
    Extract text from image using EasyOCR.
    Separate text into road sign text (within YOLO boxes) and other text.
    
    Args:
        image_path: Path to the image file
        yolo_road_sign_boxes: List of YOLO road sign bounding boxes (x1, y1, x2, y2)
                             If None, all text goes to road_signs_detections_text
                             If provided, text is separated based on overlap
    
    Returns:
        OCRResult with separated text blocks
    
    Example:
        # Without YOLO boxes (all text treated as road sign text)
        result = extract_text('image.jpg')
        
        # With YOLO boxes (text separated)
        yolo_boxes = [(100, 50, 200, 150), (300, 200, 450, 300)]
        result = extract_text('image.jpg', yolo_road_sign_boxes=yolo_boxes)
        print(result.road_signs_detections_text)  # Only in boxes
        print(result.other_text)  # Not in boxes
    """
    
    try:
        # Get EasyOCR reader
        reader = _get_easyocr_reader()
        
        # Run OCR
        print(f"Running EasyOCR on {image_path}...")
        easyocr_results = reader.readtext(image_path)
        
        if not easyocr_results:
            return OCRResult(
                text="",
                text_blocks=[],
                confidence=0.0,
                success=False,
                image_path=image_path,
                road_signs_detections_text="",
                road_sign_blocks=[],
                road_sign_classification=RoadSignClassification([], [], ""),
                other_text="",
                other_text_blocks=[],
                error="No text detected in image"
            )
        
        # Process results
        all_text_blocks = []
        all_confidences = []
        all_text_parts = []
        
        road_sign_blocks = []
        road_sign_parts = []
        
        other_text_blocks = []
        other_text_parts = []
        
        # EasyOCR results format: [([bbox_points], text, confidence), ...]
        for detection in easyocr_results:
            if len(detection) >= 3:
                text = detection[1].strip()
                conf = float(detection[2])
                text_bbox = detection[0]
                
                if not text:  # Skip empty text
                    continue
                
                # Add to all text
                all_text_blocks.append(text)
                all_confidences.append(conf)
                all_text_parts.append(text)
                
                # Determine if text is in a road sign box
                in_road_sign_box = False
                if yolo_road_sign_boxes:
                    for yolo_box in yolo_road_sign_boxes:
                        if _text_in_box(text_bbox, yolo_box):
                            in_road_sign_box = True
                            break
                
                # Separate text
                if in_road_sign_box:
                    road_sign_blocks.append(text)
                    road_sign_parts.append(text)
                else:
                    other_text_blocks.append(text)
                    other_text_parts.append(text)
        
        # Combine text with line breaks
        full_text = "\n".join(all_text_parts)
        road_signs_text = "\n".join(road_sign_parts)
        other_text = "\n".join(other_text_parts)
        
        # Classify road sign text (speedlimit vs words)
        road_sign_classification = classify_road_sign_text(road_sign_blocks)
        
        # Calculate average confidence
        avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
        
        # Success
        ocr_result = OCRResult(
            text=full_text,
            text_blocks=all_text_blocks,
            confidence=avg_confidence,
            success=True,
            image_path=image_path,
            road_signs_detections_text=road_signs_text,
            road_sign_blocks=road_sign_blocks,
            road_sign_classification=road_sign_classification,
            other_text=other_text,
            other_text_blocks=other_text_blocks
        )
        
        # Logging
        print(f"✓ OCR Complete")
        print(f"  Total text blocks: {len(all_text_blocks)}")
        print(f"  Road sign blocks: {len(road_sign_blocks)}")
        
        # Show road sign classification
        if road_sign_classification:
            print(f"    ├─ Speed limits: {len(road_sign_classification.speedlimit_values)} values {road_sign_classification.speedlimit_values}")
            print(f"    └─ Word matches: {len(road_sign_classification.word_matches)} words {road_sign_classification.word_matches}")
        
        print(f"  Other text blocks: {len(other_text_blocks)}")
        print(f"  Average confidence: {avg_confidence:.1%}")
        
        if all_text_parts:
            display_text = full_text[:80] + "..." if len(full_text) > 80 else full_text
            print(f"  Sample text: {display_text}")
        
        if other_text_blocks:
            print(f"  Other text: {', '.join(other_text_blocks[:5])}")
        
        return ocr_result
    
    except Exception as e:
        print(f"OCR Error: {e}")
        return OCRResult(
            text="",
            text_blocks=[],
            confidence=0.0,
            success=False,
            image_path=image_path,
            road_signs_detections_text="",
            road_sign_blocks=[],
            road_sign_classification=RoadSignClassification([], [], ""),
            other_text="",
            other_text_blocks=[],
            error=f"OCR Error: {str(e)}"
        )


def extract_text_paddle(image_path: str, 
                       yolo_road_sign_boxes: Optional[List[Tuple[float, float, float, float]]] = None) -> OCRResult:
    """
    Extract text from image using PaddleOCR instead of EasyOCR.
    Same interface and output as extract_text() but uses PaddleOCR engine.
    
    Args:
        image_path: Path to the image file
        yolo_road_sign_boxes: List of YOLO road sign bounding boxes (x1, y1, x2, y2)
    
    Returns:
        OCRResult with separated text blocks (same as EasyOCR version)
    """
    
    try:
        # Get PaddleOCR reader
        reader = _get_paddle_reader()
        
        # Run OCR
        print(f"Running PaddleOCR on {image_path}...")
        paddle_results = reader.ocr(image_path)
        
        # Flatten results (PaddleOCR returns list of lists)
        flattened_results = []
        if paddle_results:
            for line in paddle_results:
                if line:
                    for word_info in line:
                        flattened_results.append(word_info)
        
        if not flattened_results:
            return OCRResult(
                text="",
                text_blocks=[],
                confidence=0.0,
                success=False,
                image_path=image_path,
                road_signs_detections_text="",
                road_sign_blocks=[],
                road_sign_classification=RoadSignClassification([], [], ""),
                other_text="",
                other_text_blocks=[],
                error="No text detected in image"
            )
        
        # Process results
        all_text_blocks = []
        all_confidences = []
        all_text_parts = []
        
        road_sign_blocks = []
        road_sign_parts = []
        
        other_text_blocks = []
        other_text_parts = []
        
        # PaddleOCR results format: [([x1,y1], [x2,y2], [x3,y3], [x4,y4]), text, confidence]
        for detection in flattened_results:
            if len(detection) >= 2:
                text = detection[1].strip()
                conf = float(detection[2]) if len(detection) > 2 else 0.8
                
                # Convert PaddleOCR bbox to list format for compatibility
                bbox_points = detection[0]
                text_bbox = bbox_points  # Already in correct format
                
                if not text:  # Skip empty text
                    continue
                
                # Add to all text
                all_text_blocks.append(text)
                all_confidences.append(conf)
                all_text_parts.append(text)
                
                # Determine if text is in a road sign box
                in_road_sign_box = False
                if yolo_road_sign_boxes:
                    for yolo_box in yolo_road_sign_boxes:
                        if _text_in_box(text_bbox, yolo_box):
                            in_road_sign_box = True
                            break
                
                # Separate text
                if in_road_sign_box:
                    road_sign_blocks.append(text)
                    road_sign_parts.append(text)
                else:
                    other_text_blocks.append(text)
                    other_text_parts.append(text)
        
        # Combine text with line breaks
        full_text = "\n".join(all_text_parts)
        road_signs_text = "\n".join(road_sign_parts)
        other_text = "\n".join(other_text_parts)
        
        # Classify road sign text (speedlimit vs words)
        road_sign_classification = classify_road_sign_text(road_sign_blocks)
        
        # Calculate average confidence
        avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
        
        # Success
        ocr_result = OCRResult(
            text=full_text,
            text_blocks=all_text_blocks,
            confidence=avg_confidence,
            success=True,
            image_path=image_path,
            road_signs_detections_text=road_signs_text,
            road_sign_blocks=road_sign_blocks,
            road_sign_classification=road_sign_classification,
            other_text=other_text,
            other_text_blocks=other_text_blocks
        )
        
        # Logging
        print(f"✓ PaddleOCR Complete")
        print(f"  Total text blocks: {len(all_text_blocks)}")
        print(f"  Road sign blocks: {len(road_sign_blocks)}")
        
        # Show road sign classification
        if road_sign_classification:
            print(f"    ├─ Speed limits: {len(road_sign_classification.speedlimit_values)} values {road_sign_classification.speedlimit_values}")
            print(f"    └─ Word matches: {len(road_sign_classification.word_matches)} words {road_sign_classification.word_matches}")
        
        print(f"  Other text blocks: {len(other_text_blocks)}")
        print(f"  Average confidence: {avg_confidence:.1%}")
        
        if all_text_parts:
            display_text = full_text[:80] + "..." if len(full_text) > 80 else full_text
            print(f"  Sample text: {display_text}")
        
        if other_text_blocks:
            print(f"  Other text: {', '.join(other_text_blocks[:5])}")
        
        return ocr_result
    
    except Exception as e:
        print(f"PaddleOCR Error: {e}")
        return OCRResult(
            text="",
            text_blocks=[],
            confidence=0.0,
            success=False,
            image_path=image_path,
            road_signs_detections_text="",
            road_sign_blocks=[],
            road_sign_classification=RoadSignClassification([], [], ""),
            other_text="",
            other_text_blocks=[],
            error=f"PaddleOCR Error: {str(e)}"
        )


def extract_text_from_image(image_path: str, 
                           yolo_road_sign_boxes: Optional[List[Tuple[float, float, float, float]]] = None) -> str:
    """Quick wrapper to extract just the text string."""
    result = extract_text(image_path, yolo_road_sign_boxes)
    return result.text


def extract_text_blocks(image_path: str, 
                       yolo_road_sign_boxes: Optional[List[Tuple[float, float, float, float]]] = None) -> List[str]:
    """Quick wrapper to extract text blocks."""
    result = extract_text(image_path, yolo_road_sign_boxes)
    return result.text_blocks


def extract_road_sign_text(image_path: str, 
                          yolo_road_sign_boxes: Optional[List[Tuple[float, float, float, float]]] = None) -> str:
    """Quick wrapper to extract only road sign text (text within YOLO boxes)."""
    result = extract_text(image_path, yolo_road_sign_boxes)
    return result.road_signs_detections_text


def extract_road_sign_blocks(image_path: str, 
                            yolo_road_sign_boxes: Optional[List[Tuple[float, float, float, float]]] = None) -> List[str]:
    """Quick wrapper to extract road sign text blocks."""
    result = extract_text(image_path, yolo_road_sign_boxes)
    return result.road_sign_blocks


def extract_other_text(image_path: str, 
                      yolo_road_sign_boxes: Optional[List[Tuple[float, float, float, float]]] = None) -> str:
    """Quick wrapper to extract text NOT in road sign boxes."""
    result = extract_text(image_path, yolo_road_sign_boxes)
    return result.other_text


def extract_other_text_blocks(image_path: str, 
                             yolo_road_sign_boxes: Optional[List[Tuple[float, float, float, float]]] = None) -> List[str]:
    """Quick wrapper to extract text blocks NOT in road sign boxes."""
    result = extract_text(image_path, yolo_road_sign_boxes)
    return result.other_text_blocks


def clean_ocr_blocks(text_blocks: List[str]) -> List[str]:
    """
    Clean OCR blocks: merge articles AND filter out noise/garbage.
    
    Steps:
    1. Merges articles/prepositions separated by newlines with their next word
       Example: ['LA', 'MALTOURNÉE'] -> ['LA MALTOURNÉE']
    2. Filters out UI elements, numbers, dates, and OCR garbage
    3. Returns only valid location search terms
    """
    
    ARTICLES_PREPOSITIONS = {
        'le', 'la', 'les', 'de', 'du', 'des', 'et', 'à', 'au', 'aux', 'un', 'une',
        'the', 'a', 'an', 'and', 'at', 'in', 'on', 'or',
        'el', 'la', 'los', 'las', 'de', 'del', 'y', 'a', 'en',
        'der', 'die', 'das', 'den', 'dem', 'des', 'und', 'in', 'von',
        'il', 'lo', 'la', 'i', 'gli', 'le', 'di', 'da', 'e',
    }
    
    # when testing google view images
    BLACKLIST = {
        'google street view', 'google maps', 'voir plus de dates', 'voir plus',
        'pourquoi pas', 'rue', 'rue victor', 'victor', 'piscine'
    }
    
    # Step 1: Merge articles with next word
    merged = []
    i = 0
    while i < len(text_blocks):
        current = text_blocks[i].strip().lower()
        if current in ARTICLES_PREPOSITIONS and i + 1 < len(text_blocks):
            merged.append(f"{text_blocks[i].strip()} {text_blocks[i + 1].strip()}")
            i += 2
        else:
            merged.append(text_blocks[i].strip())
            i += 1
    
    # Step 2: Filter out noise
    cleaned = []
    for block in merged:
        lower = block.lower()
        
        # Skip empty or too short (< 3 chars)
        if not block or len(block) < 3:
            continue
        
        # Skip if in blacklist
        if lower in BLACKLIST:
            continue
        
        # Skip if only numbers/special chars (no alphabet)
        if not any(c.isalpha() for c in block):
            continue
        
        # Skip if has special chars like = ; : [ ] etc
        if any(c in '=;:[]{}()\\|' for c in block):
            continue
        
        # Skip if looks like date (digit:digit or digit/digit)
        if re.search(r'\d{1,2}[:/]\d{1,2}', block):
            continue
        
        # Skip if starts with small number + letter (OCR noise like "22 D34", "2 Jveco")
        if re.match(r'^\d{1,2}\s+[a-z]', lower):
            continue
        
        cleaned.append(block)
    
    return cleaned


## ROAD SIGNS CLASSIFICIATION


def classify_road_sign_text(road_sign_blocks: List[str]) -> RoadSignClassification:
    """
    Classify road sign text into categories:
    - Speedlimit values: pure numbers (50, 90, 110, etc)
    - Word matches: text content (STOP, YIELD, ONE WAY, etc)
    
    Args:
        road_sign_blocks: List of text blocks extracted from road sign boxes
    
    Returns:
        RoadSignClassification with categorized text
    
    Example:
        blocks = ['50', 'STOP', '90', 'YIELD']
        classification = classify_road_sign_text(blocks)
        print(classification.speedlimit_values)  # ['50', '90']
        print(classification.word_matches)  # ['STOP', 'YIELD']
    """
    speedlimit_values = []
    word_matches = []
    
    for block in road_sign_blocks:
        block = block.strip()
        if not block:
            continue
        
        # Check if it's purely numeric (potential speed limit)
        if re.match(r'^\d+$', block):
            speedlimit_values.append(block)
        # Check if it contains letters (word matching)
        elif any(c.isalpha() for c in block):
            word_matches.append(block)
    
    raw_text = "\n".join(road_sign_blocks)
    
    return RoadSignClassification(
        speedlimit_values=speedlimit_values,
        word_matches=word_matches,
        raw_text=raw_text
    )


def get_road_sign_analysis(road_sign_blocks: List[str]) -> Dict[str, any]:
    """
    Get detailed analysis of road sign text.
    
    Args:
        road_sign_blocks: List of text blocks from road signs
    
    Returns:
        Dictionary with detailed breakdown
    
    Example:
        analysis = get_road_sign_analysis(['50', 'STOP', '100'])
        print(analysis['speedlimit_count'])  # 2
        print(analysis['word_count'])  # 1
    """
    classification = classify_road_sign_text(road_sign_blocks)
    
    return {
        'total_blocks': len(road_sign_blocks),
        'speedlimit_values': classification.speedlimit_values,
        'speedlimit_count': len(classification.speedlimit_values),
        'word_matches': classification.word_matches,
        'word_count': len(classification.word_matches),
        'raw_text': classification.raw_text,
        'has_speedlimits': len(classification.speedlimit_values) > 0,
        'has_words': len(classification.word_matches) > 0,
    }