from rest_framework import serializers
from .models import Hospital, Route, TrafficData


class HospitalSerializer(serializers.ModelSerializer):
    """Serializer for Hospital model"""
    
    class Meta:
        model = Hospital
        fields = ['id', 'name', 'latitude', 'longitude', 'address', 'phone', 
                  'is_active', 'ambulance_count', 'created_at']
        read_only_fields = ['id', 'created_at']


class RouteSerializer(serializers.ModelSerializer):
    """Serializer for Route model"""
    hospital_name = serializers.CharField(source='hospital.name', read_only=True)
    
    class Meta:
        model = Route
        fields = [
            'id', 'start_latitude', 'start_longitude', 
            'end_latitude', 'end_longitude', 'hospital', 'hospital_name',
            'distance', 'duration', 'status', 'traffic_enabled',
            'route_data', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RouteCalculationSerializer(serializers.Serializer):
    """Serializer for route calculation request"""
    start_lat = serializers.FloatField()
    start_lng = serializers.FloatField()
    end_lat = serializers.FloatField()
    end_lng = serializers.FloatField()
    traffic_enabled = serializers.BooleanField(default=True)
    alternatives = serializers.IntegerField(default=3, min_value=1, max_value=5)


class TrafficDataSerializer(serializers.ModelSerializer):
    """Serializer for Traffic Data"""
    color = serializers.CharField(source='get_color', read_only=True)
    traffic_level_display = serializers.CharField(source='get_traffic_level_display', read_only=True)
    
    class Meta:
        model = TrafficData
        fields = [
            'id', 'street_name', 'start_latitude', 'start_longitude',
            'end_latitude', 'end_longitude', 'traffic_level', 'traffic_level_display',
            'congestion_percentage', 'average_speed', 'color', 'updated_at', 'is_active'
        ]
        read_only_fields = ['id', 'updated_at']
