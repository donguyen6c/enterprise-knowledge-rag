from django.db.models import Q
from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.models import UserRole
from documents.models import Document


class IsDocumentManagerOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        if request.user.role == UserRole.SYSTEM_ADMIN:
            return True

        return request.user.role == UserRole.ORG_ADMIN and request.user.organization_id is not None and request.user.organization.is_active


class CanModifyDocument(BasePermission):

    def has_object_permission(self, request, view, document):
        user = request.user

        if request.method in SAFE_METHODS:
            return True

        if user.role == UserRole.SYSTEM_ADMIN:
            return True

        if user.role != UserRole.ORG_ADMIN:
            return False

        return user.organization_id == document.organization_id and document.organization.is_active


def accessible_documents_for_user(user):

    queryset = (Document.objects.select_related("organization", "category", "uploaded_by",)
        .prefetch_related("permissions")
        .filter(is_active=True,organization__is_active=True,)
    )

    if not user.is_authenticated:
        return queryset.none()

    if user.role == UserRole.SYSTEM_ADMIN:
        return queryset

    if user.organization_id is None:
        return queryset.none()

    organization_queryset = queryset.filter(organization_id=user.organization_id)

    if user.role == UserRole.ORG_ADMIN:
        return organization_queryset.filter(
            ~Q(visibility=Document.Visibility.PRIVATE)
            | Q(uploaded_by_id=user.id)
        ).distinct()

    access_filter = (
        Q(visibility=Document.Visibility.ORGANIZATION)
        | Q( visibility=Document.Visibility.PRIVATE, uploaded_by_id=user.id,)
        | Q(visibility=Document.Visibility.ROLE, permissions__role=user.role, permissions__can_view=True,)
    )

    if user.department_id is not None:
        access_filter |= Q(visibility=Document.Visibility.DEPARTMENT,
            permissions__department_id=user.department_id,
            permissions__can_view=True,
        )

    return organization_queryset.filter(access_filter).distinct()


def user_can_download_document(user, document):
    if user.role == UserRole.SYSTEM_ADMIN:
        return True

    if user.organization_id != document.organization_id:
        return False

    if not document.is_active or not document.organization.is_active:
        return False

    if user.role == UserRole.ORG_ADMIN:
        return document.visibility != Document.Visibility.PRIVATE or document.uploaded_by_id == user.id

    if document.visibility == Document.Visibility.ORGANIZATION:
        return True

    if document.visibility == Document.Visibility.PRIVATE:
        return document.uploaded_by_id == user.id

    if document.visibility == Document.Visibility.ROLE:
        return document.permissions.filter(role=user.role, can_view=True, can_download=True,).exists()

    if document.visibility == Document.Visibility.DEPARTMENT:
        if user.department_id is None:
            return False

        return document.permissions.filter(department_id=user.department_id, can_view=True, can_download=True,).exists()

    return False
