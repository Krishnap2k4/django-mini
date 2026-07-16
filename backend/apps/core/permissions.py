from rest_framework.permissions import BasePermission
from apps.tasks.models import TaskStatus


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_superadmin

    def has_object_permission(self, request, view, obj):
        return request.user.is_superadmin


class IsCreatorOrSuperAdmin(BasePermission):
    """General field edits (title, description, assignees, priority, etc.) — DRAFT only."""
    def has_object_permission(self, request, view, obj):
        if request.user.is_superadmin:
            return True
        return obj.creator_id == request.user.id and obj.status == TaskStatus.DRAFT


class CanSubmitTask(BasePermission):
    """Submit (DRAFT→SUBMITTED) or revert (REJECTED→DRAFT) allowed for the
    creator, any current assignee, or superadmin."""
    def has_object_permission(self, request, view, obj):
        if request.user.is_superadmin:
            return True
        if obj.status not in (TaskStatus.DRAFT, TaskStatus.REJECTED):
            return False
        return obj.creator_id == request.user.id or obj.assignees.filter(pk=request.user.id).exists()


class CanAssignReviewer(BasePermission):
    """Assigning/changing the reviewer is allowed for the creator or superadmin,
    while the task is DRAFT or SUBMITTED."""
    def has_object_permission(self, request, view, obj):
        if request.user.is_superadmin:
            return True
        return obj.creator_id == request.user.id and obj.status in (TaskStatus.DRAFT, TaskStatus.SUBMITTED)


class IsAssignedReviewerOrSuperAdmin(BasePermission):
    """Approve/reject allowed only for the assigned reviewer (must be Manager+) or superadmin."""
    def has_object_permission(self, request, view, obj):
        if request.user.is_superadmin:
            return True
        return obj.reviewer_id == request.user.id and request.user.is_manager