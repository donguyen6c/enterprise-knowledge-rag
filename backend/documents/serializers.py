from pathlib import Path

from rest_framework import serializers

from accounts.models import UserRole
from documents.models import (
    Document,
    DocumentCategory,
    DocumentChunk,
    DocumentPermission,
)
from organizations.models import Organization


class DocumentCategorySerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.filter(is_active=True), required=False,)
    organization_name = serializers.CharField(source="organization.name", read_only=True,)

    class Meta:
        model = DocumentCategory
        fields = [
            "id",
            "organization",
            "organization_name",
            "name",
            "description",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "organization_name", "created_at"]

    def validate(self, attrs):
        user = self.context["request"].user
        organization = attrs.get("organization")

        if user.role == UserRole.SYSTEM_ADMIN:
            if self.instance is None and organization is None:
                raise serializers.ValidationError(
                    {"organization": "System Admin phải chọn một tổ chức."}
                )

            return attrs

        if user.organization_id is None or not user.organization.is_active:
            raise serializers.ValidationError(
                "Tài khoản không thuộc một tổ chức đang hoạt động."
            )

        if organization and organization.id != user.organization_id:
            raise serializers.ValidationError(
                {"organization": "Không thể chọn tổ chức khác."}
            )

        return attrs


class DocumentPermissionSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True,)

    class Meta:
        model = DocumentPermission
        fields = [
            "id",
            "department",
            "department_name",
            "role",
            "can_view",
            "can_download",
        ]


class DocumentSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.filter(is_active=True), required=False,)
    organization_name = serializers.CharField(source="organization.name", read_only=True,)
    category_name = serializers.CharField(source="category.name", read_only=True,)
    uploaded_by_email = serializers.EmailField(source="uploaded_by.email", read_only=True,)
    permissions = DocumentPermissionSerializer(many=True, read_only=True)

    file = serializers.FileField(write_only=True, required=False)
    download_url = serializers.SerializerMethodField()
    chunk_count = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "organization",
            "organization_name",
            "category",
            "category_name",
            "uploaded_by_email",
            "title",
            "description",
            "file",
            "download_url",
            "original_filename",
            "file_size",
            "status",
            "visibility",
            "error_message",
            "chunk_count",
            "is_active",
            "created_at",
            "updated_at",
            "permissions",
        ]
        read_only_fields = [
            "id",
            "organization_name",
            "uploaded_by_email",
            "download_url",
            "original_filename",
            "file_size",
            "status",
            "error_message",
            "chunk_count",
            "created_at",
            "updated_at",
            "permissions",
        ]

    def get_download_url(self, document):
        request = self.context.get("request")

        if request is None:
            return None

        return request.build_absolute_uri(
            f"/api/documents/{document.id}/download/"
        )

    def get_chunk_count(self, document):
        chunk_count = getattr(document, "chunk_count", None)

        if chunk_count is not None:
            return chunk_count

        return document.chunks.count()

    def validate_file(self, uploaded_file):
        extension = Path(uploaded_file.name).suffix.lower()

        if extension not in {".pdf", ".docx"}:
            raise serializers.ValidationError("Chỉ chấp nhận file PDF hoặc DOCX.")

        max_size = 20 * 1024 * 1024

        if uploaded_file.size > max_size:
            raise serializers.ValidationError("Dung lượng file không được vượt quá 20 MB.")

        return uploaded_file

    def validate(self, attrs):
        user = self.context["request"].user
        requested_organization = attrs.get("organization")
        category = attrs.get(
            "category",
            self.instance.category if self.instance else None,
        )

        if self.instance is None and attrs.get("file") is None:
            raise serializers.ValidationError(
                {"file": "Phải tải lên một file PDF hoặc DOCX."}
            )

        if self.instance is not None:
            if (
                requested_organization
                and requested_organization.id != self.instance.organization_id
            ):
                raise serializers.ValidationError(
                    {
                        "organization": (
                            "Không thể chuyển tài liệu sang tổ chức khác qua API."
                        )
                    }
                )

            effective_organization = self.instance.organization
        elif user.role == UserRole.SYSTEM_ADMIN:
            effective_organization = requested_organization

            if effective_organization is None and category is not None:
                effective_organization = category.organization

            if effective_organization is None:
                raise serializers.ValidationError(
                    {"organization": "System Admin phải chọn một tổ chức."}
                )
        else:
            if user.organization_id is None or not user.organization.is_active:
                raise serializers.ValidationError(
                    "Tài khoản không thuộc một tổ chức đang hoạt động."
                )

            if (
                requested_organization
                and requested_organization.id != user.organization_id
            ):
                raise serializers.ValidationError(
                    {"organization": "Không thể chọn tổ chức khác."}
                )

            effective_organization = user.organization

        if (
            category is not None
            and category.organization_id != effective_organization.id
        ):
            raise serializers.ValidationError(
                {"category": "Danh mục không thuộc tổ chức của tài liệu."}
            )

        return attrs


class DocumentChunkSerializer(serializers.ModelSerializer):
    document_title = serializers.CharField(source="document.title", read_only=True,)
    has_embedding = serializers.SerializerMethodField()

    class Meta:
        model = DocumentChunk
        fields = [
            "id",
            "document",
            "document_title",
            "chunk_index",
            "page_number",
            "section_title",
            "token_count",
            "content",
            "metadata",
            "has_embedding",
            "created_at",
        ]
        read_only_fields = fields

    def get_has_embedding(self, chunk):
        return chunk.embedding is not None
