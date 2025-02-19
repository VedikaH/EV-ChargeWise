import math

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat/2)**2 + 
         math.cos(math.radians(lat1)) * 
         math.cos(math.radians(lat2)) * 
         math.sin(dlon/2)**2)
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def calculate_box_bounds(latitude: float, longitude: float, radius: float) -> tuple:
    """Returns bounding box coordinates for efficient DB queries"""
    R = 6371
    dlat = radius / R
    dlon = radius / (R * math.cos(math.radians(latitude)))
    
    return (
        latitude - math.degrees(dlat),
        latitude + math.degrees(dlat),
        longitude - math.degrees(dlon),
        longitude + math.degrees(dlon)
    )