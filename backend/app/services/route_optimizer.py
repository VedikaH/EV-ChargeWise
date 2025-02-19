import math
from typing import List, Tuple
from backend.app.models.stations import Station

class RouteOptimizer:
    def __init__(self, stations: List[Station], vehicle_range: float):
        self.stations = stations
        self.vehicle_range = vehicle_range  # Maximum vehicle range in kilometers

    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371  # Earth's radius in kilometers
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat/2)**2 + 
             math.cos(math.radians(lat1)) * 
             math.cos(math.radians(lat2)) * 
             math.sin(dlon/2)**2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    def optimize_route(
        self, 
        start_coords: Tuple[float, float], 
        end_coords: Tuple[float, float]
    ) -> List[Station]:
        """
        Optimize route considering charging station availability
        
        :param start_coords: (latitude, longitude) of starting point
        :param end_coords: (latitude, longitude) of destination
        :return: Optimized list of charging stations
        """
        def find_reachable_stations(current_location):
            return [
                station for station in self.stations 
                if self.haversine_distance(
                    current_location[0], current_location[1], 
                    station.latitude, station.longitude
                ) <= self.vehicle_range and station.is_available
            ]

        route = []
        current_location = start_coords
        remaining_distance = self.haversine_distance(
            start_coords[0], start_coords[1], 
            end_coords[0], end_coords[1]
        )

        while remaining_distance > self.vehicle_range:
            reachable_stations = find_reachable_stations(current_location)
            
            if not reachable_stations:
                raise ValueError("No reachable charging stations")
            
            # Select station closest to route direction
            next_station = min(
                reachable_stations, 
                key=lambda station: self.haversine_distance(
                    station.latitude, station.longitude, 
                    end_coords[0], end_coords[1]
                )
            )
            
            route.append(next_station)
            current_location = (next_station.latitude, next_station.longitude)
            
            remaining_distance = self.haversine_distance(
                current_location[0], current_location[1], 
                end_coords[0], end_coords[1]
            )

        return route