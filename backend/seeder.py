from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.stations import Station
from app.models.bookings import Booking  # Ensure Booking model is loaded
# Sample data for EV charging stations
sample_stations = [
    {
        "name": "Downtown Fast Charging Hub",
        "latitude": 40.7128,  # New York City coordinates
        "longitude": -74.0060,
        "charging_type": "DC Fast Charging",
        "power_output": 150.0,
        "is_available": True
    },
    {
        "name": "Central Park Charging Station",
        "latitude": 40.7829,
        "longitude": -73.9654,
        "charging_type": "AC",
        "power_output": 22.0,
        "is_available": True
    },
    {
        "name": "Brooklyn Super Charger",
        "latitude": 40.6782,
        "longitude": -73.9442,
        "charging_type": "DC Fast Charging",
        "power_output": 250.0,
        "is_available": True
    },
    {
        "name": "Queens Level 2 Station",
        "latitude": 40.7282,
        "longitude": -73.7949,
        "charging_type": "AC",
        "power_output": 19.2,
        "is_available": True
    },
    {
        "name": "Bronx Rapid Charging",
        "latitude": 40.8448,
        "longitude": -73.8648,
        "charging_type": "DC Fast Charging",
        "power_output": 175.0,
        "is_available": True
    }
]

def seed_stations():
    # Create database engine
    engine = create_engine("postgresql://postgres:Vedika123@localhost/EV_Charging")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Create station objects and add to database
        for station_data in sample_stations:
            station = Station(**station_data)
            db.add(station)
        
        # Commit the changes
        db.commit()
        print(f"Successfully added {len(sample_stations)} charging stations to the database.")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {str(e)}")
        
    finally:
        db.close()

if __name__ == "__main__":
    seed_stations()