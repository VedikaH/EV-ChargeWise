import math
import heapq
import requests
import numpy as np
from typing import List, Tuple, Dict, Any
from sklearn.neighbors import BallTree
from app.models.stations import Station

class OSRMRouteOptimizer:
    def __init__(self, stations: List[Station], battery_range: float, osrm_server: str = None):
        """
        Initialize the route optimizer using OSRM for real-world routing
        
        Args:
            stations: List of SQLAlchemy Station models
            battery_range: Maximum vehicle range in kilometers
            osrm_server: OSRM API endpoint (defaults to public server)
        """
        self.stations = stations
        self.battery_range = battery_range
        self.osrm_server = osrm_server or "http://router.project-osrm.org"
        
        # Create a dictionary of station coordinates for quick lookup
        self.station_coords = {
            station: (station.latitude, station.longitude) 
            for station in stations
        }
        
        # Pre-compute distances between nearby stations to avoid repeated API calls
        self.distance_cache = {}
        
        # Build spatial index for quick lookup
        self._build_spatial_index()
    
    def _build_spatial_index(self):
        """Build a spatial index for quick station lookups"""
        self.available_stations = [s for s in self.stations if s.is_available]
        
        if not self.available_stations:
            self.station_coords_array = np.array([])
            self.spatial_index = None
            return
            
        # Store coordinates in radians for the BallTree
        self.station_coords_array = np.radians(
            np.array([[s.latitude, s.longitude] for s in self.available_stations])
        )
        
        # Create a BallTree for efficient nearest neighbor queries
        self.spatial_index = BallTree(self.station_coords_array, metric='haversine')
        
    def refresh_spatial_index(self):
        """Refresh the spatial index if stations have changed"""
        self._build_spatial_index()
    
    def get_road_distance(self, start_lat: float, start_lon: float, 
                          end_lat: float, end_lon: float) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate the real road distance between two points using OSRM API
        
        Args:
            start_lat: Starting point latitude
            start_lon: Starting point longitude
            end_lat: Ending point latitude
            end_lon: Ending point longitude
            
        Returns:
            Tuple containing distance in kilometers and route details
        """
        # Check cache first
        cache_key = (start_lat, start_lon, end_lat, end_lon)
        if cache_key in self.distance_cache:
            return self.distance_cache[cache_key]
        
        # Format the API request URL
        url = f"{self.osrm_server}/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}"
        params = {
            "overview": "full", 
            "geometries": "geojson",
            "steps": "true"
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if data["code"] != "Ok":
                # Fallback to haversine if OSRM fails
                distance = self.haversine_distance(start_lat, start_lon, end_lat, end_lon)
                route_info = {"geometry": None, "duration": distance * 1.5}  # Rough estimate
                return distance, route_info
            
            # Distance is returned in meters, convert to kilometers
            distance = data["routes"][0]["distance"] / 1000
            route_info = {
                "geometry": data["routes"][0]["geometry"],
                "duration": data["routes"][0]["duration"] / 60,  # Convert to minutes
                "steps": data["routes"][0]["legs"][0]["steps"]
            }
            
            # Cache the result to avoid repeated API calls
            self.distance_cache[cache_key] = (distance, route_info)
            return distance, route_info
            
        except Exception as e:
            # Fallback to haversine if API call fails
            print(f"OSRM API error: {e}. Falling back to haversine distance.")
            distance = self.haversine_distance(start_lat, start_lon, end_lat, end_lon)
            route_info = {"geometry": None, "duration": distance * 1.5}  # Rough estimate
            return distance, route_info

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
    ) -> List[Tuple[Station, float, Dict]]:
        """
        Find all charging stations within the specified range using spatial indexing and OSRM Table API
        
        Args:
            current_lat: Current position latitude
            current_lon: Current position longitude
            max_range: Maximum range in kilometers
            
        Returns:
            List of tuples containing (station, distance, route_info)
        """
        if not self.available_stations:
            return []
            
        if self.spatial_index is None:
            self.refresh_spatial_index()
            if self.spatial_index is None:  # Still None after refresh
                return []
        
        # Step 1: Use spatial index to pre-filter stations
        # Convert km to radians for BallTree query (Earth radius = 6371 km)
        search_radius_rad = max_range / 6371.0
        
        # Query the BallTree for stations within radius
        current_point = np.radians([[current_lat, current_lon]])
        indices = self.spatial_index.query_radius(current_point, search_radius_rad)[0]
        
        # No stations found within range
        if len(indices) == 0:
            return []
            
        # Get the candidate stations from the indices
        candidate_stations = [self.available_stations[i] for i in indices]
        
        # If only a few stations, use the direct approach
        if len(candidate_stations) <= 5:
            return self._direct_distance_calculation(current_lat, current_lon, candidate_stations, max_range)
        
        # Step 2: Use OSRM Table API for batch distance calculation
        return self._table_distance_calculation(current_lat, current_lon, candidate_stations, max_range)
    
    def _direct_distance_calculation(
        self,
        current_lat: float,
        current_lon: float,
        candidate_stations: List[Station],
        max_range: float
    ) -> List[Tuple[Station, float, Dict]]:
        """Calculate distances directly for a small number of stations"""
        nearby = []
        
        for station in candidate_stations:
            road_distance, route_info = self.get_road_distance(
                current_lat, current_lon,
                station.latitude, station.longitude
            )
            
            if road_distance <= max_range:
                nearby.append((station, road_distance, route_info))
        
        return sorted(nearby, key=lambda x: x[1])
    
    def _table_distance_calculation(
        self,
        current_lat: float,
        current_lon: float,
        candidate_stations: List[Station],
        max_range: float
    ) -> List[Tuple[Station, float, Dict]]:
        """Use OSRM Table API for batch distance calculation"""
        # Build coordinates string for the Table API
        # Format: lon1,lat1;lon2,lat2;...
        source_coords = f"{current_lon},{current_lat}"
        destination_coords = ";".join([
            f"{station.longitude},{station.latitude}" 
            for station in candidate_stations
        ])
        
        url = f"{self.osrm_server}/table/v1/driving/{source_coords};{destination_coords}"
        params = {
            "sources": "0",  # Index of source point (current location)
            "destinations": ";".join([str(i+1) for i in range(len(candidate_stations))]),
            "annotations": "distance"
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if data["code"] != "Ok":
                # Fallback to direct calculation if API fails
                return self._direct_distance_calculation(current_lat, current_lon, candidate_stations, max_range)
            
            nearby = []
            distances = data["distances"][0]  # Road distances in meters
            
            for i, station in enumerate(candidate_stations):
                distance_km = distances[i] / 1000  # Convert meters to kilometers
                
                if distance_km <= max_range:
                    # We only have distance from the Table API, get detailed route info separately
                    _, route_info = self.get_road_distance(
                        current_lat, current_lon,
                        station.latitude, station.longitude
                    )
                    nearby.append((station, distance_km, route_info))
            
            return sorted(nearby, key=lambda x: x[1])
            
        except Exception as e:
            print(f"OSRM Table API error: {e}. Falling back to direct calculation.")
            return self._direct_distance_calculation(current_lat, current_lon, candidate_stations, max_range)
    
    def find_nearest_station(
        self,
        lat: float,
        lon: float,
        filter_charging_type: str = None,
        filter_min_power: float = None
    ) -> Tuple[Station, float, Dict]:
        """
        Find the nearest available charging station using spatial indexing
        
        Args:
            lat: Latitude of the position
            lon: Longitude of the position
            filter_charging_type: Optional filter for charging type (e.g., 'DC', 'AC')
            filter_min_power: Optional minimum power output in kW
            
        Returns:
            Tuple of (station, distance, route_info)
            
        Raises:
            ValueError: If no station meets the criteria
        """
        # First filter stations by availability
        available_stations = [s for s in self.stations if s.is_available and not s.is_maintenance]
        
        if not available_stations:
            raise ValueError("No available stations found")
        
        # Then filter by charging configurations if specified
        if filter_charging_type is not None or filter_min_power is not None:
            filtered_stations = []
            
            for station in available_stations:
                # Check if any charging config meets the criteria
                matching_configs = [
                    config for config in station.charging_configs
                    if (filter_charging_type is None or config.charging_type == filter_charging_type) and
                       (filter_min_power is None or config.power_output >= filter_min_power)
                ]
                
                if matching_configs:
                    filtered_stations.append(station)
        else:
            filtered_stations = available_stations
            
        if not filtered_stations:
            raise ValueError(
                f"No available stations match the criteria: "
                f"charging_type={filter_charging_type}, min_power={filter_min_power}"
            )
            
        # Build a temporary spatial index for the filtered stations
        if len(filtered_stations) > 1:
            station_coords = np.radians(
                np.array([[s.latitude, s.longitude] for s in filtered_stations])
            )
            
            tree = BallTree(station_coords, metric='haversine')
            
            # Find nearest station by haversine distance
            query_point = np.radians([[lat, lon]])
            distances, indices = tree.query(query_point, k=min(5, len(filtered_stations)))
            
            # Get the top 5 (or fewer) stations to check road distance
            top_candidates = [(filtered_stations[i], d * 6371.0) for i, d in zip(indices[0], distances[0])]
        else:
            # Only one station, no need for spatial index
            station = filtered_stations[0]
            distance = self.haversine_distance(lat, lon, station.latitude, station.longitude)
            top_candidates = [(station, distance)]
        
        # Get road distances for top candidates
        result = []
        for station, _ in top_candidates:
            road_distance, route_info = self.get_road_distance(
                lat, lon, station.latitude, station.longitude
            )
            result.append((station, road_distance, route_info))
        
        # Return the station with the shortest road distance
        return min(result, key=lambda x: x[1])

    # def _find_nearby_stations_fallback(
    #     self,
    #     current_lat: float, 
    #     current_lon: float, 
    #     max_range: float
    # ) -> List[Tuple[Station, float, Dict]]:
    #     """Fallback method using the original implementation"""
    #     # Original implementation as fallback
    #     potential_stations = []
    #     for station in self.stations:
    #         if not station.is_available:
    #             continue
                
    #         aerial_distance = self.haversine_distance(
    #             current_lat, current_lon,
    #             station.latitude, station.longitude
    #         )
            
    #         if aerial_distance <= max_range * 1.5:
    #             potential_stations.append(station)
        
    #     nearby = []
    #     for station in potential_stations:
    #         road_distance, route_info = self.get_road_distance(
    #             current_lat, current_lon,
    #             station.latitude, station.longitude
    #         )
            
    #         if road_distance <= max_range:
    #             nearby.append((station, road_distance, route_info))
        
    #     return sorted(nearby, key=lambda x: x[1])

        
    # def _find_nearest_station_fallback(
    #     self, 
    #     lat: float,
    #     lon: float,
    #     filter_charging_type: str = None,
    #     filter_min_power: float = None
    # ) -> Tuple[Station, float, Dict]:
    #     """Fallback method using the original implementation"""
    #     # Filter available stations
    #     available_stations = [s for s in self.stations if s.is_available and not s.is_maintenance]
        
    #     # Then filter by charging configurations if specified
    #     if filter_charging_type is not None or filter_min_power is not None:
    #         filtered_stations = []
            
    #         for station in available_stations:
    #             # Check if any charging config meets the criteria
    #             matching_configs = [
    #                 config for config in station.charging_configs
    #                 if (filter_charging_type is None or config.charging_type == filter_charging_type) and
    #                    (filter_min_power is None or config.power_output >= filter_min_power)
    #             ]
                
    #             if matching_configs:
    #                 filtered_stations.append(station)
    #     else:
    #         filtered_stations = available_stations
        
    #     if not filtered_stations:
    #         raise ValueError(
    #             f"No available stations match the criteria: "
    #             f"charging_type={filter_charging_type}, min_power={filter_min_power}"
    #         )
        
    #     candidates = []
    #     for station in filtered_stations:
    #         aerial_distance = self.haversine_distance(
    #             lat, lon, station.latitude, station.longitude
    #         )
    #         candidates.append((station, aerial_distance))
        
    #     candidates.sort(key=lambda x: x[1])
        
    #     top_candidates = candidates[:5]
    #     result = []
    #     for station, _ in top_candidates:
    #         road_distance, route_info = self.get_road_distance(
    #             lat, lon, station.latitude, station.longitude
    #         )
    #         result.append((station, road_distance, route_info))
        
    #     return min(result, key=lambda x: x[1])

    

    def dijkstra_route(
        self, 
        start_coords: Tuple[float, float], 
        end_coords: Tuple[float, float]
    ) -> List[Tuple[Station, Dict]]:
        """
        Find optimal route using Dijkstra's algorithm with actual road distances
        
        Args:
            start_coords: (latitude, longitude) of starting point
            end_coords: (latitude, longitude) of destination
        
        Returns:
            List of tuples containing (station, route_info) forming the optimal route
        
        Raises:
            ValueError: If no valid route can be found
        """
        available_stations = [s for s in self.stations if s.is_available]
        
        if not available_stations:
            raise ValueError("No available charging stations")
        
        # Find closest stations to start and end points
        start_station, start_distance, _ = self.find_nearest_station(
            start_coords[0], start_coords[1]
        )
        
        end_station, end_distance, _ = self.find_nearest_station(
            end_coords[0], end_coords[1]
        )
            
        # Initialize Dijkstra's algorithm data structures
        distances = {station: float('inf') for station in self.stations}
        distances[start_station] = 0
        previous = {station: None for station in self.stations}
        route_info = {station: None for station in self.stations}
        
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
            
            for next_station, distance, info in nearby:
                new_distance = current_distance + distance
                
                if new_distance < distances[next_station]:
                    distances[next_station] = new_distance
                    previous[next_station] = current
                    route_info[next_station] = info
                    heapq.heappush(pq, (new_distance, next_station))
        
        if distances[end_station] == float('inf'):
            raise ValueError("No valid route found between start and end points")
            
        # Reconstruct path with route information
        path = []
        current = end_station
        while current:
            if current != start_station:  # Skip adding route info for the starting point
                path.append((current, route_info[current]))
            current = previous[current]
            
        # Reverse to get path from start to end
        path.reverse()
        
        return path

    def get_route_summary(
        self, 
        route: List[Tuple[Station, Dict]], 
        start_coords: Tuple[float, float],
        end_coords: Tuple[float, float]
    ) -> dict:
        """
        Generate a summary of the route including real road distances and charging details
        
        Args:
            route: List of (station, route_info) tuples in the route
            start_coords: (latitude, longitude) of starting point
            end_coords: (latitude, longitude) of destination
            
        Returns:
            Dictionary containing route summary information
        """
        segments = []
        total_distance = 0
        total_time = 0
        
        # Add segment from start point to first station
        first_station, first_route_info = route[0]
        initial_distance, initial_route_info = self.get_road_distance(
            start_coords[0], start_coords[1],
            first_station.latitude, first_station.longitude
        )
        
        total_distance += initial_distance
        total_time += initial_route_info["duration"]
        
        segments.append({
        'segment_type': 'start_to_station',
        'from_point': {
            'latitude': start_coords[0],
            'longitude': start_coords[1]
        },
        'to_station': {
            'id': first_station.id,
            'name': first_station.name,
            'charging_configs': [
                {
                    'charging_type': config.charging_type,
                    'connector_type': config.connector_type,
                    'power_output': config.power_output,
                    'cost_per_kwh': config.cost_per_kwh
                }
                for config in first_station.charging_configs
            ]
        },
        'distance': round(initial_distance, 2),
        'duration': round(initial_route_info["duration"], 2),
        'route_geometry': initial_route_info["geometry"]
    })
        
        # Add segments between stations
        for i in range(len(route) - 1):
            current_station, _ = route[i]
            next_station, next_route_info = route[i + 1]
            
            distance, route_info = self.get_road_distance(
                current_station.latitude, current_station.longitude,
                next_station.latitude, next_station.longitude
            )
            
            total_distance += distance
            total_time += route_info["duration"]
            
            segments.append({
            'segment_type': 'station_to_station',
            'from_station': {
                'id': current_station.id,
                'name': current_station.name,
                'charging_configs': [
                    {
                        'charging_type': config.charging_type,
                        'connector_type': config.connector_type,
                        'power_output': config.power_output,
                        'cost_per_kwh': config.cost_per_kwh
                    }
                    for config in current_station.charging_configs
                ]
            },
            'to_station': {
                'id': next_station.id,
                'name': next_station.name,
                'charging_configs': [
                    {
                        'charging_type': config.charging_type,
                        'connector_type': config.connector_type,
                        'power_output': config.power_output,
                        'cost_per_kwh': config.cost_per_kwh
                    }
                    for config in next_station.charging_configs
                ]
            },
            'distance': round(distance, 2),
            'duration': round(route_info["duration"], 2),
            'route_geometry': route_info["geometry"]
        })
        
        # Add final segment from last station to destination
        last_station, _ = route[-1]
        final_distance, final_route_info = self.get_road_distance(
            last_station.latitude, last_station.longitude,
            end_coords[0], end_coords[1]
        )
        
        total_distance += final_distance
        total_time += final_route_info["duration"]
        
        segments.append({
            'segment_type': 'station_to_destination',
            'from_station': {
                'id': last_station.id,
                'name': last_station.name,
                'charging_configs': [
                {
                    'charging_type': config.charging_type,
                    'connector_type': config.connector_type,
                    'power_output': config.power_output,
                    'cost_per_kwh': config.cost_per_kwh
                }
                for config in last_station.charging_configs
            ]
        },
            'to_point': {
                'latitude': end_coords[0],
                'longitude': end_coords[1]
            },
            'distance': round(final_distance, 2),
            'duration': round(final_route_info["duration"], 2),
            'route_geometry': final_route_info["geometry"]
        })
        
        # Get direct distance and time between start and end for comparison
        direct_distance, direct_route_info = self.get_road_distance(
            start_coords[0], start_coords[1],
            end_coords[0], end_coords[1]
        )
        
        charging_time_estimate = 0
        for station, _ in route:
            # Rough estimate: 30 minutes for charging at each station
            # In a real app, you'd calculate based on battery level, charging rate, etc.
            charging_time_estimate += 30
        
        return {
            'total_distance': round(total_distance, 2),
            'total_duration_minutes': round(total_time, 2),
            'direct_distance': round(direct_distance, 2),
            'direct_duration_minutes': round(direct_route_info["duration"], 2),
            'distance_overhead_percent': round(((total_distance - direct_distance) / direct_distance) * 100, 2),
            'time_overhead_percent': round(((total_time - direct_route_info["duration"]) / direct_route_info["duration"]) * 100, 2),
            'number_of_stops': len(route),
            'estimated_charging_time_minutes': charging_time_estimate,
            'total_trip_time_minutes': round(total_time + charging_time_estimate, 2),
            'route_segments': segments
        }