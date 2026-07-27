from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)

    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE,
        related_name="users", null=True, blank=True,)

    department = models.ForeignKey("organizations.Department", on_delete=models.SET_NULL,
        related_name="users", null=True, blank=True, )

    class Role(models.TextChoices):
        SYSTEM_ADMIN = "SYSTEM_ADMIN", "System Admin"
        ORG_ADMIN = "ORG_ADMIN", "Organization Admin"
        EMPLOYEE = "EMPLOYEE", "Employee"

    role = models.CharField( max_length=30, choices=Role.choices, default=Role.EMPLOYEE,)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self) -> str:
        return self.email