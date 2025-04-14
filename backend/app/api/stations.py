from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, Field
from app.database.session import get_db
from app.models.stations import Station
from app.schemas.stations import StationCreate, StationResponse, StationSearchRequest
from app.services.route import RouteOptimizer
from app.models.admin import Admin
from app.auth.dependencies import get_current_admin, get_current_user, require_super_admin

router = APIRouter()

@router.post("/search", response_model=List[StationResponse])
def search_stations(
    search_params: StationSearchRequest, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)  
):
    """
    Search for nearby charging stations using Dijkstra-based route optimization
    """
    # Get available stations
    query = db.query(Station).filter(Station.is_available == True)
    
    # Apply charging type filter if specified
    if search_params.charging_type:
        query = query.filter(Station.charging_type == search_params.charging_type)
    
    if search_params.power_output:
        query = query.filter(Station.power_output >= search_params.power_output)
    
    stations = query.all()
    
    if not stations:
        return []
    
    # Initialize route optimizer
    optimizer = RouteOptimizer(stations, battery_range=search_params.radius)
    
    # Find nearby stations
    try:
        nearby = optimizer.find_nearby_stations(
            search_params.latitude,
            search_params.longitude,
            search_params.radius
        )
        
        # Convert to response format
        station_responses = []
        for station, distance in nearby:
            station_responses.append(
                StationResponse(
                    id=station.id,
                    name=station.name,
                    latitude=station.latitude,
                    longitude=station.longitude,
                    charging_type=station.charging_type,
                    power_output=station.power_output,
                    is_available=station.is_available,
                    distance=round(distance, 2)
                )
            )
        
        return station_responses
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/super-admin/create-station", response_model=StationResponse)
def create_station(
    station: StationCreate, 
    current_admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Create a new charging station (admin only)"""
    if not current_admin.is_super_admin:
        raise HTTPException(
            status_code=403,
            detail="Only super admins can create new stations"
        )
    
    db_station = Station(
        name=station.name,
        latitude=station.latitude,
        longitude=station.longitude,
        charging_type=station.charging_type,
        power_output=station.power_output,
        is_available=station.is_available
    )
    
    try:
        db.add(db_station)
        # Add the station to the creating admin's managed stations
        current_admin.stations.append(db_station)
        db.commit()
        db.refresh(db_station)
        
        return StationResponse(
            id=db_station.id,
            name=db_station.name,
            latitude=db_station.latitude,
            longitude=db_station.longitude,
            charging_type=db_station.charging_type,
            power_output=db_station.power_output,
            is_available=db_station.is_available,
            distance=None
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to create charging station"
        )
