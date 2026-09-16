from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from accounts.models import User, UserRole
from organizations.models import Organization


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


class RegisterSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.filter(is_active=True),
        required=True,
    )
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "organization",
        ]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email này đã được sử dụng.")
        return value

    def validate(self, attrs):
        organization = attrs.get("organization")

        if organization is not None and not organization.is_active:
            raise serializers.ValidationError(
                {"organization": "Tổ chức đã bị vô hiệu hóa."}
            )

        return attrs

    def create(self, validated_data):
        organization = validated_data.pop("organization")
        password = validated_data.pop("password")

        user = User.objects.create_user(
            organization=organization,
            role=UserRole.EMPLOYEE,
            password=password,
            **validated_data,
        )

        try:
            user.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc

        return user


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class AdminUserSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "role",
            "organization",
            "organization_name",
            "department",
            "department_name",
            "is_active",
            "date_joined",
        ]
        read_only_fields = fields


class AdminUserWriteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=False)
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "role",
            "organization",
            "is_active",
        ]
        extra_kwargs = {
            "role": {"required": False},
            "is_active": {"required": False},
        }

    def validate(self, attrs):
        actor = self.context["request"].user

        if actor.role == UserRole.ORG_ADMIN:
            if actor.organization_id is None or not actor.organization.is_active:
                raise serializers.ValidationError(
                    "Tài khoản không thuộc một tổ chức đang hoạt động."
                )

            if any(field in attrs for field in ("organization", "is_active")):
                raise serializers.ValidationError(
                    "Organization Admin không được thay đổi tổ chức hoặc trạng thái tài khoản."
                )

            requested_role = attrs.get(
                "role",
                self.instance.role if self.instance else UserRole.EMPLOYEE,
            )

            if requested_role not in {UserRole.EMPLOYEE, UserRole.ORG_ADMIN}:
                raise serializers.ValidationError(
                    {"role": "Organization Admin chỉ được gán Employee hoặc Organization Admin."}
                )

            if self.instance and self.instance.id == actor.id and "role" in attrs:
                raise serializers.ValidationError(
                    {"role": "Không thể thay đổi vai trò của chính tài khoản đang đăng nhập."}
                )

            attrs["organization"] = actor.organization

        if self.instance and self.instance.id == actor.id and "role" in attrs:
            raise serializers.ValidationError(
                {"role": "Không thể thay đổi vai trò của chính tài khoản đang đăng nhập."}
            )

        effective_role = attrs.get(
            "role",
            self.instance.role if self.instance else UserRole.EMPLOYEE,
        )
        effective_organization = attrs.get(
            "organization",
            self.instance.organization if self.instance else None,
        )

        if effective_role != UserRole.SYSTEM_ADMIN and effective_organization is None:
            raise serializers.ValidationError(
                {"organization": "Người dùng không phải System Admin phải thuộc một tổ chức."}
            )

        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)

        for field, value in validated_data.items():
            setattr(instance, field, value)

        if password:
            instance.set_password(password)

        instance.full_clean()
        instance.save()
        return instance
