from ultralytics import YOLO
from data_types.road_sign_type import SignResult
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np

@dataclass
class YoloDetectionResult:
    """Raw YOLO detection result from image"""
    detections: List[SignResult]
    vienna_confidences: List[float]
    mutcd_confidences: List[float]
    bias: float
    bias_confidence: float
    convention: str

def _calculate_bias(vienna_confidence_sum: float, mutcd_confidence_sum: float) -> float:
    """
    Calculate the convention bias based on detection confidence scores.
    
    Bias ranges from -1 to 1:
    - Positive bias: Vienna convention signs detected (European/Asian patterns)
    - Negative bias: MUTCD convention signs detected (North American patterns)
    - 0: Perfectly balanced (ambiguous region)
    
    Args:
        vienna_confidence_sum: Sum of confidence scores for Vienna convention signs
        mutcd_confidence_sum: Sum of confidence scores for MUTCD convention signs
    
    Returns:
        Bias value between -1 and 1
    """
    total_confidence = vienna_confidence_sum + mutcd_confidence_sum
    
    # Handle edge case: no detections
    if total_confidence == 0:
        return 0.0
    
    # Calculate bias: positive favors Vienna, negative favors MUTCD
    bias = (vienna_confidence_sum - mutcd_confidence_sum) / total_confidence
    
    # Clamp to [-1, 1] range
    return max(-1.0, min(1.0, bias))


def get_detection_confidence(vienna_confs: List[float], 
                            mutcd_confs: List[float]) -> float:
    """Calculate overall confidence in the convention detection."""
    total_signs = len(vienna_confs) + len(mutcd_confs)
    
    if total_signs == 0:
        return 0.0
    
    all_confs = vienna_confs + mutcd_confs
    avg_conf = sum(all_confs) / len(all_confs)
    sign_count_factor = min(total_signs / 5, 1.0)
    detection_confidence = avg_conf * sign_count_factor
    
    return min(detection_confidence, 1.0)


def print_detection_summary(vienna_confs: List[float],
                           mutcd_confs: List[float],
                           bias: float,
                           bias_confidence: float,
                           convention: str):
    """Print detailed breakdown of sign detections."""
    print("\n" + "="*70)
    print("SIGN DETECTION SUMMARY")
    print("="*70)
    
    print(f"\nVienna Convention Signs: {len(vienna_confs)} detected")
    if vienna_confs:
        avg_vienna = sum(vienna_confs) / len(vienna_confs)
        print(f"  Confidences: {[f'{c:.2f}' for c in vienna_confs]}")
        print(f"  Sum: {sum(vienna_confs):.2f}, Average: {avg_vienna:.2f}")
    else:
        print("  (none detected)")
    
    print(f"\nMUTCD Convention Signs: {len(mutcd_confs)} detected")
    if mutcd_confs:
        avg_mutcd = sum(mutcd_confs) / len(mutcd_confs)
        print(f"  Confidences: {[f'{c:.2f}' for c in mutcd_confs]}")
        print(f"  Sum: {sum(mutcd_confs):.2f}, Average: {avg_mutcd:.2f}")
    else:
        print("  (none detected)")
    
    total = sum(vienna_confs) + sum(mutcd_confs)
    print(f"\nBias Calculation:")
    print(f"  ({sum(vienna_confs):.2f} - {sum(mutcd_confs):.2f}) / {total:.2f}")
    print(f"  = {bias:+.3f}")
    if bias != 0:
        bias_pct = abs(bias) * 100
        bias_dir = 'Vienna (European/Asian)' if bias > 0 else 'MUTCD (North American)'
        print(f"  = {bias_pct:.1f}% bias towards {bias_dir}")
    
    print(f"\nDetection Confidence: {bias_confidence:.1%}")
    print(f"Convention Classification: {convention.upper()}")
    if convention == 'vienna':
        print(f"  → Filtering to Vienna countries (Europe, Asia-Pacific, Africa, Middle East)")
    elif convention == 'mutcd':
        print(f"  → Filtering to MUTCD countries (North America, Oceania)")
    else:
        print(f"  → Ambiguous region, using all countries")
    
    print("="*70 + "\n")


def detect_signs(image_path: str, model: YOLO) -> YoloDetectionResult:
    """
    Detect signs in an image using YOLO.
    Returns raw detection results without country filtering.
    
    Country filtering is handled in country_filtering.py
    
    Args:
        image_path: Path to the image to analyze
        model: YOLO model for detection
    
    Returns:
        YoloDetectionResult containing raw detections and convention bias
    """
    results = model(
        source=image_path,
        save=False,
        save_conf=True,
        conf=0.5,
        stream=True,
    )
    
    print("Analyzing image...\n")
    all_results: List[SignResult] = []
    
    # Store lists of confidences
    vienna_confidences: List[float] = []
    mutcd_confidences: List[float] = []

    for result in results:
        for box in result.boxes:
            class_id = int(box.cls.item())
            confidence = float(box.conf.item())
            class_name = model.names[class_id]
            bbox = box.xyxy[0].tolist()
            print(f"Detected: {class_name} | conf: {confidence:.2f} | box: {bbox}")
            
            if 'vienna' in class_name.lower():
                vienna_confidences.append(confidence)
            elif 'mutcd' in class_name.lower():
                mutcd_confidences.append(confidence)

        result.show()
        all_results.append(result)
    
    # Calculate bias and confidence
    vienna_sum = sum(vienna_confidences)
    mutcd_sum = sum(mutcd_confidences)
    bias = _calculate_bias(vienna_sum, mutcd_sum)
    bias_confidence = get_detection_confidence(vienna_confidences, mutcd_confidences)
    
    # Determine convention
    if bias_confidence > 0.7:
        threshold = 0.2
    elif bias_confidence > 0.4:
        threshold = 0.3
    else:
        threshold = 0.5
    
    if bias > threshold:
        convention = 'vienna'
    elif bias < -threshold:
        convention = 'mutcd'
    else:
        convention = 'hybrid'
    
    # Print detection summary
    print_detection_summary(vienna_confidences, mutcd_confidences, bias, bias_confidence, convention)
    
    return YoloDetectionResult(
        detections=all_results,
        vienna_confidences=vienna_confidences,
        mutcd_confidences=mutcd_confidences,
        bias=bias,
        bias_confidence=bias_confidence,
        convention=convention
    )

