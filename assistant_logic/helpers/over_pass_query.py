"""
Generate Overpass QL queries from qualified location detections.
"""

from typing import List, Tuple, Optional, Dict, Any, Union
from dataclasses import dataclass
import math
import requests
import time
from helpers.location_clustering import LocationCluster, LocationResult


CONTINENTS = {
    'Europe': (35.0, 71.0, -10.0, 40.0),
    'Asia': (-10.0, 75.0, 26.0, 180.0),
    'Africa': (-35.0, 37.0, -18.0, 52.0),
    'North_America': (15.0, 85.0, -170.0, -50.0),
    'South_America': (-56.0, 13.0, -82.0, -35.0),
    'Australia_Oceania': (-47.0, -10.0, 113.0, 180.0),
}

# Valid OSM top-level tag keys worth querying
VALID_OSM_TAGS = {
    'amenity', 'shop', 'tourism', 'historic', 'leisure',
    'highway', 'railway', 'aeroway', 'waterway', 'building',
    'landuse', 'natural', 'office', 'sport', 'place'
}


@dataclass
class QualifiedLocation:
    location: LocationResult
    continent: str
    distance_from_primary_km: float
    cluster_size: int


def _get_continent(latitude: float, longitude: float) -> Optional[str]:
    for continent, (lat_min, lat_max, lon_min, lon_max) in CONTINENTS.items():
        if lat_min <= latitude <= lat_max and lon_min <= longitude <= lon_max:
            return continent
    return None


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def filter_qualified_detections(clusters: List[LocationCluster],
                                max_distance_km: float = 300,
                                same_continent_only: bool = True) -> List[QualifiedLocation]:
    if not clusters:
        return []

    primary = max(clusters, key=lambda c: len(c.results))
    primary_result = primary.best_result()
    primary_continent = _get_continent(primary_result.latitude, primary_result.longitude)

    qualified = [QualifiedLocation(
        location=primary_result,
        continent=primary_continent,
        distance_from_primary_km=0.0,
        cluster_size=len(primary.results)
    )]

    for cluster in clusters:
        if cluster == primary:
            continue
        best = cluster.best_result()
        continent = _get_continent(best.latitude, best.longitude)
        if same_continent_only and continent != primary_continent:
            continue
        distance = _haversine_distance(
            primary_result.latitude, primary_result.longitude,
            best.latitude, best.longitude
        )
        if distance <= max_distance_km:
            qualified.append(QualifiedLocation(
                location=best,
                continent=continent,
                distance_from_primary_km=distance,
                cluster_size=len(cluster.results)
            ))

    return qualified


def generate_overpass_query(qualified_detections: List[QualifiedLocation],
                            search_radius_m: int = 5000,
                            tags: Optional[List[str]] = None) -> str:
    """Generate Overpass QL query from qualified detections."""
    if not qualified_detections:
        return ""

    if tags is None:
        tags = ['amenity', 'shop', 'tourism', 'historic']

    # Filter to valid OSM keys only
    tags = [t for t in tags if t in VALID_OSM_TAGS] or ['amenity', 'shop']

    lines = ['[out:json];(']
    for detection in qualified_detections:
        lat = detection.location.latitude
        lon = detection.location.longitude
        for tag in tags:
            lines.append(f'  node["{tag}"](around:{search_radius_m},{lat:.7f},{lon:.7f});')
            lines.append(f'  way["{tag}"](around:{search_radius_m},{lat:.7f},{lon:.7f});')
            lines.append(f'  relation["{tag}"](around:{search_radius_m},{lat:.7f},{lon:.7f});')
    lines.append(');')
    lines.append('out geom center;')

    return '\n'.join(lines)


def print_overpass_query(qualified_detections: List[QualifiedLocation],
                         search_radius_m: int = 5000) -> None:
    """Print the generated Overpass QL query."""
    query = generate_overpass_query(qualified_detections, search_radius_m)

    print("\n" + "="*70)
    print("OVERPASS QL QUERY")
    print("="*70)
    print(query)
    print("="*70)

    if qualified_detections:
        avg_lat = sum(d.location.latitude for d in qualified_detections) / len(qualified_detections)
        avg_lon = sum(d.location.longitude for d in qualified_detections) / len(qualified_detections)
        print("\nAVERAGE SAFE COORDINATE")
        print("="*70)
        print(f"Latitude:  {avg_lat:.7f}")
        print(f"Longitude: {avg_lon:.7f}")
        print("="*70)


def get_average_safe_coordinate(qualified_detections: List[QualifiedLocation]) -> Tuple[float, float]:
    if not qualified_detections:
        return (0.0, 0.0)
    avg_lat = sum(d.location.latitude for d in qualified_detections) / len(qualified_detections)
    avg_lon = sum(d.location.longitude for d in qualified_detections) / len(qualified_detections)
    return (avg_lat, avg_lon)


def get_qualified_locations_info(qualified_detections: List[QualifiedLocation]) -> str:
    info = "\n" + "="*70 + "\nQUALIFIED LOCATION DETECTIONS\n" + "="*70
    if not qualified_detections:
        return info + "\nNo qualified detections found"
    info += f"\nTotal qualified: {len(qualified_detections)}"
    info += f"\nContinent: {qualified_detections[0].continent}"
    for i, d in enumerate(qualified_detections, 1):
        info += f"\n\n{i}. {d.location.query}"
        info += f"\n   Address: {d.location.address}"
        info += f"\n   Coordinates: ({d.location.latitude:.4f}, {d.location.longitude:.4f})"
        info += f"\n   Distance from primary: {d.distance_from_primary_km:.1f} km"
        info += f"\n   Cluster size: {d.cluster_size}"
    return info + "\n" + "="*70


