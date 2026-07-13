from django.urls import path, include
# from rest_framework_nested import routers  # need drf-nested-routers? We'll do nested manually.
from .views import (
    TaskViewSet, TaskCommentViewSet, TaskAttachmentViewSet,
    TaskStatusHistoryViewSet, DashboardCountsView
)

# We'll use a simple router for the tasks, then manually add nested routes
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'tasks', TaskViewSet, basename='task')

# Nested routes for comments, attachments, history
urlpatterns = router.urls

# Manually add nested paths using path() with task_pk
urlpatterns += [
    path('tasks/<int:task_pk>/comments/', TaskCommentViewSet.as_view({'get': 'list', 'post': 'create'}), name='task-comments-list'),
    path('tasks/<int:task_pk>/comments/<int:pk>/', TaskCommentViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='task-comments-detail'),
    path('tasks/<int:task_pk>/attachments/', TaskAttachmentViewSet.as_view({'get': 'list', 'post': 'create'}), name='task-attachments-list'),
    path('tasks/<int:task_pk>/attachments/<int:pk>/', TaskAttachmentViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'}), name='task-attachments-detail'),
    path('tasks/<int:task_pk>/history/', TaskStatusHistoryViewSet.as_view({'get': 'list'}), name='task-history-list'),
    path('tasks/<int:task_pk>/history/<int:pk>/', TaskStatusHistoryViewSet.as_view({'get': 'retrieve'}), name='task-history-detail'),
    path('dashboard/counts/', DashboardCountsView.as_view({'get': 'list'}), name='dashboard-counts'),
]