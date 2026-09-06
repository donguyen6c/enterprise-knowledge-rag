from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class UserRole(models.TextChoices):
    SYSTEM_ADMIN = "SYSTEM_ADMIN", "System Admin"
    ORG_ADMIN = "ORG_ADMIN", "Organization Admin"
    EMPLOYEE = "EMPLOYEE", "Employee"


class User(AbstractUser):
    email = models.EmailField(unique=True)
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="users", null=True, blank=True,)
    department = models.ForeignKey("organizations.Department",on_delete=models.SET_NULL, related_name="users", null=True, blank=True,)
    role = models.CharField( max_length=30, choices=UserRole.choices, default=UserRole.EMPLOYEE,)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def clean(self) -> None:
        super().clean()

        if (self.department_id and self.organization_id != self.department.organization_id):
            raise ValidationError(
                { "department": ("Phòng ban phải thuộc cùng tổ chức với người dùng.") }
            )

    def __str__(self) -> str:
        return self.email
