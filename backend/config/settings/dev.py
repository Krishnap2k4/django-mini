from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]
AUTH_PASSWORD_VALIDATORS = []

# Dev: print emails to console instead of sending via SMTP
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
