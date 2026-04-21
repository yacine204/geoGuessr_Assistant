"""
Generate Overpass QL queries from qualified location detections.
Filters location clusters by distance and continent, then generates queries.
"""

from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
import math
import requests
import time
from helpers.location_clustering import LocationCluster, LocationResult


# Continent bounding boxes (lat_min, lat_max, lon_min, lon_max)
CONTINENTS = {
    'Europe': (35.0, 71.0, -10.0, 40.0),
    'Asia': (-10.0, 75.0, 26.0, 180.0),
    'Africa': (-35.0, 37.0, -18.0, 52.0),
    'North_America': (15.0, 85.0, -170.0, -50.0),
    'South_America': (-56.0, 13.0, -82.0, -35.0),
    'Australia_Oceania': (-47.0, -10.0, 113.0, 180.0),
}


@dataclass
class QualifiedLocation:
    """A location that passed distance and continent filtering"""
    location: LocationResult
    continent: str
    distance_from_primary_km: float
    cluster_size: int


def _get_continent(latitude: float, longitude: float) -> Optional[str]:
    """
    Determine continent from coordinates.
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
    
    Returns:
        Continent name or None if not found
    """
    for continent, (lat_min, lat_max, lon_min, lon_max) in CONTINENTS.items():
        if lat_min <= latitude <= lat_max and lon_min <= longitude <= lon_max:
            return continent
    return None


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates in kilometers."""
    R = 6371  # Earth radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def filter_qualified_detections(clusters: List[LocationCluster],
                               max_distance_km: float = 300,
                               same_continent_only: bool = True) -> List[QualifiedLocation]:
    """
    Filter location clusters to get only qualified detections.
    
    Criteria:
    - Distance between detections must be <= max_distance_km
    - All must belong to same continent (if same_continent_only=True)
    - Cluster must have at least 2 results for a location to be qualified
    
    Args:
        clusters: List of LocationCluster objects
        max_distance_km: Maximum distance between detections
        same_continent_only: Require all detections on same continent
    
    Returns:
        List of QualifiedLocation objects
    """
    
    if not clusters:
        return []
    
    # Primary cluster (largest)
    primary = max(clusters, key=lambda c: len(c.results))
    primary_result = primary.best_result()
    primary_continent = _get_continent(primary_result.latitude, primary_result.longitude)
    
    qualified = [
        QualifiedLocation(
            location=primary_result,
            continent=primary_continent,
            distance_from_primary_km=0.0,
            cluster_size=len(primary.results)
        )
    ]
    
    # Filter other clusters by distance and continent
    for cluster in clusters:
        if cluster == primary:
            continue
        
        best = cluster.best_result()
        continent = _get_continent(best.latitude, best.longitude)
        
        # Check continent match
        if same_continent_only and continent != primary_continent:
            continue
        
        # Check distance
        distance = _haversine_distance(
            primary_result.latitude, primary_result.longitude,
            best.latitude, best.longitude
        )
        
        if distance <= max_distance_km:
            qualified.append(
                QualifiedLocation(
                    location=best,
                    continent=continent,
                    distance_from_primary_km=distance,
                    cluster_size=len(cluster.results)
                )
            )
    
    return qualified


def generate_overpass_query(qualified_detections: List[QualifiedLocation],
                           search_radius_m: int = 5000,
                           tags: Optional[List[str]] = None) -> str:
    """
    Generate Overpass QL query from qualified detections.
    
    Args:
        qualified_detections: List of QualifiedLocation objects
        search_radius_m: Search radius in meters around each detection
        tags: List of OSM tags to search for (e.g., ['amenity', 'shop', 'tourism'])
    
    Returns:
        Overpass QL query string
    """
    
    if not qualified_detections:
        return ""
    
    if tags is None:
        tags = ['amenity', 'shop', 'tourism', 'historic']
    
    # Build Overpass query
    query_parts = ['[out:json];']
    
    # Add union of all search areas around detections
    query_parts.append('(')
    
    for detection in qualified_detections:
        lat = detection.location.latitude
        lon = detection.location.longitude
        radius = search_radius_m
        
        # Search for nodes/ways/relations with specified tags
        for tag in tags:
            query_parts.append(f'  node["{tag}"](around:{radius},{lat},{lon});')
            query_parts.append(f'  way["{tag}"](around:{radius},{lat},{lon});')
            query_parts.append(f'  relation["{tag}"](around:{radius},{lat},{lon});')
    
    query_parts.append(');')
    
    # Return results
    query_parts.append('out geom center;')
    
    return '\n'.join(query_parts)


def get_qualified_locations_info(qualified_detections: List[QualifiedLocation]) -> str:
    """
    Get formatted info about qualified detections.
    
    Args:
        qualified_detections: List of QualifiedLocation objects
    
    Returns:
        Formatted string with detection info
    """
    
    info = "\n" + "="*70
    info += "\nQUALIFIED LOCATION DETECTIONS"
    info += "\n" + "="*70
    
    if not qualified_detections:
        info += "\nNo qualified detections found"
        return info
    
    info += f"\nTotal qualified: {len(qualified_detections)}"
    info += f"\nContinent: {qualified_detections[0].continent}"
    
    for i, detection in enumerate(qualified_detections, 1):
        info += f"\n\n{i}. {detection.location.query}"
        info += f"\n   Address: {detection.location.address}"
        info += f"\n   Coordinates: ({detection.location.latitude:.4f}, {detection.location.longitude:.4f})"
        info += f"\n   Distance from primary: {detection.distance_from_primary_km:.1f} km"
        info += f"\n   Cluster size: {detection.cluster_size}"
    
    info += "\n" + "="*70
    
    return info


def get_average_safe_coordinate(qualified_detections: List[QualifiedLocation]) -> Tuple[float, float]:
    """
    Calculate average safe coordinate from qualified detections.
    
    Args:
        qualified_detections: List of QualifiedLocation objects
    
    Returns:
        Tuple of (latitude, longitude) representing the average coordinate
    """
    
    if not qualified_detections:
        return (0.0, 0.0)
    
    avg_lat = sum(d.location.latitude for d in qualified_detections) / len(qualified_detections)
    avg_lon = sum(d.location.longitude for d in qualified_detections) / len(qualified_detections)
    
    return (avg_lat, avg_lon)


def print_overpass_query(qualified_detections: List[QualifiedLocation],
                        search_radius_m: int = 5000) -> None:
    """Print the generated Overpass QL query."""
    
    query = generate_overpass_query(qualified_detections, search_radius_m)
    
    print("\n" + "="*70)
    print("OVERPASS QL QUERY")
    print("="*70)
    print(query)
    print("="*70)
    
    # Calculate and print average safe coordinate
    if qualified_detections:
        avg_lat = sum(d.location.latitude for d in qualified_detections) / len(qualified_detections)
        avg_lon = sum(d.location.longitude for d in qualified_detections) / len(qualified_detections)
        
        print("\nAVERAGE SAFE COORDINATE")
        print("="*70)
        print(f"Latitude:  {avg_lat:.7f}")
        print(f"Longitude: {avg_lon:.7f}")
        print(f"Coordinate: ({avg_lat:.7f}, {avg_lon:.7f})")
        print("="*70)


def query_overpass_api(latitude: float, 
                       longitude: float,
                       search_radius_m: int = 5000,
                       tags: Optional[List[str]] = None,
                       timeout: int = 30,
                       retries: int = 2) -> Dict[str, Any]:
    """
    Execute an Overpass API query for a specific coordinate.
    
    Args:
        latitude: Center latitude
        longitude: Center longitude
        search_radius_m: Search radius in meters
        tags: List of OSM tags to search for
        timeout: API request timeout in seconds
        retries: Number of retries on failure
    
    Returns:
        Dictionary with query results
    """
    
    if tags is None:
        tags = ['amenity', 'shop']  # Simplified to fewer tags for faster query
    
    # Build simplified Overpass query (fewer tags = faster)
    query_parts = ['[out:json];(']
    
    for tag in tags:
        query_parts.append(f'node["{tag}"](around:{search_radius_m},{latitude},{longitude});')
        query_parts.append(f'way["{tag}"](around:{search_radius_m},{latitude},{longitude});')
    
    query_parts.append(');out center limit 100;')  # Limit results for faster response
    
    overpass_query = '\n'.join(query_parts)
    
    # Overpass API endpoints
    overpass_urls = [
        "https://z.overpass-api.de/api/interpreter",  # Try fast mirror first
        "https://overpass-api.de/api/interpreter",
    ]
    
    headers = {
        'User-Agent': 'geoGussr-Assistant/1.0',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }
    
    print(f"\n" + "="*70)
    print("QUERYING OVERPASS API")
    print("="*70)
    print(f"Location: ({latitude:.7f}, {longitude:.7f})")
    print(f"Radius: {search_radius_m}m")
    print("Sending request (this may take a moment)...\n")
    
    for attempt in range(retries):
        for url_idx, overpass_url in enumerate(overpass_urls):
            try:
                if attempt > 0 or url_idx > 0:
                    print(f"Trying alternative endpoint...")
                    time.sleep(1)
                
                response = requests.post(
                    overpass_url,
                    data=overpass_query,
                    headers=headers,
                    timeout=timeout
                )
                
                # Handle rate limiting
                if response.status_code == 429:
                    print(f"⚠ Rate limited. Waiting 5 seconds...")
                    time.sleep(5)
                    continue
                
                # Handle server errors
                if response.status_code >= 500:
                    print(f"✗ Server error {response.status_code}")
                    continue
                
                # Handle other HTTP errors
                if response.status_code >= 400:
                    print(f"✗ HTTP {response.status_code}")
                    continue
                
                response.raise_for_status()
                data = response.json()
                
                elements = data.get('elements', [])
                print(f"✓ Query successful!")
                print(f"✓ Found {len(elements)} elements\n")
                
                return data
                
            except requests.exceptions.Timeout:
                print(f"✗ Timeout ({timeout}s)")
                continue
            except requests.exceptions.ConnectionError as e:
                print(f"✗ Connection error")
                continue
            except Exception as e:
                print(f"✗ Error: {str(e)}")
                continue
    
    print(f"\n✗ Could not query Overpass API")
    return {"error": "api_unavailable", "elements": []}


def parse_overpass_results(data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Parse Overpass API results and organize by type.
    
    Args:
        data: Dictionary from Overpass API response
    
    Returns:
        Dictionary with categorized results
    """
    
    results = {
        'amenities': [],
        'shops': [],
        'tourism': [],
        'historic': [],
        'other': []
    }
    
    if 'error' in data or 'elements' not in data:
        return results
    
    for element in data['elements']:
        elem_type = element.get('type', 'unknown')
        tags = element.get('tags', {})
        
        # Get coordinates
        lat = element.get('lat')
        lon = element.get('lon')
        
        if elem_type == 'way' and 'geometry' in element:
            # For ways, use center if available
            geometry = element['geometry']
            if geometry:
                lat = geometry[0].get('lat', lat)
                lon = geometry[0].get('lon', lon)
        
        elem_info = {
            'id': element.get('id'),
            'type': elem_type,
            'name': tags.get('name', 'Unknown'),
            'latitude': lat,
            'longitude': lon,
            'tags': tags
        }
        
        # Categorize by tag
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
    """Print formatted Overpass results."""
    
    print("\n" + "="*70)
    print("OVERPASS RESULTS")
    print("="*70)
    
    categories = {
        'amenities': 'Amenities',
        'shops': 'Shops',
        'tourism': 'Tourism',
        'historic': 'Historic Sites',
        'other': 'Other'
    }
    
    total_found = sum(len(items) for items in parsed_results.values())
    print(f"\nTotal elements found: {total_found}\n")
    
    for key, label in categories.items():
        items = parsed_results[key]
        if items:
            print(f"{label}: {len(items)}")
            for i, item in enumerate(items[:5], 1):  # Show first 5
                print(f"  {i}. {item['name']} ({item['type']})")
                if item['latitude'] and item['longitude']:
                    print(f"     Location: ({item['latitude']:.4f}, {item['longitude']:.4f})")
            if len(items) > 5:
                print(f"  ... and {len(items) - 5} more")
            print()
    
    print("="*70)
