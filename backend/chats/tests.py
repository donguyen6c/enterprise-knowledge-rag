from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from chats.models import ChatSession


class ChatSessionAccessTests(APITestCase):
    def test_user_only_lists_own_active_sessions(self):
        user = User.objects.create_user(
            username="chat-user",
            email="chat-user@example.com",
        )
        other_user = User.objects.create_user(
            username="other-chat-user",
            email="other-chat-user@example.com",
        )
        own_session = ChatSession.objects.create(user=user, title="Own session")
        ChatSession.objects.create(user=user, title="Archived", is_active=False)
        ChatSession.objects.create(user=other_user, title="Other session")
        self.client.force_authenticate(user=user)

        response = self.client.get("/api/chats/sessions/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [session["id"] for session in response.data],
            [own_session.id],
        )
