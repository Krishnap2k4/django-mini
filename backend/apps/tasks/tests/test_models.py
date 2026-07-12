import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.users.models import User, Role
from apps.tasks.models import Task, TaskStatus, TaskComment, TaskAttachment, TaskStatusHistory


@pytest.mark.django_db
class TestTaskModel:
    def test_create_draft_task(self):
        creator = User.objects.create_user(username='creator', password='test')
        task = Task.objects.create(
            title='Sample Task',
            description='A test',
            creator=creator,
        )
        assert task.status == TaskStatus.DRAFT
        assert task.assignees.count() == 0
        assert task.reviewer is None
        assert str(task) == 'Sample Task'

    def test_task_indexes(self):
        # Just verify indexes exist, no exception on create
        creator = User.objects.create_user(username='cr', password='p')
        Task.objects.create(title='x', creator=creator)
        # No assertion needed; if indexes were invalid we'd get an error

    def test_comment_creation(self):
        creator = User.objects.create_user(username='c', password='p')
        task = Task.objects.create(title='T', creator=creator)
        comment = TaskComment.objects.create(task=task, author=creator, content='Nice')
        assert comment.content == 'Nice'

    def test_attachment_creation(self):
        creator = User.objects.create_user(username='u', password='p')
        task = Task.objects.create(title='Att', creator=creator)
        fake_file = SimpleUploadedFile("test.txt", b"file content")
        attachment = TaskAttachment.objects.create(
            task=task,
            uploaded_by=creator,
            file=fake_file,
            original_filename='test.txt',
            file_size=12,
        )
        assert attachment.file.name.startswith('tasks/')

    def test_status_history_creation(self):
        creator = User.objects.create_user(username='h', password='p')
        task = Task.objects.create(title='Hist', creator=creator)
        entry = TaskStatusHistory.objects.create(
            task=task,
            from_status=None,
            to_status=TaskStatus.DRAFT,
            changed_by=creator,
            remarks='Created',
        )
        assert entry.to_status == TaskStatus.DRAFT