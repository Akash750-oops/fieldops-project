import math

def calculate_distance(loc1: str, loc2: str) -> float:
    """
    Calculate the distance (Euclidean) between two points defined as "lat, lon".
    Returns distance in arbitrary units (degrees-like).
    
    If conversion fails (e.g. city names), returns a large number or 0 depending on logic.
    For this engine, we assume "lat, lon" format.
    """
    try:
        lat1, lon1 = map(float, loc1.split(','))
        lat2, lon2 = map(float, loc2.split(','))
        
        # Simple Euclidean distance for simplicity
        # For real-world use Haversine, but this satisfies "Compare nearest"
        return math.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2)
    except Exception:
        # Fallback if locations are names
        if loc1.lower() == loc2.lower():
            return 0.0
        return 999999.0
