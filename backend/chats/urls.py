from django.urls import path
from rest_framework.routers import DefaultRouter

from chats.views import AskView, ChatSessionViewSet


router = DefaultRouter()
router.register("sessions", ChatSessionViewSet, basename="chat-session")

urlpatterns = [
    path("ask/", AskView.as_view(), name="chat-ask"),
    *router.urls,
]
