import re
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from documents.services.extractors import ExtractedPage


@dataclass
class TextChunk:
    chunk_index: int
    content: str
    page_number: int | None
    section_title: str
    token_count: int
    metadata: dict


SECTION_PATTERN = re.compile(r"^(CHƯƠNG\s+[IVXLCDM]+|Điều\s+\d+[\.:]?)", re.IGNORECASE,)


def estimate_token_count(text: str) -> int:
    # Sau này thay bằng tokenizer của embedding model.
    return max(1, len(text.split()))


def split_long_text( text: str, max_words: int = 350, overlap_words: int = 50,) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_words,
        chunk_overlap=overlap_words,
        length_function=lambda value: len(value.split()),
        separators=[
            "\n\n",
            "\n",
            ". ",
            "; ",
            ", ",
            " ",
            "",
        ],
    )

    return [
        chunk.strip()
        for chunk in splitter.split_text(text)
        if chunk.strip()
    ]


def chunk_pages( pages: list[ExtractedPage], max_words: int = 350, overlap_words: int = 50,) -> list[TextChunk]:
    result = []
    chunk_index = 0
    current_section = ""

    for page in pages:
        if not page.content:
            continue

        paragraphs = [ paragraph.strip() for paragraph in page.content.split("\n") if paragraph.strip()]

        buffer = []

        for paragraph in paragraphs:
            if SECTION_PATTERN.match(paragraph):
                current_section = paragraph[:500]

            buffer.append(paragraph)

            combined = "\n".join(buffer)
            word_count = len(combined.split())

            if word_count >= max_words:
                parts = split_long_text( combined, max_words=max_words, overlap_words=overlap_words,)

                for part in parts:
                    result.append(
                        TextChunk(
                            chunk_index=chunk_index,
                            content=part,
                            page_number=page.page_number,
                            section_title=current_section,
                            token_count=estimate_token_count(part),
                            metadata={
                                "page_number": page.page_number,
                                **(page.metadata or {}),
                            },
                        )
                    )
                    chunk_index += 1

                buffer = []

        if buffer:
            combined = "\n".join(buffer)

            for part in split_long_text( combined, max_words=max_words, overlap_words=overlap_words,):
                result.append(
                    TextChunk(
                        chunk_index=chunk_index,
                        content=part,
                        page_number=page.page_number,
                        section_title=current_section,
                        token_count=estimate_token_count(part),
                            metadata={
                                "page_number": page.page_number,
                                **(page.metadata or {}),
                            },
                        )
                    )
                chunk_index += 1

    return result
