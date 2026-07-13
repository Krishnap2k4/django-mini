from .base import *

DEBUG = False
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split()

# Security
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Production Celery: use the real Redis broker (eager mode is off by default)
CELERY_TASK_ALWAYS_EAGER = False

# CORS: strictly from environment in prod
CORS_ALLOW_ALL_ORIGINS = False