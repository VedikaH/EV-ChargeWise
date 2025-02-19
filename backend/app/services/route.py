import math
import heapq
from typing import List, Tuple
from app.models.stations import Station

class RouteOptimizer:
    def __init__(self, stations: List[Station], battery_range: float):
        """
        Initialize the route optimizer
        
        Args:
            stations: List of SQLAlchemy Station models
            battery_range: Maximum vehicle range in kilometers
        """
        self.stations = stations
        self.battery_range = battery_range

    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate the great circle distance between two points in kilometers"""
        R = 6371  # Earth's radius in kilometers
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat/2)**2 +
             math.cos(math.radians(lat1)) *
             math.cos(math.radians(lat2)) *
             math.sin(dlon/2)**2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    def find_nearby_stations(
        self, 
        current_lat: float, 
        current_lon: float, 
        max_range: float
    ) -> List[Tuple[Station, float]]:
        """Find all charging stations within the specified range"""
        nearby = []
        for station in self.stations:
            if not station.is_available:
                continue
                
            distance = self.haversine_distance(
                current_lat, current_lon,
                station.latitude, station.longitude
            )
            if distance <= max_range:
                nearby.append((station, distance))
        
        return sorted(nearby, key=lambda x: x[1])

    def dijkstra_route(
        self, 
        start_coords: Tuple[float, float], 
        end_coords: Tuple[float, float]
    ) -> List[Station]:
        """
        Find optimal route using Dijkstra's algorithm
        
        Args:
            start_coords: (latitude, longitude) of starting point
            end_coords: (latitude, longitude) of destination
        
        Returns:
            List of stations forming the optimal route
        
        Raises:
            ValueError: If no valid route can be found
        """
        available_stations = [s for s in self.stations if s.is_available]
        
        if not available_stations:
            raise ValueError("No available charging stations")
            
        # Find closest stations to start and end points
        start_station = min(
            available_stations,
            key=lambda s: self.haversine_distance(
                start_coords[0], start_coords[1],
                s.latitude, s.longitude
            )
        )
        
        end_station = min(
            available_stations,
            key=lambda s: self.haversine_distance(
                end_coords[0], end_coords[1],
                s.latitude, s.longitude
            )
        )

        # Initialize Dijkstra's algorithm data structures
        distances = {station: float('inf') for station in self.stations}
        distances[start_station] = 0
        previous = {station: None for station in self.stations}
        
        # Priority queue of (distance, station)
        pq = [(0, start_station)]
        
        while pq:
            current_distance, current = heapq.heappop(pq)
            
            if current == end_station:
                break
                
            if current_distance > distances[current]:
                continue
            
            # Check all possible next stations within range
            nearby = self.find_nearby_stations(
                current.latitude,
                current.longitude,
                self.battery_range
            )
            
            for next_station, distance in nearby:
                new_distance = current_distance + distance
                
                if new_distance < distances[next_station]:
                    distances[next_station] = new_distance
                    previous[next_station] = current
                    heapq.heappush(pq, (new_distance, next_station))
        
        if distances[end_station] == float('inf'):
            raise ValueError("No valid route found between start and end points")
            
        # Reconstruct path
        path = []
        current = end_station
        while current:
            path.append(current)
            current = previous[current]
            
        return list(reversed(path))

    # def get_route_summary(self, route: List[Station]) -> dict:
    #     """
    #     Generate a summary of the route including distances and charging details
        
    #     Args:
    #         route: List of stations in the route
            
    #     Returns:
    #         Dictionary containing route summary information
    #     """
    #     total_distance = 0
    #     segments = []
        
    #     for i in range(len(route) - 1):
    #         current = route[i]
    #         next_station = route[i + 1]
            
    #         distance = self.haversine_distance(
    #             current.latitude, current.longitude,
    #             next_station.latitude, next_station.longitude
    #         )
            
    #         segments.append({
    #             'from_station': {
    #                 'id': current.id,
    #                 'name': current.name,
    #                 'charging_type': current.charging_type,
    #                 'power_output': current.power_output
    #             },
    #             'to_station': {
    #                 'id': next_station.id,
    #                 'name': next_station.name,
    #                 'charging_type': next_station.charging_type,
    #                 'power_output': next_station.power_output
    #             },
    #             'distance': round(distance, 2)
    #         })
            
    #         total_distance += distance
            
    #     return {
    #         'total_distance': round(total_distance, 2),
    #         'number_of_stops': len(route),
    #         'route_segments': segments
    #     }
    def get_route_summary(
        self, 
        route: List[Station], 
        start_coords: Tuple[float, float],
        end_coords: Tuple[float, float]
    ) -> dict:
        """
        Generate a summary of the route including distances and charging details
        
        Args:
            route: List of stations in the route
            start_coords: (latitude, longitude) of starting point
            end_coords: (latitude, longitude) of destination
            
        Returns:
            Dictionary containing route summary information
        """
        segments = []
        
        # Add segment from start point to first station
        first_station = route[0]
        initial_distance = self.haversine_distance(
            start_coords[0], start_coords[1],
            first_station.latitude, first_station.longitude
        )
        
        segments.append({
            'segment_type': 'start_to_station',
            'from_point': {
                'latitude': start_coords[0],
                'longitude': start_coords[1]
            },
            'to_station': {
                'id': first_station.id,
                'name': first_station.name,
                'charging_type': first_station.charging_type,
                'power_output': first_station.power_output
            },
            'distance': round(initial_distance, 2)
        })
        
        # Add segments between stations
        for i in range(len(route) - 1):
            current = route[i]
            next_station = route[i + 1]
            
            distance = self.haversine_distance(
                current.latitude, current.longitude,
                next_station.latitude, next_station.longitude
            )
            
            segments.append({
                'segment_type': 'station_to_station',
                'from_station': {
                    'id': current.id,
                    'name': current.name,
                    'charging_type': current.charging_type,
                    'power_output': current.power_output
                },
                'to_station': {
                    'id': next_station.id,
                    'name': next_station.name,
                    'charging_type': next_station.charging_type,
                    'power_output': next_station.power_output
                },
                'distance': round(distance, 2)
            })
        
        # Add final segment from last station to destination
        last_station = route[-1]
        final_distance = self.haversine_distance(
            last_station.latitude, last_station.longitude,
            end_coords[0], end_coords[1]
        )
        
        segments.append({
            'segment_type': 'station_to_destination',
            'from_station': {
                'id': last_station.id,
                'name': last_station.name,
                'charging_type': last_station.charging_type,
                'power_output': last_station.power_output
            },
            'to_point': {
                'latitude': end_coords[0],
                'longitude': end_coords[1]
            },
            'distance': round(final_distance, 2)
        })
        print(final_distance)
        print(last_station)
        
        # Calculate total direct distance between start and end points
        total_direct_distance = self.haversine_distance(
            start_coords[0], start_coords[1],
            end_coords[0], end_coords[1]
        )
        
        return {
            'total_distance': round(total_direct_distance, 2),
            'number_of_stops': len(route),
            'route_segments': segments
        }