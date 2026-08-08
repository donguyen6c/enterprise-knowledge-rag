from django.contrib import admin
from .models import ( Document, DocumentCategory, DocumentPermission, DocumentChunk)

class DocumentPermissionInline(admin.TabularInline):
    model = DocumentPermission
    extra = 1


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "organization",
        "is_active",
        "created_at",
    )
    search_fields = (
        "name",
        "organization__name",
    )
    list_filter = (
        "organization",
        "is_active",
    )


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "organization",
        "category",
        "uploaded_by",
        "status",
        "visibility",
        "created_at",
    )
    search_fields = (
        "title",
        "organization__name",
        "uploaded_by__email",
    )
    list_filter = (
        "organization",
        "category",
        "status",
        "visibility",
        "is_active",
    )
    readonly_fields = (
        "original_filename",
        "file_size",
        "created_at",
        "updated_at",
    )
    inlines = [DocumentPermissionInline]


@admin.register(DocumentPermission)
class DocumentPermissionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "document",
        "department",
        "role",
        "can_view",
        "can_download",
    )
    list_filter = (
        "role",
        "can_view",
        "can_download",
    )

@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "document",
        "chunk_index",
        "page_number",
        "section_title",
        "token_count",
        "created_at",
    ]

    list_filter = [
        "document",
        "created_at",
    ]

    search_fields = [
        "document__title",
        "section_title",
        "content",
    ]

    readonly_fields = [
        "created_at",
    ]

    ordering = [
        "document",
        "chunk_index",
    ]