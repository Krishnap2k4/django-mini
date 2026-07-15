from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect


class SuperAdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Only allows SUPERADMIN users. Redirects others to login."""
    login_url = '/panel/login/'

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superadmin

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return redirect('/panel/login/?error=forbidden')
        return super().handle_no_permission()