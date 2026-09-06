from django.db import transaction
from django.db.models import QuerySet

from documents.models import Document, DocumentChunk
from rag.services.embeddings import (
    embed_documents,
    embedding_token_count,
)


def build_embedding_text(chunk: DocumentChunk) -> str:
    parts = [f"Tài liệu: {chunk.document.title}"]

    if chunk.section_title:
        parts.append(f"Mục: {chunk.section_title}")

    parts.append(chunk.content)
    return "\n".join(parts)


def generate_chunk_embeddings(
    queryset: QuerySet[DocumentChunk],
    *,
    batch_size: int = 16,
) -> int:
    if batch_size <= 0:
        raise ValueError("batch_size phải lớn hơn 0.")

    queryset = queryset.select_related("document").order_by("id")
    processed = 0
    last_id = 0

    while True:
        chunks = list(queryset.filter(id__gt=last_id)[:batch_size])

        if not chunks:
            break

        vectors = embed_documents(
            [build_embedding_text(chunk) for chunk in chunks]
        )

        with transaction.atomic():
            for chunk, vector in zip(chunks, vectors, strict=True):
                chunk.embedding = vector
                chunk.token_count = max(
                    1,
                    embedding_token_count(chunk.content),
                )

            DocumentChunk.objects.bulk_update(
                chunks,
                ["embedding", "token_count"],
                batch_size=batch_size,
            )

        processed += len(chunks)
        last_id = chunks[-1].id

    return processed


def generate_document_embeddings(
    document: Document,
    *,
    batch_size: int = 16,
) -> int:
    return generate_chunk_embeddings(
        document.chunks.all(),
        batch_size=batch_size,
    )
