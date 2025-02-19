from datetime import datetime, timedelta

def validate_booking_time(start_time: datetime, end_time: datetime) -> bool:
    now = datetime.now()
    max_booking_period = timedelta(hours=4)
    
    if start_time < now:
        return False
    if end_time <= start_time:
        return False
    if end_time - start_time > max_booking_period:
        return False
    return True

def validate_coordinates(latitude: float, longitude: float) -> bool:
    return -90 <= latitude <= 90 and -180 <= longitude <= 180