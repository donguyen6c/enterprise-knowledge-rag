from django.conf import settings
from django.db import models


class ChatSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_sessions",)
    title = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-created_at"]
        indexes = [
            models.Index(
                fields=["user", "is_active", "-updated_at"],
                name="chat_session_user_idx",
            ),
        ]

    def __str__(self):
        return self.title or f"Chat #{self.id}"


class ChatMessage(models.Model):
    class Role(models.TextChoices):
        USER = "USER", "User"
        ASSISTANT = "ASSISTANT", "Assistant"

    session = models.ForeignKey( ChatSession, on_delete=models.CASCADE, related_name="messages",)
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(
                fields=["session", "created_at"],
                name="chat_message_session_idx",
            ),
        ]

    def __str__(self):
        return f"{self.session_id} - {self.role}"
