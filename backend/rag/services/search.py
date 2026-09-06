import re

from django.db.models import (
    Case,
    F,
    FloatField,
    Q,
    QuerySet,
    Value,
    When,
)
from django.db.models.functions import Cast
from pgvector.django import CosineDistance

from documents.models import Document, DocumentChunk
from documents.permissions import accessible_documents_for_user
from documents.services.vietnamese_corrector import normalize_for_match
from rag.services.embeddings import embed_query
from rag.services.intents import (
    QueryIntent,
    chunk_condition_for_intent,
    classify_query_intent,
    document_condition_for_intent,
    narrow_documents_for_intent,
    topic_condition_for_query,
)
from rag.services.study_time import (
    build_campus_condition,
    build_study_time_condition,
    is_study_time_query,
    narrow_study_time_documents,
)
from rag.services.tuition import extract_requested_major, major_search_terms


def normalize_query(query: str) -> str:
    """
    Chuẩn hóa khoảng trắng và chuyển câu hỏi thành chữ thường.
    """
    return " ".join(query.strip().lower().split())


def extract_years(query: str) -> list[str]:
    """
    Lấy tất cả năm có trong câu hỏi.
    """
    return re.findall(r"\b20\d{2}\b", query)


def normalize_cohort_year(value: str) -> str:
    if len(value) == 2:
        return f"20{value}"

    return value


def extract_cohort_year(query: str) -> str | None:
    """
    Phân biệt năm của khóa học với năm học.

    Ví dụ:
    'khóa 2025 năm học 2025-2026'
    → cohort_year = 2025
    """
    match = re.search(
        r"\b(?:kh[oó]a|k)\s*(20\d{2}|\d{2})\b",
        query,
        flags=re.IGNORECASE,
    )

    return normalize_cohort_year(match.group(1)) if match else None


def is_tuition_query(query: str) -> bool:
    return "học phí" in query or "hoc phi" in query


def asks_for_advanced_program(query: str) -> bool:
    return "tiên tiến" in query or "tien tien" in query


def asks_for_high_quality_program(query: str) -> bool:
    return (
        "chất lượng cao" in query
        or "chat luong cao" in query
        or "clc" in query
    )


def asks_for_regular_program(query: str) -> bool:
    return (
        "đhcq" in query
        or "dhcq" in query
        or "đại học chính quy" in query
        or "dai hoc chinh quy" in query
        or "chương trình chuẩn" in query
        or "chuong trinh chuan" in query
    )


def asks_for_specific_program(query: str) -> bool:
    return (
        asks_for_advanced_program(query)
        or asks_for_high_quality_program(query)
        or asks_for_regular_program(query)
    )


def asks_for_amount(query: str) -> bool:
    amount_phrases = (
        "bao nhiêu",
        "bao nhieu",
        "mức thu",
        "muc thu",
        "giá",
        "gia",
        "đồng",
        "tín chỉ",
        "tin chi",
    )

    return any(phrase in query for phrase in amount_phrases)


def document_title_matches_query_topic(title: str, query: str) -> bool:
    requested_topic = extract_requested_major(query)
    terms = major_search_terms(requested_topic)

    if len(terms) < 2:
        return False

    normalized_title = normalize_for_match(title)
    return all(term in normalized_title for term in terms)


