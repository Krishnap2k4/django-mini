from .dev import *

# Force Celery to run tasks inline during tests
CELERY_TASK_ALWAYS_EAGER = True