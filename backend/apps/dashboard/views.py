import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.http import JsonResponse

from apps.users.models import User, Role
from apps.tasks.models import Task, TaskStatus, TaskComment, TaskAttachment, TaskStatusHistory
from apps.tasks.services import transition_task, assign_reviewer
from apps.notifications.models import Notification
from apps.notifications.tasks import send_task_notification, send_daily_digest
from apps.core.exceptions import InvalidTransitionError, PermissionDeniedError
from django.http import JsonResponse

from .mixins import SuperAdminRequiredMixin
from .forms import (
    UserForm, TaskForm, TaskCommentForm, TaskAttachmentForm,
    SendNotificationForm, TaskAssigneesForm,
)


# ── API / Autocomplete ──────────────────────────────────────────────────

class UserAutocompleteView(SuperAdminRequiredMixin, View):
    """AJAX endpoint for TomSelect user search."""
    def get(self, request):
        q = request.GET.get('q', '').strip()
        qs = User.objects.filter(is_active=True)
        if q:
            qs = qs.filter(
                Q(username__icontains=q) |
                Q(email__icontains=q) |
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q)
            )
        # Limit to 50 results so we don't crash
        qs = qs.order_by('username')[:50]
        
        results = [
            {'id': user.pk, 'text': f"{user.username} - {user.get_full_name()}" if user.get_full_name() else user.username}
            for user in qs
        ]
        return JsonResponse({'results': results})


# ── Authentication ──────────────────────────────────────────────────────

class LoginView(View):
    def get(self, request):
        if request.user.is_authenticated and request.user.is_superadmin:
            return redirect('dashboard:home')
        error = request.GET.get('error')
        return render(request, 'dashboard/login.html', {'error': error})

    def post(self, request):
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user and user.is_superadmin:
            login(request, user)
            return redirect('dashboard:home')
        return render(request, 'dashboard/login.html', {
            'error': 'Invalid credentials or insufficient permissions.',
            'username': username,
        })


class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('dashboard:login')


# ── Dashboard Home ──────────────────────────────────────────────────────

class DashboardHomeView(SuperAdminRequiredMixin, View):
    def get(self, request):
        now = timezone.now()

        # Stat cards
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        total_tasks = Task.objects.count()
        tasks_by_status = {
            s: Task.objects.filter(status=s).count()
            for s in [TaskStatus.DRAFT, TaskStatus.SUBMITTED, TaskStatus.APPROVED, TaskStatus.REJECTED]
        }
        pending_reviews = Task.objects.filter(status=TaskStatus.SUBMITTED).count()
        unread_notifications = Notification.objects.filter(is_read=False).count()

        # Chart: Tasks created per day (last 30 days)
        thirty_days_ago = now - timedelta(days=30)
        tasks_per_day = (
            Task.objects.filter(created_at__gte=thirty_days_ago)
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        chart_labels = [entry['day'].strftime('%b %d') for entry in tasks_per_day]
        chart_data = [entry['count'] for entry in tasks_per_day]

        # Chart: Task status distribution
        status_labels = [s.label for s in TaskStatus]
        status_data = [tasks_by_status.get(s.value, 0) for s in TaskStatus]

        # Recent activity (last 10 status changes)
        recent_activity = TaskStatusHistory.objects.select_related(
            'task', 'changed_by'
        ).order_by('-changed_at')[:10]

        # Recent tasks
        recent_tasks = Task.objects.select_related('creator', 'reviewer').order_by('-created_at')[:5]

        context = {
            'total_users': total_users,
            'active_users': active_users,
            'total_tasks': total_tasks,
            'tasks_by_status': tasks_by_status,
            'pending_reviews': pending_reviews,
            'unread_notifications': unread_notifications,
            'chart_labels': json.dumps(chart_labels),
            'chart_data': json.dumps(chart_data),
            'status_labels': json.dumps(status_labels),
            'status_data': json.dumps(status_data),
            'recent_activity': recent_activity,
            'recent_tasks': recent_tasks,
        }
        return render(request, 'dashboard/index.html', context)


# ── User CRUD ───────────────────────────────────────────────────────────

class UserListView(SuperAdminRequiredMixin, View):
    def get(self, request):
        qs = User.objects.all().order_by('-date_joined')

        # Search
        q = request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(username__icontains=q) | Q(email__icontains=q) |
                Q(first_name__icontains=q) | Q(last_name__icontains=q)
            )

        # Filter by role
        role = request.GET.get('role', '')
        if role:
            qs = qs.filter(role=role)

        paginator = Paginator(qs, 15)
        page = paginator.get_page(request.GET.get('page'))

        return render(request, 'dashboard/users/list.html', {
            'page_obj': page,
            'q': q,
            'role': role,
            'roles': Role.choices,
        })


