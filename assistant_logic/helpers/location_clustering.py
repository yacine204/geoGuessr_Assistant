"""
Cluster geolocation results by proximity and filter outliers.
Groups similar coordinates and returns the best result from each cluster.
"""

from typing import List, Tuple, NamedTuple
from dataclasses import dataclass
import math


@dataclass
class LocationResult:
    """Single geolocation result"""
    query: str
    latitude: float
    longitude: float
    address: str
    confidence: float = 1.0  # Optional confidence score


@dataclass
class LocationCluster:
    """Cluster of similar locations"""
    center_lat: float
    center_lon: float
    results: List[LocationResult]
    cluster_radius_km: float = 0.0
    
    def best_result(self) -> LocationResult:
        """Get the best result in cluster (most detailed address)"""
        return max(self.results, key=lambda r: len(r.address.split(',')))
    
    def center(self) -> Tuple[float, float]:
        """Get cluster center"""
        return (self.center_lat, self.center_lon)


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two coordinates in kilometers.
    """
    R = 6371  # Earth radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def cluster_locations(results: List[LocationResult], 
                     cluster_distance_km: float = 100) -> List[LocationCluster]:
    """
    Cluster location results by proximity.
    
    Args:
        results: List of LocationResult objects
        cluster_distance_km: Distance in km to consider locations as same cluster
    
    Returns:
        List of LocationCluster objects
    """
    
    if not results:
        return []
    
    # Sort by confidence (or address length as proxy)
    sorted_results = sorted(results, key=lambda r: len(r.address.split(',')), reverse=True)
    
    clusters = []
    used = set()
    
    for i, result in enumerate(sorted_results):
        if i in used:
            continue
        
        # Start new cluster with this result
        cluster_results = [result]
        used.add(i)
        
        # Find all nearby results
        for j, other in enumerate(sorted_results):
            if j in used or j <= i:
                continue
            
            distance = _haversine_distance(
                result.latitude, result.longitude,
                other.latitude, other.longitude
            )
            
            if distance <= cluster_distance_km:
                cluster_results.append(other)
                used.add(j)
        
        # Calculate cluster center
        avg_lat = sum(r.latitude for r in cluster_results) / len(cluster_results)
        avg_lon = sum(r.longitude for r in cluster_results) / len(cluster_results)
        
        # Calculate cluster radius
        max_distance = max(
            _haversine_distance(avg_lat, avg_lon, r.latitude, r.longitude)
            for r in cluster_results
        )
        
        cluster = LocationCluster(
            center_lat=avg_lat,
            center_lon=avg_lon,
            results=cluster_results,
            cluster_radius_km=max_distance
        )
        clusters.append(cluster)
    
    return clusters


def filter_by_distance(clusters: List[LocationCluster], 
                       max_distance_km: float = 500) -> List[LocationCluster]:
    """
    Keep only clusters within a max distance from the best cluster.
    
    Args:
        clusters: List of location clusters
        max_distance_km: Max distance from primary cluster
    
    Returns:
        Filtered clusters (primary + nearby ones)
    """
    
    if not clusters:
        return []
    
    # Primary cluster is the one with most results
    primary = max(clusters, key=lambda c: len(c.results))
    
    filtered = [primary]
    
    for cluster in clusters:
        if cluster == primary:
            continue
        
        distance = _haversine_distance(
            primary.center_lat, primary.center_lon,
            cluster.center_lat, cluster.center_lon
        )
        
        if distance <= max_distance_km:
            filtered.append(cluster)
    
    return sorted(filtered, key=lambda c: len(c.results), reverse=True)


def get_best_locations(results: List[LocationResult],
                      cluster_distance_km: float = 100,
                      max_distance_from_primary_km: float = 500,
                      min_cluster_size: int = 1) -> List[Tuple[LocationResult, int]]:
    """
    Get best location results, grouped and filtered by proximity.
    
    Args:
        results: List of LocationResult objects
        cluster_distance_km: Distance to group results together
        max_distance_from_primary_km: Max distance from primary result
        min_cluster_size: Minimum results per cluster to include
    
    Returns:
        List of (best_result, cluster_size) tuples, sorted by cluster size
    
    Example:
        results = [
            LocationResult('CHELLES', 48.84, 2.50, 'Chelles, France'),
            LocationResult('MARNE', 48.96, 4.31, 'Marne, France'),
            LocationResult('LA MALTOURNEE', 47.75, 1.90, 'La Maltournee, France'),
        ]
        
        best = get_best_locations(results)
        # Returns best result from largest cluster + others within distance
    """
    
    # Step 1: Cluster by proximity
    clusters = cluster_locations(results, cluster_distance_km)
    
    # Step 2: Filter by distance from primary
    filtered = filter_by_distance(clusters, max_distance_from_primary_km)
    
    # Step 3: Extract best result from each cluster
    best_locations = [
        (cluster.best_result(), len(cluster.results))
        for cluster in filtered
        if len(cluster.results) >= min_cluster_size
    ]
    
    return best_locations


def print_cluster_summary(clusters: List[LocationCluster]) -> None:
    """Print a summary of clusters for debugging."""
    print("\n" + "="*70)
    print("LOCATION CLUSTERING SUMMARY")
    print("="*70)
    
    for i, cluster in enumerate(clusters, 1):
        best = cluster.best_result()
        print(f"\nCluster {i}: {len(cluster.results)} result(s)")
        print(f"  Center: ({cluster.center_lat:.4f}, {cluster.center_lon:.4f})")
        print(f"  Radius: {cluster.cluster_radius_km:.1f} km")
        print(f"  Best: {best.query}")
        print(f"    → {best.address}")
        print(f"    → ({best.latitude:.4f}, {best.longitude:.4f})")
        
        if len(cluster.results) > 1:
            print(f"  Other results in cluster:")
            for result in cluster.results[1:]:
                print(f"    • {result.query}: {result.address.split(',')[0]}")
    
    print("\n" + "="*70)