from rest_framework import permissions, status
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from accounts.serializers import (
    CurrentUserSerializer,
    CustomTokenObtainPairSerializer,
    LogoutSerializer,
    RegisterSerializer,
    AdminUserSerializer,
    AdminUserWriteSerializer,
)
from accounts.models import User, UserRole
from accounts.permissions import IsApplicationAdmin, IsSystemAdmin
from organizations.models import Organization
from organizations.admin_serializers import AdminOrganizationSerializer
from organizations.serializers import OrganizationSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


class CurrentUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = CurrentUserSerializer(request.user)
        return Response(serializer.data)


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "organization": user.organization_id,
            },
            status=status.HTTP_201_CREATED,
        )


class ActiveOrganizationsView(ListAPIView):
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Organization.objects.filter(is_active=True).order_by("name")


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            refresh_token = RefreshToken(
                serializer.validated_data["refresh"]
            )
            refresh_token.blacklist()
        except TokenError:
            return Response(
                {"detail": "Refresh token không hợp lệ hoặc đã hết hạn."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"detail": "Đăng xuất thành công."},
            status=status.HTTP_200_OK,
        )


class AdminUserListCreateView(APIView):
    permission_classes = [IsApplicationAdmin]

    def get_queryset(self, user):
        queryset = User.objects.select_related("organization", "department").order_by(
            "email"
        )

        if user.role == UserRole.SYSTEM_ADMIN:
            return queryset

        return queryset.filter(organization_id=user.organization_id)

    def get(self, request):
        serializer = AdminUserSerializer(self.get_queryset(request.user), many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = AdminUserWriteSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            AdminUserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class AdminUserDetailView(APIView):
    permission_classes = [IsApplicationAdmin]

    def get_object(self, request, user_id):
        queryset = User.objects.select_related("organization", "department")

        if request.user.role != UserRole.SYSTEM_ADMIN:
            queryset = queryset.filter(organization_id=request.user.organization_id)

        try:
            return queryset.get(id=user_id)
        except User.DoesNotExist as exc:
            raise NotFound("Không tìm thấy người dùng trong phạm vi quản trị.") from exc

    def patch(self, request, user_id):
        user = self.get_object(request, user_id)
        serializer = AdminUserWriteSerializer(
            user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        updated_user = serializer.save()
        return Response(AdminUserSerializer(updated_user).data)


class AdminOrganizationListCreateView(APIView):
    permission_classes = [IsSystemAdmin]

    def get(self, request):
        organizations = Organization.objects.order_by("name")
        return Response(AdminOrganizationSerializer(organizations, many=True).data)

    def post(self, request):
        serializer = AdminOrganizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AdminOrganizationDetailView(APIView):
    permission_classes = [IsSystemAdmin]

    def patch(self, request, organization_id):
        try:
            organization = Organization.objects.get(id=organization_id)
        except Organization.DoesNotExist as exc:
            raise NotFound("Không tìm thấy tổ chức.") from exc

        serializer = AdminOrganizationSerializer(
            organization,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
