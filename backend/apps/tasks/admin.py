from django.contrib import admin
from .models import Task, TaskComment, TaskAttachment, TaskStatusHistory


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'creator', 'status', 'priority', 'created_at')
    list_filter = ('status', 'priority')
    search_fields = ('title', 'description')
    raw_id_fields = ('creator', 'reviewer')


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ('task', 'author', 'created_at')
    search_fields = ('content',)


@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ('task', 'uploaded_by', 'original_filename', 'file_size', 'uploaded_at')


@admin.register(TaskStatusHistory)
class TaskStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('task', 'from_status', 'to_status', 'changed_by', 'changed_at')
    list_filter = ('to_status',)