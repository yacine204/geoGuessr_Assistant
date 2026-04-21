from ultralytics import YOLO
from helpers.file_parsing import detect_signs
from helpers.ocr import extract_text, extract_text_paddle, clean_ocr_blocks
from helpers.nominatim import search, get_top_countries_names, clear_search_cache
from helpers.location_clustering import LocationResult, cluster_locations
from helpers.country_filtering import filter_countries
from helpers.over_pass_query import (
    filter_qualified_detections,
    print_overpass_query,
    get_average_safe_coordinate,
    get_qualified_locations_info,
    query_overpass_api,
    parse_overpass_results,
    print_overpass_results
)
import os
import asyncio

model = YOLO("yolo_pts/best2.pt")
image_test = '/home/yacine/Desktop/codes/geoGussr-Assistant/tests2/ocr_test.png'

# Analyze signs and detect convention
yolo_result = detect_signs(image_test, model)

# Extract road sign boxes for text detection
sign_boxes = []
if yolo_result.detections and len(yolo_result.detections) > 0:
    boxes = yolo_result.detections[0].boxes
    for box in boxes:                          # 
        x1, y1, x2, y2 = map(float, box.xyxy[0])
        sign_boxes.append((x1, y1, x2, y2))

# Extract text from full image with road sign boxes
# PaddleOCR : extract_text_paddle() ! doesnt work 
ocr_result = extract_text(image_test, yolo_road_sign_boxes=sign_boxes if sign_boxes else None)

# Extract speed limits from road signs (clue for Overpass query)
speed_limits = []
if ocr_result.road_sign_classification:
    speed_limits = ocr_result.road_sign_classification.speedlimit_values
    if speed_limits:
        print(f"\n✓ Speed limits detected on signs: {speed_limits}")

# Save detection visualization
os.makedirs("detections/", exist_ok=True)
if yolo_result.detections:
    output_path = f"detections/{os.path.basename(yolo_result.detections[0].path)}"
    yolo_result.detections[0].save(output_path)

# ============================================================================
# COUNTRY FILTERING PIPELINE
# ============================================================================
country_result = filter_countries(
    convention=yolo_result.convention,
    ocr_text=ocr_result.text if ocr_result.success else None,
    boost_multiplier=3.0,
    show_details=True
)

# ============================================================================
# NOMINATIM GEOLOCATION TEST
# ============================================================================
async def test_nominatim(ocr_result, country_result):
    """Search for locations using text extracted from OCR with country filtering"""   
    print("\nNOMINATIM GEOLOCATION SEARCH")
    print("=" * 70)

    search_queries = clean_ocr_blocks(ocr_result.other_text_blocks)
    if not search_queries:
        print("  No search terms found")
        return [], []

    # Extract top countries from filtering pipeline for smart search
    top_countries = get_top_countries_names(country_result.filtered_countries)
    if top_countries:
        print(f"  Using top countries as search hints: {', '.join(top_countries[:3])}")
    print(f"  Found {len(search_queries)} search term(s)\n")

    nominatim_results = []
    location_results = []

    for query in search_queries:
        print(f"Searching for: '{query}'")
        try:
            # Pass top_countries to filter results to only predicted regions
            results = await search(
                query,
                language='en',
                top_countries=top_countries if top_countries else None
            )
            if results:
                print(f"  ✓ Found {len(results)} result(s)")
                result = results[0]
                print(f"  ✓ Location: {result.address}")
                print(f"  ✓ Country: {result.country_name}")
                print(f"  ✓ POI Type: {result.poi_type}, Class: {result.poi_class}")
                print(f"  ✓ Coordinates: ({result.latitude}, {result.longitude})\n")
                nominatim_results.append(result)
                location_results.append(LocationResult(
                    query=query,
                    latitude=result.latitude,
                    longitude=result.longitude,
                    address=result.address
                ))
            else:
                print(f"  ✗ No results found in predicted countries\n")
        except Exception as e:
            print(f"  ✗ Error: {str(e)}\n")
        await asyncio.sleep(1)

    return nominatim_results, location_results

# Run nominatim search with country filtering
clear_search_cache()  # Start fresh cache
nominatim_results, location_results = asyncio.run(test_nominatim(ocr_result, country_result))

# ============================================================================
# LOCATION CLUSTERING & OVERPASS QUERY GENERATION
# ============================================================================
if location_results and len(location_results) > 0:
    from helpers.nominatim_to_overpass import extract_overpass_tags

    # --- fill in your clustering logic here, e.g.: ---
    clustered = cluster_locations(location_results)
    qualified = filter_qualified_detections(clustered)   # ← must exist before use
    # --------------------------------------------------

    smart_tags = extract_overpass_tags(nominatim_results)
    print(f"\n✓ Extracted OSM tags from Nominatim: {smart_tags}")

    if qualified:
        print_overpass_query(qualified, search_radius_m=5000)
        avg_lat, avg_lon = get_average_safe_coordinate(qualified)

        # Add speed limit info as context for Overpass query
        if speed_limits:
            print(f"\n  Speed limit clues for region: {', '.join(speed_limits)} km/h")

        try:
            overpass_data = query_overpass_api(
                latitude=avg_lat,
                longitude=avg_lon,
                search_radius_m=5000,
                tags=smart_tags,
                timeout=30,
                retries=2
            )
            if overpass_data and overpass_data.get('elements'):
                parsed_results = parse_overpass_results(overpass_data)
                print_overpass_results(parsed_results)
            elif 'error' not in overpass_data:
                print("\n" + "=" * 70)
                print("OVERPASS RESULTS")
                print("=" * 70)
                print("No elements found in this area")
                print("=" * 70)
        except KeyboardInterrupt:
            print("\n⚠ Query interrupted by user")
        except Exception as e:
            print(f"\n⚠ Error querying Overpass API: {str(e)}")