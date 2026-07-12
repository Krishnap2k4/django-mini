import pytest
from apps.users.models import User, Role

@pytest.mark.django_db
class TestUserModel:
    def test_create_user(self):
        user = User.objects.create_user(username='staff1', password='test123')
        assert user.role == Role.STAFF
        assert not user.is_manager
        assert not user.is_superadmin

    def test_manager_role(self):
        user = User.objects.create_user(username='mgr', password='test123', role=Role.MANAGER)
        assert user.is_manager
        assert not user.is_superadmin

    def test_superadmin_role(self):
        user = User.objects.create_user(username='admin', password='test123', role=Role.SUPERADMIN)
        assert user.is_manager
        assert user.is_superadmin