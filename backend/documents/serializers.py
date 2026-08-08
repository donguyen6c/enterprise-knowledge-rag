from pathlib import Path
from rest_framework import serializers
from documents.models import (Document, DocumentCategory, DocumentPermission,)


class DocumentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentCategory
        fields = [ "id", "name", "description","is_active","created_at",]
        read_only_fields = [ "id", "created_at",]

class DocumentPermissionSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField( source="department.name", read_only=True,)

    class Meta:
        model = DocumentPermission
        fields = [ "id", "department", "department_name", "role", "can_view", "can_download",]


class DocumentSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField( source="organization.name", read_only=True,)
    category_name = serializers.CharField( source="category.name", read_only=True,)
    uploaded_by_email = serializers.EmailField( source="uploaded_by.email", read_only=True,)
    permissions = DocumentPermissionSerializer( many=True, read_only=True,)

    # Không công khai trực tiếp đường dẫn /media/.
    # Upload được phép, nhưng API response không trả URL file vật lý.
    file = serializers.FileField( write_only=True, required=False,)

    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
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
            "created_at",
            "updated_at",
            "permissions",
        ]

    def get_download_url(self, document):
        request = self.context.get("request")

        if request is None:
            return None

        return request.build_absolute_uri(f"/api/documents/{document.id}/download/")

    def validate_file(self, uploaded_file):
        extension = Path(uploaded_file.name).suffix.lower()

        if extension not in {".pdf", ".docx"}:
            raise serializers.ValidationError("Chỉ chấp nhận file PDF hoặc DOCX.")

        max_size = 20 * 1024 * 1024

        if uploaded_file.size > max_size:
            raise serializers.ValidationError("Dung lượng file không được vượt quá 20 MB.")

        return uploaded_file

    def validate_category(self, category):
        request = self.context["request"]
        user = request.user

        if ( user.role != "SYSTEM_ADMIN" and category.organization_id != user.organization_id
        ):
            raise serializers.ValidationError("Danh mục không thuộc organization của người dùng.")

        return category