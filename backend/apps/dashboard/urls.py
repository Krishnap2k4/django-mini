from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Auth
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    # Dashboard home
    path('', views.DashboardHomeView.as_view(), name='home'),

    # Users
    path('users/', views.UserListView.as_view(), name='user-list'),
    path('users/autocomplete/', views.UserAutocompleteView.as_view(), name='user-autocomplete'),
    path('users/create/', views.UserCreateView.as_view(), name='user-create'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    path('users/<int:pk>/edit/', views.UserUpdateView.as_view(), name='user-edit'),
    path('users/<int:pk>/delete/', views.UserDeleteView.as_view(), name='user-delete'),

    # Tasks
    path('tasks/', views.TaskListView.as_view(), name='task-list'),
    path('tasks/create/', views.TaskCreateView.as_view(), name='task-create'),
    path('tasks/<int:pk>/', views.TaskDetailView.as_view(), name='task-detail'),
    path('tasks/<int:pk>/edit/', views.TaskUpdateView.as_view(), name='task-edit'),
    path('tasks/<int:pk>/delete/', views.TaskDeleteView.as_view(), name='task-delete'),
    path('tasks/<int:pk>/transition/', views.TaskTransitionView.as_view(), name='task-transition'),
    path('tasks/<int:pk>/comment/', views.TaskCommentCreateView.as_view(), name='task-comment'),
    path('tasks/<int:pk>/attachment/', views.TaskAttachmentUploadView.as_view(), name='task-attachment'),
    path('tasks/<int:pk>/attachment/<int:attachment_pk>/delete/', views.TaskAttachmentDeleteView.as_view(), name='task-attachment-delete'),
    path('tasks/<int:pk>/assignees/', views.TaskAssigneesUpdateView.as_view(), name='task-assignees'),

    # Notifications
    path('notifications/', views.NotificationListView.as_view(), name='notification-list'),
    path('notifications/send/', views.SendNotificationView.as_view(), name='notification-send'),
    path('notifications/<int:pk>/mark-read/', views.NotificationMarkReadView.as_view(), name='notification-mark-read'),
    path('notifications/mark-all-read/', views.NotificationMarkAllReadView.as_view(), name='notification-mark-all-read'),

    # Audit
    path('audit/', views.AuditLogView.as_view(), name='audit-log'),

    # Actions
    path('trigger-digest/', views.TriggerDailyDigestView.as_view(), name='trigger-digest'),
]