from django.http import JsonResponse
from django.db import connections
from django.core.cache import cache
import redis

def health_check(request):
    """Return 200 if database and redis are reachable."""
    status = {}
    # Check database
    try:
        connections['default'].cursor()
        status['database'] = 'ok'
    except Exception as e:
        status['database'] = f'error: {e}'

    # Check redis
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            status['redis'] = 'ok'
        else:
            status['redis'] = 'unexpected value'
    except Exception as e:
        status['redis'] = f'error: {e}'

    overall_healthy = all(v == 'ok' for v in status.values())
    return JsonResponse(status, status=200 if overall_healthy else 503)