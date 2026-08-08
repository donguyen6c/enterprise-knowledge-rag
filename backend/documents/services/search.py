from pgvector.django import CosineDistance

from documents.models import DocumentChunk
from documents.permissions import accessible_documents_for_user
from rag.services.embeddings import embed_query


def semantic_search(
    *,
    user,
    query: str,
    limit: int = 5,
):
    cleaned_query = query.strip()

    if not cleaned_query:
        raise ValueError(
            "Câu tìm kiếm không được để trống."
        )

    if limit < 1 or limit > 20:
        raise ValueError(
            "limit phải nằm trong khoảng 1 đến 20."
        )

    accessible_documents = accessible_documents_for_user(
        user
    ).filter(
        status="READY",
    )

    query_vector = embed_query(cleaned_query)

    return (
        DocumentChunk.objects.filter(
            document__in=accessible_documents,
            embedding__isnull=False,
        )
        .select_related(
            "document",
            "document__category",
            "document__organization",
        )
        .annotate(
            distance=CosineDistance(
                "embedding",
                query_vector,
            )
        )
        .order_by("distance")[:limit]
    )

