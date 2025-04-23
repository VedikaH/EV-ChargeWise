from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

class StationBase(BaseModel):
    name: str
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    charging_type: Optional[str] = None
    power_output: Optional[float] = None
    is_available: bool = True

class ChargingConfigResponse(BaseModel):
    charging_type: str
    connector_type: str
    power_output: float
    cost_per_kwh: float

    class Config:
        orm_mode = True

class StationCreate(BaseModel):
    name: str
    latitude: float
    longitude: float
    is_available: bool
    charging_configs: Optional[List[ChargingConfigResponse]] = None


class StationResponse(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float
    is_available: bool
    distance_to_next: Optional[float] = None
    distance_from_previous: Optional[float] = None
    distance_from_start: Optional[float] = None
    distance_to_destination: Optional[float] = None
    charging_configs: List[ChargingConfigResponse]
    route_geometry: Optional[dict] = None

class StationCreateResponse(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float
    is_available: bool
    message: str

class StationSearchRequest(BaseModel):
    latitude: float
    longitude: float
    radius: float = 10.0
    charging_type: Optional[str] = None
    power_output: Optional[float] = None

class RouteOptimizationRequest(BaseModel):
    start_latitude: float = Field(..., ge=-90, le=90)
    start_longitude: float = Field(..., ge=-180, le=180)
    end_latitude: float = Field(..., ge=-90, le=90)
    end_longitude: float = Field(..., ge=-180, le=180)

class RouteResponse(BaseModel):
    charging_stations: List[StationResponse]
    total_distance: float
    total_duration: float
    number_of_stops: int
    estimated_charging_time: float
    total_trip_time: float
    route_segments: List[Dict[str, Any]] 

    class Config:
        schema_extra = {
            "example": {
                "charging_stations": [
                    {
                        "id": 1,
                        "name": "Charging Station A",
                        "latitude": 17.385044,
                        "longitude": 78.486671,
                        "charging_type": "DC",
                        "power_output": 50,
                        "is_available": True,
                        "distance_from_start": 2.5,
                        "distance_to_next": 5.2
                    }
                ],
                "total_distance": 25.6,
                "total_duration": 45.3,
                "number_of_stops": 2,
                "estimated_charging_time": 60.0,
                "total_trip_time": 105.3,
                "route_segments": [
                    {
                        "segment_type": "start_to_station",
                        "distance": 2.5,
                        "duration": 5.2,
                        "geometry": "..." # GeoJSON for this segment 
                    }
                ]
            }
        }