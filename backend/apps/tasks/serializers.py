from rest_framework import serializers
from django.core.validators import FileExtensionValidator
from apps.users.models import User
from .models import Task, TaskComment, TaskAttachment, TaskStatusHistory, TaskStatus


class TaskSerializer(serializers.ModelSerializer):
    # Display fields (read-only for list/detail)
    creator_name = serializers.CharField(source='creator.username', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.username', read_only=True)
    assignees_names = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'creator', 'creator_name',
            'assignees', 'assignees_names', 'reviewer', 'reviewer_name',
            'status', 'priority', 'due_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['creator', 'created_at', 'updated_at', 'status']

    def get_assignees_names(self, obj):
        return [user.username for user in obj.assignees.all()]

    def validate_assignees(self, value):
        if value and len(value) > 2:
            raise serializers.ValidationError("A task can have at most 2 assignees.")
        return value

    def validate_reviewer(self, value):
        if value and not value.is_manager:
            raise serializers.ValidationError("Reviewer must be a Manager or Superadmin.")
        return value

    def validate(self, attrs):
        # Enforce that reviewer cannot be the creator (except on creation we don't have instance yet)
        instance = getattr(self, 'instance', None)
        if instance:
            creator = instance.creator
        else:
            creator = self.context['request'].user  # creator will be set on create
        reviewer = attrs.get('reviewer')
        if reviewer and reviewer == creator:
            raise serializers.ValidationError({"reviewer": "A task's creator cannot also be its reviewer."})
        return attrs


class TaskCreateSerializer(TaskSerializer):
    class Meta(TaskSerializer.Meta):
        read_only_fields = ['creator', 'created_at', 'updated_at', 'status']

    def create(self, validated_data):
        validated_data['creator'] = self.context['request'].user
        return super().create(validated_data)


class TaskUpdateSerializer(TaskSerializer):
    """For PATCH requests – all fields optional, but status is not editable here."""
    class Meta(TaskSerializer.Meta):
        read_only_fields = ['creator', 'created_at', 'updated_at', 'status']


class AssignReviewerSerializer(serializers.Serializer):
    reviewer = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role__in=['MANAGER', 'SUPERADMIN']))


class SubmitTaskSerializer(serializers.Serializer):
    pass  # no extra data needed


class ApproveRejectSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True)


class TaskCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)
    # Make task read‑only; it comes from the URL
    task = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = TaskComment
        fields = ['id', 'task', 'author', 'author_name', 'content', 'created_at']
        read_only_fields = ['author', 'created_at']

    def create(self, validated_data):
        return super().create(validated_data)


class TaskAttachmentSerializer(serializers.ModelSerializer):
    task = serializers.PrimaryKeyRelatedField(read_only=True)
    original_filename = serializers.CharField(read_only=True)
    file_size = serializers.IntegerField(read_only=True)

    class Meta:
        model = TaskAttachment
        fields = ['id', 'task', 'uploaded_by', 'file', 'original_filename', 'file_size', 'uploaded_at']
        read_only_fields = ['uploaded_by', 'uploaded_at']

    def validate_file(self, value):
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError("File size must be under 10MB.")
        allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx', 'xls', 'xlsx']
        ext = value.name.split('.')[-1].lower()
        if ext not in allowed_extensions:
            raise serializers.ValidationError(f"Unsupported file type: .{ext}")
        return value


class TaskStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source='changed_by.username', read_only=True)

    class Meta:
        model = TaskStatusHistory
        fields = ['id', 'task', 'from_status', 'to_status', 'changed_by', 'changed_by_name', 'remarks', 'changed_at']
        read_only_fields = ['changed_at']