from functools import lru_cache
import os

from sentence_transformers import SentenceTransformer


MODEL_NAME = (
    "sentence-transformers/"
    "paraphrase-multilingual-MiniLM-L12-v2"
)

EMBEDDING_DIMENSIONS = 384


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """
    Chỉ tải model một lần trong mỗi Python process.
    """
    local_files_only = os.getenv(
        "RAG_EMBEDDING_LOCAL_FILES_ONLY",
        "1",
    ).lower() not in {"0", "false", "no"}

    return SentenceTransformer(
        MODEL_NAME,
        local_files_only=local_files_only,
    )


def embed_documents(texts: list[str]) -> list[list[float]]:
    """
    Tạo embedding cho nội dung tài liệu.
    """
    if not texts:
        return []

    model = get_embedding_model()

    embeddings = model.encode( texts, batch_size=16, show_progress_bar=True, normalize_embeddings=True, convert_to_numpy=True,)

    return embeddings.tolist()


def embed_query(query: str) -> list[float]:
    """
    Tạo embedding cho câu hỏi tìm kiếm.
    """
    cleaned_query = query.strip()

    if not cleaned_query:
        raise ValueError("Câu tìm kiếm không được để trống.")

    model = get_embedding_model()

    embedding = model.encode( cleaned_query, normalize_embeddings=True, convert_to_numpy=True,)

    return embedding.tolist()
