from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]
AUTH_PASSWORD_VALIDATORS = []

# Dev: Emails will now send via SMTP (credentials from .env)
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
