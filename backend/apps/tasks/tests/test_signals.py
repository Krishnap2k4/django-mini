import pytest
from django.db.models.signals import m2m_changed
from unittest.mock import patch
from apps.users.models import User, Role
from apps.tasks.models import Task, TaskStatus, TaskStatusHistory
from apps.tasks.services import transition_task, assign_reviewer

@pytest.mark.django_db(transaction=True)
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

    @patch('apps.tasks.signals.send_task_notification.delay')
    def test_status_change_notifies_recipients(self, mock_delay):
        task = Task.objects.create(title='Notify test', creator=self.creator)
        task.assignees.add(self.assignee)
        task.reviewer = self.manager
        task.save()

        # Submit
        transition_task(task, to_status=TaskStatus.SUBMITTED, actor=self.creator)
        # Notifications should be sent to assignee and reviewer (not creator because they acted)
        
        # We need to verify that mock_delay was called with specific arguments
        called_args = [call.args for call in mock_delay.call_args_list]
        assert (self.assignee.id, task.id, TaskStatus.SUBMITTED) in called_args
        assert (self.manager.id, task.id, TaskStatus.SUBMITTED) in called_args
        assert (self.creator.id, task.id, TaskStatus.SUBMITTED) not in called_args

    @patch('apps.tasks.signals.send_task_notification.delay')
    def test_approve_notifies_creator(self, mock_delay):
        task = Task.objects.create(title='Approve test', creator=self.creator, reviewer=self.manager, status=TaskStatus.SUBMITTED)
        transition_task(task, to_status=TaskStatus.APPROVED, actor=self.manager)
        mock_delay.assert_called_with(self.creator.id, task.id, TaskStatus.APPROVED)

    @patch('apps.tasks.signals.send_task_notification.delay')
    def test_reviewer_assigned_notifies_reviewer(self, mock_delay):
        task = Task.objects.create(title='Assign reviewer', creator=self.creator)
        assign_reviewer(task, reviewer=self.manager, actor=self.creator)
        mock_delay.assert_called_with(self.manager.id, task.id, 'REVIEWER_ASSIGNED_DRAFT')

    @patch('apps.tasks.signals.send_task_notification.delay')
    def test_assignee_added_notifies_assignee(self, mock_delay):
        task = Task.objects.create(title='Assign test', creator=self.creator)
        task.assignees.add(self.assignee)  # triggers m2m_changed
        mock_delay.assert_called_with(self.assignee.id, task.id, 'ASSIGNED')