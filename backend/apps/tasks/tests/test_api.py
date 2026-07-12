import json
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.urls import reverse
from apps.users.models import User, Role
from apps.tasks.models import Task, TaskStatus, TaskComment, TaskAttachment, TaskStatusHistory

class TaskAPITests(APITestCase):
    def setUp(self):
        # Create users
        self.creator = User.objects.create_user(username='creator', password='testpass')
        self.assignee1 = User.objects.create_user(username='assignee1', password='testpass')
        self.assignee2 = User.objects.create_user(username='assignee2', password='testpass')
        self.manager = User.objects.create_user(username='manager', password='testpass', role=Role.MANAGER)
        self.superadmin = User.objects.create_user(username='superadmin', password='testpass', role=Role.SUPERADMIN)
        self.random_staff = User.objects.create_user(username='staff', password='testpass')
        
        # Tasks
        self.draft_task = Task.objects.create(title='Draft Task', description='desc', creator=self.creator)
        self.submitted_task = Task.objects.create(title='Submitted Task', creator=self.creator, status=TaskStatus.SUBMITTED, reviewer=self.manager)
        self.approved_task = Task.objects.create(title='Approved Task', creator=self.creator, status=TaskStatus.APPROVED)

    def get_token(self, user):
        # Helper to login and return access token
        url = reverse('token_obtain_pair')
        resp = self.client.post(url, {'username': user.username, 'password': 'testpass'}, format='json')
        return resp.data['access']

    def auth_client(self, user):
        token = self.get_token(user)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        return self.client

    # --- Task List / Create ---
    def test_list_tasks_as_creator(self):
        self.auth_client(self.creator)
        url = reverse('task-list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # The creator should see all tasks? In our current implementation, list is not filtered by user. That's okay for now.
        self.assertGreaterEqual(len(resp.data['results']), 3)

    def test_create_task(self):
        self.auth_client(self.creator)
        url = reverse('task-list')
        data = {'title': 'New Task', 'description': 'test'}
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.count(), 4)

    # --- Task Detail / Update ---
    def test_update_draft_as_creator(self):
        self.auth_client(self.creator)
        url = reverse('task-detail', args=[self.draft_task.pk])
        data = {'title': 'Updated Title'}
        resp = self.client.patch(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.draft_task.refresh_from_db()
        self.assertEqual(self.draft_task.title, 'Updated Title')

    def test_update_submitted_as_creator_forbidden(self):
        self.auth_client(self.creator)
        url = reverse('task-detail', args=[self.submitted_task.pk])
        data = {'title': 'Should fail'}
        resp = self.client.patch(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # --- Submit ---
    def test_submit_draft_as_creator(self):
        self.auth_client(self.creator)
        url = reverse('task-submit', args=[self.draft_task.pk])
        resp = self.client.post(url, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.draft_task.refresh_from_db()
        self.assertEqual(self.draft_task.status, TaskStatus.SUBMITTED)

    def test_submit_draft_as_assignee(self):
        self.draft_task.assignees.add(self.assignee1)
        self.auth_client(self.assignee1)
        url = reverse('task-submit', args=[self.draft_task.pk])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_submit_draft_as_random_staff_forbidden(self):
        self.auth_client(self.random_staff)
        url = reverse('task-submit', args=[self.draft_task.pk])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # --- Assign Reviewer ---
    def test_assign_reviewer_as_creator(self):
        self.auth_client(self.creator)
        url = reverse('task-assign-reviewer', args=[self.draft_task.pk])
        data = {'reviewer': self.manager.pk}
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.draft_task.refresh_from_db()
        self.assertEqual(self.draft_task.reviewer, self.manager)

    def test_assign_reviewer_to_submitted_task(self):
        self.auth_client(self.creator)
        url = reverse('task-assign-reviewer', args=[self.submitted_task.pk])
        data = {'reviewer': self.manager.pk}
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_assign_reviewer_as_non_creator_forbidden(self):
        self.auth_client(self.assignee1)
        url = reverse('task-assign-reviewer', args=[self.draft_task.pk])
        data = {'reviewer': self.manager.pk}
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # --- Approve / Reject ---
    def test_approve_as_assigned_reviewer(self):
        self.auth_client(self.manager)
        url = reverse('task-approve', args=[self.submitted_task.pk])
        resp = self.client.post(url, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.submitted_task.refresh_from_db()
        self.assertEqual(self.submitted_task.status, TaskStatus.APPROVED)

    def test_approve_as_non_reviewer_manager_denied(self):
        other_mgr = User.objects.create_user(username='othermgr', password='testpass', role=Role.MANAGER)
        self.auth_client(other_mgr)
        url = reverse('task-approve', args=[self.submitted_task.pk])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_approve_as_superadmin(self):
        self.auth_client(self.superadmin)
        url = reverse('task-approve', args=[self.submitted_task.pk])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # --- Comments ---
    def test_add_comment_as_creator(self):
        self.auth_client(self.creator)
        url = reverse('task-comments-list', args=[self.draft_task.pk])
        data = {'content': 'My comment'}
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TaskComment.objects.count(), 1)

    def test_add_comment_as_assignee(self):
        self.draft_task.assignees.add(self.assignee1)
        self.auth_client(self.assignee1)
        url = reverse('task-comments-list', args=[self.draft_task.pk])
        data = {'content': 'Assignee comment'}
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_add_comment_as_random_user_denied(self):
        self.auth_client(self.random_staff)
        url = reverse('task-comments-list', args=[self.draft_task.pk])
        data = {'content': 'Unauthorized'}
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # --- Attachments ---
    def test_upload_attachment_as_creator(self):
        self.auth_client(self.creator)
        url = reverse('task-attachments-list', args=[self.draft_task.pk])
        file = SimpleUploadedFile("test.pdf", b"file_content", content_type="application/pdf")
        data = {'file': file}
        resp = self.client.post(url, data, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TaskAttachment.objects.count(), 1)

    def test_upload_attachment_as_non_creator_denied(self):
        self.auth_client(self.random_staff)
        url = reverse('task-attachments-list', args=[self.draft_task.pk])
        file = SimpleUploadedFile("test.pdf", b"file_content", content_type="application/pdf")
        data = {'file': file}
        resp = self.client.post(url, data, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # --- History ---
    def test_history_view(self):
        TaskStatusHistory.objects.create(task=self.draft_task, to_status=TaskStatus.DRAFT, changed_by=self.creator)
        self.auth_client(self.creator)
        url = reverse('task-history-list', args=[self.draft_task.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 1)   # was `resp.data`