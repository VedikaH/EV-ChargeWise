from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import stations, bookings, payments, routes
from app.core.config import settings
from app.database.session import engine
from app.database import base

# Create database tables
base.Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(stations.router, prefix="/stations", tags=["stations"])
app.include_router(bookings.router, prefix="/bookings", tags=["bookings"])
app.include_router(payments.router, prefix="/payments", tags=["payments"])
app.include_router(routes.router, prefix="/routes", tags=["routes"])

@app.get("/")
def health_check():
    return {"status": "healthy"}