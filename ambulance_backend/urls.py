"""
URL configuration for ambulance_backend project.
"""
from django.contrib import admin
from django.urls import path, include
from api.views import index_view

urlpatterns = [
    path('', index_view, name='index'),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]
