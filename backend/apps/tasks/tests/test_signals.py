import pytest
from django.db.models.signals import m2m_changed
from apps.users.models import User, Role
from apps.tasks.models import Task, TaskStatus, TaskStatusHistory
from apps.notifications.models import Notification
from apps.tasks.services import transition_task, assign_reviewer

@pytest.mark.django_db
class TestSignals:
    def setup_method(self):
        self.creator = User.objects.create_user(username='creator', password='p')
        self.assignee = User.objects.create_user(username='assignee', password='p')
        self.manager = User.objects.create_user(username='manager', password='p', role=Role.MANAGER)
        self.superadmin = User.objects.create_user(username='superadmin', password='p', role=Role.SUPERADMIN)

    def test_status_change_creates_history(self):
        task = Task.objects.create(title='Test', creator=self.creator)
        transition_task(task, to_status=TaskStatus.SUBMITTED, actor=self.creator)
        assert TaskStatusHistory.objects.filter(task=task, to_status=TaskStatus.SUBMITTED).exists()

    def test_status_change_notifies_recipients(self):
        task = Task.objects.create(title='Notify test', creator=self.creator)
        task.assignees.add(self.assignee)
        task.reviewer = self.manager
        task.save()

        # Submit
        transition_task(task, to_status=TaskStatus.SUBMITTED, actor=self.creator)
        # Notifications should be created for assignee and reviewer (not creator because they acted)
        assert Notification.objects.filter(recipient=self.assignee, notification_type='SUBMITTED').exists()
        assert Notification.objects.filter(recipient=self.manager, notification_type='SUBMITTED').exists()
        assert not Notification.objects.filter(recipient=self.creator, notification_type='SUBMITTED').exists()

    def test_approve_notifies_creator(self):
        task = Task.objects.create(title='Approve test', creator=self.creator, reviewer=self.manager, status=TaskStatus.SUBMITTED)
        transition_task(task, to_status=TaskStatus.APPROVED, actor=self.manager)
        assert Notification.objects.filter(recipient=self.creator, notification_type='APPROVED').exists()

    def test_reviewer_assigned_notifies_reviewer(self):
        task = Task.objects.create(title='Assign reviewer', creator=self.creator)
        assign_reviewer(task, reviewer=self.manager, actor=self.creator)
        assert Notification.objects.filter(recipient=self.manager, notification_type='REVIEWER_ASSIGNED_DRAFT').exists()

    def test_assignee_added_notifies_assignee(self):
        task = Task.objects.create(title='Assign test', creator=self.creator)
        task.assignees.add(self.assignee)  # triggers m2m_changed
        assert Notification.objects.filter(recipient=self.assignee, notification_type='ASSIGNED').exists()