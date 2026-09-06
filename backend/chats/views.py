from django.db import transaction
from django.db.models import Count
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from chats.models import ChatMessage, ChatSession
from chats.serializers import (
    AskSerializer,
    ChatMessageSerializer,
    ChatSessionDetailSerializer,
    ChatSessionSerializer,
)
from rag.services.answering import answer_question


class ChatSessionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = (
            ChatSession.objects.filter(
                user=self.request.user,
                is_active=True,
            )
            .annotate(message_count=Count("messages"))
            .order_by("-updated_at", "-created_at")
        )

        if self.action in {"retrieve", "messages"}:
            queryset = queryset.prefetch_related("messages")

        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ChatSessionDetailSerializer

        return ChatSessionSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        session = self.get_object()
        session.is_active = False
        session.save(update_fields=["is_active", "updated_at"])

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="messages")
    def messages(self, request, pk=None):
        session = self.get_object()
        serializer = ChatMessageSerializer(
            session.messages.all(),
            many=True,
        )

        return Response(serializer.data)


class AskView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = AskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question = serializer.validated_data["question"]
        limit = serializer.validated_data["limit"]
        session_id = serializer.validated_data.get("session_id")

        with transaction.atomic():
            session = self._get_or_create_session(
                user=request.user,
                question=question,
                session_id=session_id,
            )
            conversation_history = list(
                session.messages.order_by(
                    "-created_at",
                    "-id",
                )[:8]
            )
            conversation_history.reverse()
            user_message = ChatMessage.objects.create(
                session=session,
                role=ChatMessage.Role.USER,
                content=question,
            )

        result = answer_question(
            user=request.user,
            question=question,
            limit=limit,
            conversation_history=conversation_history,
        )

        with transaction.atomic():
            assistant_message = ChatMessage.objects.create(
                session=session,
                role=ChatMessage.Role.ASSISTANT,
                content=result.answer,
                metadata={
                    "citations": result.citations,
                    "retrieval_limit": limit,
                    "retrieval_queries": result.retrieval_queries,
                },
            )
            session.save(update_fields=["updated_at"])

        return Response(
            {
                "session": ChatSessionSerializer(session).data,
                "user_message": ChatMessageSerializer(user_message).data,
                "assistant_message": ChatMessageSerializer(assistant_message).data,
                "answer": result.answer,
                "citations": result.citations,
                "retrieval_queries": result.retrieval_queries,
            },
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _get_or_create_session(
        *,
        user,
        question: str,
        session_id: int | None,
    ) -> ChatSession:
        if session_id is None:
            title = question[:80]

            return ChatSession.objects.create(
                user=user,
                title=title,
            )

        try:
            return ChatSession.objects.get(
                id=session_id,
                user=user,
                is_active=True,
            )
        except ChatSession.DoesNotExist:
            raise ValidationError(
                {"session_id": "session_id không hợp lệ."}
            )
