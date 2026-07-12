from django.conf import settings
from django.db import models


class TaskStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"


class Task(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_tasks",
    )
    assignees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="assigned_tasks",
        blank=True,
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="tasks_to_review",
        null=True,
        blank=True,
        limit_choices_to={"role__in": ["MANAGER", "SUPERADMIN"]},
    )
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.DRAFT,
        db_index=True,
    )
    priority = models.CharField(
        max_length=10,
        choices=[("LOW", "Low"), ("MEDIUM", "Medium"), ("HIGH", "High")],
        default="MEDIUM",
    )
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["creator", "status"]),
            models.Index(fields=["reviewer", "status"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class TaskComment(models.Model):
    task = models.ForeignKey(
        Task, on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"Comment by {self.author} on {self.task}"


def attachment_upload_path(instance, filename):
    return f"tasks/{instance.task_id}/attachments/{filename}"


class TaskAttachment(models.Model):
    task = models.ForeignKey(
        Task, on_delete=models.CASCADE, related_name="attachments"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    file = models.FileField(upload_to=attachment_upload_path)
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.original_filename} ({self.file_size} bytes)"


class TaskStatusHistory(models.Model):
    task = models.ForeignKey(
        Task, on_delete=models.CASCADE, related_name="history"
    )
    from_status = models.CharField(max_length=20, null=True, blank=True)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    remarks = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.task} → {self.to_status}"