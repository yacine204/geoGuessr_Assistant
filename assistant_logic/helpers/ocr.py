"""
Simple EasyOCR Text Extraction
- Uses ONLY EasyOCR (no Tesseract)
- Separates road sign text into dedicated variable
- Road sign text is determined by YOLO bounding boxes (external input)
"""

import easyocr
from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np
import re
from difflib import get_close_matches


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
    
    error: str = ""  # Error message if failed


_easyocr_reader: Optional[easyocr.Reader] = None


def _get_easyocr_reader():
    """Get or create EasyOCR reader instance."""
    global _easyocr_reader
    if _easyocr_reader is None:
        print("Loading EasyOCR model (first time only)...")
        _easyocr_reader = easyocr.Reader(['en'], gpu=False)
    return _easyocr_reader


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


from difflib import get_close_matches

def fuzzy_fix_keywords(block: str) -> str:
    # Common words found on signs/buildings (todo: look for github repo that contains these infos)
    VOCABULARY = [
        "SUPERMERCADO", "RESTAURANTE", "BOULANGERIE", "PHARMACIE", 
        "HOSPITAL", "AYUNTAMIENTO", "GENDARMERIE"
    ]
    
    words = block.split()
    fixed_words = []
    
    for word in words:
        # If word is high confidence but slightly off
        matches = get_close_matches(word.upper(), VOCABULARY, n=1, cutoff=0.7)
        if matches:
            fixed_words.append(matches[0])
        else:
            fixed_words.append(word)
            
    return " ".join(fixed_words)


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
            other_text=other_text,
            other_text_blocks=other_text_blocks
        )
        
        # Logging
        print(f"✓ OCR Complete")
        print(f"  Total text blocks: {len(all_text_blocks)}")
        print(f"  Road sign blocks: {len(road_sign_blocks)}")
        print(f"  Other text blocks: {len(other_text_blocks)}")
        print(f"  Average confidence: {avg_confidence:.1%}")
        
        if all_text_parts:
            display_text = full_text[:80] + "..." if len(full_text) > 80 else full_text
            print(f"  Sample text: {display_text}")
        
        if road_sign_blocks:
            print(f"  Road sign text: {', '.join(road_sign_blocks[:5])}")
        
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
            other_text="",
            other_text_blocks=[],
            error=f"OCR Error: {str(e)}"
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
    ARTICLES_PREPOSITIONS = {
        'le', 'la', 'les', 'de', 'du', 'des', 'et', 'à', 'au', 'aux', 'un', 'une',
        'the', 'a', 'an', 'and', 'at', 'in', 'on', 'or',
        'el', 'la', 'los', 'las', 'de', 'del', 'y', 'a', 'en',
    }
    
    # Step 1: Branching Grammar Logic
    # Instead of just merging, we create multiple search candidates
    candidates = []
    for block in text_blocks:
        words = block.strip().split()
        if not words:
            continue
            
        # Add the original full block
        candidates.append(" ".join(words))
        
        # Look for articles/prepositions to create sub-searches
        for i, word in enumerate(words):
            if word.lower() in ARTICLES_PREPOSITIONS:
                # Branch 1: From the article to the end (e.g., "la despensa @p")
                branch_to_end = " ".join(words[i:])
                candidates.append(branch_to_end)
                
                # Branch 2: Just the article + next word (e.g., "la despensa")
                if i + 1 < len(words):
                    short_phrase = f"{words[i]} {words[i+1]}"
                    candidates.append(short_phrase)
    
    cleaned = []
    for block in candidates:
        # 1. Basic Sanitization (Remove OCR noise symbols, keep @ for now)
        block = re.sub(r'[=;:\[\]{}()\\|]', '', block).strip()
        
        # 2. Geoguessr Road Sign Fix: 034 -> D34
        block = re.sub(r'^[0O](\d{2,3})', r'D\1', block)
        
        # 3. Fuzzy Correction (Fixes DUPERMERCADO -> SUPERMERCADO)
        block = fuzzy_fix_keywords(block)
        
        # 4. Filter Logic
        lower = block.lower()
        has_alpha = any(c.isalpha() for c in block)
        has_digit = any(c.isdigit() for c in block)
        is_road = re.search(r'[A-Z]\s?\d+', block) 

        # Reject if purely garbage or known UI noise
        if not block or len(block) < 2:
            continue
        if any(ui in lower for ui in {'view', 'map', 'data', 'street', 'google'}):
            continue
            
        # Reject if it's just OCR noise (e.g., "2 Jveco") but keep road signs
        if re.match(r'^\d{1,2}\s+[a-z]', lower) and not is_road:
            continue

        # Final Cleanup: Remove trailing OCR artifacts like "@p" or " @ "
        block = re.sub(r'\s*@\w*$', '', block).strip()

        # Final Approval
        if has_alpha or (has_digit and len(block) > 1):
            cleaned.append(block)
    
    # Remove duplicates while preserving order
    return list(dict.fromkeys(cleaned))