def narrow_candidate_documents(documents: QuerySet[Document], query: str,) -> QuerySet[Document]:
    narrowed_documents = documents
    intent = classify_query_intent(query)

    if intent != QueryIntent.GENERAL:
        narrowed_documents = narrow_documents_for_intent(
            documents=narrowed_documents,
            intent=intent,
        )

    if intent == QueryIntent.GENERAL and is_tuition_query(query):
        tuition_documents = narrowed_documents.filter(
            Q(title__icontains="học phí")
            | Q(category__name__icontains="học phí")
        )

        if tuition_documents.exists():
            narrowed_documents = tuition_documents

    title_topic_matched = False

    if is_tuition_query(query):
        title_topic_ids = [
            document_id
            for document_id, title in narrowed_documents.values_list(
                "id",
                "title",
            )
            if document_title_matches_query_topic(title, query)
        ]

        if title_topic_ids:
            narrowed_documents = narrowed_documents.filter(
                id__in=title_topic_ids,
            )
            title_topic_matched = True

    cohort_year = extract_cohort_year(query)

    if cohort_year:
        cohort_documents = narrowed_documents.filter(
            Q(title__icontains=f"khóa {cohort_year}")
            | Q(title__icontains=f"-{cohort_year}")
            | Q(title__icontains=f"–{cohort_year}")
        )

        if cohort_documents.exists():
            narrowed_documents = cohort_documents

    if asks_for_advanced_program(query):
        advanced_documents = narrowed_documents.filter(
            title__icontains="tiên tiến",
        )

        if advanced_documents.exists():
            narrowed_documents = advanced_documents

    if asks_for_high_quality_program(query):
        high_quality_documents = narrowed_documents.filter(
            title__icontains="chất lượng cao",
        )

        if high_quality_documents.exists():
            narrowed_documents = high_quality_documents

    if asks_for_regular_program(query):
        regular_documents = narrowed_documents.filter(
            title__icontains="ĐHCQ",
        )

        if regular_documents.exists():
            narrowed_documents = regular_documents

    if (
        is_tuition_query(query)
        and not asks_for_specific_program(query)
        and not title_topic_matched
    ):
        regular_documents = narrowed_documents.filter(
            title__icontains="ĐHCQ",
        )

        if regular_documents.exists():
            narrowed_documents = regular_documents

    if is_study_time_query(query):
        narrowed_documents = narrow_study_time_documents(
            documents=narrowed_documents,
            query=query,
        )

    return narrowed_documents


def build_topic_condition(query: str) -> Q | None:
    """
    Xác định điều kiện chunk có chứa ngành/chủ đề chính.

    Không hardcode từng ngành; tách cụm ngành từ câu hỏi rồi dùng các token
    chính để cộng điểm lexical cho retrieval.
    """
    requested_major = extract_requested_major(query)
    terms = major_search_terms(requested_major)

    if not terms:
        return None

    condition = None

    for term in terms:
        part = Q(content__icontains=term)

        if term == "hoc":
            part = part | Q(content__icontains="h9c")

        condition = part if condition is None else condition & part

    return condition


def build_amount_condition() -> Q:
    """
    Nhận diện chunk có chứa mức tiền.

    Ví dụ:
    925.000đ/tín chỉ
    46.500.000đ/sinh viên
    """
    return (
        Q(
            content__iregex=(
                r"\d{1,3}(?:\.\d{3})+"
                r"\s*(?:đ|d)"
                r"\s*/\s*"
                r"(?:tín|tin)"
            )
        )
        | Q(
            content__iregex=(
                r"\d{1,3}(?:\.\d{3})+"
                r"\s*(?:đ|d)"
                r"\s*/\s*sinh"
            )
        )
    )


