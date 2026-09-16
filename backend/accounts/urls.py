from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from accounts.views import (
    ActiveOrganizationsView,
    AdminOrganizationDetailView,
    AdminOrganizationListCreateView,
    AdminUserDetailView,
    AdminUserListCreateView,
    CurrentUserView,
    CustomTokenObtainPairView,
    LogoutView,
    RegisterView,
)


urlpatterns = [
    path("login/", CustomTokenObtainPairView.as_view(), name="jwt-login"),
    path("register/", RegisterView.as_view(), name="register"),
    path("organizations/", ActiveOrganizationsView.as_view(), name="active-organizations"),
    path("refresh/", TokenRefreshView.as_view(), name="jwt-refresh"),
    path("verify/", TokenVerifyView.as_view(), name="jwt-verify"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("logout/", LogoutView.as_view(), name="jwt-logout"),
    path("admin/users/", AdminUserListCreateView.as_view(), name="admin-users"),
    path("admin/users/<int:user_id>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("admin/organizations/", AdminOrganizationListCreateView.as_view(), name="admin-organizations"),
    path("admin/organizations/<int:organization_id>/", AdminOrganizationDetailView.as_view(), name="admin-organization-detail"),
]
