"""
Traffic Data Manager Module
Manages traffic data for street network with realistic simulation
"""
import random
from typing import Dict, List, Optional
from datetime import datetime


class TrafficManager:
    """Manages traffic data for street network"""
    
    # Traffic levels configuration
    TRAFFIC_LEVELS = {
        'free': {'min': 0, 'max': 30, 'color': '#22c55e', 'label': 'Свободно'},
        'light': {'min': 30, 'max': 50, 'color': '#eab308', 'label': 'Легкий'},
        'moderate': {'min': 50, 'max': 70, 'color': '#f97316', 'label': 'Умеренный'},
        'heavy': {'min': 70, 'max': 90, 'color': '#ef4444', 'label': 'Плотный'},
        'jam': {'min': 90, 'max': 100, 'color': '#991b1b', 'label': 'Пробка'}
    }
    
    # Time-based traffic patterns (hour -> congestion multiplier)
    TIME_PATTERNS = {
        # Night (0-6): Low traffic
        **{h: 0.2 for h in range(0, 6)},
        # Morning (6-9): Rush hour
        **{h: 1.5 for h in range(6, 9)},
        # Day (9-17): Moderate
        **{h: 0.8 for h in range(9, 17)},
        # Evening (17-20): Rush hour
        **{h: 1.6 for h in range(17, 20)},
        # Night (20-24): Decreasing
        **{h: 0.6 for h in range(20, 24)}
    }
    
    # Major streets that tend to have more traffic
    MAJOR_STREETS = [
        'Чуй', 'Манас', 'Жибек Жолу', 'Ахунбаева', 'Советская',
        'Московская', 'Киевская', '7 Апреля', 'Боконбаева'
    ]
    
    @classmethod
    def generate_traffic_for_streets(cls, streets: List[Dict]) -> List[Dict]:
        """
        Generate realistic traffic data for streets
        
        Args:
            streets: List of street dictionaries with geometry
            
        Returns:
            List of streets with added traffic data
        """
        current_hour = datetime.now().hour
        time_multiplier = cls.TIME_PATTERNS.get(current_hour, 1.0)
        
        result = []
        
        for street in streets:
            # Base congestion (random)
            base_congestion = random.randint(10, 60)
            
            # Apply time multiplier
            congestion = min(100, int(base_congestion * time_multiplier))
            
            # Major streets get +10-20% congestion
            if any(major in street['name'] for major in cls.MAJOR_STREETS):
                congestion = min(100, congestion + random.randint(10, 20))
            
            # Calculate traffic level
            traffic_level = cls._get_traffic_level(congestion)
            
            # Calculate average speed (km/h)
            average_speed = cls._calculate_speed(congestion, street.get('highway_type', 'tertiary'))
            
            # Add traffic data to street
            street_with_traffic = {
                **street,
                'congestion_percentage': congestion,
                'traffic_level': traffic_level,
                'average_speed': average_speed,
                'color': cls.TRAFFIC_LEVELS[traffic_level]['color'],
                'label': cls.TRAFFIC_LEVELS[traffic_level]['label']
            }
            
            result.append(street_with_traffic)
        
        return result
    
    @classmethod
    def _get_traffic_level(cls, congestion: int) -> str:
        """Get traffic level name from congestion percentage"""
        for level, config in cls.TRAFFIC_LEVELS.items():
            if config['min'] <= congestion < config['max']:
                return level
        return 'jam'  # Default to jam if >= 90
    
    @classmethod
    def _calculate_speed(cls, congestion: int, highway_type: str) -> float:
        """Calculate average speed based on congestion and road type"""
        # Base speeds by road type (km/h)
        base_speeds = {
            'motorway': 80,
            'trunk': 70,
            'primary': 60,
            'secondary': 50,
            'tertiary': 40,
            'residential': 30
        }
        
        base_speed = base_speeds.get(highway_type, 40)
        
        # Reduce speed based on congestion
        speed_reduction = (congestion / 100) * 0.7  # Max 70% reduction
        actual_speed = base_speed * (1 - speed_reduction)
        
        # Minimum speed is 10 km/h
        return max(10.0, round(actual_speed, 1))
    
    @classmethod
    def get_traffic_color(cls, congestion: int) -> str:
        """Get color for congestion percentage"""
        level = cls._get_traffic_level(congestion)
        return cls.TRAFFIC_LEVELS[level]['color']
    
    @classmethod
    def get_traffic_statistics(cls, streets_with_traffic: List[Dict]) -> Dict:
        """Calculate traffic statistics"""
        if not streets_with_traffic:
            return {}
        
        total_streets = len(streets_with_traffic)
        level_counts = {level: 0 for level in cls.TRAFFIC_LEVELS.keys()}
        
        for street in streets_with_traffic:
            level = street.get('traffic_level', 'free')
            level_counts[level] += 1
        
        avg_congestion = sum(s.get('congestion_percentage', 0) for s in streets_with_traffic) / total_streets
        
        return {
            'total_streets': total_streets,
            'average_congestion': round(avg_congestion, 1),
            'level_distribution': {
                level: {
                    'count': count,
                    'percentage': round((count / total_streets) * 100, 1)
                }
                for level, count in level_counts.items()
            }
        }
