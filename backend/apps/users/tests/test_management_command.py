import pytest
from django.core.management import call_command
from io import StringIO
from apps.users.models import User, Role

@pytest.mark.django_db
class TestCreateSuperadminCommand:
    def test_create_superadmin(self):
        out = StringIO()
        call_command(
            'create_superadmin',
            username='supreme',
            email='supreme@admin.com',
            password='supersecret',
            stdout=out
        )
        assert 'Superadmin' in out.getvalue()
        user = User.objects.get(username='supreme')
        assert user.role == Role.SUPERADMIN

    def test_duplicate_username(self):
        User.objects.create_user(username='dup', password='p')
        out = StringIO()
        err = StringIO()                     # capture stderr here
        call_command(
            'create_superadmin',
            username='dup',
            email='dup@admin.com',
            password='secret',
            stdout=out,
            stderr=err,                     # pass the same buffer
        )
        assert 'already exists' in err.getvalue()   # check the captured stderr