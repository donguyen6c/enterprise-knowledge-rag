from django.db import transaction

from documents.models import Document


class DocumentQueueError(Exception):
    pass


def queue_document(document: Document) -> Document:
    if document.status == Document.Status.PROCESSING:
        raise DocumentQueueError("Tài liệu đang được xử lý.")

    if document.status == Document.Status.ARCHIVED:
        raise DocumentQueueError("Không thể xử lý tài liệu đã lưu trữ.")

    document.status = Document.Status.UPLOADED
    document.error_message = ""
    document.save(update_fields=["status", "error_message", "updated_at"])
    return document


def claim_next_document() -> Document | None:
    with transaction.atomic():
        document = (
            Document.objects.select_for_update(skip_locked=True)
            .filter(status=Document.Status.UPLOADED, is_active=True, organization__is_active=True,)
            .order_by("updated_at", "id")
            .first()
        )

        if document is None:
            return None

        document.status = Document.Status.PROCESSING
        document.error_message = ""
        document.save(update_fields=["status", "error_message", "updated_at"])

    return document
