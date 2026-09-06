from pathlib import Path

from django.db.models import Count
from django.http import FileResponse, Http404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from accounts.models import UserRole
from documents.models import Document, DocumentCategory, DocumentChunk
from documents.permissions import (
    CanModifyDocument,
    IsDocumentManagerOrReadOnly,
    accessible_documents_for_user,
    user_can_download_document,
)
from documents.serializers import (
    DocumentCategorySerializer,
    DocumentChunkSerializer,
    DocumentSerializer,
)
from documents.services.jobs import DocumentQueueError, queue_document
from documents.services.media_paths import normalize_document_file_path


class DocumentCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentCategorySerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsDocumentManagerOrReadOnly,
    ]

    def get_queryset(self):
        user = self.request.user

        if user.role == UserRole.SYSTEM_ADMIN:
            return DocumentCategory.objects.all()

        if user.organization_id is None:
            return DocumentCategory.objects.none()

        return DocumentCategory.objects.filter(
            organization_id=user.organization_id,
            organization__is_active=True,
            is_active=True,
        )

    def perform_create(self, serializer):
        user = self.request.user

        if user.role == UserRole.SYSTEM_ADMIN:
            serializer.save()
            return

        serializer.save(organization=user.organization)


class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [
        permissions.IsAuthenticated,
        IsDocumentManagerOrReadOnly,
        CanModifyDocument,
    ]

    def get_queryset(self):
        return accessible_documents_for_user(self.request.user).annotate(
            chunk_count=Count("chunks"),
        )

    def perform_create(self, serializer):
        user = self.request.user
        uploaded_file = self.request.FILES.get("file")

        if user.role == UserRole.SYSTEM_ADMIN:
            organization = serializer.validated_data.get("organization")
            category = serializer.validated_data.get("category")

            if organization is None and category is not None:
                organization = category.organization
        else:
            organization = user.organization

        if organization is None:
            raise ValidationError(
                {"organization": "Không xác định được tổ chức của tài liệu."}
            )

        document = serializer.save(
            organization=organization,
            uploaded_by=user,
            original_filename=uploaded_file.name,
            file_size=uploaded_file.size,
            status=Document.Status.UPLOADED,
            error_message="",
        )
        normalize_document_file_path(
            document,
            apply=True,
            replace_target=True,
        )

    def perform_update(self, serializer):
        uploaded_file = self.request.FILES.get("file")

        if uploaded_file is None:
            serializer.save()
            return

        document = serializer.save(
            original_filename=uploaded_file.name,
            file_size=uploaded_file.size,
            status=Document.Status.UPLOADED,
            error_message="",
        )
        normalize_document_file_path(
            document,
            apply=True,
            replace_target=True,
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="download",
        permission_classes=[permissions.IsAuthenticated],
    )
    def download(self, request, pk=None):
        try:
            document = accessible_documents_for_user(request.user).get(pk=pk)
        except Document.DoesNotExist as exc:
            raise Http404("Không tìm thấy tài liệu.") from exc

        if not user_can_download_document(request.user, document):
            return Response(
                {"detail": "Bạn không có quyền tải tài liệu này."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not document.file:
            raise Http404("Document chưa có file.")

        try:
            file_handle = document.file.open("rb")
        except FileNotFoundError as exc:
            raise Http404("File vật lý không còn tồn tại.") from exc

        download_name = document.original_filename or Path(document.file.name).name

        return FileResponse(
            file_handle,
            as_attachment=False,
            filename=download_name,
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="chunks",
        permission_classes=[permissions.IsAuthenticated],
    )
    def chunks(self, request, pk=None):
        try:
            document = accessible_documents_for_user(request.user).get(pk=pk)
        except Document.DoesNotExist as exc:
            raise Http404("Không tìm thấy tài liệu.") from exc

        chunks = (
            DocumentChunk.objects.filter(document=document)
            .select_related("document")
            .order_by("chunk_index")
        )
        serializer = DocumentChunkSerializer(chunks, many=True)

        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        url_path="process",
    )
    def process(self, request, pk=None):
        document = self.get_object()

        try:
            queue_document(document)
        except DocumentQueueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = self.get_serializer(document)
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
