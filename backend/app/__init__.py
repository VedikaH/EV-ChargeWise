from requests import Session
from app.models.admin import Admin
from app.models.admin import admin_stations
from app.models.stations import Station
from app.models.chargingCosts import ChargingConfig
from app.models.bookings import Booking
from app.models.user import User
from app.models.payments import Payment  # Import the Booking model
from app.models.stations import Station  # Import the Booking model

from app.auth.dependencies import get_password_hash


def init_super_admin(db: Session):
    super_admin = Admin(
        username="superadmin",
        email="superadmin@example.com",
        hashed_password=get_password_hash("initial-password"),
        is_super_admin=True
    )
    db.add(super_admin)
    db.commit()