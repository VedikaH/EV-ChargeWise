from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, Field
from app.database.session import get_db
from app.models.stations import Station
from app.schemas.stations import ChargingConfigResponse, StationCreate, StationCreateResponse, StationResponse, StationSearchRequest
from app.models.admin import Admin
from app.auth.dependencies import get_current_admin, get_current_user, require_super_admin
from sqlalchemy.orm import joinedload
from app.services.route_optimizer import OSRMRouteOptimizer
from app.core.config import Settings,settings
from app.models.chargingCosts import ChargingConfig


router = APIRouter()

@router.post("/search", response_model=List[StationResponse])
def get_nearby_stations(
    latitude: float,
    longitude: float,
    max_range: float = Query(30.0, description="Max search range in kilometers"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Find nearby charging stations using OSRM-based spatial + real-road filtering
    """
    # Fetch all available stations
    stations = db.query(Station).options(joinedload(Station.charging_configs)).filter(Station.is_available == True).all()

    if not stations:
        raise HTTPException(status_code=404, detail="No available stations found")

    try:
        optimizer = OSRMRouteOptimizer(
            stations=stations,
            battery_range=settings.MAX_SEARCH_RADIUS,
            osrm_server=settings.OSRM_SERVER_URL
        )

        results = optimizer.find_nearby_stations(latitude, longitude, max_range)

        if not results:
            return []

        response = []
        for station, distance, route_info in results:
            charging_configs = [
                ChargingConfigResponse(
                    charging_type=config.charging_type,
                    connector_type=config.connector_type,
                    power_output=config.power_output,
                    cost_per_kwh=config.cost_per_kwh
                )
                for config in station.charging_configs
            ]

            response.append(
                StationResponse(
                    id=station.id,
                    name=station.name,
                    latitude=station.latitude,
                    longitude=station.longitude,
                    is_available=station.is_available,
                    charging_configs=charging_configs,
                    distance_from_start=round(distance, 2)
                )
            )

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/super-admin/create-station", response_model=StationCreateResponse)
def create_station(
    station: StationCreate, 
    current_admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    if not current_admin.is_super_admin:
        raise HTTPException(status_code=403, detail="Only super admins can create new stations")

    db_station = Station(
        name=station.name,
        latitude=station.latitude,
        longitude=station.longitude,
        is_available=station.is_available
    )

    try:
        db.add(db_station)
        current_admin.stations.append(db_station)
        db.commit()
        db.refresh(db_station)

        # If charging configs are included, add them
        if station.charging_configs:
            for config in station.charging_configs:
                db_config = ChargingConfig(
                    charging_type=config.charging_type,
                    connector_type=config.connector_type,
                    power_output=config.power_output,
                    cost_per_kwh=config.cost_per_kwh,
                    station_id=db_station.id
                )
                db.add(db_config)

            db.commit()

        return StationCreateResponse(
            id=db_station.id,
            name=db_station.name,
            latitude=db_station.latitude,
            longitude=db_station.longitude,
            is_available=db_station.is_available,
            message="Station created successfully"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to create charging station"
        )
    
@router.delete("/super-admin/delete-station/{station_id}", response_model=StationCreateResponse)
def delete_station(
    station_id: int,
    current_admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Delete a charging station (super admin only)"""
    if not current_admin.is_super_admin:
        raise HTTPException(
            status_code=403,
            detail="Only super admins can delete stations"
        )
    
    # Fetch the station to be deleted
    db_station = db.query(Station).filter(Station.id == station_id).first()
    
    if db_station is None:
        raise HTTPException(
            status_code=404,
            detail="Charging station not found"
        )
    
    try:
        # Delete associated charging configs if they exist
        db.query(ChargingConfig).filter(ChargingConfig.station_id == db_station.id).delete()
        
        # Now delete the station itself
        db.delete(db_station)
        db.commit()

        # Return a success response
        return StationCreateResponse(
            id=db_station.id,
            name=db_station.name,
            latitude=db_station.latitude,
            longitude=db_station.longitude,
            is_available=db_station.is_available,
            message="Station deleted successfully"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to delete charging station"
        )
