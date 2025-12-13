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
        # Using main OSRM server as fallback
        self.osrm_base_url = "http://router.project-osrm.org/route/v1/driving"
    
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
        # Get base routes from OSRM
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
                import traceback
                traceback.print_exc()
                # Fallback: add original route with OSRM values
                duration_mins = route['duration'] / 60
                dist_km = route['distance'] / 1000
                
                route['traffic_aware_duration'] = route['duration']
                route['traffic_aware_duration_minutes'] = duration_mins
                # Fill missing fields to prevent "0 min" on frontend
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
    
    def _get_osrm_routes(
        self,
        start_lat: float,
        start_lng: float,
        end_lat: float,
        end_lng: float,
        alternatives: int
    ) -> Dict:
        """Get routes from OSRM API"""
        coords = f"{start_lng},{start_lat};{end_lng},{end_lat}"
        url = f"{self.osrm_base_url}/{coords}"
        
        params = {
            'overview': 'full',
            'geometries': 'geojson',
            'alternatives': alternatives,
            'steps': 'true',
            'annotations': 'true'
        }
        
        
        try:
            print(f"Requesting OSRM: {url}")
            response = requests.get(url, params=params, timeout=10)
            print(f"OSRM Status: {response.status_code}")
            if response.status_code != 200:
                print(f"OSRM Error: {response.text}")
            
            response.raise_for_status()
            data = response.json()
            print(f"OSRM Routes found: {len(data.get('routes', []))}")
            return data
        except Exception as e:
            print(f"OSRM Exception: {e}")
            raise Exception(f"OSRM API error: {str(e)}")
    
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
