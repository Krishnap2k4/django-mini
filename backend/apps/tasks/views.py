from rest_framework import viewsets, permissions, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import CursorPagination, PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.shortcuts import get_object_or_404

from .models import Task, TaskComment, TaskAttachment, TaskStatusHistory
from .serializers import (
    TaskSerializer, TaskCreateSerializer, TaskUpdateSerializer,
    AssignReviewerSerializer, SubmitTaskSerializer, ApproveRejectSerializer,
    TaskCommentSerializer, TaskAttachmentSerializer, TaskStatusHistorySerializer
)
from .services import transition_task, assign_reviewer as assign_reviewer_service
from apps.core.permissions import (
    IsSuperAdmin, IsCreatorOrSuperAdmin, CanSubmitTask,
    CanAssignReviewer, IsAssignedReviewerOrSuperAdmin
)
from apps.core.exceptions import InvalidTransitionError, PermissionDeniedError


class TaskPagination(CursorPagination):
    ordering = '-created_at'
    page_size = 20

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.select_related('creator', 'reviewer').prefetch_related('assignees').all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'priority', 'creator', 'reviewer', 'assignees']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'due_date', 'priority']
    ordering = ['-created_at']
    pagination_class = TaskPagination

    def get_permissions(self):
        # Base permission: authenticated
        permission_classes = [permissions.IsAuthenticated]
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes.append(IsCreatorOrSuperAdmin)
        elif self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]  # anyone authenticated can create
        elif self.action in ['retrieve', 'list']:
            permission_classes = [permissions.IsAuthenticated]  # anyone can view (filter by ownership later)
        return [p() for p in permission_classes]

    def get_serializer_class(self):
        if self.action == 'create':
            return TaskCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TaskUpdateSerializer
        return TaskSerializer

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[CanSubmitTask])
    def submit(self, request, pk=None):
        task = self.get_object()
        try:
            transition_task(task, to_status='SUBMITTED', actor=request.user)
        except InvalidTransitionError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionDeniedError as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
        return Response({'status': 'SUBMITTED'})

    @action(detail=True, methods=['post'], permission_classes=[CanAssignReviewer])
    def assign_reviewer(self, request, pk=None):
        task = self.get_object()
        serializer = AssignReviewerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reviewer = serializer.validated_data['reviewer']
        try:
            assign_reviewer_service(task, reviewer=reviewer, actor=request.user)
        except InvalidTransitionError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionDeniedError as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
        return Response({'status': 'reviewer assigned'})

    @action(detail=True, methods=['post'], permission_classes=[IsAssignedReviewerOrSuperAdmin])
    def approve(self, request, pk=None):
        task = self.get_object()
        serializer = ApproveRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        remarks = serializer.validated_data.get('remarks', '')
        try:
            transition_task(task, to_status='APPROVED', actor=request.user, remarks=remarks)
        except InvalidTransitionError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionDeniedError as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
        return Response({'status': 'APPROVED'})

    @action(detail=True, methods=['post'], permission_classes=[IsAssignedReviewerOrSuperAdmin])
    def reject(self, request, pk=None):
        task = self.get_object()
        serializer = ApproveRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        remarks = serializer.validated_data.get('remarks', '')
        try:
            transition_task(task, to_status='REJECTED', actor=request.user, remarks=remarks)
        except InvalidTransitionError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionDeniedError as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
        return Response({'status': 'REJECTED'})

class TaskCommentViewSet(viewsets.ModelViewSet):
    serializer_class = TaskCommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        task_id = self.kwargs['task_pk']
        return TaskComment.objects.filter(task_id=task_id)

    def perform_create(self, serializer):
        task = get_object_or_404(Task, pk=self.kwargs['task_pk'])
        # Permission: must be creator, assignee, or reviewer (or superadmin)
        user = self.request.user
        if not (user.is_superadmin or task.creator_id == user.id or task.assignees.filter(pk=user.id).exists() or task.reviewer_id == user.id):
            raise PermissionDeniedError("You do not have permission to comment on this task.")
        serializer.save(author=user, task=task)


class TaskAttachmentViewSet(viewsets.ModelViewSet):
    serializer_class = TaskAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        task_id = self.kwargs['task_pk']
        return TaskAttachment.objects.filter(task_id=task_id)

    def perform_create(self, serializer):
        task = get_object_or_404(Task, pk=self.kwargs['task_pk'])
        user = self.request.user
        if not (user.is_superadmin or task.creator_id == user.id or task.assignees.filter(pk=user.id).exists()):
            raise PermissionDeniedError("Only creator or assignees can attach files.")
        file = self.request.FILES['file']
        serializer.save(
            uploaded_by=user,
            task=task,
            original_filename=file.name,
            file_size=file.size
        )


class TaskStatusHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TaskStatusHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        task_id = self.kwargs['task_pk']
        return TaskStatusHistory.objects.filter(task_id=task_id)


class DashboardCountsView(viewsets.ViewSet):
    """Returns cached per-user dashboard aggregate counts."""
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        from .cache import get_dashboard_counts
        counts = get_dashboard_counts(request.user)
        return Response(counts)