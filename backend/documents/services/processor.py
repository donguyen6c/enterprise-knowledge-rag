from pathlib import Path

from django.db import transaction

from documents.models import Document, DocumentChunk
from documents.services.chunker import chunk_pages
from documents.services.extractors import ( DocumentExtractionError, UnsupportedDocumentTypeError, extract_document,)


class EmptyDocumentError(Exception):
    pass


@transaction.atomic
def process_document(document: Document) -> int:
    if not document.file:
        raise DocumentExtractionError( "Document chưa có file.")

    document.status = "PROCESSING"
    document.error_message = ""

    document.save( update_fields=[ "status", "error_message", "updated_at", ]
    )

    try:
        file_path = Path(document.file.path)

        if not file_path.exists():
            raise DocumentExtractionError( "File vật lý không tồn tại.")

        pages = extract_document(file_path)

        total_text = "".join( page.content for page in pages).strip()

        if not total_text:
            raise EmptyDocumentError( "Không trích xuất được văn bản. " "Tài liệu có thể là PDF scan và cần OCR.")

        chunks = chunk_pages(pages)

        if not chunks:
            raise EmptyDocumentError( "Không tạo được chunk từ tài liệu.")

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

        document.status = "READY"
        document.error_message = ""

        document.save(update_fields=[ "status", "error_message", "updated_at", ])

        return len(chunks)

    except ( DocumentExtractionError, UnsupportedDocumentTypeError, EmptyDocumentError,) as exc:
        document.status = "FAILED"
        document.error_message = str(exc)

        document.save( update_fields=["status", "error_message", "updated_at", ])

        raise

    except Exception as exc:
        document.status = "FAILED"
        document.error_message = (f"Lỗi không xác định khi xử lý tài liệu: {exc}")

        document.save( update_fields=[ "status", "error_message", "updated_at",] )

        raise