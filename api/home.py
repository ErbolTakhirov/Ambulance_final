from django.http import JsonResponse
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def api_home(request):
    """
    API Home page with all available endpoints
    """
    return JsonResponse({
        'message': '🚑 Ambulance Route API',
        'version': '2.0.0',
        'status': 'running',
        'features': [
            'Multi-level traffic visualization (like 2GIS)',
            'Smart route calculation with OSRM',
            'Real-time traffic updates',
            'Hospital management',
            'Route tracking'
        ],
        'endpoints': {
            'hospitals': {
                'list_all': {
                    'url': '/api/hospitals/',
                    'method': 'GET',
                    'description': 'Get all hospitals'
                },
                'active': {
                    'url': '/api/hospitals/active/',
                    'method': 'GET',
                    'description': 'Get active hospitals only'
                },
                'detail': {
                    'url': '/api/hospitals/{id}/',
                    'method': 'GET',
                    'description': 'Get hospital details'
                },
                'create': {
                    'url': '/api/hospitals/',
                    'method': 'POST',
                    'description': 'Create new hospital'
                }
            },
            'routes': {
                'list_all': {
                    'url': '/api/routes/',
                    'method': 'GET',
                    'description': 'Get all routes'
                },
                'calculate': {
                    'url': '/api/routes/calculate/',
                    'method': 'POST',
                    'description': 'Calculate new route',
                    'example': {
                        'start_lat': 42.875144,
                        'start_lng': 74.562028,
                        'end_lat': 42.8755,
                        'end_lng': 74.6030,
                        'traffic_enabled': True,
                        'alternatives': 3
                    }
                },
                'detail': {
                    'url': '/api/routes/{id}/',
                    'method': 'GET',
                    'description': 'Get route details'
                },
                'update_status': {
                    'url': '/api/routes/{id}/update_status/',
                    'method': 'PATCH',
                    'description': 'Update route status'
                }
            },
            'traffic': {
                'list_all': {
                    'url': '/api/traffic/',
                    'method': 'GET',
                    'description': 'Get all traffic data'
                },
                'current': {
                    'url': '/api/traffic/current/',
                    'method': 'GET',
                    'description': 'Get current traffic conditions'
                },
                'generate': {
                    'url': '/api/traffic/generate/',
                    'method': 'POST',
                    'description': 'Generate random traffic data for testing'
                },
                'detail': {
                    'url': '/api/traffic/{id}/',
                    'method': 'GET',
                    'description': 'Get traffic details for specific street'
                }
            }
        },
        'traffic_levels': {
            'free': {'color': '#22c55e', 'range': '0-30%', 'description': 'Free Flow'},
            'light': {'color': '#eab308', 'range': '30-50%', 'description': 'Light Traffic'},
            'moderate': {'color': '#f97316', 'range': '50-70%', 'description': 'Moderate Traffic'},
            'heavy': {'color': '#ef4444', 'range': '70-90%', 'description': 'Heavy Traffic'},
            'jam': {'color': '#991b1b', 'range': '90-100%', 'description': 'Traffic Jam'}
        },
        'admin_panel': '/admin/',
        'main_page': '/',
        'documentation': {
            'base_url': 'http://127.0.0.1:8000',
            'cors_enabled': True,
            'authentication': 'Not required for testing',
            'rate_limiting': 'Not implemented'
        }
    })
