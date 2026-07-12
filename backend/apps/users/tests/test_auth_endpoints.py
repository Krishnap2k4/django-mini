import pytest
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User, Role

@pytest.mark.django_db
class TestAuthEndpoints:
    def setup_method(self):
        self.client = APIClient()
        self.register_url = '/api/v1/auth/register/'
        self.login_url = '/api/v1/auth/login/'
        self.refresh_url = '/api/v1/auth/refresh/'
        self.logout_url = '/api/v1/auth/logout/'          # added

    def test_register_staff(self):
        data = {
            'username': 'newstaff',
            'email': 'new@staff.com',
            'password': 'Str0ngP@ss1',
            'password2': 'Str0ngP@ss1',
            'role': Role.STAFF,
        }
        resp = self.client.post(self.register_url, data, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert 'access' in resp.data
        user = User.objects.get(username='newstaff')
        assert user.role == Role.STAFF

    def test_register_manager(self):
        data = {
            'username': 'newmgr',
            'email': 'mgr@org.com',
            'password': 'Str0ngP@ss1',
            'password2': 'Str0ngP@ss1',
            'role': Role.MANAGER,
        }
        resp = self.client.post(self.register_url, data, format='json')
        assert resp.status_code == status.HTTP_201_CREATED

    def test_register_superadmin_rejected(self):
        data = {
            'username': 'badadmin',
            'email': 'bad@admin.com',
            'password': 'Str0ngP@ss1',
            'password2': 'Str0ngP@ss1',
            'role': Role.SUPERADMIN,
        }
        resp = self.client.post(self.register_url, data, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'role' in resp.data

    def test_register_password_mismatch(self):
        data = {
            'username': 'mismatch',
            'email': 'mm@fail.com',
            'password': 'Str0ngP@ss1',
            'password2': 'WrongP@ss',
        }
        resp = self.client.post(self.register_url, data, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_and_refresh(self):
        user = User.objects.create_user(username='loginuser', password='Str0ngP@ss1')
        user.is_active = True
        user.save()

        # Login
        login_resp = self.client.post(self.login_url, {
            'username': 'loginuser',
            'password': 'Str0ngP@ss1'
        }, format='json')
        assert login_resp.status_code == status.HTTP_200_OK
        assert 'access' in login_resp.data
        assert 'refresh' in login_resp.data

        # Refresh token
        refresh_resp = self.client.post(self.refresh_url, {
            'refresh': login_resp.data['refresh']
        }, format='json')
        assert refresh_resp.status_code == status.HTTP_200_OK
        assert 'access' in refresh_resp.data

    def test_logout_blacklists_refresh(self):
        # Create a fresh user and login
        user = User.objects.create_user(username='logoutuser', password='Str0ngP@ss1')
        login_resp = self.client.post(self.login_url, {
            'username': 'logoutuser',
            'password': 'Str0ngP@ss1'
        }, format='json')
        refresh = login_resp.data['refresh']

        # Logout – should blacklist the refresh token
        resp = self.client.post(self.logout_url, {'refresh': refresh}, format='json')
        assert resp.status_code == status.HTTP_200_OK

        # Try to use the same refresh token again – must be rejected
        refresh_resp = self.client.post(self.refresh_url, {'refresh': refresh}, format='json')
        assert refresh_resp.status_code == status.HTTP_401_UNAUTHORIZED