import re
from collections.abc import Sequence
from typing import Any

from documents.services.vietnamese_corrector import normalize_for_match


ACRONYM_PATTERNS = (
    (re.compile(r"\bhp\b", flags=re.IGNORECASE), "học phí"),
    (re.compile(r"\bcntt\b", flags=re.IGNORECASE), "công nghệ thông tin"),
    (re.compile(r"\bclc\b", flags=re.IGNORECASE), "chất lượng cao"),
    (re.compile(r"\bđhcq\b|\bdhcq\b", flags=re.IGNORECASE), "đại học chính quy"),
    (re.compile(r"\bsv\b", flags=re.IGNORECASE), "sinh viên"),
    (re.compile(r"\bhb\b", flags=re.IGNORECASE), "học bổng"),
    (re.compile(r"\bctdt\b", flags=re.IGNORECASE), "chương trình đào tạo"),
)

CONTEXT_REFERENCE_TERMS = (
    "no",
    "do",
    "nay",
    "van ban nay",
    "quyet dinh nay",
    "thong bao nay",
    "nganh nay",
    "muc nay",
    "hoc phi nay",
    "chuong trinh nay",
)


def normalize_spacing(text: str) -> str:
    return " ".join(text.strip().split())


def expand_acronyms(question: str) -> str:
    expanded = question

    for pattern, replacement in ACRONYM_PATTERNS:
        expanded = pattern.sub(replacement, expanded)

    return normalize_spacing(expanded)


def has_context_reference(question: str) -> bool:
    normalized = f" {normalize_for_match(question)} "

    return any(f" {term} " in normalized for term in CONTEXT_REFERENCE_TERMS)


def message_role(message: Any) -> str:
    if isinstance(message, dict):
        return str(message.get("role", ""))

    return str(getattr(message, "role", ""))


def message_content(message: Any) -> str:
    if isinstance(message, dict):
        return str(message.get("content", ""))

    return str(getattr(message, "content", ""))


def message_metadata(message: Any) -> dict:
    if isinstance(message, dict):
        metadata = message.get("metadata", {})
    else:
        metadata = getattr(message, "metadata", {})

    return metadata if isinstance(metadata, dict) else {}


def recent_context_from_history(
    conversation_history: Sequence[Any] | None,
    max_messages: int = 4,
) -> str:
    if not conversation_history:
        return ""

    context_parts: list[str] = []

    for message in reversed(conversation_history):
        role = message_role(message)
        content = normalize_spacing(message_content(message))

        if role == "USER" and content:
            context_parts.append(f"Câu hỏi trước: {content}")

        metadata = message_metadata(message)
        citations = metadata.get("citations", [])

        if isinstance(citations, list):
            for citation in citations[:2]:
                if not isinstance(citation, dict):
                    continue

                title = citation.get("document_title")
                page = citation.get("page_number")

                if title:
                    context_parts.append(f"Nguồn trước: {title}, trang {page}")

        if len(context_parts) >= max_messages:
            break

    context = " | ".join(context_parts[:max_messages])

    return context[:800]


def rewrite_question_with_history(
    question: str,
    conversation_history: Sequence[Any] | None,
) -> str:
    cleaned_question = normalize_spacing(question)

    if not has_context_reference(cleaned_question):
        return cleaned_question

    context = recent_context_from_history(conversation_history)

    if not context:
        return cleaned_question

    return f"{cleaned_question}. Ngữ cảnh hội thoại trước: {context}"


def build_query_variants(
    question: str,
    conversation_history: Sequence[Any] | None = None,
    max_variants: int = 4,
) -> list[str]:
    variants: list[str] = []
    seen: set[str] = set()

    def add_variant(value: str) -> None:
        cleaned = normalize_spacing(value)

        if not cleaned:
            return

        key = normalize_for_match(cleaned)

        if key in seen:
            return

        seen.add(key)
        variants.append(cleaned)

    original = normalize_spacing(question)
    expanded = expand_acronyms(original)
    rewritten = rewrite_question_with_history(expanded, conversation_history)

    add_variant(original)
    add_variant(expanded)
    add_variant(rewritten)

    return variants[:max_variants]
