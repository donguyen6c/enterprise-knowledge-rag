from __future__ import annotations

from functools import lru_cache
import os
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from sentence_transformers import SentenceTransformer
    from transformers import PreTrainedTokenizerBase


MODEL_NAME = (
    "sentence-transformers/"
    "paraphrase-multilingual-MiniLM-L12-v2"
)
EMBEDDING_DIMENSIONS = 384

# Model chỉ nhận tối đa 128 subword tokens. Chunk mới chừa chỗ cho tiêu đề
# tài liệu và section được ghép vào trước khi tạo embedding.
DOCUMENT_CHUNK_TOKEN_LIMIT = 96
DOCUMENT_CHUNK_TOKEN_OVERLAP = 16
EMBEDDING_WINDOW_TOKEN_LIMIT = 120
EMBEDDING_WINDOW_TOKEN_OVERLAP = 16


def local_files_only() -> bool:
    return os.getenv(
        "RAG_EMBEDDING_LOCAL_FILES_ONLY",
        "1",
    ).lower() not in {"0", "false", "no"}


@lru_cache(maxsize=1)
def get_embedding_tokenizer() -> PreTrainedTokenizerBase:
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(
        MODEL_NAME,
        local_files_only=local_files_only(),
    )


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """Tải model một lần trong mỗi Python process."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(
        MODEL_NAME,
        local_files_only=local_files_only(),
    )


def embedding_token_count(text: str) -> int:
    tokenizer = get_embedding_tokenizer()
    content_tokens = len(
        tokenizer(
            text,
            add_special_tokens=False,
            truncation=False,
            verbose=False,
            return_attention_mask=False,
        )["input_ids"]
    )
    special_tokens = tokenizer.num_special_tokens_to_add(pair=False)
    return content_tokens + special_tokens


@lru_cache(maxsize=1)
def get_embedding_window_splitter() -> RecursiveCharacterTextSplitter:
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    return RecursiveCharacterTextSplitter(
        chunk_size=EMBEDDING_WINDOW_TOKEN_LIMIT,
        chunk_overlap=EMBEDDING_WINDOW_TOKEN_OVERLAP,
        length_function=embedding_token_count,
        separators=["\n\n", "\n", ". ", "; ", ", ", " ", ""],
    )


def split_text_for_embedding(text: str) -> list[str]:
    cleaned_text = text.strip()

    if not cleaned_text:
        return []

    if embedding_token_count(cleaned_text) <= EMBEDDING_WINDOW_TOKEN_LIMIT:
        return [cleaned_text]

    return [
        part.strip()
        for part in get_embedding_window_splitter().split_text(cleaned_text)
        if part.strip()
    ]


def _mean_pool_embeddings(
    vectors: np.ndarray,
    indexes: list[int],
) -> list[float]:
    pooled = vectors[indexes].mean(axis=0)
    norm = np.linalg.norm(pooled)

    if norm:
        pooled = pooled / norm

    return pooled.tolist()


def embed_documents(texts: list[str]) -> list[list[float]]:
    """
    Tạo một vector cho mỗi văn bản.

    Các chunk cũ dài hơn giới hạn model được chia thành nhiều cửa sổ bằng
    LangChain. Vector cửa sổ được lấy trung bình rồi chuẩn hóa, tránh việc
    SentenceTransformer âm thầm bỏ phần cuối văn bản.
    """
    if not texts:
        return []

    segments: list[str] = []
    segment_indexes_by_text: list[list[int]] = []

    for text in texts:
        parts = split_text_for_embedding(text)

        if not parts:
            parts = [" "]

        indexes = list(range(len(segments), len(segments) + len(parts)))
        segment_indexes_by_text.append(indexes)
        segments.extend(parts)

    model = get_embedding_model()
    segment_vectors = model.encode(
        segments,
        batch_size=16,
        show_progress_bar=len(segments) > 16,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    return [
        _mean_pool_embeddings(segment_vectors, indexes)
        for indexes in segment_indexes_by_text
    ]


def embed_query(query: str) -> list[float]:
    cleaned_query = query.strip()

    if not cleaned_query:
        raise ValueError("Câu tìm kiếm không được để trống.")

    model = get_embedding_model()
    embedding = model.encode(
        cleaned_query,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    return embedding.tolist()
