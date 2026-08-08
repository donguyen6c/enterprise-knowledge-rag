from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from django.db.models import Q

from documents.models import DocumentChunk
from rag.services.query_transform import build_query_variants
from rag.services.search import semantic_search


@dataclass
class RetrievalResult:
    chunks: list[DocumentChunk]
    queries: list[str]


def retrieval_score(chunk: DocumentChunk, query_index: int, rank: int) -> float:
    final_score = float(getattr(chunk, "final_score", 0.0))

    return final_score - query_index * 0.02 - rank * 0.001


def attach_parent_context(
    chunks: list[DocumentChunk],
    window: int = 1,
) -> None:
    if not chunks:
        return

    if window < 1:
        for chunk in chunks:
            chunk.parent_content = chunk.content
            chunk.parent_chunk_indexes = [chunk.chunk_index]

        return

    requested_indexes: dict[int, set[int]] = defaultdict(set)
    chunk_windows: dict[int, set[int]] = {}

    for chunk in chunks:
        start_index = max(0, chunk.chunk_index - window)
        end_index = chunk.chunk_index + window
        chunk_window = set(range(start_index, end_index + 1))

        chunk_windows[chunk.id] = chunk_window
        requested_indexes[chunk.document_id].update(chunk_window)

    condition = None

    for document_id, chunk_indexes in requested_indexes.items():
        part = Q(
            document_id=document_id,
            chunk_index__in=chunk_indexes,
        )
        condition = part if condition is None else condition | part

    if condition is None:
        return

    neighbors = (
        DocumentChunk.objects.filter(condition)
        .order_by("document_id", "chunk_index")
    )
    neighbor_map: dict[int, dict[int, DocumentChunk]] = defaultdict(dict)

    for neighbor in neighbors:
        neighbor_map[neighbor.document_id][neighbor.chunk_index] = neighbor

    for chunk in chunks:
        indexes = sorted(chunk_windows[chunk.id])
        parent_chunks = [
            neighbor_map[chunk.document_id][index]
            for index in indexes
            if index in neighbor_map[chunk.document_id]
        ]

        chunk.parent_content = "\n\n".join(
            parent_chunk.content
            for parent_chunk in parent_chunks
        )
        chunk.parent_chunk_indexes = [
            parent_chunk.chunk_index
            for parent_chunk in parent_chunks
        ]


def retrieve_relevant_chunks(
    *,
    user,
    question: str,
    limit: int = 5,
    conversation_history: Sequence[Any] | None = None,
    parent_window: int = 1,
) -> RetrievalResult:
    query_variants = build_query_variants(
        question=question,
        conversation_history=conversation_history,
    )
    merged_chunks: dict[int, DocumentChunk] = {}
    query_limit = min(max(limit, 3), 10)

    for query_index, query in enumerate(query_variants):
        chunks = semantic_search(
            user=user,
            query=query,
            limit=query_limit,
        )

        for rank, chunk in enumerate(chunks, start=1):
            score = retrieval_score(
                chunk=chunk,
                query_index=query_index,
                rank=rank,
            )
            existing = merged_chunks.get(chunk.id)

            if (
                existing is not None
                and score <= getattr(existing, "retrieval_score", float("-inf"))
            ):
                continue

            chunk.retrieval_query = query
            chunk.retrieval_query_index = query_index
            chunk.retrieval_rank = rank
            chunk.retrieval_score = score
            merged_chunks[chunk.id] = chunk

    ranked_chunks = sorted(
        merged_chunks.values(),
        key=lambda chunk: (
            -getattr(chunk, "retrieval_score", 0.0),
            float(getattr(chunk, "distance", 0.0)),
        ),
    )[:limit]

    attach_parent_context(ranked_chunks, window=parent_window)

    return RetrievalResult(
        chunks=ranked_chunks,
        queries=query_variants,
    )
