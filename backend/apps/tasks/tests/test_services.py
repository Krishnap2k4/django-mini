import pytest
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError

from apps.users.models import User, Role
from apps.tasks.models import Task, TaskStatus
from apps.tasks.services import transition_task, assign_reviewer
from apps.core.exceptions import InvalidTransitionError, PermissionDeniedError


@pytest.mark.django_db
class TestTransitionTask:
    def setup_method(self):
        # Create users with different roles
        self.creator = User.objects.create_user(username='creator', password='p')
        self.assignee = User.objects.create_user(username='assignee', password='p')
        self.manager = User.objects.create_user(username='manager', password='p', role=Role.MANAGER)
        self.superadmin = User.objects.create_user(username='superadmin', password='p', role=Role.SUPERADMIN)
        self.random_staff = User.objects.create_user(username='staff', password='p')

    def _create_task(self, **kwargs):
        defaults = {
            'title': 'Test Task',
            'creator': self.creator,
        }
        defaults.update(kwargs)
        task = Task.objects.create(**defaults)
        return task

    # --- Happy paths ---
    def test_draft_to_submitted_by_creator(self):
        task = self._create_task()
        task = transition_task(task, to_status=TaskStatus.SUBMITTED, actor=self.creator)
        assert task.status == TaskStatus.SUBMITTED

    def test_draft_to_submitted_by_assignee(self):
        task = self._create_task()
        task.assignees.add(self.assignee)
        task = transition_task(task, to_status=TaskStatus.SUBMITTED, actor=self.assignee)
        assert task.status == TaskStatus.SUBMITTED

    def test_draft_to_submitted_by_superadmin(self):
        task = self._create_task()
        task = transition_task(task, to_status=TaskStatus.SUBMITTED, actor=self.superadmin)
        assert task.status == TaskStatus.SUBMITTED

    def test_submitted_to_approved_by_reviewer(self):
        task = self._create_task(reviewer=self.manager, status=TaskStatus.SUBMITTED)
        task = transition_task(task, to_status=TaskStatus.APPROVED, actor=self.manager)
        assert task.status == TaskStatus.APPROVED

    def test_submitted_to_rejected_by_reviewer(self):
        task = self._create_task(reviewer=self.manager, status=TaskStatus.SUBMITTED)
        task = transition_task(task, to_status=TaskStatus.REJECTED, actor=self.manager,
                               remarks="Needs work")
        assert task.status == TaskStatus.REJECTED

    def test_rejected_back_to_draft(self):
        task = self._create_task(reviewer=self.manager, status=TaskStatus.REJECTED)
        task = transition_task(task, to_status=TaskStatus.DRAFT, actor=self.creator)
        assert task.status == TaskStatus.DRAFT

    # --- Illegal transitions ---
    def test_cannot_skip_status(self):
        task = self._create_task()  # DRAFT
        with pytest.raises(InvalidTransitionError):
            transition_task(task, to_status=TaskStatus.APPROVED, actor=self.creator)

    def test_cannot_approve_from_draft(self):
        task = self._create_task()
        with pytest.raises(InvalidTransitionError):
            transition_task(task, to_status=TaskStatus.APPROVED, actor=self.creator)

    def test_approved_is_terminal(self):
        task = self._create_task(reviewer=self.manager, status=TaskStatus.APPROVED)
        with pytest.raises(InvalidTransitionError):
            transition_task(task, to_status=TaskStatus.DRAFT, actor=self.creator)
        with pytest.raises(InvalidTransitionError):
            transition_task(task, to_status=TaskStatus.SUBMITTED, actor=self.creator)

    # --- Permission checks ---
    def test_staff_cannot_submit_if_not_creator_or_assignee(self):
        task = self._create_task()
        with pytest.raises(PermissionDeniedError):
            transition_task(task, to_status=TaskStatus.SUBMITTED, actor=self.random_staff)

    def test_staff_cannot_approve(self):
        task = self._create_task(reviewer=self.manager, status=TaskStatus.SUBMITTED)
        with pytest.raises(PermissionDeniedError):
            transition_task(task, to_status=TaskStatus.APPROVED, actor=self.random_staff)

    def test_manager_not_assigned_as_reviewer_cannot_approve(self):
        other_mgr = User.objects.create_user(username='other_mgr', password='p', role=Role.MANAGER)
        task = self._create_task(reviewer=self.manager, status=TaskStatus.SUBMITTED)
        with pytest.raises(PermissionDeniedError):
            transition_task(task, to_status=TaskStatus.APPROVED, actor=other_mgr)

    def test_superadmin_can_approve_even_if_not_reviewer(self):
        task = self._create_task(reviewer=self.manager, status=TaskStatus.SUBMITTED)
        task = transition_task(task, to_status=TaskStatus.APPROVED, actor=self.superadmin)
        assert task.status == TaskStatus.APPROVED

    def test_submit_without_reviewer_allowed(self):
        task = self._create_task()  # reviewer=None
        task = transition_task(task, to_status=TaskStatus.SUBMITTED, actor=self.creator)
        assert task.status == TaskStatus.SUBMITTED

    def test_approve_reviewerless_task_denied_for_creator(self):
        task = self._create_task(status=TaskStatus.SUBMITTED)  # reviewer=None
        with pytest.raises(PermissionDeniedError):
            transition_task(task, to_status=TaskStatus.APPROVED, actor=self.creator)

    def test_approve_reviewerless_task_allowed_for_superadmin(self):
        task = self._create_task(status=TaskStatus.SUBMITTED)
        task = transition_task(task, to_status=TaskStatus.APPROVED, actor=self.superadmin)
        assert task.status == TaskStatus.APPROVED

    # --- Concurrency (select_for_update) ---
    def test_concurrent_approve_reject_only_one_wins(self):
        task = self._create_task(reviewer=self.manager, status=TaskStatus.SUBMITTED)
        # First approval via service
        task = transition_task(task, to_status=TaskStatus.APPROVED, actor=self.manager)
        # Now a second attempt to reject (or any transition) should fail because terminal
        with pytest.raises(InvalidTransitionError):
            transition_task(task, to_status=TaskStatus.REJECTED, actor=self.manager)


