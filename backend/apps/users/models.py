from django.contrib.auth.models import AbstractUser
from django.db import models

class Role(models.TextChoices):
    STAFF = "STAFF", "Staff"
    MANAGER = "MANAGER", "Manager"
    SUPERADMIN = "SUPERADMIN", "Super Admin"

class User(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STAFF,
        db_index=True
    )
    department = models.CharField(max_length=100, blank=True)
    is_active_employee = models.BooleanField(default=True)

    @property
    def is_manager(self):
        return self.role in (Role.MANAGER, Role.SUPERADMIN)

    @property
    def is_superadmin(self):
        return self.role == Role.SUPERADMIN

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"