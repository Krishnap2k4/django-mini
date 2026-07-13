from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    task_title = serializers.CharField(source='task.title', read_only=True, default=None, allow_null=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'task', 'task_title',
            'notification_type', 'message', 'is_read', 'created_at',
        ]
        read_only_fields = [
            'recipient', 'task', 'notification_type', 'message', 'created_at',
        ]
