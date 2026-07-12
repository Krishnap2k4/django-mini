import django.dispatch
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from .models import Task, TaskStatus, TaskStatusHistory
from apps.notifications.tasks import send_task_notification

# Custom signals
task_status_changed = django.dispatch.Signal()
reviewer_assigned = django.dispatch.Signal()

@receiver(task_status_changed)
def create_status_history(sender, task, from_status, to_status, actor, remarks, **kwargs):
    TaskStatusHistory.objects.create(
        task=task,
        from_status=from_status,
        to_status=to_status,
        changed_by=actor,
        remarks=remarks,
    )

@receiver(task_status_changed)
def notify_on_status_change(sender, task, from_status, to_status, actor, **kwargs):
    recipients = set(task.assignees.all())
    creator = task.creator

    if to_status == TaskStatus.SUBMITTED:
        # Notify the reviewer (if assigned) and the creator
        if task.reviewer_id:
            recipients.add(task.reviewer)
        recipients.add(creator)
    elif to_status in (TaskStatus.APPROVED, TaskStatus.REJECTED):
        # Notify the creator and assignees
        recipients.add(creator)

    for user in recipients:
        if user != actor:   # don't notify the actor themselves
            send_task_notification.delay(user.id, task.id, to_status)

@receiver(reviewer_assigned)
def notify_new_reviewer(sender, task, reviewer, previous_reviewer, actor, **kwargs):
    event_type = "REVIEWER_ASSIGNED_SUBMITTED" if task.status == TaskStatus.SUBMITTED else "REVIEWER_ASSIGNED_DRAFT"
    # Notify the newly assigned reviewer (unless they assigned themselves)
    if reviewer != actor:
        send_task_notification.delay(reviewer.id, task.id, event_type)

# Handle assignee changes (m2m_changed)
@receiver(m2m_changed, sender=Task.assignees.through)
def notify_assignee_change(sender, instance, action, reverse, pk_set, **kwargs):
    if action == "post_add":
        # New assignees added
        for user_id in pk_set:
            from apps.users.models import User
            user = User.objects.get(pk=user_id)
            send_task_notification.delay(user.id, instance.id, "ASSIGNED")
            
            
        
        
        
        
from .cache import invalidate_dashboard_cache

@receiver(task_status_changed)
def invalidate_cache_on_status_change(sender, task, **kwargs):
    invalidate_dashboard_cache(task.creator_id)
    if task.reviewer_id:
        invalidate_dashboard_cache(task.reviewer_id)
    for assignee in task.assignees.all():
        invalidate_dashboard_cache(assignee.id)

@receiver(reviewer_assigned)
def invalidate_cache_on_reviewer_change(sender, task, reviewer, previous_reviewer, **kwargs):
    invalidate_dashboard_cache(task.creator_id)
    if reviewer:
        invalidate_dashboard_cache(reviewer.id)
    if previous_reviewer:
        invalidate_dashboard_cache(previous_reviewer.id)

@receiver(m2m_changed, sender=Task.assignees.through)
def invalidate_cache_on_assignee_change(sender, instance, action, pk_set, **kwargs):
    if action in ["post_add", "post_remove", "post_clear"]:
        invalidate_dashboard_cache(instance.creator_id)
        if instance.reviewer_id:
            invalidate_dashboard_cache(instance.reviewer_id)
        for uid in pk_set or []:
            invalidate_dashboard_cache(uid)