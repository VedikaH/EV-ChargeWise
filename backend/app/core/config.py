from pydantic_settings import BaseSettings
from typing import List
from dotenv import load_dotenv
import os

# Force reload of the .env file
load_dotenv(dotenv_path=".env", override=True)

class Settings(BaseSettings):
    PROJECT_NAME: str = "EV Charging Station Booking"
    DATABASE_URL: str = "postgresql://postgres:Vedika123@localhost/EV_Charging"
    ALLOWED_HOSTS: List[str] = ["*"]
    PAYPAL_BASE_URL: str = "https://api-m.sandbox.paypal.com"
    PAYPAL_CLIENT_ID: str
    PAYPAL_CLIENT_SECRET: str
    PAYPAL_RETURN_URL: str
    PAYPAL_CANCEL_URL: str
    MAX_SEARCH_RADIUS: float = 20.0  # kilometers

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

# Debug to verify the loaded DATABASE_URL
print(settings.DATABASE_URL)
print(settings.MAX_SEARCH_RADIUS)

