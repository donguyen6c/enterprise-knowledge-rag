from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from pgvector.django import VectorField

from accounts.models import UserRole


class DocumentCategory(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="document_categories",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="unique_document_category_per_organization",
            )
        ]
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.organization.name} - {self.name}"


def document_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()
    unique_filename = f"{uuid4().hex}{extension}"

    return (
        f"organizations/{instance.organization_id}/"
        f"documents/{unique_filename}"
    )


class Document(models.Model):
    class Status(models.TextChoices):
        UPLOADED = "UPLOADED", "Uploaded"
        PROCESSING = "PROCESSING", "Processing"
        READY = "READY", "Ready"
        FAILED = "FAILED", "Failed"
        ARCHIVED = "ARCHIVED", "Archived"

    class Visibility(models.TextChoices):
        ORGANIZATION = "ORGANIZATION", "Entire organization"
        DEPARTMENT = "DEPARTMENT", "Selected departments"
        ROLE = "ROLE", "Selected roles"
        PRIVATE = "PRIVATE", "Uploader only"

    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="documents",)
    category = models.ForeignKey(DocumentCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="documents",)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploaded_documents",)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    file = models.FileField(upload_to=document_upload_path,validators=[FileExtensionValidator(allowed_extensions=["pdf", "docx"])],)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPLOADED,)
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.ORGANIZATION,)

    original_filename = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveBigIntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self) -> None:
        super().clean()

        if (
            self.category_id
            and self.organization_id != self.category.organization_id
        ):
            raise ValidationError(
                {"category": "Danh mục phải thuộc cùng tổ chức với tài liệu."}
            )

    def __str__(self) -> str:
        return self.title


class DocumentPermission(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="permissions",)
    department = models.ForeignKey( "organizations.Department", on_delete=models.CASCADE, related_name="document_permissions", null=True, blank=True,)
    role = models.CharField(max_length=30, choices=UserRole.choices, blank=True)

    can_view = models.BooleanField(default=True)
    can_download = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(department__isnull=False) | ~models.Q(role="")),
                name="document_permission_requires_department_or_role",
            )
        ]

    def clean(self) -> None:
        super().clean()
        target_count = int(self.department_id is not None) + int(bool(self.role))

        if target_count != 1:
            raise ValidationError(
                "Mỗi quyền tài liệu phải chọn đúng một phòng ban hoặc một vai trò."
            )

        if (
            self.department_id
            and self.department.organization_id != self.document.organization_id
        ):
            raise ValidationError(
                "Phòng ban được cấp quyền phải thuộc tổ chức của tài liệu."
            )

    def __str__(self) -> str:
        target = self.department or self.role
        return f"{self.document.title} - {target}"


class DocumentChunk(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chunks",)
    chunk_index = models.PositiveIntegerField()
    content = models.TextField()
    page_number = models.PositiveIntegerField(null=True, blank=True)
    section_title = models.CharField(max_length=500, blank=True)
    token_count = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    embedding = VectorField(dimensions=384, null=True, blank=True)

    class Meta:
        ordering = ["document_id", "chunk_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"],
                name="unique_chunk_index_per_document",
            )
        ]
        indexes = [
            models.Index(
                fields=["document", "chunk_index"],
                name="document_chunk_lookup_idx",
            )
        ]

    def __str__(self):
        return f"{self.document.title} - Chunk {self.chunk_index}"
