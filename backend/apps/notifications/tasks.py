from celery import shared_task
from django.conf import settings
from apps.users.models import User
from apps.tasks.models import Task
from .models import Notification

def build_message(event_type, task):
    # Simple message builder – can be enhanced later
    return f"Task '{task.title}' status changed to {event_type}."

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_task_notification(self, user_id, task_id, event_type):
    try:
        user = User.objects.get(pk=user_id)
        task = Task.objects.get(pk=task_id)
        message = build_message(event_type, task)
        Notification.objects.create(
            recipient=user,
            task=task,
            notification_type=event_type,
            message=message,
        )
        # Stubbed email sending – will integrate later
        # send_mail(...)
    except (User.DoesNotExist, Task.DoesNotExist):
        return  # don't retry
    except Exception as exc:
        raise self.retry(exc=exc)