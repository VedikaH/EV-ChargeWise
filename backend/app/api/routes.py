import traceback
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, Field
from app.core.config import Settings,settings
from app.database.session import get_db
from app.models.stations import Station
from app.models.chargingCosts import ChargingConfig
from app.schemas.stations import ChargingConfigResponse, RouteOptimizationRequest, RouteResponse, StationResponse
from app.services.route_optimizer import OSRMRouteOptimizer
from app.auth.dependencies import get_current_user
from sqlalchemy.orm import joinedload


router = APIRouter()

@router.post("/optimize", response_model=RouteResponse)
def optimize_route(
    route_request: RouteOptimizationRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Optimize a route between two points with charging stations using OSRM
    """
    # Fetch all available stations
    stations = db.query(Station).\
    options(joinedload(Station.charging_configs)).\
    filter(Station.is_available == True).\
    all()
    
    if not stations:
        raise HTTPException(
            status_code=404,
            detail="No available charging stations found"
        )
    
    try:
        # Use OSRM-based optimizer
        route_optimizer = OSRMRouteOptimizer(
            stations=stations,
            battery_range=settings.MAX_SEARCH_RADIUS,
            osrm_server=settings.OSRM_SERVER_URL
        )
        
        # Get optimized route using Dijkstra's algorithm with OSRM distances
        optimized_route = route_optimizer.dijkstra_route(
            start_coords=(route_request.start_latitude, route_request.start_longitude),
            end_coords=(route_request.end_latitude, route_request.end_longitude)
        )
        
        if not optimized_route:
            raise HTTPException(status_code=404, detail="No optimized route found")
        
        # Get detailed route summary with geometry
        route_summary = route_optimizer.get_route_summary(
            optimized_route,
            start_coords=(route_request.start_latitude, route_request.start_longitude),
            end_coords=(route_request.end_latitude, route_request.end_longitude)
        )
        
        #station_responses = [StationResponse.from_orm(station) for station in optimized_route]
        station_responses = []
        segments = route_summary['route_segments']

        for i, station in enumerate(optimized_route):
            station= station[0]  # Get the Station object from the tuple
            charging_configs = [
                ChargingConfigResponse(
                    charging_type=config.charging_type,
                    connector_type=config.connector_type,
                    power_output=config.power_output,
                    cost_per_kwh=config.cost_per_kwh
                )
                for config in station.charging_configs
            ]
            station_response = StationResponse (
                id=station.id,
                name=station.name,
                latitude=station.latitude,
                longitude=station.longitude,
                charging_configs=charging_configs,
                is_available=station.is_available,
                distance_to_next=None
            )
            
            # Find the corresponding segment and set distance
            if i == 0:
                # First station - use distance from start_to_station segment
                station_response.distance_from_start = segments[0]['distance']
                
                # Distance to next charging station
                if len(segments) > 1:
                    station_response.distance_to_next = segments[1]['distance']
            
            elif i == len(optimized_route) - 1:
                # Last station - use distance to destination from last segment
                station_response.distance_to_destination = segments[-1]['distance']
                station_response.distance_to_next = None
            
            else:
                # Middle stations - use distance from previous segment
                segment_index = i  # Since segment[0] is start_to_station
                station_response.distance_from_previous = segments[segment_index]['distance']
                
                # Assign distance to next station
                if segment_index + 1 < len(segments):
                    station_response.distance_to_next = segments[segment_index + 1]['distance']
            
            station_responses.append(station_response)

        return RouteResponse(
            charging_stations=station_responses,
            total_distance=route_summary['total_distance'],
            total_duration=route_summary['total_duration_minutes'],
            number_of_stops=route_summary['number_of_stops'],
            estimated_charging_time=route_summary['estimated_charging_time_minutes'],
            total_trip_time=route_summary['total_trip_time_minutes'],
            route_segments=route_summary['route_segments']
        )
        
    except Exception as e:
        # Error handling (same as existing)
        error_details = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "stack_trace": traceback.format_exc()
        }
        print(error_details)
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.get("/nearest-station", response_model=StationResponse)
def find_nearest_station(
    latitude: float,
    longitude: float,
    charging_type: str = None,
    min_power: float = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Find the nearest charging station to the given coordinates.
    """
    # Fetch all available stations with their charging configs
    stations = db.query(Station).options(
        joinedload(Station.charging_configs)
    ).filter(Station.is_available == True).all()

    if not stations:
        raise HTTPException(
            status_code=404,
            detail="No matching charging stations found"
        )

    optimizer = OSRMRouteOptimizer(
        stations=stations,
        battery_range=settings.MAX_SEARCH_RADIUS,
        osrm_server=settings.OSRM_SERVER_URL
    )

    try:
        station, distance, route_info = optimizer.find_nearest_station(
            latitude,
            longitude,
            filter_charging_type=charging_type,
            filter_min_power=min_power
        )

        # Build filtered configs (if filters provided)
        charging_configs = [
            ChargingConfigResponse(
                charging_type=config.charging_type,
                connector_type=config.connector_type,
                power_output=config.power_output,
                cost_per_kwh=config.cost_per_kwh
            )
            for config in station.charging_configs
            if ((charging_type is None or config.charging_type == charging_type) and
                (min_power is None or config.power_output >= min_power))
        ]

        # If filtering gave no result, include all configs
        if not charging_configs:
            charging_configs = [
                ChargingConfigResponse(
                    charging_type=config.charging_type,
                    connector_type=config.connector_type,
                    power_output=config.power_output,
                    cost_per_kwh=config.cost_per_kwh
                )
                for config in station.charging_configs
            ]

        return StationResponse(
            id=station.id,
            name=station.name,
            latitude=station.latitude,
            longitude=station.longitude,
            is_available=station.is_available,
            charging_configs=charging_configs,
            distance=round(distance, 2),
            route_geometry=route_info.get("geometry") if route_info else None
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print("🔥 Nearest station error:", str(e))
        raise HTTPException(status_code=500, detail="An error occurred while finding the nearest station.")
# @router.get("/nearest-station", response_model=StationResponse)
# def find_nearest_station(
#     latitude: float,
#     longitude: float,
#     charging_type: str = None,
#     min_power: float = None,
#     db: Session = Depends(get_db),
#     current_user: dict = Depends(get_current_user)
# ):
#     """
#     Find the nearest charging station to the given coordinates
#     """
#     # Get available stations with their charging configs
#     query = db.query(Station).options(
#         joinedload(Station.charging_configs)
#     ).filter(Station.is_available == True)
    
#     stations = query.all()
    
#     if not stations:
#         raise HTTPException(
#             status_code=404,
#             detail="No matching charging stations found"
#         )
    
#     # Initialize OSRM optimizer
#     optimizer = OSRMRouteOptimizer(
#         stations=stations,
#         battery_range=settings.MAX_SEARCH_RADIUS,
#         osrm_server=settings.OSRM_SERVER_URL
#     )
    
#     try:
#         station, distance, route_info = optimizer.find_nearest_station(
#             latitude,
#             longitude,
#             filter_charging_type=charging_type,
#             filter_min_power=min_power
#         )
        
#         # Find matching charging config for response
#         matching_config = None
#         if charging_type or min_power:
#             for config in station.charging_configs:
#                 if ((charging_type is None or config.charging_type == charging_type) and
#                     (min_power is None or config.power_output >= min_power)):
#                     matching_config = config
#                     break
#         else:
#             # Use the first config if no specific filters
#             matching_config = station.charging_configs[0] if station.charging_configs else None
        
#         # return StationResponse(
#         #     id=station.id,
#         #     name=station.name,
#         #     latitude=station.latitude,
#         #     longitude=station.longitude,
#         #     charging_type=matching_config.charging_type if matching_config else None,
#         #     power_output=matching_config.power_output if matching_config else None,
#         #     cost_per_kwh=matching_config.cost_per_kwh if matching_config else None,
#         #     connector_type=matching_config.connector_type if matching_config else None,
#         #     is_available=station.is_available,
#         #     distance=round(distance, 2),
#         #     route_geometry=route_info.get("geometry") if route_info else None
#         # )
#         try:
#             return StationResponse(
#                 id=station.id,
#                 name=station.name,
#                 latitude=station.latitude,
#                 longitude=station.longitude,
#                 charging_type=matching_config.charging_type if matching_config else None,
#                 power_output=matching_config.power_output if matching_config else None,
#                 cost_per_kwh=matching_config.cost_per_kwh if matching_config else None,
#                 connector_type=matching_config.connector_type if matching_config else None,
#                 is_available=station.is_available,
#                 distance=round(distance, 2),
#                 route_geometry=route_info.get("geometry") if route_info else None
#             )
#         except Exception as e:
#             print("🔥 Response model error:", str(e))
#             raise HTTPException(status_code=500, detail="Response model failed")
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.get("/direct-route")
def get_direct_route(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    current_user: dict = Depends(get_current_user)
):
    """
    Get direct route between two points using OSRM
    """
    try:
        # Create temporary optimizer without stations just to use OSRM functionality
        route_optimizer = OSRMRouteOptimizer(
            stations=[],
            battery_range=settings.MAX_SEARCH_RADIUS,
            osrm_server=settings.OSRM_SERVER_URL
        )
        
        distance, route_info = route_optimizer.get_road_distance(
            start_lat, start_lon,
            end_lat, end_lon
        )
        
        return {
            "distance": round(distance, 2),
            "duration_minutes": round(route_info["duration"], 2),
            "geometry": route_info.get("geometry")
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get direct route: {str(e)}"
        )