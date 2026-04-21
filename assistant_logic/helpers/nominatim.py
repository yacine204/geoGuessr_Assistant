import asyncio
from geopy.geocoders import Nominatim


from dataclasses import dataclass
from typing import Optional, List

# Create a Nominatim geocoder
geolocator = Nominatim(user_agent="geogussr-assistant")

async def search(query):
    """Search for a location using Nominatim"""
    try:
        location = geolocator.geocode(query)
        if location:
            return [location]
        return []
    except Exception as e:
        print(f"Error searching for {query}: {e}")
        return []