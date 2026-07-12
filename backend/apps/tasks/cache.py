from django.core.cache import cache
from apps.users.models import User
from .models import Task, TaskStatus

def get_dashboard_counts(user: User) -> dict:
    cache_key = f"dashboard:counts:{user.id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    counts = {
        "draft": Task.objects.filter(creator=user, status=TaskStatus.DRAFT).count(),
        "unassigned": Task.objects.filter(
            creator=user, status=TaskStatus.DRAFT,
            assignees__isnull=True, reviewer__isnull=True
        ).distinct().count(),
        "submitted": Task.objects.filter(creator=user, status=TaskStatus.SUBMITTED).count(),
        "needs_reviewer": Task.objects.filter(
            creator=user, status=TaskStatus.SUBMITTED,
            reviewer__isnull=True
        ).count(),
        "pending_review": (
            Task.objects.filter(reviewer=user, status=TaskStatus.SUBMITTED).count()
            if user.is_manager else 0
        ),
        "approved": Task.objects.filter(creator=user, status=TaskStatus.APPROVED).count(),
        "rejected": Task.objects.filter(creator=user, status=TaskStatus.REJECTED).count(),
    }
    cache.set(cache_key, counts, timeout=60 * 5)  # 5 minutes
    return counts

def invalidate_dashboard_cache(user_id: int):
    cache.delete(f"dashboard:counts:{user_id}")