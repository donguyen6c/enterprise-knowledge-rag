from pathlib import Path

from django.http import FileResponse, Http404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from accounts.models import UserRole
from documents.models import Document, DocumentCategory
from documents.permissions import (CanModifyDocument,IsDocumentManagerOrReadOnly,accessible_documents_for_user,user_can_download_document,)
from documents.serializers import (DocumentCategorySerializer, DocumentSerializer,)


class DocumentCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentCategorySerializer
    permission_classes = [ permissions.IsAuthenticated, IsDocumentManagerOrReadOnly,]

    def get_queryset(self):
        user = self.request.user

        if user.role == UserRole.SYSTEM_ADMIN:
            return DocumentCategory.objects.all()

        if user.organization_id is None:
            return DocumentCategory.objects.none()

        return DocumentCategory.objects.filter(organization_id=user.organization_id, is_active=True,)

    def perform_create(self, serializer):
        serializer.save( organization=self.request.user.organization,)


class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    parser_classes = [ MultiPartParser, FormParser,]
    permission_classes = [ permissions.IsAuthenticated, IsDocumentManagerOrReadOnly, CanModifyDocument,]

    def get_queryset(self):
        return accessible_documents_for_user(self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        uploaded_file = self.request.FILES.get("file")

        if user.role == UserRole.SYSTEM_ADMIN:
            category = serializer.validated_data["category"]
            organization = category.organization
        else:
            organization = user.organization

        serializer.save(
            organization=organization,
            uploaded_by=user,
            original_filename=( uploaded_file.name if uploaded_file else ""),
            file_size=( uploaded_file.size if uploaded_file else 0),
            status="UPLOADED",
            error_message="",
        )

    @action(detail=True, methods=["get"], url_path="download", permission_classes=[permissions.IsAuthenticated],)
    def download(self, request, pk=None):
        try:
            document = accessible_documents_for_user( request.user).get(pk=pk)
        except Document.DoesNotExist as exc:
            raise Http404("Không tìm thấy tài liệu.") from exc

        if not user_can_download_document( request.user,document,):
            return Response( {"detail": "Bạn không có quyền tải tài liệu này."}, status=status.HTTP_403_FORBIDDEN,)

        if not document.file:
            raise Http404("Document chưa có file.")

        try:
            file_handle = document.file.open("rb")
        except FileNotFoundError as exc:
            raise Http404("File vật lý không còn tồn tại.") from exc

        download_name = (document.original_filename or Path(document.file.name).name)

        return FileResponse(file_handle, as_attachment=False, filename=download_name,)