from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HospitalViewSet, RouteViewSet, TrafficDataViewSet, index_view
from .home import api_home

router = DefaultRouter()
router.register(r'hospitals', HospitalViewSet, basename='hospital')
router.register(r'routes', RouteViewSet, basename='route')
router.register(r'traffic', TrafficDataViewSet, basename='traffic')

urlpatterns = [
    path('', api_home, name='api-home'),
    path('', include(router.urls)),
]
