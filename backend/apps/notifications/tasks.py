"""
Celery task for sending notifications via three channels:
  1. Database  — save a Notification record (for API/history)
  2. Email     — send via Django's email backend (SMTP in prod, console in dev)
  3. WebSocket — push to the user's browser in real-time via Channel Layer
"""
import logging

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.core.mail import send_mail
from django.conf import settings

from apps.users.models import User
from apps.tasks.models import Task
from .models import Notification

logger = logging.getLogger(__name__)


def build_message(event_type, task):
    """Build a human-readable notification message."""
    messages = {
        'SUBMITTED': f"Task '{task.title}' has been submitted for review.",
        'APPROVED': f"Task '{task.title}' has been approved.",
        'REJECTED': f"Task '{task.title}' has been rejected.",
        'ASSIGNED': f"You have been assigned to task '{task.title}'.",
        'REVIEWER_ASSIGNED_DRAFT': f"You have been assigned as reviewer for task '{task.title}'.",
        'REVIEWER_ASSIGNED_SUBMITTED': f"You have been assigned as reviewer for task '{task.title}'.",
    }
    return messages.get(event_type, f"Task '{task.title}' — {event_type}.")


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_task_notification(self, user_id, task_id, event_type):
    try:
        user = User.objects.get(pk=user_id)
        task = Task.objects.get(pk=task_id)
    except (User.DoesNotExist, Task.DoesNotExist):
        return  # don't retry if the objects are gone

    message = build_message(event_type, task)

    try:
        # 1. Save to database
        notification = Notification.objects.create(
            recipient=user,
            task=task,
            notification_type=event_type,
            message=message,
        )

        # 2. Push via WebSocket (non-blocking, best-effort)
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"notifications_user_{user_id}",
                {
                    "type": "send_notification",
                    "data": {
                        "id": notification.id,
                        "type": event_type,
                        "message": message,
                        "task_id": task_id,
                        "task_title": task.title,
                        "is_read": False,
                        "created_at": str(notification.created_at),
                    },
                },
            )
        except Exception as ws_err:
            logger.warning("WebSocket push failed (non-critical): %s", ws_err)

        # 3. Send email (best-effort, don't fail the task if email fails)
        if user.email:
            try:
                send_mail(
                    subject=f"[Task Approval] {event_type.replace('_', ' ').title()}",
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            except Exception as email_err:
                logger.warning("Email send failed (non-critical): %s", email_err)

    except Exception as exc:
        raise self.retry(exc=exc)