from pathlib import Path

from django.db import transaction

from documents.models import Document, DocumentChunk
from documents.services.chunker import chunk_pages
from documents.services.extractors import (
    DocumentExtractionError,
    UnsupportedDocumentTypeError,
    extract_document,
)
from documents.services.indexing import generate_document_embeddings


class EmptyDocumentError(Exception):
    pass


def mark_processing_failed(document: Document, message: str) -> None:
    document.status = Document.Status.FAILED
    document.error_message = message
    document.save(update_fields=["status", "error_message", "updated_at"])


def mark_processing_ready(document: Document) -> None:
    document.status = Document.Status.READY
    document.error_message = ""
    document.save(update_fields=["status", "error_message", "updated_at"])


def process_document(document: Document) -> int:
    if not document.file:
        raise DocumentExtractionError("Document chưa có file.")

    document.status = Document.Status.PROCESSING
    document.error_message = ""
    document.save(update_fields=["status", "error_message", "updated_at"])

    try:
        file_path = Path(document.file.path)

        if not file_path.exists():
            raise DocumentExtractionError("File vật lý không tồn tại.")

        pages = extract_document(file_path)
        total_text = "".join(page.content for page in pages).strip()

        if not total_text:
            raise EmptyDocumentError(
                "Không trích xuất được văn bản từ tài liệu."
            )

        chunks = chunk_pages(pages)

        if not chunks:
            raise EmptyDocumentError("Không tạo được chunk từ tài liệu.")

        with transaction.atomic():
            document.chunks.all().delete()
            DocumentChunk.objects.bulk_create(
                [
                    DocumentChunk(
                        document=document,
                        chunk_index=chunk.chunk_index,
                        content=chunk.content,
                        page_number=chunk.page_number,
                        section_title=chunk.section_title,
                        token_count=chunk.token_count,
                        metadata=chunk.metadata,
                    )
                    for chunk in chunks
                ]
            )

        return len(chunks)

    except (
        DocumentExtractionError,
        UnsupportedDocumentTypeError,
        EmptyDocumentError,
    ) as exc:
        mark_processing_failed(document, str(exc))
        raise
    except Exception as exc:
        mark_processing_failed(
            document,
            f"Lỗi không xác định khi xử lý tài liệu: {exc}",
        )
        raise


def process_and_index_document(
    document: Document,
    *,
    batch_size: int = 16,
) -> tuple[int, int]:
    try:
        chunk_count = process_document(document)
        embedding_count = generate_document_embeddings(
            document,
            batch_size=batch_size,
        )

        if embedding_count != chunk_count:
            raise RuntimeError(
                "Số embedding không khớp với số chunk đã tạo."
            )

        mark_processing_ready(document)
        return chunk_count, embedding_count
    except Exception as exc:
        document.refresh_from_db(fields=["status"])

        if document.status != Document.Status.FAILED:
            mark_processing_failed(
                document,
                f"Không thể hoàn tất pipeline tài liệu: {exc}",
            )

        raise