def semantic_search(
    *,
    user,
    query: str,
    limit: int = 5,
):
    cleaned_query = normalize_query(query)

    if not cleaned_query:
        raise ValueError(
            "Câu tìm kiếm không được để trống."
        )

    if limit < 1 or limit > 20:
        raise ValueError(
            "limit phải nằm trong khoảng 1 đến 20."
        )

    accessible_documents = (
        accessible_documents_for_user(user)
        .filter(status="READY")
        .select_related("category")
    )

    candidate_documents = narrow_candidate_documents(
        documents=accessible_documents,
        query=cleaned_query,
    )
    intent = classify_query_intent(cleaned_query)

    query_vector = embed_query(cleaned_query)

    queryset = (
        DocumentChunk.objects.filter(
            document__in=candidate_documents,
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
        .annotate(
            semantic_score=(
                Value(1.0)
                - Cast(
                    F("distance"),
                    FloatField(),
                )
            )
        )
    )

    tuition_bonus = Case(
        When(
            document__title__icontains="học phí",
            then=Value(
                0.15 if is_tuition_query(cleaned_query) else 0.0
            ),
        ),
        default=Value(0.0),
        output_field=FloatField(),
    )

    cohort_year = extract_cohort_year(cleaned_query)

    if cohort_year:
        cohort_bonus = Case(
            When(
                Q(document__title__icontains=f"khóa {cohort_year}")
                | Q(document__title__icontains=f"-{cohort_year}")
                | Q(document__title__icontains=f"–{cohort_year}"),
                then=Value(0.20),
            ),
            default=Value(0.0),
            output_field=FloatField(),
        )
    else:
        cohort_bonus = Value(
            0.0,
            output_field=FloatField(),
        )

    topic_condition = build_topic_condition(cleaned_query)
    amount_condition = build_amount_condition()
    amount_requested = asks_for_amount(cleaned_query)
    study_time_requested = is_study_time_query(cleaned_query)
    study_time_condition = build_study_time_condition()
    campus_condition = build_campus_condition(cleaned_query)
    intent_document_condition = document_condition_for_intent(
        intent,
        chunk_relation=True,
    )
    intent_chunk_condition = chunk_condition_for_intent(intent)
    intent_topic_condition = topic_condition_for_query(cleaned_query)

    if topic_condition is not None:
        topic_bonus = Case(
            When(
                topic_condition,
                then=Value(0.30),
            ),
            default=Value(0.0),
            output_field=FloatField(),
        )
    else:
        topic_bonus = Value(
            0.0,
            output_field=FloatField(),
        )

    if amount_requested:
        amount_bonus = Case(
            When(
                amount_condition,
                then=Value(0.20),
            ),
            default=Value(0.0),
            output_field=FloatField(),
        )
    else:
        amount_bonus = Value(
            0.0,
            output_field=FloatField(),
        )

    # Điểm lớn nhất dành cho chunk đồng thời có:
    # tên ngành + mức tiền.
    if topic_condition is not None and amount_requested:
        direct_answer_bonus = Case(
            When(
                topic_condition & amount_condition,
                then=Value(0.55),
            ),
            default=Value(0.0),
            output_field=FloatField(),
        )
    else:
        direct_answer_bonus = Value(
            0.0,
            output_field=FloatField(),
        )

    if study_time_requested:
        study_document_bonus = Case(
            When(
                Q(document__title__icontains="Sổ")
                | Q(document__title__icontains="sinh viên"),
                then=Value(0.18),
            ),
            When(
                Q(document__title__icontains="Quy chế đào tạo")
                | Q(document__title__icontains="Long Hưng")
                | Q(document__title__icontains="GDQP")
                | Q(document__title__icontains="GDTC"),
                then=Value(0.10),
            ),
            default=Value(0.0),
            output_field=FloatField(),
        )
        study_time_bonus = Case(
            When(
                study_time_condition,
                then=Value(0.35),
            ),
            default=Value(0.0),
            output_field=FloatField(),
        )

        if campus_condition is not None:
            campus_bonus = Case(
                When(
                    campus_condition,
                    then=Value(0.35),
                ),
                default=Value(0.0),
                output_field=FloatField(),
            )
            direct_study_time_bonus = Case(
                When(
                    study_time_condition & campus_condition,
                    then=Value(0.55),
                ),
                default=Value(0.0),
                output_field=FloatField(),
            )
        else:
            campus_bonus = Value(
                0.0,
                output_field=FloatField(),
            )
            direct_study_time_bonus = Value(
                0.0,
                output_field=FloatField(),
            )

        tuition_time_penalty = Case(
            When(
                Q(document__title__icontains="học phí")
                & Q(content__icontains="Thời gian áp dụng"),
                then=Value(-0.45),
            ),
            default=Value(0.0),
            output_field=FloatField(),
        )
    else:
        study_document_bonus = Value(
            0.0,
            output_field=FloatField(),
        )
        study_time_bonus = Value(
            0.0,
            output_field=FloatField(),
        )
        campus_bonus = Value(
            0.0,
            output_field=FloatField(),
        )
        direct_study_time_bonus = Value(
            0.0,
            output_field=FloatField(),
        )
        tuition_time_penalty = Value(
            0.0,
            output_field=FloatField(),
        )

    if intent != QueryIntent.GENERAL:
        if intent_document_condition is not None:
            intent_document_bonus = Case(
                When(
                    intent_document_condition,
                    then=Value(0.16),
                ),
                default=Value(0.0),
                output_field=FloatField(),
            )
        else:
            intent_document_bonus = Value(
                0.0,
                output_field=FloatField(),
            )

        if intent_chunk_condition is not None:
            intent_section_bonus = Case(
                When(
                    intent_chunk_condition,
                    then=Value(0.22),
                ),
                default=Value(0.0),
                output_field=FloatField(),
            )
        else:
            intent_section_bonus = Value(
                0.0,
                output_field=FloatField(),
            )

        if intent_topic_condition is not None:
            intent_topic_bonus = Case(
                When(
                    intent_topic_condition,
                    then=Value(0.34),
                ),
                default=Value(0.0),
                output_field=FloatField(),
            )

            if intent_chunk_condition is not None:
                direct_intent_bonus = Case(
                    When(
                        intent_chunk_condition & intent_topic_condition,
                        then=Value(0.42),
                    ),
                    default=Value(0.0),
                    output_field=FloatField(),
                )
            else:
                direct_intent_bonus = Value(
                    0.0,
                    output_field=FloatField(),
                )
        else:
            intent_topic_bonus = Value(
                0.0,
                output_field=FloatField(),
            )
            direct_intent_bonus = Value(
                0.0,
                output_field=FloatField(),
            )
    else:
        intent_document_bonus = Value(
            0.0,
            output_field=FloatField(),
        )
        intent_section_bonus = Value(
            0.0,
            output_field=FloatField(),
        )
        intent_topic_bonus = Value(
            0.0,
            output_field=FloatField(),
        )
        direct_intent_bonus = Value(
            0.0,
            output_field=FloatField(),
        )

    # Giảm điểm phần mở đầu/căn cứ pháp lý nếu câu hỏi cần số tiền.
    if amount_requested:
        introduction_penalty = Case(
            When(
                Q(content__icontains="căn cứ")
                | Q(content__icontains="căn c"),
                then=Value(-0.15),
            ),
            default=Value(0.0),
            output_field=FloatField(),
        )
    else:
        introduction_penalty = Value(
            0.0,
            output_field=FloatField(),
        )

    queryset = (
        queryset.annotate(
            tuition_bonus=tuition_bonus,
            cohort_bonus=cohort_bonus,
            topic_bonus=topic_bonus,
            amount_bonus=amount_bonus,
            direct_answer_bonus=direct_answer_bonus,
            study_document_bonus=study_document_bonus,
            study_time_bonus=study_time_bonus,
            campus_bonus=campus_bonus,
            direct_study_time_bonus=direct_study_time_bonus,
            tuition_time_penalty=tuition_time_penalty,
            intent_document_bonus=intent_document_bonus,
            intent_section_bonus=intent_section_bonus,
            intent_topic_bonus=intent_topic_bonus,
            direct_intent_bonus=direct_intent_bonus,
            introduction_penalty=introduction_penalty,
        )
        .annotate(
            final_score=(
                F("semantic_score")
                + F("tuition_bonus")
                + F("cohort_bonus")
                + F("topic_bonus")
                + F("amount_bonus")
                + F("direct_answer_bonus")
                + F("study_document_bonus")
                + F("study_time_bonus")
                + F("campus_bonus")
                + F("direct_study_time_bonus")
                + F("tuition_time_penalty")
                + F("intent_document_bonus")
                + F("intent_section_bonus")
                + F("intent_topic_bonus")
                + F("direct_intent_bonus")
                + F("introduction_penalty")
            )
        )
    )

    return queryset.order_by(
        "-final_score",
        "distance",
    )[:limit]
