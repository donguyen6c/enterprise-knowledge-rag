from rest_framework.permissions import BasePermission, SAFE_METHODS
from accounts.models import UserRole
from django.db.models import Q
from documents.models import Document

class IsDocumentManagerOrReadOnly(BasePermission):
    """
    Employee chỉ được đọc.
    ORG_ADMIN và SYSTEM_ADMIN được thêm, sửa, xóa.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        return request.user.role in { UserRole.SYSTEM_ADMIN, UserRole.ORG_ADMIN,}


class CanModifyDocument(BasePermission):
    """
    Kiểm tra quyền sửa/xóa trên từng document.
    """

    def has_object_permission(self, request, view, document):
        user = request.user

        if user.role == UserRole.SYSTEM_ADMIN:
            return True

        if user.role != UserRole.ORG_ADMIN:
            return False

        return user.organization_id == document.organization_id

def accessible_documents_for_user(user):
    """
    QuerySet duy nhất dùng cho Document API, Semantic Search và RAG.

    Quan trọng: phải lọc quyền trước khi retrieval.
    """

    queryset = Document.objects.select_related( "organization", "category", "uploaded_by",).prefetch_related("permissions",)

    if not user.is_authenticated:
        return queryset.none()

    if user.role == UserRole.SYSTEM_ADMIN:
        return queryset

    if user.organization_id is None:
        return queryset.none()

    access_filter = (
        Q(visibility="ORGANIZATION")
        | Q( visibility="PRIVATE", uploaded_by_id=user.id,)
        | Q( visibility="ROLE",  permissions__role=user.role, permissions__can_view=True,)
    )

    if user.department_id is not None:
        access_filter |= Q( visibility="DEPARTMENT", permissions__department_id=user.department_id, permissions__can_view=True,)

    return (
        queryset.filter( organization_id=user.organization_id, is_active=True,)
        .filter(access_filter).distinct()
    )


def user_can_download_document(user, document):
    if user.role == UserRole.SYSTEM_ADMIN:
        return True

    if user.organization_id != document.organization_id:
        return False

    if document.visibility == "ORGANIZATION":
        return True

    if document.visibility == "PRIVATE":
        return document.uploaded_by_id == user.id

    if document.visibility == "ROLE":
        return document.permissions.filter(role=user.role, can_view=True, can_download=True,).exists()

    if document.visibility == "DEPARTMENT":
        if user.department_id is None:
            return False

        return document.permissions.filter(department_id=user.department_id, can_view=True, can_download=True,).exists()

    return False