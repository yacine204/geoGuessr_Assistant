from ultralytics import YOLO
from helpers.file_parsing import detect_signs
from helpers.ocr import extract_text, clean_ocr_blocks
from helpers.nominatim import search
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
    for box in boxes:
        x1, y1, x2, y2 = map(float, box.xyxy[0])
        sign_boxes.append((x1, y1, x2, y2))

# Extract text from full image with road sign boxes
ocr_result = extract_text(image_test, yolo_road_sign_boxes=sign_boxes if sign_boxes else None)

# Save detection visualization
os.makedirs("detections/", exist_ok=True)
if yolo_result.detections:
    output_path = f"detections/{os.path.basename(yolo_result.detections[0].path)}"
    yolo_result.detections[0].save(output_path)

# ============================================================================
# COUNTRY FILTERING PIPELINE
# ============================================================================

# Run complete country filtering pipeline (3 stages)
country_result = filter_countries(
    convention=yolo_result.convention,
    ocr_text=ocr_result.text if ocr_result.success else None,
    boost_multiplier=3.0,
    show_details=True
)

# ============================================================================
# RESULTS SUMMARY
# ============================================================================

# print("\n" + "="*70)
# print("ANALYSIS RESULTS")
# print("="*70)

# OCR Results
# print(f"\nOCR TEXT EXTRACTION")
# print(f"  Status: {'Success' if ocr_result.success else 'Failed'}")
# if ocr_result.success:
#     print(f"  Confidence: {ocr_result.confidence:.1%}")
#     print(f"  Text blocks detected: {len(ocr_result.text_blocks)}")
#     print(f"  Total characters: {len(ocr_result.text)}")
#     print(f"\n  Detected Text:")
#     print(f"  {ocr_result.text}")
# else:
#     print(f"  Error: {ocr_result.error}")

# # Road Sign Detection
# print(f"\nROAD SIGN DETECTION")
# print(f"  Vienna signs: {analysis_result.vienna_count}")
# print(f"  MUTCD signs: {analysis_result.mutcd_count}")
# print(f"  Total signs: {analysis_result.vienna_count + analysis_result.mutcd_count}")

# if analysis_result.vienna_count + analysis_result.mutcd_count > 0:
#     print(f"  Vienna avg confidence: {analysis_result.vienna_avg_confidence:.2f}")
#     print(f"  MUTCD avg confidence: {analysis_result.mutcd_avg_confidence:.2f}")
    
#     total_signs = analysis_result.vienna_count + analysis_result.mutcd_count
#     total_text_blocks = len(ocr_result.text_blocks) if ocr_result.success else 0
    
#     if total_text_blocks > 0:
#         signs_ratio = (total_signs / total_text_blocks) * 100
#         other_ratio = 100 - signs_ratio
#         print(f"\n  Text Source Analysis:")
#         print(f"    Road signs: {signs_ratio:.1f}% ({total_signs}/{total_text_blocks})")
#         print(f"    Other text: {other_ratio:.1f}%")
    
#     # Display text extracted from road signs
#     if ocr_result.road_sign_blocks:
#         print(f"\n  Text detected on road signs:")
#         for i, text in enumerate(ocr_result.road_sign_blocks, 1):
#             print(f"    {i}. '{text}'")
#     else:
#         print(f"\n  No text detected on road signs")

# # Convention & Geolocation
# print(f"\nGEOLOCATION ANALYSIS")
# print(f"  Convention: {analysis_result.convention.upper()}")
# print(f"  Bias: {analysis_result.bias:+.3f}")
# print(f"  Detection Confidence: {analysis_result.bias_confidence:.1%}")
# print(f"  Filtered Countries: {len(analysis_result.filtered_countries)}")

# if analysis_result.top_countries:
#     print(f"\n  Top Predictions:")
#     for i, country in enumerate(analysis_result.top_countries[:5], 1):
#         print(f"    {i}. {country.country} ({country.confidence:.2f}%)")
# else:
#     print(f"  No countries matched")

# print("\n" + "="*70)


# ============================================================================
# NOMINATIM GEOLOCATION TEST
# ============================================================================

async def test_nominatim(ocr_result):
    """Search for locations using text extracted from OCR"""
    print("\nNOMINATIM GEOLOCATION SEARCH")
    print("="*70)
    
    # Clean the blocks (merge articles with next word)
    search_queries = clean_ocr_blocks(ocr_result.other_text_blocks)
    
    if not search_queries:
        print("  No search terms found")
        return []
    
    print(f"  Found {len(search_queries)} search term(s)\n")
    
    location_results = []
    
    for query in search_queries:
        print(f"Searching for: '{query}'")
        try:
            results = await search(query)
            if results:
                print(f"  ✓ Found {len(results)} result(s)")
                result = results[0]
                print(f"  ✓ Location: {result.address}")
                print(f"  ✓ Coordinates: ({result.latitude}, {result.longitude})\n")
                
                # Store as LocationResult for clustering
                location_results.append(LocationResult(
                    query=query,
                    latitude=result.latitude,
                    longitude=result.longitude,
                    address=result.address
                ))
            else:
                print(f"  ✗ No results found\n")
        except Exception as e:
            print(f"  ✗ Error: {str(e)}\n")
        
        await asyncio.sleep(1)
    
    return location_results


# Run nominatim test with OCR results
location_results = asyncio.run(test_nominatim(ocr_result))

# ============================================================================
# LOCATION CLUSTERING & OVERPASS QUERY GENERATION
# ============================================================================

if location_results and len(location_results) > 0:
    print("\n" + "="*70)
    print("LOCATION CLUSTERING")
    print("="*70)
    
    # Cluster locations by proximity
    clusters = cluster_locations(location_results, cluster_distance_km=100)
    
    print(f"\nClusters found: {len(clusters)}")
    for i, cluster in enumerate(clusters, 1):
        best = cluster.best_result()
        print(f"\n  Cluster {i}: {len(cluster.results)} location(s)")
        print(f"    Center: ({cluster.center_lat:.4f}, {cluster.center_lon:.4f})")
        print(f"    Radius: {cluster.cluster_radius_km:.1f} km")
        print(f"    Best match: {best.address}")
    
    # Filter qualified detections
    qualified = filter_qualified_detections(
        clusters,
        max_distance_km=300,
        same_continent_only=True
    )
    
    print(get_qualified_locations_info(qualified))
    
    # Generate and print Overpass QL query
    if qualified:
        print_overpass_query(qualified, search_radius_m=5000)
        
        # Get average safe coordinate
        avg_lat, avg_lon = get_average_safe_coordinate(qualified)
        
        # Query Overpass API with the average coordinate
        try:
            overpass_data = query_overpass_api(
                latitude=avg_lat,
                longitude=avg_lon,
                search_radius_m=5000,
                timeout=30,
                retries=2
            )
            
            # Parse and display results only if we got valid data
            if overpass_data and 'elements' in overpass_data and len(overpass_data['elements']) > 0:
                parsed_results = parse_overpass_results(overpass_data)
                print_overpass_results(parsed_results)
            elif 'error' not in overpass_data:
                print("\n" + "="*70)
                print("OVERPASS RESULTS")
                print("="*70)
                print("No elements found in this area")
                print("="*70)
        except KeyboardInterrupt:
            print("\n⚠ Query interrupted by user")
        except Exception as e:
            print(f"\n⚠ Error querying Overpass API: {str(e)}")
            print("You can manually use the Overpass QL query above on https://overpass-turbo.osm.de/")
else:
    print("\n⚠ No location results to cluster")