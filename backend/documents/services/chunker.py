import re
from dataclasses import dataclass

from documents.services.extractors import ExtractedPage
from rag.services.embeddings import (
    DOCUMENT_CHUNK_TOKEN_LIMIT,
    DOCUMENT_CHUNK_TOKEN_OVERLAP,
    embedding_token_count,
)


@dataclass
class TextChunk:
    chunk_index: int
    content: str
    page_number: int | None
    section_title: str
    token_count: int
    metadata: dict


SECTION_PATTERN = re.compile(
    r"^(CHƯƠNG\s+[IVXLCDM]+|Điều\s+\d+[\.:]?)",
    re.IGNORECASE,
)


def estimate_token_count(text: str) -> int:
    return max(1, embedding_token_count(text))


def split_long_text(
    text: str,
    max_tokens: int = DOCUMENT_CHUNK_TOKEN_LIMIT,
    overlap_tokens: int = DOCUMENT_CHUNK_TOKEN_OVERLAP,
) -> list[str]:
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_tokens,
        chunk_overlap=overlap_tokens,
        length_function=embedding_token_count,
        separators=["\n\n", "\n", ". ", "; ", ", ", " ", ""],
    )

    return [
        chunk.strip()
        for chunk in splitter.split_text(text)
        if chunk.strip()
    ]


def section_blocks(
    content: str,
    current_section: str,
) -> tuple[list[tuple[str, str]], str]:
    """Nhóm đoạn theo heading để section metadata không bị gán lệch."""
    blocks: list[tuple[str, str]] = []
    buffer: list[str] = []

    for raw_paragraph in content.splitlines():
        paragraph = raw_paragraph.strip()

        if not paragraph:
            continue

        if SECTION_PATTERN.match(paragraph):
            if buffer:
                blocks.append((current_section, "\n".join(buffer)))
                buffer = []

            current_section = paragraph[:500]

        buffer.append(paragraph)

    if buffer:
        blocks.append((current_section, "\n".join(buffer)))

    return blocks, current_section


def chunk_pages(
    pages: list[ExtractedPage],
    max_tokens: int = DOCUMENT_CHUNK_TOKEN_LIMIT,
    overlap_tokens: int = DOCUMENT_CHUNK_TOKEN_OVERLAP,
) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    current_section = ""

    for page in pages:
        if not page.content:
            continue

        blocks, current_section = section_blocks(
            page.content,
            current_section,
        )

        for section_title, block in blocks:
            for part in split_long_text(
                block,
                max_tokens=max_tokens,
                overlap_tokens=overlap_tokens,
            ):
                chunks.append(
                    TextChunk(
                        chunk_index=len(chunks),
                        content=part,
                        page_number=page.page_number,
                        section_title=section_title,
                        token_count=estimate_token_count(part),
                        metadata={
                            "page_number": page.page_number,
                            **(page.metadata or {}),
                        },
                    )
                )

    return chunks
