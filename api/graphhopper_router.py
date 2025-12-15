"""
Alternative routing service using GraphHopper API
Provides backup routing when OSRM is unavailable
"""
import requests
from typing import Dict, Optional


class GraphHopperRouter:
    """
    GraphHopper routing service as alternative to OSRM
    Free tier: 500 requests/day
    """
    
    def __init__(self):
        self.base_url = "https://graphhopper.com/api/1/route"
        # Using demo API key - replace with your own for production
        self.api_key = "8984bbb7-a75b-4231-a098-a3274d2b40d1"  # Get free key at graphhopper.com
        self.timeout = 30
    
    def get_route(
        self,
        start_lat: float,
        start_lng: float,
        end_lat: float,
        end_lng: float,
        alternatives: int = 3
    ) -> Optional[Dict]:
        """
        Get route from GraphHopper API
        
        Returns:
            Dict with OSRM-compatible format or None if failed
        """
        # Check if API key is configured
        if not self.api_key or self.api_key == "YOUR_API_KEY_HERE" or len(self.api_key) < 10:
            print("⚠️ GraphHopper API key not configured, skipping")
            return None
        
        params = {
            'point': [f"{start_lat},{start_lng}", f"{end_lat},{end_lng}"],
            'vehicle': 'car',
            'locale': 'ru',
            'key': self.api_key,
            'points_encoded': False,
            'algorithm': 'alternative_route',
            'alternative_route.max_paths': alternatives
        }
        
        try:
            print(f"🚀 Requesting GraphHopper route (key: {self.api_key[:8]}...)")
            response = requests.get(self.base_url, params=params, timeout=self.timeout)
            print(f"📡 GraphHopper response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                routes_count = len(data.get('paths', []))
                print(f"✅ GraphHopper success! Found {routes_count} route(s)")
                return self._convert_to_osrm_format(data)
            else:
                print(f"❌ GraphHopper error: {response.status_code}")
                print(f"Response: {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"❌ GraphHopper request failed: {e}")
            return None
    
    def _convert_to_osrm_format(self, graphhopper_data: Dict) -> Dict:
        """Convert GraphHopper response to OSRM-compatible format"""
        routes = []
        
        for path in graphhopper_data.get('paths', []):
            # Extract coordinates
            coordinates = []
            for point in path.get('points', {}).get('coordinates', []):
                coordinates.append(point)  # [lng, lat] format
            
            route = {
                'geometry': {
                    'coordinates': coordinates,
                    'type': 'LineString'
                },
                'distance': path.get('distance', 0),  # meters
                'duration': path.get('time', 0) / 1000,  # convert ms to seconds
                'legs': [],
                'weight': path.get('time', 0) / 1000
            }
            routes.append(route)
        
        return {
            'code': 'Ok',
            'routes': routes,
            'waypoints': [
                {'name': 'Start', 'location': routes[0]['geometry']['coordinates'][0] if routes else [0, 0]},
                {'name': 'End', 'location': routes[0]['geometry']['coordinates'][-1] if routes else [0, 0]}
            ]
        }


# Global instance
_graphhopper_instance = None

def get_graphhopper() -> GraphHopperRouter:
    """Get singleton GraphHopper instance"""
    global _graphhopper_instance
    if _graphhopper_instance is None:
        _graphhopper_instance = GraphHopperRouter()
    return _graphhopper_instance
