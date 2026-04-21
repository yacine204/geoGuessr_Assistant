from ultralytics import YOLO
from helpers.file_parsing import detect_signs
from helpers.ocr import extract_text
import os

model = YOLO("yolo_pts/best2.pt")

image_test = '/home/yacine/Desktop/codes/geoGussr-Assistant/tests2/ocr_test.png'

# Analyze signs and detect convention
analysis_result = detect_signs(image_test, model)

# Extract road sign boxes for text detection
sign_boxes = []
if analysis_result.detections and len(analysis_result.detections) > 0:
    boxes = analysis_result.detections[0].boxes
    for box in boxes:
        x1, y1, x2, y2 = map(float, box.xyxy[0])
        sign_boxes.append((x1, y1, x2, y2))

# Extract text from full image with road sign boxes
ocr_result = extract_text(image_test, yolo_road_sign_boxes=sign_boxes if sign_boxes else None)

# Save detection visualization
os.makedirs("detections/", exist_ok=True)
if analysis_result.detections:
    output_path = f"detections/{os.path.basename(analysis_result.detections[0].path)}"
    analysis_result.detections[0].save(output_path)

# ============================================================================
# RESULTS SUMMARY
# ============================================================================

print("\n" + "="*70)
print("ANALYSIS RESULTS")
print("="*70)

# OCR Results
print(f"\nOCR TEXT EXTRACTION")
print(f"  Status: {'Success' if ocr_result.success else 'Failed'}")
if ocr_result.success:
    print(f"  Confidence: {ocr_result.confidence:.1%}")
    print(f"  Text blocks detected: {len(ocr_result.text_blocks)}")
    print(f"  Total characters: {len(ocr_result.text)}")
    print(f"\n  Detected Text:")
    print(f"  {ocr_result.text}")
else:
    print(f"  Error: {ocr_result.error}")

# Road Sign Detection
print(f"\nROAD SIGN DETECTION")
print(f"  Vienna signs: {analysis_result.vienna_count}")
print(f"  MUTCD signs: {analysis_result.mutcd_count}")
print(f"  Total signs: {analysis_result.vienna_count + analysis_result.mutcd_count}")

if analysis_result.vienna_count + analysis_result.mutcd_count > 0:
    print(f"  Vienna avg confidence: {analysis_result.vienna_avg_confidence:.2f}")
    print(f"  MUTCD avg confidence: {analysis_result.mutcd_avg_confidence:.2f}")
    
    total_signs = analysis_result.vienna_count + analysis_result.mutcd_count
    total_text_blocks = len(ocr_result.text_blocks) if ocr_result.success else 0
    
    if total_text_blocks > 0:
        signs_ratio = (total_signs / total_text_blocks) * 100
        other_ratio = 100 - signs_ratio
        print(f"\n  Text Source Analysis:")
        print(f"    Road signs: {signs_ratio:.1f}% ({total_signs}/{total_text_blocks})")
        print(f"    Other text: {other_ratio:.1f}%")
    
    # Display text extracted from road signs
    if ocr_result.road_sign_blocks:
        print(f"\n  Text detected on road signs:")
        for i, text in enumerate(ocr_result.road_sign_blocks, 1):
            print(f"    {i}. '{text}'")
    else:
        print(f"\n  No text detected on road signs")

# Convention & Geolocation
print(f"\nGEOLOCATION ANALYSIS")
print(f"  Convention: {analysis_result.convention.upper()}")
print(f"  Bias: {analysis_result.bias:+.3f}")
print(f"  Detection Confidence: {analysis_result.bias_confidence:.1%}")
print(f"  Filtered Countries: {len(analysis_result.filtered_countries)}")

if analysis_result.top_countries:
    print(f"\n  Top Predictions:")
    for i, country in enumerate(analysis_result.top_countries[:5], 1):
        print(f"    {i}. {country.country} ({country.confidence:.2f}%)")
else:
    print(f"  No countries matched")

print("\n" + "="*70)
