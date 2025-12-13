from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods
import requests
import random

from .traffic_manager import TrafficManager
from .traffic_router import get_router
from .osm_loader import OSMStreetLoader


from .models import Hospital, Route, TrafficData
from .serializers import (
    HospitalSerializer, RouteSerializer, 
    RouteCalculationSerializer, TrafficDataSerializer
)

# Mock data to bypass database
MOCK_HOSPITALS = [
    {
        "id": 1, 
        "name": "Central Hospital", 
        "latitude": 42.875144, 
        "longitude": 74.562028, 
        "address": "Bishkek, Main St", 
        "phone": "0312-000-000", 
        "is_active": True, 
        "ambulance_count": 5
    },
    {
        "id": 2, 
        "name": "City Clinic No. 2", 
        "latitude": 42.855144, 
        "longitude": 74.602028, 
        "address": "Bishkek, South St", 
        "phone": "0312-000-001", 
        "is_active": True, 
        "ambulance_count": 3
    }
]

MOCK_STREETS = [
    {"name": "Sovetskaya", "start": [42.8200, 74.6090], "end": [42.8950, 74.6090], "congestion_percentage": 0, "traffic_level": "free", "average_speed": 60},
    {"name": "Akhunbaev", "start": [42.8430, 74.5600], "end": [42.8430, 74.6700], "congestion_percentage": 0, "traffic_level": "free", "average_speed": 60},
    {"name": "7 April", "start": [42.8200, 74.6480], "end": [42.9000, 74.6480], "congestion_percentage": 0, "traffic_level": "free", "average_speed": 60},
    {"name": "Chuy Avenue", "start": [42.8750, 74.5500], "end": [42.8750, 74.6800], "congestion_percentage": 0, "traffic_level": "free", "average_speed": 60},
    {"name": "Manas Avenue", "start": [42.8100, 74.5870], "end": [42.8800, 74.5870], "congestion_percentage": 0, "traffic_level": "free", "average_speed": 60},
    {"name": "Jibek Jolu", "start": [42.8940, 74.5500], "end": [42.8940, 74.6800], "congestion_percentage": 0, "traffic_level": "free", "average_speed": 60},
    {"name": "Suerkulov", "start": [42.8380, 74.6000], "end": [42.8380, 74.6400], "congestion_percentage": 0, "traffic_level": "free", "average_speed": 60},
    {"name": "Elebesova", "start": [42.9000, 74.6150], "end": [42.9300, 74.6150], "congestion_percentage": 0, "traffic_level": "free", "average_speed": 60},
    {"name": "Gorkiy", "start": [42.8560, 74.5800], "end": [42.8560, 74.6400], "congestion_percentage": 0, "traffic_level": "free", "average_speed": 60},
    {"name": "Kievskaya", "start": [42.8730, 74.5700], "end": [42.8730, 74.6300], "congestion_percentage": 0, "traffic_level": "free", "average_speed": 60},
    {"name": "Moskovskaya", "start": [42.8690, 74.5700], "end": [42.8690, 74.6300], "congestion_percentage": 0, "traffic_level": "free", "average_speed": 60},
    {"name": "Bokonbaeva", "start": [42.8640, 74.5700], "end": [42.8640, 74.6500], "congestion_percentage": 0, "traffic_level": "free", "average_speed": 60},
    {"name": "Lev Tolstoy", "start": [42.8580, 74.5500], "end": [42.8580, 74.6800], "congestion_percentage": 0, "traffic_level": "free", "average_speed": 60},
    {"name": "Molodaya Gvardiya", "start": [42.8600, 74.5650], "end": [42.9000, 74.5650], "congestion_percentage": 0, "traffic_level": "free", "average_speed": 60},
]


def index_view(request):
    """Main page view"""
    return render(request, 'index.html')


class HospitalViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Hospital CRUD operations
    """
    queryset = Hospital.objects.none() # Dummy queryset
    serializer_class = HospitalSerializer

    def list(self, request, *args, **kwargs):
        """List all active hospitals (mock)"""
        return Response(MOCK_HOSPITALS)

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all active hospitals"""
        return Response(MOCK_HOSPITALS)

    @action(detail=True, methods=['get'])
    def nearest_route(self, request, pk=None):
        """Calculate route from hospital to a destination"""
        # Find hospital in mock data
        hospital = next((h for h in MOCK_HOSPITALS if str(h['id']) == str(pk)), None)
        if not hospital:
            return Response({'error': 'Hospital not found'}, status=404)
        
        # Create a simple object to access attributes like the model
        class MockHospitalObj:
            def __init__(self, data):
                self.__dict__.update(data)
        
        hospital = MockHospitalObj(hospital)
        
        end_lat = request.query_params.get('end_lat')
        end_lng = request.query_params.get('end_lng')

        if not end_lat or not end_lng:
            return Response(
                {'error': 'end_lat and end_lng are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Load current traffic data
            streets = OSMStreetLoader.get_bishkek_streets()
            traffic_data = TrafficManager.generate_traffic_for_streets(streets)
            
            # Calculate route using TrafficAwareRouter
            router = get_router()
            route_data = router.calculate_optimal_route(
                hospital.latitude, hospital.longitude,
                float(end_lat), float(end_lng),
                traffic_data=traffic_data
            )
            return Response(route_data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RouteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Route CRUD operations
    """
    queryset = Route.objects.all()
    serializer_class = RouteSerializer

    @action(detail=False, methods=['get', 'post'])
    def calculate(self, request):
        """
        Calculate route using OSRM
        GET: Returns API documentation
        POST: Calculates route
        """
        if request.method == 'GET':
            return Response({
                'message': 'Route Calculation API',
                'method': 'POST',
                'endpoint': '/api/routes/calculate/',
                'required_fields': {
                    'start_lat': 'float (e.g., 42.875144)',
                    'start_lng': 'float (e.g., 74.562028)',
                    'end_lat': 'float (e.g., 42.8755)',
                    'end_lng': 'float (e.g., 74.6030)',
                },
                'optional_fields': {
                    'traffic_enabled': 'boolean (default: true)',
                    'alternatives': 'integer (default: 3, min: 1, max: 5)'
                },
                'example_request': {
                    'start_lat': 42.875144,
                    'start_lng': 74.562028,
                    'end_lat': 42.8755,
                    'end_lng': 74.6030,
                    'traffic_enabled': True,
                    'alternatives': 3
                }
            })
        
        # POST request
        serializer = RouteCalculationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        
        try:
            # Load current traffic data
            streets = OSMStreetLoader.get_bishkek_streets()
            traffic_data = TrafficManager.generate_traffic_for_streets(streets)

            # Calculate route using TrafficAwareRouter
            router = get_router()
            route_data = router.calculate_optimal_route(
                data['start_lat'], data['start_lng'],
                data['end_lat'], data['end_lng'],
                traffic_data=traffic_data,
                alternatives=data.get('alternatives', 3)
            )
            
            # Save route to database
            id_counter = random.randint(1000, 9999)
            try:
                if route_data.get('routes') and len(route_data['routes']) > 0:
                    main_route = route_data['routes'][0]
                    # Attempt to save, but catch error if DB is not ready
                    route = Route.objects.create(
                        start_latitude=data['start_lat'],
                        start_longitude=data['start_lng'],
                        end_latitude=data['end_lat'],
                        end_longitude=data['end_lng'],
                        distance=main_route['distance'] / 1000,  # Convert to km
                        duration=int(main_route['duration'] / 60),  # Convert to minutes
                        traffic_enabled=data.get('traffic_enabled', True),
                        route_data=route_data,
                        status='active'
                    )
                    route_id = route.id
            except Exception:
                # Fallback if DB write fails
                route_id = id_counter

            if route_data.get('routes') and len(route_data['routes']) > 0:
                return Response({
                    'success': True,
                    'route_id': route_id,
                    'routes': route_data['routes'],
                    'waypoints': route_data.get('waypoints', [])
                })
            
            return Response(route_data)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """Update route status"""
        route = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in dict(Route.STATUS_CHOICES):
            return Response(
                {'error': 'Invalid status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        route.status = new_status
        route.save()
        serializer = self.get_serializer(route)
        return Response(serializer.data)


class TrafficDataViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Traffic Data
    """
    queryset = TrafficData.objects.none() # Dummy queryset
    serializer_class = TrafficDataSerializer

    def list(self, request, *args, **kwargs):
        """List all traffic data (mock)"""
        return Response(MOCK_STREETS)

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current traffic data for all streets"""
        # Return in-memory data
        return Response(MOCK_STREETS)
    
    @action(detail=False, methods=['get'])
    def streets_osm(self, request):
        """Get real street geometries from OpenStreetMap with traffic data"""
        try:
            # Load real streets from OSM
            streets = OSMStreetLoader.get_bishkek_streets()
            
            # Add traffic data
            streets_with_traffic = TrafficManager.generate_traffic_for_streets(streets)
            
            return Response({
                'success': True,
                'count': len(streets_with_traffic),
                'streets': streets_with_traffic
            })
        except Exception as e:
            return Response(
                {'error': str(e), 'fallback': True, 'streets': MOCK_STREETS},
                status=status.HTTP_200_OK
            )
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get traffic statistics"""
        try:
            streets = OSMStreetLoader.get_bishkek_streets()
            streets_with_traffic = TrafficManager.generate_traffic_for_streets(streets)
            stats = TrafficManager.get_traffic_statistics(streets_with_traffic)
            
            return Response({
                'success': True,
                'statistics': stats
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate random traffic data for testing"""
        global MOCK_STREETS
        
        created_count = 0
        for street in MOCK_STREETS:
            congestion = random.randint(0, 100)
            speed = 60 - (congestion * 0.5)  # Speed decreases with congestion
            
            street['congestion_percentage'] = congestion
            street['average_speed'] = max(10, speed)
            
            if congestion < 30:
                street['traffic_level'] = 'free'
            elif congestion < 50:
                street['traffic_level'] = 'light'
            elif congestion < 70:
                street['traffic_level'] = 'moderate'
            elif congestion < 90:
                street['traffic_level'] = 'heavy'
            else:
                street['traffic_level'] = 'jam'
            
            created_count += 1

        return Response({
            'message': f'Generated traffic data for {len(MOCK_STREETS)} streets',
            'created': created_count,
            'updated': 0
        })


def calculate_osrm_route(start_lat, start_lng, end_lat, end_lng, alternatives=3):
    """
    Legacy helper - kept for backward compatibility if needed, 
    but logic is moved to TrafficAwareRouter
    """
    coords = f"{start_lng},{start_lat};{end_lng},{end_lat}"
    url = f"https://routing.openstreetmap.de/routed-car/route/v1/driving/{coords}"
    
    params = {
        'overview': 'full',
        'geometries': 'geojson',
        'alternatives': alternatives
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        return response.json()
    except:
        return {}
