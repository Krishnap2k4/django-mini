from django.db.models import Q
from .models import Task, TaskStatus
from apps.users.models import User

def get_user_created_tasks(user: User):
    """All tasks created by the user (any status)."""
    return Task.objects.filter(creator=user).select_related('reviewer').prefetch_related('assignees')

def get_user_assigned_tasks(user: User):
    """Tasks where the user is an assignee."""
    return Task.objects.filter(assignees=user).select_related('creator', 'reviewer').prefetch_related('assignees')

def get_user_review_tasks(user: User):
    """Tasks where the user is the assigned reviewer and status is SUBMITTED."""
    return Task.objects.filter(reviewer=user, status=TaskStatus.SUBMITTED).select_related('creator').prefetch_related('assignees')

def get_all_tasks():
    """All tasks (superadmin view)."""
    return Task.objects.select_related('creator', 'reviewer').prefetch_related('assignees').all()

def get_dashboard_counts(user: User) -> dict:
    """Cached aggregate counts (already implemented in cache.py, but we can reuse)."""
    from .cache import get_dashboard_counts
    return get_dashboard_counts(user)