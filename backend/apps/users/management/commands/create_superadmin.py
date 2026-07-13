from django.core.management.base import BaseCommand
from apps.users.models import User, Role

class Command(BaseCommand):
    help = "Create a superadmin user (bypasses registration restrictions)."

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True)
        parser.add_argument('--email', required=True)
        parser.add_argument('--password', required=True)
        parser.add_argument('--department', default='')

    def handle(self, *args, **options):
        user, _ = User.objects.get_or_create(username=options['username'])
        user.email = options['email']
        user.role = Role.SUPERADMIN
        user.department = options['department']
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.set_password(options['password'])
        user.save()
        self.stdout.write(self.style.SUCCESS(f"Superadmin '{user.username}' created."))