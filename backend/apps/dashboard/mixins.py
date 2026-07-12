from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from apps.users.models import Role

class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    required_role = None

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        if self.required_role == Role.STAFF:
            # Any authenticated staff/manager/superadmin can view staff dashboard
            return True
        elif self.required_role == Role.MANAGER:
            return user.is_manager   # manager or superadmin
        elif self.required_role == Role.SUPERADMIN:
            return user.is_superadmin
        return False

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return redirect('dashboard:redirect')  # we'll create a redirect view
        return super().handle_no_permission()