from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class StationBase(BaseModel):
    name: str
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    charging_type: Optional[str] = None
    power_output: Optional[float] = None
    is_available: bool = True

class StationCreate(StationBase):
    pass

class StationResponse(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float
    charging_type: str
    power_output: Optional[float] = None
    is_available: Optional[bool] = True
    distance: Optional[float] = None
    distance_to_next: Optional[float] = None
    distance_from_start: Optional[float] = None,
    distance_to_destination: Optional[float] = None,
    admin_ids: Optional[List[int]] = None  # Added to show managing admins


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
    number_of_stops: int
    route_segments: List[dict]