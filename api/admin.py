from django.contrib import admin
from .models import Hospital, Route, TrafficData


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ['name', 'latitude', 'longitude', 'ambulance_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'address']
    ordering = ['name']
    list_editable = ['is_active', 'ambulance_count']


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ['id', 'hospital', 'distance', 'duration', 'status', 'traffic_enabled', 'created_at']
    list_filter = ['status', 'traffic_enabled', 'created_at']
    search_fields = ['id', 'hospital__name']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['status']


@admin.register(TrafficData)
class TrafficDataAdmin(admin.ModelAdmin):
    list_display = ['street_name', 'traffic_level', 'congestion_percentage', 'average_speed', 'is_active', 'updated_at']
    list_filter = ['traffic_level', 'is_active', 'updated_at']
    search_fields = ['street_name']
    ordering = ['street_name']
    list_editable = ['traffic_level', 'congestion_percentage', 'is_active']
    readonly_fields = ['updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request)
