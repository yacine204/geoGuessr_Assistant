"""Convert Nominatim results to Overpass query parameters."""

from typing import List, Set
from helpers.nominatim import NominatimResult

VALID_OSM_TAGS = {
    'amenity', 'shop', 'tourism', 'historic', 'leisure',
    'highway', 'railway', 'aeroway', 'waterway', 'building',
    'landuse', 'natural', 'office', 'sport', 'place'
}

def extract_overpass_tags(nominatim_results: List[NominatimResult]) -> List[str]:
    tags = set()
    for result in nominatim_results:
        if result.poi_type and result.poi_type in VALID_OSM_TAGS:
            tags.add(result.poi_type)
        if result.poi_class:
            mapped = {
                'bakery': 'shop', 'restaurant': 'amenity', 'cafe': 'amenity',
                'hotel': 'tourism', 'monument': 'historic', 'museum': 'tourism',
                'shop': 'shop', 'supermarket': 'shop',
            }.get(result.poi_class)
            if mapped:
                tags.add(mapped)

    return list(tags) if tags else ['amenity', 'shop']

def nominatim_to_location_result(nominatim_result: NominatimResult):
    """Convert NominatimResult to LocationResult for clustering."""
    from helpers.location_clustering import LocationResult
    
    return LocationResult(
        query=nominatim_result.query,
        latitude=nominatim_result.latitude,
        longitude=nominatim_result.longitude,
        address=nominatim_result.address,
        confidence=1.0
    )