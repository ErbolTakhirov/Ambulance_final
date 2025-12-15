"""
Traffic-Aware Routing Algorithm
Implements A* pathfinding with traffic-weighted edges for optimal route calculation
"""
import heapq
import math
from typing import Dict, List, Tuple, Optional
import requests
from datetime import datetime


class TrafficAwareRouter:
    """
    Router that finds optimal paths considering real-time traffic conditions
    """
    
    def __init__(self):
        # List of OSRM servers to try (Main + Backup + More alternatives)
        self.osrm_servers = [
            "http://router.project-osrm.org/route/v1/driving",
            "https://routing.openstreetmap.de/routed-car/route/v1/driving",
            "https://router.project-osrm.org/route/v1/driving",  # HTTPS version
        ]
        self.osrm_base_url = self.osrm_servers[0] # backward compatibility if needed
        self.timeout = 10  # Reduced timeout for faster failover
        self.max_retries = 1  # Only 1 retry per server for faster failover
    
    def calculate_optimal_route(
        self,
        start_lat: float,
        start_lng: float,
        end_lat: float,
        end_lng: float,
        traffic_data: List[Dict],
        alternatives: int = 3
    ) -> Dict:
        """
        Calculate optimal route considering traffic conditions
        
        Args:
            start_lat, start_lng: Starting coordinates
            end_lat, end_lng: Destination coordinates
            traffic_data: List of traffic conditions for streets
            alternatives: Number of alternative routes to calculate
        
        Returns:
            Dictionary with routes, each annotated with traffic-aware predictions
        """
        # Try to get base routes from OSRM
        try:
            base_routes = self._get_osrm_routes(
                start_lat, start_lng, end_lat, end_lng, alternatives
            )
            
            if not base_routes or 'routes' not in base_routes:
                raise Exception("Failed to get routes from OSRM")
            
            # Enhance each route with traffic-aware predictions
            enhanced_routes = []
            for idx, route in enumerate(base_routes['routes']):
                try:
                    enhanced_route = self._enhance_route_with_traffic(
                        route, traffic_data, idx == 0  # First route is primary
                    )
                    enhanced_routes.append(enhanced_route)
                except Exception as e:
                    print(f"Error enhancing route {idx}: {e}")
                    # Fallback: add original route with OSRM values
                    duration_mins = route['duration'] / 60
                    dist_km = route['distance'] / 1000
                    
                    route['traffic_aware_duration'] = route['duration']
                    route['traffic_aware_duration_minutes'] = duration_mins
                    route['min_time_minutes'] = duration_mins
                    route['max_time_minutes'] = duration_mins
                    route['confidence'] = 100.0
                    route['average_speed'] = (dist_km / (duration_mins/60)) if duration_mins > 0 else 50
                    route['average_congestion'] = 0
                    route['traffic_delay_minutes'] = 0
                    route['quality'] = 'good'
                    
                    enhanced_routes.append(route)
            
            # Sort routes by predicted time (accounting for traffic)
            enhanced_routes.sort(key=lambda r: r['traffic_aware_duration'])
            
            return {
                'code': 'Ok',
                'routes': enhanced_routes,
                'waypoints': base_routes.get('waypoints', [])
            }
            
        except Exception as e:
            print(f"Routing failed, trying alternatives: {e}")
            
            # Try GraphHopper as alternative
            try:
                from .graphhopper_router import get_graphhopper
                gh_router = get_graphhopper()
                gh_data = gh_router.get_route(start_lat, start_lng, end_lat, end_lng, alternatives)
                
                if gh_data and gh_data.get('routes'):
                    print("Using GraphHopper route")
                    # Enhance routes with traffic data
                    enhanced_routes = []
                    for idx, route in enumerate(gh_data['routes']):
                        try:
                            enhanced_route = self._enhance_route_with_traffic(
                                route, traffic_data, idx == 0
                            )
                            enhanced_routes.append(enhanced_route)
                        except Exception as enhance_error:
                            print(f"Error enhancing GraphHopper route: {enhance_error}")
                            enhanced_routes.append(route)
                    
                    return {
                        'code': 'Ok',
                        'routes': enhanced_routes,
                        'waypoints': gh_data.get('waypoints', [])
                    }
            except Exception as gh_error:
                print(f"GraphHopper also failed: {gh_error}")
            
            # Final fallback: street-based route
            return self._generate_fallback_route(start_lat, start_lng, end_lat, end_lng)

    def _generate_fallback_route(self, start_lat, start_lng, end_lat, end_lng):
        """Generate a route using A* on street network when OSRM is down"""
        try:
            # Load street network
            from .osm_loader import OSMStreetLoader
            from .street_graph_router import StreetGraphRouter
            
            streets = OSMStreetLoader.get_bishkek_streets()
            
            if streets and len(streets) > 0:
                print(f"Building route using A* on {len(streets)} streets")
                
                # Build graph and find route
                router = StreetGraphRouter(streets)
                route_coords = router.find_route(start_lat, start_lng, end_lat, end_lng)
                
                print(f"A* route found with {len(route_coords)} points")
            else:
                # Ultimate fallback: straight line
                route_coords = [[start_lng, start_lat], [end_lng, end_lat]]
                print("No streets available, using straight line")
        except Exception as e:
            print(f"A* routing failed: {e}, using straight line")
            import traceback
            traceback.print_exc()
            route_coords = [[start_lng, start_lat], [end_lng, end_lat]]
        
        # Calculate distance along route
        total_dist_km = 0
        for i in range(len(route_coords) - 1):
            lng1, lat1 = route_coords[i]
            lng2, lat2 = route_coords[i + 1]
            total_dist_km += self._haversine_distance(lat1, lng1, lat2, lng2)
        
        # Assume 30 km/h speed for city driving fallback
        speed_kmh = 30
        duration_hours = total_dist_km / speed_kmh
        duration_seconds = duration_hours * 3600
        duration_minutes = duration_hours * 60
        
        is_real_route = len(route_coords) > 2
        
        return {
            'code': 'Fallback',
            'routes': [{
                'geometry': {
                    'coordinates': route_coords,
                    'type': 'LineString'
                },
                'distance': total_dist_km * 1000,
                'duration': duration_seconds,
                'traffic_aware_duration': duration_seconds,
                'traffic_aware_duration_minutes': duration_minutes,
                'min_time_minutes': duration_minutes * 0.9,
                'max_time_minutes': duration_minutes * 1.5,
                'confidence': 70.0 if is_real_route else 0.0,
                'average_speed': speed_kmh,
                'average_congestion': 0,
                'quality': 'good' if is_real_route else 'unknown',
                'is_recommended': True,
                'warnings': ['OSRM unavailable' + (', using A* street routing' if is_real_route else ', showing direct line')]
            }],
            'waypoints': [
                {'name': 'Start', 'location': [start_lng, start_lat]},
                {'name': 'End', 'location': [end_lng, end_lat]}
            ]
        }
    
    def _build_street_route(self, start_lat, start_lng, end_lat, end_lng, streets):
        """DEPRECATED: Use StreetGraphRouter instead"""
        # This method is no longer used, kept for compatibility
        return [[start_lng, start_lat], [end_lng, end_lat]]
    
    def _find_nearest_street_point(self, lat, lng, streets):
        """DEPRECATED: Use StreetGraphRouter instead"""
        # This method is no longer used, kept for compatibility
        return None
    
    def _get_osrm_routes(
        self,
        start_lat: float,
        start_lng: float,
        end_lat: float,
        end_lng: float,
        alternatives: int
    ) -> Dict:
        """Get routes from OSRM API with failover and retry logic"""
        coords = f"{start_lng},{start_lat};{end_lng},{end_lat}"
        
        params = {
            'overview': 'full',
            'geometries': 'geojson',
            'alternatives': alternatives,
            'steps': 'true',
            'annotations': 'true'
        }
        
        headers = {
            'User-Agent': 'AmbulanceRouteOptimizer/1.0 (Educational Project)'
        }
        
        last_exception = None
        
        # Try each server with retries
        for base_url in self.osrm_servers:
            for attempt in range(self.max_retries):
                url = f"{base_url}/{coords}"
                try:
                    print(f"Requesting OSRM (attempt {attempt + 1}/{self.max_retries}): {url}")
                    response = requests.get(url, params=params, headers=headers, timeout=self.timeout)
                    print(f"OSRM Status: {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        print(f"OSRM Routes found: {len(data.get('routes', []))}")
                        return data
                    else:
                        print(f"OSRM Error on {base_url}: {response.text}")
                        last_exception = Exception(f"HTTP {response.status_code}: {response.text}")
                except Exception as e:
                    print(f"OSRM Connection Error on {base_url} (attempt {attempt + 1}): {e}")
                    last_exception = e
                    # Don't continue to next attempt if it's the last one
                    if attempt < self.max_retries - 1:
                        import time
                        time.sleep(1)  # Wait 1 second before retry
                    continue
                
                # If we got here and succeeded, break the retry loop
                break
        
        # If we get here, all servers failed
        raise Exception(f"All OSRM servers failed after {self.max_retries} retries. Last error: {str(last_exception)}")
    
    def _enhance_route_with_traffic(
        self,
        route: Dict,
        traffic_data: List[Dict],
        is_primary: bool
    ) -> Dict:
        """
        Enhance route with traffic-aware time predictions
        """
        from .ml_predictor import get_predictor
        
        # Get route geometry
        geometry = route.get('geometry', {})
        coordinates = geometry.get('coordinates', [])
        
        # Match route segments with traffic data
        matched_traffic = self._match_traffic_to_route(coordinates, traffic_data)
        
        # Calculate traffic-aware duration
        predictor = get_predictor()
        distance_km = route['distance'] / 1000
        
        prediction = predictor.predict_travel_time(
            distance_km=distance_km,
            traffic_conditions=matched_traffic,
            time_of_day=datetime.now()
        )
        
        # Calculate traffic delay
        base_duration = route['duration']  # seconds
        traffic_duration = prediction['predicted_time_seconds']
        traffic_delay = traffic_duration - base_duration
        
        # Determine route quality based on traffic
        quality = self._calculate_route_quality(
            matched_traffic,
            traffic_delay,
            distance_km
        )
        
        # Enhanced route object
        enhanced = {
            **route,
            'traffic_aware_duration': traffic_duration,
            'traffic_aware_duration_minutes': prediction['predicted_time_minutes'],
            'base_duration': base_duration,
            'base_duration_minutes': round(base_duration / 60, 1),
            'traffic_delay_seconds': max(0, traffic_delay),
            'traffic_delay_minutes': round(max(0, traffic_delay) / 60, 1),
            'min_time_minutes': prediction['min_time_minutes'],
            'max_time_minutes': prediction['max_time_minutes'],
            'confidence': prediction['confidence'],
            'average_speed': prediction['average_speed_kmh'],
            'average_congestion': prediction['average_congestion_percent'],
            'quality': quality,
            'is_recommended': is_primary and quality in ['excellent', 'good'],
            'traffic_segments': self._create_traffic_segments(matched_traffic),
            'prediction_breakdown': prediction['breakdown']
        }
        
        return enhanced
    
    def _match_traffic_to_route(
        self,
        route_coordinates: List[List[float]],
        traffic_data: List[Dict]
    ) -> List[Dict]:
        """
        Match traffic data to route segments
        Returns list of traffic conditions along the route
        """
        if not route_coordinates or not traffic_data:
            return []
        
        matched_traffic = []
        
        # Sample points along route (every ~500m)
        sample_points = self._sample_route_points(route_coordinates, interval_meters=500)
        
        for point in sample_points:
            # Find nearest traffic segment
            nearest_traffic = self._find_nearest_traffic(point, traffic_data)
            if nearest_traffic:
                matched_traffic.append(nearest_traffic)
        
        # If no matches, return default traffic
        if not matched_traffic:
            return [{
                'congestion_percentage': 20,
                'average_speed': 45,
                'traffic_level': 'light'
            }]
        
        return matched_traffic
    
    def _sample_route_points(
        self,
        coordinates: List[List[float]],
        interval_meters: float = 500
    ) -> List[Tuple[float, float]]:
        """Sample points along route at regular intervals"""
        if not coordinates:
            return []
        
        points = []
        total_distance = 0
        last_sample_distance = 0
        
        for i in range(len(coordinates) - 1):
            lon1, lat1 = coordinates[i]
            lon2, lat2 = coordinates[i + 1]
            
            segment_distance = self._haversine_distance(lat1, lon1, lat2, lon2) * 1000  # to meters
            total_distance += segment_distance
            
            # Sample if we've traveled enough distance
            if total_distance - last_sample_distance >= interval_meters:
                points.append((lat2, lon2))
                last_sample_distance = total_distance
        
        # Always include start and end
        if coordinates:
            points.insert(0, (coordinates[0][1], coordinates[0][0]))
            points.append((coordinates[-1][1], coordinates[-1][0]))
        
        return points
    
    def _find_nearest_traffic(
        self,
        point: Tuple[float, float],
        traffic_data: List[Dict],
        max_distance_km: float = 0.5
    ) -> Optional[Dict]:
        """Find nearest traffic segment to a point"""
        lat, lng = point
        nearest = None
        min_distance = float('inf')
        
        for traffic in traffic_data:
            # Calculate distance to traffic segment midpoint
            mid_lat = (traffic.get('start', [0, 0])[0] + traffic.get('end', [0, 0])[0]) / 2
            mid_lng = (traffic.get('start', [0, 0])[1] + traffic.get('end', [0, 0])[1]) / 2
            
            distance = self._haversine_distance(lat, lng, mid_lat, mid_lng)
            
            if distance < min_distance and distance <= max_distance_km:
                min_distance = distance
                nearest = traffic
        
        return nearest
    
    def _haversine_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points in kilometers"""
        R = 6371  # Earth radius in km
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) ** 2)
        
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def _calculate_route_quality(
        self,
        traffic_conditions: List[Dict],
        traffic_delay: float,
        distance_km: float
    ) -> str:
        """
        Calculate overall route quality
        Returns: 'excellent', 'good', 'fair', 'poor'
        """
        if not traffic_conditions:
            return 'good'
        
        avg_congestion = sum(t.get('congestion_percentage', 0) for t in traffic_conditions) / len(traffic_conditions)
        delay_per_km = traffic_delay / max(distance_km, 0.1) / 60  # minutes per km
        
        # Excellent: low congestion, minimal delay
        if avg_congestion < 25 and delay_per_km < 1:
            return 'excellent'
        # Good: moderate congestion, acceptable delay
        elif avg_congestion < 50 and delay_per_km < 2:
            return 'good'
        # Fair: higher congestion, noticeable delay
        elif avg_congestion < 75 and delay_per_km < 4:
            return 'fair'
        # Poor: heavy congestion, significant delay
        else:
            return 'poor'
    
    def _create_traffic_segments(self, traffic_conditions: List[Dict]) -> List[Dict]:
        """Create summary of traffic segments"""
        if not traffic_conditions:
            return []
        
        # Group consecutive similar traffic levels
        segments = []
        current_level = None
        current_count = 0
        
        for traffic in traffic_conditions:
            level = traffic.get('traffic_level', 'unknown')
            if level != current_level:
                if current_level is not None:
                    segments.append({
                        'level': current_level,
                        'count': current_count
                    })
                current_level = level
                current_count = 1
            else:
                current_count += 1
        
        # Add last segment
        if current_level is not None:
            segments.append({
                'level': current_level,
                'count': current_count
            })
        
        return segments


# Global router instance
_router_instance = None

def get_router() -> TrafficAwareRouter:
    """Get singleton router instance"""
    global _router_instance
    if _router_instance is None:
        _router_instance = TrafficAwareRouter()
    return _router_instance
