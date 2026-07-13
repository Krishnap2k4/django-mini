import django.dispatch
from django.db import transaction
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from .models import Task, TaskStatus, TaskStatusHistory
from .cache import invalidate_dashboard_cache
from apps.notifications.tasks import send_task_notification

# ── Custom signals ──────────────────────────────────────────────────────
task_status_changed = django.dispatch.Signal()
reviewer_assigned = django.dispatch.Signal()


# ── Audit trail ─────────────────────────────────────────────────────────
@receiver(task_status_changed)
def create_status_history(sender, task, from_status, to_status, actor, remarks, **kwargs):
    TaskStatusHistory.objects.create(
        task=task,
        from_status=from_status,
        to_status=to_status,
        changed_by=actor,
        remarks=remarks,
    )


# ── Notifications (deferred until DB transaction commits) ───────────────
@receiver(task_status_changed)
def notify_on_status_change(sender, task, from_status, to_status, actor, **kwargs):
    recipients = set(task.assignees.all())
    creator = task.creator

    if to_status == TaskStatus.SUBMITTED:
        if task.reviewer_id:
            recipients.add(task.reviewer)
        recipients.add(creator)
    elif to_status in (TaskStatus.APPROVED, TaskStatus.REJECTED):
        recipients.add(creator)

    for user in recipients:
        if user != actor:
            # Defer until the DB transaction is committed so the worker
            # doesn't try to fetch a task that hasn't been saved yet.
            _user_id, _task_id, _to_status = user.id, task.id, to_status
            transaction.on_commit(
                lambda uid=_user_id, tid=_task_id, ts=_to_status:
                    send_task_notification.delay(uid, tid, ts)
            )


@receiver(reviewer_assigned)
def notify_new_reviewer(sender, task, reviewer, previous_reviewer, actor, **kwargs):
    event_type = "REVIEWER_ASSIGNED_SUBMITTED" if task.status == TaskStatus.SUBMITTED else "REVIEWER_ASSIGNED_DRAFT"
    if reviewer != actor:
        _reviewer_id, _task_id = reviewer.id, task.id
        transaction.on_commit(
            lambda rid=_reviewer_id, tid=_task_id, et=event_type:
                send_task_notification.delay(rid, tid, et)
        )


@receiver(m2m_changed, sender=Task.assignees.through)
def notify_assignee_change(sender, instance, action, reverse, pk_set, **kwargs):
    if action == "post_add":
        for user_id in pk_set:
            _uid, _tid = user_id, instance.id
            transaction.on_commit(
                lambda uid=_uid, tid=_tid:
                    send_task_notification.delay(uid, tid, "ASSIGNED")
            )


# ── Cache invalidation ──────────────────────────────────────────────────
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