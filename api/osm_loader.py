"""
OpenStreetMap Data Loader Module
Loads real street geometries from Overpass API for Bishkek
"""
import requests
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class OSMStreetLoader:
    """Loads and caches street geometries from OpenStreetMap"""
    
    OVERPASS_URL = "https://overpass-api.de/api/interpreter"
    
    # Bishkek bounding box [south, west, north, east]
    BISHKEK_BBOX = [42.80, 74.50, 42.92, 74.70]
    
    # Cache for street data
    _cache = None
    _cache_timestamp = None
    _cache_duration = timedelta(hours=24)  # Cache for 24 hours
    
    @classmethod
    def get_bishkek_streets(cls, force_refresh: bool = False) -> List[Dict]:
        """
        Get street geometries for Bishkek
        
        Args:
            force_refresh: Force refresh from API even if cache is valid
            
        Returns:
            List of street dictionaries with name and geometry
        """
        # Check cache
        if not force_refresh and cls._is_cache_valid():
            return cls._cache
        
        # Fetch from API
        streets = cls._fetch_from_overpass()
        
        # Update cache
        cls._cache = streets
        cls._cache_timestamp = datetime.now()
        
        return streets
    
    @classmethod
    def _is_cache_valid(cls) -> bool:
        """Check if cache is still valid"""
        if cls._cache is None or cls._cache_timestamp is None:
            return False
        
        age = datetime.now() - cls._cache_timestamp
        return age < cls._cache_duration
    
    @classmethod
    def _fetch_from_overpass(cls) -> List[Dict]:
        """Fetch street data from Overpass API"""
        
        # Overpass QL query for major roads in Bishkek
        query = f"""
        [out:json][timeout:25];
        (
          way["highway"~"^(motorway|trunk|primary|secondary|tertiary)$"]
              ({cls.BISHKEK_BBOX[0]},{cls.BISHKEK_BBOX[1]},{cls.BISHKEK_BBOX[2]},{cls.BISHKEK_BBOX[3]});
        );
        out geom;
        """
        
        try:
            response = requests.post(
                cls.OVERPASS_URL,
                data={'data': query},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            return cls._process_overpass_data(data)
            
        except Exception as e:
            print(f"Error fetching from Overpass API: {e}")
            # Return fallback data if API fails
            return cls._get_fallback_streets()
    
    @classmethod
    def _process_overpass_data(cls, data: Dict) -> List[Dict]:
        """Process Overpass API response into street geometries"""
        streets = []
        
        for element in data.get('elements', []):
            if element.get('type') != 'way':
                continue
            
            # Get street name
            tags = element.get('tags', {})
            name = tags.get('name', tags.get('name:ru', tags.get('name:ky', 'Unnamed Street')))
            
            # Get geometry
            geometry = element.get('geometry', [])
            if len(geometry) < 2:
                continue
            
            # Convert to coordinate pairs [lat, lng]
            coords = [[node['lat'], node['lon']] for node in geometry]
            
            # Get road category for width
            highway_type = tags.get('highway', 'tertiary')
            width = cls._get_road_width(highway_type)
            
            streets.append({
                'name': name,
                'coords': coords,
                'highway_type': highway_type,
                'width': width,
                'osm_id': element.get('id')
            })
        
        return streets
    
    @classmethod
    def _get_road_width(cls, highway_type: str) -> int:
        """Get visual width for road type"""
        width_map = {
            'motorway': 8,
            'trunk': 7,
            'primary': 6,
            'secondary': 5,
            'tertiary': 4,
            'residential': 3
        }
        return width_map.get(highway_type, 4)
    
    @classmethod
    def _get_fallback_streets(cls) -> List[Dict]:
        """Fallback street data if API is unavailable"""
        return [
            {
                "name": "Жибек Жолу",
                "coords": [[42.8940, 74.5500], [42.8940, 74.6800]],
                "highway_type": "primary",
                "width": 6
            },
            {
                "name": "Чуй проспект",
                "coords": [[42.8750, 74.5500], [42.8750, 74.6900]],
                "highway_type": "primary",
                "width": 6
            },
            {
                "name": "Манас проспект",
                "coords": [[42.8100, 74.5870], [42.8900, 74.5870]],
                "highway_type": "primary",
                "width": 6
            },
            {
                "name": "Советская",
                "coords": [[42.8200, 74.6000], [42.8900, 74.6000]],
                "highway_type": "secondary",
                "width": 5
            },
            {
                "name": "Ахунбаева",
                "coords": [[42.8430, 74.5600], [42.8430, 74.6800]],
                "highway_type": "secondary",
                "width": 5
            },
            {
                "name": "7 Апреля",
                "coords": [[42.8200, 74.6480], [42.8900, 74.6480]],
                "highway_type": "secondary",
                "width": 5
            },
            {
                "name": "Московская",
                "coords": [[42.8690, 74.5600], [42.8690, 74.6600]],
                "highway_type": "tertiary",
                "width": 4
            },
            {
                "name": "Киевская",
                "coords": [[42.8730, 74.5600], [42.8730, 74.6400]],
                "highway_type": "tertiary",
                "width": 4
            },
            {
                "name": "Боконбаева",
                "coords": [[42.8640, 74.5600], [42.8640, 74.6600]],
                "highway_type": "tertiary",
                "width": 4
            },
            {
                "name": "Льва Толстого",
                "coords": [[42.8580, 74.5500], [42.8580, 74.6700]],
                "highway_type": "tertiary",
                "width": 4
            }
        ]
