"""Native GPS values are suggestions only; existing driver confirmation performs writes."""
import math

def gps_suggestion(movement, query):
    if str(query.get('gps_id', '')) != str(movement['id']):
        return None
    try:
        distance = float(query.get('gps_km', ''))
        if not math.isfinite(distance) or not 0 <= distance <= 100000:
            return None
        return int(movement.get('km_inicial') or 0) + round(distance)
    except (ValueError, TypeError, OverflowError):
        return None
