from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User, UserRole
from organizations.models import Department, Organization


class AuthenticationTests(APITestCase):
    def test_login_uses_canonical_trailing_slash_endpoint(self):
        organization = Organization.objects.create(name="Active organization")
        User.objects.create_user(
            username="active-user",
            email="active@example.com",
            password="test-password",
            organization=organization,
            role=UserRole.EMPLOYEE,
        )

        response = self.client.post(
            "/api/auth/login/",
            {"email": "active@example.com", "password": "test-password"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_user_from_locked_organization_cannot_login(self):
        organization = Organization.objects.create(
            name="Locked organization",
            is_active=False,
        )
        User.objects.create_user(
            username="locked-user",
            email="locked@example.com",
            password="test-password",
            organization=organization,
            role=UserRole.EMPLOYEE,
        )

        response = self.client.post(
            "/api/auth/login/",
            {"email": "locked@example.com", "password": "test-password"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_department_must_belong_to_users_organization(self):
        organization = Organization.objects.create(name="Organization A")
        other_organization = Organization.objects.create(name="Organization B")
        department = Department.objects.create(
            organization=other_organization,
            name="Other department",
        )
        user = User(
            username="invalid-user",
            email="invalid@example.com",
            organization=organization,
            department=department,
        )

        with self.assertRaises(ValidationError):
            user.full_clean()
