from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'notification_type', 'task', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('message',)
    raw_id_fields = ('recipient', 'task')