def query_overpass_api(latitude: float,
                       longitude: float,
                       search_radius_m: int = 5000,
                       tags: Optional[Union[Dict[str, str], List[str]]] = None,
                       timeout: int = 30,
                       retries: int = 2) -> Dict[str, Any]:
    """Execute an Overpass API query for a specific coordinate."""

    if tags is None:
        tags = ['amenity', 'shop']

    # Normalize tags → list of QL filter expressions, filtered to valid OSM keys
    tag_filters = []
    if isinstance(tags, dict):
        for key, value in tags.items():
            if key not in VALID_OSM_TAGS:
                continue
            if value:
                tag_filters.append(f'"{key}"="{value}"')
            else:
                tag_filters.append(f'"{key}"')
    else:
        tag_filters = [f'"{t}"' for t in tags if t in VALID_OSM_TAGS]

    # Fall back to safe defaults if filtering removed everything
    if not tag_filters:
        print("⚠ No valid OSM tags after filtering, using defaults: amenity, shop")
        tag_filters = ['"amenity"', '"shop"']

    # Build query
    lines = [f'[out:json][timeout:{timeout}];(']
    for tag_expr in tag_filters:
        lines.append(f'  node[{tag_expr}](around:{search_radius_m},{latitude:.7f},{longitude:.7f});')
        lines.append(f'  way[{tag_expr}](around:{search_radius_m},{latitude:.7f},{longitude:.7f});')
    lines.append(');')
    lines.append('out center 100;')

    overpass_query = '\n'.join(lines)

    print(f"\nDEBUG QUERY:\n{overpass_query}\n")

    overpass_urls = [
        "https://overpass-api.de/api/interpreter",
        "https://z.overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    ]

    headers = {'User-Agent': 'geoGussr-Assistant/1.0'}

    print("="*70)
    print("QUERYING OVERPASS API")
    print("="*70)
    print(f"Location: ({latitude:.7f}, {longitude:.7f})")
    print(f"Radius: {search_radius_m}m")
    print(f"Tags: {tag_filters}")
    print("Sending request (this may take a moment)...\n")

    for attempt in range(retries):
        for url_idx, overpass_url in enumerate(overpass_urls):
            try:
                if attempt > 0 or url_idx > 0:
                    print(f"Trying alternative endpoint: {overpass_url}")
                    time.sleep(2)

                response = requests.post(
                    overpass_url,
                    data={"data": overpass_query},
                    headers=headers,
                    timeout=timeout
                )

                if response.status_code == 429:
                    print("⚠ Rate limited. Waiting 10 seconds...")
                    time.sleep(10)
                    continue
                if response.status_code >= 500:
                    print(f"✗ Server error {response.status_code}: {response.text[:300]}")
                    continue
                if response.status_code >= 400:
                    print(f"✗ HTTP {response.status_code}: {response.text[:300]}")
                    continue

                data = response.json()
                elements = data.get('elements', [])
                print(f"✓ Query successful! Found {len(elements)} elements\n")
                return data

            except requests.exceptions.Timeout:
                print(f"✗ Timeout after {timeout}s")
            except requests.exceptions.ConnectionError:
                print(f"✗ Connection error to {overpass_url}")
            except Exception as e:
                print(f"✗ Error: {e}")

    print("\n✗ Could not query Overpass API")
    return {"error": "api_unavailable", "elements": []}


def parse_overpass_results(data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    results = {'amenities': [], 'shops': [], 'tourism': [], 'historic': [], 'other': []}

    if 'error' in data or 'elements' not in data:
        return results

    for element in data['elements']:
        elem_type = element.get('type', 'unknown')
        tags = element.get('tags', {})
        lat = element.get('lat')
        lon = element.get('lon')

        # For ways, prefer the center point
        if elem_type == 'way' and 'center' in element:
            lat = element['center'].get('lat', lat)
            lon = element['center'].get('lon', lon)

        elem_info = {
            'id': element.get('id'),
            'type': elem_type,
            'name': tags.get('name', 'Unknown'),
            'latitude': lat,
            'longitude': lon,
            'tags': tags
        }

        if 'amenity' in tags:
            results['amenities'].append(elem_info)
        elif 'shop' in tags:
            results['shops'].append(elem_info)
        elif 'tourism' in tags:
            results['tourism'].append(elem_info)
        elif 'historic' in tags:
            results['historic'].append(elem_info)
        else:
            results['other'].append(elem_info)

    return results


def print_overpass_results(parsed_results: Dict[str, List[Dict[str, Any]]]) -> None:
    print("\n" + "="*70)
    print("OVERPASS RESULTS")
    print("="*70)

    total = sum(len(v) for v in parsed_results.values())
    print(f"\nTotal elements found: {total}\n")

    labels = {'amenities': 'Amenities', 'shops': 'Shops',
              'tourism': 'Tourism', 'historic': 'Historic Sites', 'other': 'Other'}

    for key, label in labels.items():
        items = parsed_results[key]
        if items:
            print(f"{label}: {len(items)}")
            for i, item in enumerate(items, 1):
                print(f"  {i}. {item['name']} ({item['type']})")
                if item['latitude'] and item['longitude']:
                    print(f"     Location: ({item['latitude']:.4f}, {item['longitude']:.4f})")
            
            print()

    print("="*70)