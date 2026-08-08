from rest_framework import serializers

from chats.models import ChatMessage, ChatSession


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "role",
            "content",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


class ChatSessionSerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = [
            "id",
            "title",
            "is_active",
            "message_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "is_active",
            "message_count",
            "created_at",
            "updated_at",
        ]

    def get_message_count(self, session):
        return session.messages.count()


class ChatSessionDetailSerializer(ChatSessionSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta(ChatSessionSerializer.Meta):
        fields = ChatSessionSerializer.Meta.fields + ["messages"]


class AskSerializer(serializers.Serializer):
    question = serializers.CharField(
        max_length=2000,
        trim_whitespace=True,
    )
    session_id = serializers.IntegerField(
        required=False,
        min_value=1,
    )
    limit = serializers.IntegerField(
        required=False,
        default=5,
        min_value=1,
        max_value=10,
    )