class UserCreateView(SuperAdminRequiredMixin, View):
    def get(self, request):
        form = UserForm()
        return render(request, 'dashboard/users/form.html', {
            'form': form, 'title': 'Create User',
        })

    def post(self, request):
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get('password')
            if not password:
                messages.error(request, 'Password is required for new users.')
                return render(request, 'dashboard/users/form.html', {
                    'form': form, 'title': 'Create User',
                })
            user.set_password(password)
            user.save()
            messages.success(request, f'User "{user.username}" created successfully.')
            return redirect('dashboard:user-list')
        return render(request, 'dashboard/users/form.html', {
            'form': form, 'title': 'Create User',
        })


class UserUpdateView(SuperAdminRequiredMixin, View):
    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        form = UserForm(instance=user)
        return render(request, 'dashboard/users/form.html', {
            'form': form, 'title': f'Edit User: {user.username}', 'editing': True,
        })

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'User "{user.username}" updated successfully.')
            return redirect('dashboard:user-list')
        return render(request, 'dashboard/users/form.html', {
            'form': form, 'title': f'Edit User: {user.username}', 'editing': True,
        })


class UserDeleteView(SuperAdminRequiredMixin, View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        username = user.username
        user.is_active = False
        user.save(update_fields=['is_active'])
        messages.success(request, f'User "{username}" has been deactivated.')
        return redirect('dashboard:user-list')


class UserDetailView(SuperAdminRequiredMixin, View):
    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        created_tasks = Task.objects.filter(creator=user).order_by('-created_at')[:10]
        assigned_tasks = Task.objects.filter(assignees=user).order_by('-created_at')[:10]
        review_tasks = Task.objects.filter(reviewer=user).order_by('-created_at')[:10]
        notifications = Notification.objects.filter(recipient=user).order_by('-created_at')[:10]
        return render(request, 'dashboard/users/detail.html', {
            'profile_user': user,
            'created_tasks': created_tasks,
            'assigned_tasks': assigned_tasks,
            'review_tasks': review_tasks,
            'notifications': notifications,
        })


# ── Task CRUD ───────────────────────────────────────────────────────────

class TaskListView(SuperAdminRequiredMixin, View):
    def get(self, request):
        qs = Task.objects.select_related('creator', 'reviewer').order_by('-created_at')

        # Search
        q = request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

        # Filters
        status = request.GET.get('status', '')
        if status:
            qs = qs.filter(status=status)
        priority = request.GET.get('priority', '')
        if priority:
            qs = qs.filter(priority=priority)

        paginator = Paginator(qs, 15)
        page = paginator.get_page(request.GET.get('page'))

        return render(request, 'dashboard/tasks/list.html', {
            'page_obj': page,
            'q': q,
            'status': status,
            'priority': priority,
            'statuses': TaskStatus.choices,
            'priorities': [('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High')],
        })


class TaskCreateView(SuperAdminRequiredMixin, View):
    def get(self, request):
        form = TaskForm(initial={'creator': request.user})
        return render(request, 'dashboard/tasks/form.html', {
            'form': form, 'title': 'Create Task',
        })

    def post(self, request):
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save()
            messages.success(request, f'Task "{task.title}" created successfully.')
            return redirect('dashboard:task-detail', pk=task.pk)
        return render(request, 'dashboard/tasks/form.html', {
            'form': form, 'title': 'Create Task',
        })


class TaskUpdateView(SuperAdminRequiredMixin, View):
    def get(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        form = TaskForm(instance=task)
        return render(request, 'dashboard/tasks/form.html', {
            'form': form, 'title': f'Edit Task: {task.title}', 'editing': True,
        })

    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        old_status = task.status
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            with transaction.atomic():
                task = form.save()
                # Log status change to audit trail if status was modified
                if task.status != old_status:
                    TaskStatusHistory.objects.create(
                        task=task,
                        from_status=old_status,
                        to_status=task.status,
                        changed_by=request.user,
                        remarks='Status changed via admin edit.',
                    )
            
            # Fire the signal outside the transaction or at the end so listeners can run
            if task.status != old_status:
                from apps.tasks.signals import task_status_changed
                task_status_changed.send(
                    sender=Task,
                    task=task,
                    from_status=old_status,
                    to_status=task.status,
                    actor=request.user,
                    remarks='Status changed via admin edit.',
                )

            messages.success(request, f'Task "{task.title}" updated successfully.')
            return redirect('dashboard:task-detail', pk=task.pk)
        return render(request, 'dashboard/tasks/form.html', {
            'form': form, 'title': f'Edit Task: {task.title}', 'editing': True,
        })


class TaskDeleteView(SuperAdminRequiredMixin, View):
    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        title = task.title
        task.delete()
        messages.success(request, f'Task "{title}" deleted.')
        return redirect('dashboard:task-list')


class TaskDetailView(SuperAdminRequiredMixin, View):
    def get(self, request, pk):
        task = get_object_or_404(
            Task.objects.select_related('creator', 'reviewer')
            .prefetch_related('assignees', 'comments__author', 'attachments__uploaded_by', 'history__changed_by'),
            pk=pk,
        )
        comment_form = TaskCommentForm()
        attachment_form = TaskAttachmentForm()
        assignees_form = TaskAssigneesForm(initial={'assignees': task.assignees.all()})
        return render(request, 'dashboard/tasks/detail.html', {
            'task': task,
            'comment_form': comment_form,
            'attachment_form': attachment_form,
            'assignees_form': assignees_form,
        })


class TaskTransitionView(SuperAdminRequiredMixin, View):
    """POST-only: transition task status via the service layer."""
    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        to_status = request.POST.get('to_status')
        remarks = request.POST.get('remarks', '')
        try:
            transition_task(task, to_status=to_status, actor=request.user, remarks=remarks)
            messages.success(request, f'Task status changed to {to_status}.')
        except (InvalidTransitionError, PermissionDeniedError) as e:
            messages.error(request, str(e))
        return redirect('dashboard:task-detail', pk=pk)


class TaskCommentCreateView(SuperAdminRequiredMixin, View):
    """POST-only: add comment to task."""
    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        form = TaskCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.task = task
            comment.author = request.user
            comment.save()
            messages.success(request, 'Comment added.')
        else:
            messages.error(request, 'Failed to add comment.')
        return redirect('dashboard:task-detail', pk=pk)


class TaskAttachmentUploadView(SuperAdminRequiredMixin, View):
    """POST-only: upload attachment to task."""
    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        form = TaskAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']
            TaskAttachment.objects.create(
                task=task,
                uploaded_by=request.user,
                file=uploaded_file,
                original_filename=uploaded_file.name,
                file_size=uploaded_file.size,
            )
            messages.success(request, f'Attachment "{uploaded_file.name}" uploaded.')
        else:
            messages.error(request, 'Failed to upload attachment.')
        return redirect('dashboard:task-detail', pk=pk)


class TaskAttachmentDeleteView(SuperAdminRequiredMixin, View):
    """POST-only: delete an attachment."""
    def post(self, request, pk, attachment_pk):
        attachment = get_object_or_404(TaskAttachment, pk=attachment_pk, task_id=pk)
        attachment.file.delete(save=False)
        attachment.delete()
        messages.success(request, 'Attachment deleted.')
        return redirect('dashboard:task-detail', pk=pk)


class TaskAssigneesUpdateView(SuperAdminRequiredMixin, View):
    """POST-only: update task assignees."""
    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        form = TaskAssigneesForm(request.POST)
        if form.is_valid():
            task.assignees.set(form.cleaned_data['assignees'])
            messages.success(request, 'Assignees updated.')
        return redirect('dashboard:task-detail', pk=pk)


# ── Notifications ───────────────────────────────────────────────────────

class NotificationListView(SuperAdminRequiredMixin, View):
    def get(self, request):
        qs = Notification.objects.select_related('recipient', 'task').order_by('-created_at')

        # Filters
        ntype = request.GET.get('type', '')
        if ntype:
            qs = qs.filter(notification_type=ntype)
        read = request.GET.get('read', '')
        if read == 'true':
            qs = qs.filter(is_read=True)
        elif read == 'false':
            qs = qs.filter(is_read=False)

        paginator = Paginator(qs, 20)
        page = paginator.get_page(request.GET.get('page'))

        notification_types = (
            Notification.objects.values_list('notification_type', flat=True)
            .distinct().order_by('notification_type')
        )

        return render(request, 'dashboard/notifications/list.html', {
            'page_obj': page,
            'ntype': ntype,
            'read': read,
            'notification_types': notification_types,
        })


class NotificationMarkReadView(SuperAdminRequiredMixin, View):
    """POST-only: mark a single notification as read."""
    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return redirect(request.META.get('HTTP_REFERER', 'dashboard:notification-list'))


class NotificationMarkAllReadView(SuperAdminRequiredMixin, View):
    """POST-only: mark all unread notifications as read."""
    def post(self, request):
        Notification.objects.filter(is_read=False).update(is_read=True)
        messages.success(request, 'All notifications marked as read.')
        return redirect(request.META.get('HTTP_REFERER', 'dashboard:notification-list'))


class SendNotificationView(SuperAdminRequiredMixin, View):
    def get(self, request):
        form = SendNotificationForm()
        return render(request, 'dashboard/notifications/send.html', {'form': form})

    def post(self, request):
        form = SendNotificationForm(request.POST)
        if form.is_valid():
            recipient = form.cleaned_data['recipient']
            message_text = form.cleaned_data['message']
            send_email = form.cleaned_data['send_email']

            # Dispatch background Celery task
            from apps.notifications.tasks import send_custom_notification
            send_custom_notification.delay(recipient.id, message_text, send_email)

            if send_email:
                messages.success(request, f'Notification is being sent and emailed to {recipient.email} in the background.')
            else:
                messages.success(request, f'Notification is being sent to {recipient.username} in the background.')
            
            return redirect('dashboard:notification-list')
        return render(request, 'dashboard/notifications/send.html', {'form': form})


class TriggerDailyDigestView(SuperAdminRequiredMixin, View):
    """POST-only: manually trigger the daily digest Celery task."""
    def post(self, request):
        send_daily_digest.delay()
        messages.success(request, 'Daily digest task has been queued.')
        return redirect('dashboard:home')


# ── Audit Log ───────────────────────────────────────────────────────────

class AuditLogView(SuperAdminRequiredMixin, View):
    def get(self, request):
        qs = TaskStatusHistory.objects.select_related(
            'task', 'changed_by'
        ).order_by('-changed_at')

        # Filters
        status = request.GET.get('status', '')
        if status:
            qs = qs.filter(to_status=status)

        q = request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(task__title__icontains=q) | Q(changed_by__username__icontains=q)
            )

        paginator = Paginator(qs, 20)
        page = paginator.get_page(request.GET.get('page'))

        return render(request, 'dashboard/audit/list.html', {
            'page_obj': page,
            'status': status,
            'q': q,
            'statuses': TaskStatus.choices,
        })