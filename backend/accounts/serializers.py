from rest_framework import serializers
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from accounts.models import User, UserRole


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user: User):
        token = super().get_token(user)

        token["email"] = user.email
        token["username"] = user.username
        token["role"] = user.role
        token["organization_id"] = user.organization_id
        token["department_id"] = user.department_id

        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user

        if ( user.role != UserRole.SYSTEM_ADMIN and user.organization_id and not user.organization.is_active
        ):
            raise AuthenticationFailed("Tổ chức của tài khoản đã bị khóa.")

        data["user"] = {"id": user.id, "email": user.email, "username": user.username, "first_name": user.first_name, "last_name": user.last_name, "role": user.role, "organization_id": user.organization_id, "department_id": user.department_id, }

        return data


class CurrentUserSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True,)
    department_name = serializers.CharField(source="department.name", read_only=True,)

    class Meta:
        model = User
        fields = ["id", "email", "username", "first_name", "last_name", "role", "organization", "organization_name", "department", "department_name", "is_active",]
        read_only_fields = fields


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
