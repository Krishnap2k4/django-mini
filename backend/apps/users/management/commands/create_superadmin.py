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
        username = options['username']

        if User.objects.filter(username=username).exists():
            self.stderr.write(self.style.ERROR(
                f"User '{username}' already exists. Use Django admin to edit."
            ))
            return

        user = User.objects.create_user(
            username=username,
            email=options['email'],
            password=options['password'],
            role=Role.SUPERADMIN,
            department=options['department'],
            is_active=True,
            is_staff=True,
            is_superuser=True,
        )
        self.stdout.write(self.style.SUCCESS(f"Superadmin '{user.username}' created."))