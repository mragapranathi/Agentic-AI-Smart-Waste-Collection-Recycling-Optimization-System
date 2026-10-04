import math
from typing import List, Tuple

def haversine_distance_km(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """
    Computes great-circle distance between two (lat, lon) coordinates in kilometers.
    """
    lat1, lon1 = coord1
    lat2, lon2 = coord2

    R = 6371.0  # Earth radius in kilometers

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    distance = R * c
    return round(distance, 3)

def compute_distance_matrix(locations: List[Tuple[float, float]]) -> List[List[int]]:
    """
    Computes an NxN distance matrix in meters (as integers) for OR-Tools solver.
    """
    n = len(locations)
    matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                dist_km = haversine_distance_km(locations[i], locations[j])
                # Convert to meters for integer OR-Tools precision
                matrix[i][j] = int(dist_km * 1000)
            else:
                matrix[i][j] = 0
    return matrix

def estimate_duration_minutes(distance_km: float, num_stops: int, avg_speed_kmh: float = 30.0) -> float:
    """
    Estimates travel + service duration.
    Avg service time per bin stop = 4 minutes.
    """
    travel_time_min = (distance_km / avg_speed_kmh) * 60.0
    service_time_min = num_stops * 4.0
    return round(travel_time_min + service_time_min, 1)
