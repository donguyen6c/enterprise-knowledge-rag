from django.urls import path
from rest_framework_simplejwt.views import (TokenRefreshView, TokenVerifyView,)
from accounts.views import (CurrentUserView, CustomTokenObtainPairView, LogoutView,)


urlpatterns = [
    path("login/", CustomTokenObtainPairView.as_view(), name="jwt-login",),
    path("refresh/", TokenRefreshView.as_view(), name="jwt-refresh",),
    path("verify/",TokenVerifyView.as_view(), name="jwt-verify",),
    path("me/", CurrentUserView.as_view(), name="current-user",),
    path("logout/", LogoutView.as_view(), name="jwt-logout",),
]