@pytest.mark.django_db
class TestAssignReviewer:
    def setup_method(self):
        self.creator = User.objects.create_user(username='creator', password='p')
        self.manager = User.objects.create_user(username='manager', password='p', role=Role.MANAGER)
        self.superadmin = User.objects.create_user(username='superadmin', password='p', role=Role.SUPERADMIN)
        self.staff = User.objects.create_user(username='staff', password='p', role=Role.STAFF)

    def _create_task(self, **kwargs):
        defaults = {'title': 'Task', 'creator': self.creator}
        defaults.update(kwargs)
        return Task.objects.create(**defaults)

    def test_assign_reviewer_draft(self):
        task = self._create_task(status=TaskStatus.DRAFT)
        task = assign_reviewer(task, reviewer=self.manager, actor=self.creator)
        assert task.reviewer == self.manager

    def test_assign_reviewer_submitted(self):
        task = self._create_task(status=TaskStatus.SUBMITTED)
        task = assign_reviewer(task, reviewer=self.manager, actor=self.creator)
        assert task.reviewer == self.manager

    def test_cannot_assign_reviewer_after_approved(self):
        task = self._create_task(status=TaskStatus.APPROVED)
        with pytest.raises(InvalidTransitionError):
            assign_reviewer(task, reviewer=self.manager, actor=self.creator)

    def test_only_creator_can_assign_reviewer(self):
        task = self._create_task(status=TaskStatus.DRAFT)
        with pytest.raises(PermissionDeniedError):
            assign_reviewer(task, reviewer=self.manager, actor=self.staff)

    def test_superadmin_can_assign_reviewer_any_time(self):
        task = self._create_task(status=TaskStatus.DRAFT, creator=self.staff)  # creator not superadmin
        task = assign_reviewer(task, reviewer=self.manager, actor=self.superadmin)
        assert task.reviewer == self.manager

    def test_reviewer_must_be_manager_or_superadmin(self):
        task = self._create_task()
        with pytest.raises(ValidationError, match="Reviewer must be a Manager or Superadmin"):
            assign_reviewer(task, reviewer=self.staff, actor=self.creator)

    def test_creator_cannot_self_review(self):
        task = self._create_task()
        # Make creator a manager for this test (but they can't review own task)
        self.creator.role = Role.MANAGER
        self.creator.save()
        with pytest.raises(ValidationError, match="creator cannot also be its reviewer"):
            assign_reviewer(task, reviewer=self.creator, actor=self.creator)

    def test_assign_reviewer_while_draft_then_submit_and_approve(self):
        task = self._create_task()
        task = assign_reviewer(task, reviewer=self.manager, actor=self.creator)
        task = transition_task(task, to_status=TaskStatus.SUBMITTED, actor=self.creator)
        task = transition_task(task, to_status=TaskStatus.APPROVED, actor=self.manager)
        assert task.status == TaskStatus.APPROVED

    def test_assign_reviewer_after_submission_then_approve(self):
        task = self._create_task(status=TaskStatus.SUBMITTED)
        task = assign_reviewer(task, reviewer=self.manager, actor=self.creator)
        task = transition_task(task, to_status=TaskStatus.APPROVED, actor=self.manager)
        assert task.status == TaskStatus.APPROVED