from django.views.generic import TemplateView, RedirectView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from apps.tasks.selectors import (
    get_user_created_tasks,
    get_user_review_tasks,
    get_all_tasks,
    get_dashboard_counts,
)
from .mixins import RoleRequiredMixin
from apps.users.models import Role

class DashboardRedirectView(LoginRequiredMixin, RedirectView):
    """Redirects to the user's role‑specific dashboard."""
    def get_redirect_url(self, *args, **kwargs):
        user = self.request.user
        if user.is_superadmin:
            return reverse_lazy('dashboard:admin')
        elif user.is_manager:
            return reverse_lazy('dashboard:manager')
        else:
            return reverse_lazy('dashboard:staff')

class StaffDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/staff.html'
    required_role = Role.STAFF

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['tasks'] = get_user_created_tasks(user)
        context['counts'] = get_dashboard_counts(user)
        return context

class ManagerDashboardView(RoleRequiredMixin, TemplateView):
    template_name = 'dashboard/manager.html'
    required_role = Role.MANAGER

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['created_tasks'] = get_user_created_tasks(user)
        context['review_tasks'] = get_user_review_tasks(user)
        context['counts'] = get_dashboard_counts(user)
        return context

class AdminDashboardView(RoleRequiredMixin, TemplateView):
    template_name = 'dashboard/admin.html'
    required_role = Role.SUPERADMIN

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['all_tasks'] = get_all_tasks()
        # Superadmins can also see all users maybe, but we'll keep it simple
        return context