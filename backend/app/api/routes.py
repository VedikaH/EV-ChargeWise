import traceback
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, Field
from app.core.config import Settings,settings
from app.database.session import get_db
from app.models.stations import Station
from app.schemas.stations import RouteOptimizationRequest, RouteResponse, StationResponse
from app.services.route import RouteOptimizer


router = APIRouter()

@router.post("/optimize", response_model=RouteResponse)
def optimize_route(
    route_request: RouteOptimizationRequest,
    db: Session = Depends(get_db)
):
    """
    Optimize a route between two points with charging stations
    """
    # Fetch all available stations
    stations = db.query(Station).filter(Station.is_available == True).all()
    
    if not stations:
        raise HTTPException(
            status_code=404,
            detail="No available charging stations found"
        )
    
    try:
        route_optimizer = RouteOptimizer(
            stations=stations,
            battery_range=settings.MAX_SEARCH_RADIUS
        )
        
        # Get optimized route using Dijkstra's algorithm
        optimized_route = route_optimizer.dijkstra_route(
            start_coords=(route_request.start_latitude, route_request.start_longitude),
            end_coords=(route_request.end_latitude, route_request.end_longitude)
        )
        if not optimized_route:
            raise HTTPException(status_code=404, detail="No optimized route found")
        
        # Get detailed route summary
        route_summary = route_optimizer.get_route_summary(optimized_route,start_coords=(route_request.start_latitude, route_request.start_longitude),end_coords=(route_request.end_latitude, route_request.end_longitude))
        
        # Prepare response with station details and distances
        station_responses = []
        segments = route_summary['route_segments']

        for i, station in enumerate(optimized_route):
            station_response = StationResponse(
                id=station.id,
                name=station.name,
                latitude=station.latitude,
                longitude=station.longitude,
                charging_type=station.charging_type,
                power_output=station.power_output,
                distance_to_next=None  # Will be updated below
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
                # Middle stations - use distance from station_to_station segment
                segment_index = i + 1  # Account for initial start_to_station segment
                station_response.distance_to_next = segments[segment_index]['distance']
            
            station_responses.append(station_response)

        return RouteResponse(
            charging_stations=station_responses,
            total_distance=route_summary['total_distance'],
            number_of_stops=route_summary['number_of_stops'],
            route_segments=[{
                'segment_type': segment['segment_type'],
                'distance': segment['distance']
            } for segment in segments]
        )
        
    # except ValueError as e:
    #     raise HTTPException(status_code=400, detail=str(e))
    # except Exception as e:
    #     raise HTTPException(
    #         status_code=500,
    #         detail=str(e)
    #     )
    except Exception as e:
    # Log the full exception details, including traceback, error message, etc.
        error_details = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "stack_trace": traceback.format_exc()
        }
        
        # Print the error details for debugging
        print(error_details)

    # Raise the HTTPException with detailed information
    # raise HTTPException(
    #     status_code=500,
    #     detail=f"An error occurred: {str(e)}"
    # )