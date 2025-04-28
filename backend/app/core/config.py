from pydantic_settings import BaseSettings
from typing import List
from dotenv import load_dotenv
import os

# Force reload of the .env file
load_dotenv(dotenv_path=".env", override=True)

class Settings(BaseSettings):
    PROJECT_NAME: str = "EV Charging Station Booking"
    #DATABASE_URL: str = "postgresql://postgres:Vedika123@localhost/EV_Charging"
    DATABASE_URL:str = "postgresql://postgres:postgres@db:5432/EV_Charging"
    POSTGRES_USER:str
    POSTGRES_PASSWORD:str
    POSTGRES_DB:str
    ALLOWED_HOSTS: List[str] = ["*"]
    PAYPAL_BASE_URL: str = "https://api-m.sandbox.paypal.com"
    PAYPAL_CLIENT_ID: str
    PAYPAL_CLIENT_SECRET: str
    PAYPAL_RETURN_URL: str
    PAYPAL_CANCEL_URL: str
    MAX_SEARCH_RADIUS: float = 20.0  # kilometers
    SECRET_KEY:str 
    ALGORITHM: str 
    ACCESS_TOKEN_EXPIRE_MINUTES:int
    OSRM_SERVER_URL: str = "http://router.project-osrm.org"
    MAX_SEARCH_RADIUS: float = 20  # in kilometers
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    PAYMENT_TIMEOUT_MINUTES: int = 15



    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"

settings = Settings()

# Debug to verify the loaded DATABASE_URL
print(settings.DATABASE_URL)
print(settings.MAX_SEARCH_RADIUS)

