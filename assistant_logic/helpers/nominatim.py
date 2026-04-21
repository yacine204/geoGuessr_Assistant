import asyncio
from geopy.geocoders import Nominatim
from dataclasses import dataclass, field
from typing import Optional, List, Dict

@dataclass
class NominatimResult:
    query: str
    latitude: float
    longitude: float
    address: str
    poi_type: Optional[str] = None      # 'shop', 'amenity', 'tourism', etc.
    poi_class: Optional[str] = None     # Specific class (e.g., 'bakery', 'restaurant')
    country: Optional[str] = None       # Country code (e.g., 'fr', 'de')
    country_name: Optional[str] = None  # Full country name
    state: Optional[str] = None         # State/Region
    city: Optional[str] = None          # City
    postcode: Optional[str] = None      # Postal code
    tags: Dict[str, str] = field(default_factory=dict)

# Create a Nominatim geocoder (non-blocking)
geolocator = Nominatim(user_agent="geogussr-assistant")

def _extract_poi_type(location) -> tuple[str, str]:
    """Extract POI type and class from Nominatim result."""
    raw = location.raw if hasattr(location, 'raw') else {}
    poi_type = raw.get('type', 'unknown')
    poi_class = raw.get('class', 'unknown')
    return poi_type, poi_class

def _extract_address_parts(location) -> Dict[str, str]:
    """Extract structured address components from Nominatim."""
    raw = location.raw if hasattr(location, 'raw') else {}
    address_parts = raw.get('address', {})
    
    return {
        'country': address_parts.get('country'),
        'country_code': address_parts.get('country_code'),
        'state': address_parts.get('state'),
        'city': address_parts.get('city'),
        'postcode': address_parts.get('postcode'),
        'shop': address_parts.get('shop'),
        'amenity': address_parts.get('amenity'),
        'tourism': address_parts.get('tourism'),
        'historic': address_parts.get('historic'),
    }

async def search(query: str, language: str = 'en') -> List[NominatimResult]:
    """Search for a location using Nominatim"""
    try:
        # Run geocoding in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        location = await loop.run_in_executor(
            None, 
            lambda: geolocator.geocode(query, language=language, addressdetails=True, timeout=10)
        )
        
        if not location:
            return []
        
        poi_type, poi_class = _extract_poi_type(location)
        address_parts = _extract_address_parts(location)
        
        result = NominatimResult(
            query=query,
            latitude=location.latitude,
            longitude=location.longitude,
            address=location.address,
            poi_type=poi_type,
            poi_class=poi_class,
            country=address_parts.get('country_code'),
            country_name=address_parts.get('country'),
            state=address_parts.get('state'),
            city=address_parts.get('city'),
            postcode=address_parts.get('postcode'),
            tags=address_parts
        )
        return [result]
    except Exception as e:
        print(f"Error searching for {query}: {e}")
        return []

def filter_by_country(results: List[NominatimResult], 
                      allowed_countries: List[str]) -> List[NominatimResult]:
    """Filter Nominatim results by country code."""
    return [r for r in results if r.country and r.country.lower() in [c.lower() for c in allowed_countries]]

def group_by_type(results: List[NominatimResult]) -> Dict[str, List[NominatimResult]]:
    """Group Nominatim results by POI type."""
    grouped = {}
    for result in results:
        poi_type = result.poi_type or 'unknown'
        if poi_type not in grouped:
            grouped[poi_type] = []
        grouped[poi_type].append(result)
    return grouped