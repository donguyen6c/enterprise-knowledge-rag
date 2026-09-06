from dataclasses import dataclass
from pathlib import Path
import shutil
from uuid import uuid4

from django.db import transaction

from documents.models import Document


@dataclass(frozen=True)
class DocumentMediaNormalization:
    document_id: int
    current_name: str
    target_name: str
    changed: bool
    source_exists: bool
    target_exists: bool
    applied: bool


def canonical_document_file_name(document: Document) -> str:
    extension = Path(document.file.name or document.original_filename).suffix.lower()

    if extension not in {".pdf", ".docx"}:
        extension = ".pdf"

    return (
        f"organizations/{document.organization_id}/"
        f"documents/{document.id}/original{extension}"
    )


def normalize_document_file_path(
    document: Document,
    *,
    apply: bool = False,
    keep_source: bool = False,
    replace_target: bool = False,
) -> DocumentMediaNormalization:
    current_name = document.file.name if document.file else ""
    target_name = canonical_document_file_name(document) if current_name else ""
    storage = document.file.storage if document.file else None
    changed = bool(current_name and current_name != target_name)
    source_exists = bool(current_name and storage and storage.exists(current_name))
    target_exists = bool(target_name and storage and storage.exists(target_name))

    result = DocumentMediaNormalization(
        document_id=document.id,
        current_name=current_name,
        target_name=target_name,
        changed=changed,
        source_exists=source_exists,
        target_exists=target_exists,
        applied=False,
    )

    if (
        not apply
        or not changed
        or not source_exists
        or (target_exists and not replace_target)
    ):
        return result

    source_path = Path(storage.path(current_name))
    target_path = Path(storage.path(target_name))
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_target = target_path.with_name(
        f".{target_path.name}.{uuid4().hex}.tmp"
    )

    try:
        shutil.copy2(source_path, temporary_target)
        temporary_target.replace(target_path)
    finally:
        temporary_target.unlink(missing_ok=True)

    with transaction.atomic():
        type(document).objects.filter(pk=document.pk).update(file=target_name)
        document.file.name = target_name

    if not keep_source and source_path.exists():
        source_path.unlink()

    return DocumentMediaNormalization(
        document_id=document.id,
        current_name=current_name,
        target_name=target_name,
        changed=changed,
        source_exists=source_exists,
        target_exists=target_exists,
        applied=True,
    )
