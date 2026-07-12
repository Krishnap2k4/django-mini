from django.db import transaction
from django.core.exceptions import ValidationError

from apps.users.models import User
from apps.core.exceptions import InvalidTransitionError, PermissionDeniedError
from .models import Task, TaskStatus

ALLOWED_TRANSITIONS = {
    TaskStatus.DRAFT: {TaskStatus.SUBMITTED},
    TaskStatus.SUBMITTED: {TaskStatus.APPROVED, TaskStatus.REJECTED},
    TaskStatus.REJECTED: {TaskStatus.DRAFT},
    TaskStatus.APPROVED: set(),  # terminal
}


@transaction.atomic
def transition_task(task: Task, *, to_status: str, actor: User, remarks: str = "") -> Task:
    # Row lock first – ensures we’re looking at the latest committed status
    task = Task.objects.select_for_update().get(pk=task.pk)

    # Now check if this transition is allowed based on *current* DB status
    if to_status not in ALLOWED_TRANSITIONS.get(task.status, set()):
        raise InvalidTransitionError(
            f"Cannot move task from {task.status} to {to_status}"
        )

    # Permission checks (these always work with the locked task object)
    if to_status == TaskStatus.SUBMITTED:
        is_creator = task.creator_id == actor.id
        is_assignee = task.assignees.filter(pk=actor.id).exists()
        if not (is_creator or is_assignee or actor.is_superadmin):
            raise PermissionDeniedError(
                "Only the creator or an assignee can submit this task."
            )

    if to_status in (TaskStatus.APPROVED, TaskStatus.REJECTED):
        if not actor.is_superadmin and (
            task.reviewer_id != actor.id or not actor.is_manager
        ):
            raise PermissionDeniedError(
                "Only the assigned reviewer (manager/superadmin) can approve/reject."
            )

    from_status = task.status
    task.status = to_status
    task.save(update_fields=["status", "updated_at"])

    from .signals import task_status_changed
    task_status_changed.send(
        sender=Task,
        task=task,
        from_status=from_status,
        to_status=to_status,
        actor=actor,
        remarks=remarks,
    )

    return task

@transaction.atomic
def assign_reviewer(task: Task, *, reviewer: User, actor: User) -> Task:
    """
    Assign or change the reviewer. Allowed while DRAFT or SUBMITTED.
    """
    if task.status not in (TaskStatus.DRAFT, TaskStatus.SUBMITTED):
        raise InvalidTransitionError(
            "Reviewer can only be set while the task is DRAFT or SUBMITTED."
        )
    if task.creator_id != actor.id and not actor.is_superadmin:
        raise PermissionDeniedError("Only the creator can assign a reviewer.")
    if not reviewer.is_manager:
        raise ValidationError("Reviewer must be a Manager or Superadmin.")
    if reviewer.id == task.creator_id:
        raise ValidationError("A task's creator cannot also be its reviewer.")

    task = Task.objects.select_for_update().get(pk=task.pk)
    previous_reviewer = task.reviewer
    task.reviewer = reviewer
    task.save(update_fields=["reviewer", "updated_at"])

    from .signals import reviewer_assigned
    reviewer_assigned.send(
        sender=Task,
        task=task,
        reviewer=reviewer,
        previous_reviewer=previous_reviewer,
        actor=actor,
    )

    return task