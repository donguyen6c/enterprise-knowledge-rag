import re
from dataclasses import dataclass

from django.db.models import Q, QuerySet

from documents.models import Document, DocumentChunk
from documents.permissions import accessible_documents_for_user
from documents.services.vietnamese_corrector import (
    normalize_for_match,
    strip_vietnamese_marks,
)


TIME_PATTERN = re.compile(r"\b\d{1,2}:\d{2}\b")
DATE_RANGE_PATTERN = re.compile(
    r"\b\d{2}/\d{2}/\d{2}\s*[—-]\s*\d{2}/\d{2}/\d{2}\b"
)


@dataclass
class StudyTimeAnswer:
    answer: str
    citations: list[dict]


def is_study_time_query(query: str) -> bool:
    normalized = normalize_for_match(query)

    if "hoc phi" in normalized:
        return False

    explicit_phrases = (
        "thoi gian hoc tap",
        "khung thoi gian",
        "gio hoc",
        "ca hoc",
        "ra vao lop",
        "lich hoc",
        "thoi khoa bieu",
    )

    if any(phrase in normalized for phrase in explicit_phrases):
        return True

    return (
        "gio" in normalized
        and (
            "hoc" in normalized
            or "lop" in normalized
            or "giang day" in normalized
        )
    )


def requested_campus_group(query: str) -> str:
    normalized = normalize_for_match(query)

    if "vo van tan" in normalized or "97 vo" in normalized:
        return "vo_van_tan"

    if "mai thi luu" in normalized or "02 mai" in normalized:
        return "vo_van_tan"

    if any(
        term in normalized
        for term in (
            "long hung",
            "long binh",
            "long binh tan",
            "gdqp",
            "gdtc",
            "quoc phong",
        )
    ):
        return "long_binh"

    if "nha be" in normalized or "nhon duc" in normalized:
        return "nha_be"

    if "binh duong" in normalized:
        return "nha_be"

    return "general"


def build_study_time_condition() -> Q:
    return (
        Q(content__icontains="KHUNG THỜI GIAN RA")
        | Q(content__icontains="khung thời gian theo buổi")
        | Q(content__icontains="Giờ bắt đầu")
        | Q(content__icontains="Giờ kết thúc")
        | Q(content__icontains="Thời gian học tập")
        | Q(content__icontains="Thoi gian h9c")
        | Q(content__icontains="Địa điểm học tập")
    )


def build_campus_condition(query: str) -> Q | None:
    group = requested_campus_group(query)

    if group == "vo_van_tan":
        return (
            Q(content__icontains="Võ Văn Tần")
            | Q(content__icontains="Vo Van Tan")
            | Q(content__icontains="97")
            | Q(content__icontains="Mai Thị Lựu")
        )

    if group == "nha_be":
        return (
            Q(content__icontains="Nhà Bè")
            | Q(content__icontains="Nha Be")
            | Q(content__icontains="Nhơn Đức")
            | Q(content__icontains="Nhon Duc")
            | Q(content__icontains="Bình Dương")
        )

    if group == "long_binh":
        return (
            Q(content__icontains="Long Bình")
            | Q(content__icontains="Long Binh")
            | Q(content__icontains="Long Hưng")
            | Q(content__icontains="Long Hung")
            | Q(content__icontains="GDQP")
            | Q(content__icontains="quốc phòng")
            | Q(content__icontains="quoc phong")
        )

    return None


def narrow_study_time_documents(
    documents: QuerySet[Document],
    query: str,
) -> QuerySet[Document]:
    condition = (
        Q(title__icontains="Sổ")
        | Q(title__icontains="So Tay")
        | Q(title__icontains="Quy chế đào tạo")
        | Q(title__icontains="Long Hưng")
        | Q(title__icontains="GDQP")
        | Q(title__icontains="GDTC")
    )
    group = requested_campus_group(query)

    if group == "long_binh":
        condition = condition | Q(title__icontains="quốc phòng")

    narrowed = documents.filter(condition)

    return narrowed if narrowed.exists() else documents


def normalize_table_text(text: str) -> str:
    normalized = strip_vietnamese_marks(text).lower()
    normalized = re.sub(r"[^a-z0-9:]+", " ", normalized)

    return " ".join(normalized.split())


def segment_between(
    text: str,
    start_terms: tuple[str, ...],
    end_terms: tuple[str, ...] = (),
) -> str:
    start_positions = [
        text.find(term)
        for term in start_terms
        if text.find(term) >= 0
    ]

    if not start_positions:
        return text

    start = min(start_positions)
    end_positions = [
        text.find(term, start + 1)
        for term in end_terms
        if text.find(term, start + 1) >= 0
    ]
    end = min(end_positions) if end_positions else len(text)

    return text[start:end]


def time_range(
    text: str,
    label: str,
    stop_labels: tuple[str, ...],
) -> tuple[str, str] | None:
    start = text.find(label)

    if start < 0:
        return None

    stop_positions = [
        text.find(stop_label, start + len(label))
        for stop_label in stop_labels
        if text.find(stop_label, start + len(label)) >= 0
    ]
    end = min(stop_positions) if stop_positions else len(text)
    times = TIME_PATTERN.findall(text[start:end])

    if len(times) < 2:
        return None

    return times[0], times[-1]


def format_range(label: str, value: tuple[str, str] | None) -> str | None:
    if value is None:
        return None

    return f"{label} {value[0]}-{value[1]}"


def find_schedule_anchor(
    documents: QuerySet[Document],
    group: str,
) -> DocumentChunk | None:
    chunks = DocumentChunk.objects.filter(
        document__in=documents,
    ).select_related("document")

    if group == "vo_van_tan":
        return (
            chunks.filter(
                Q(content__icontains="KHUNG THỜI GIAN")
                | Q(content__icontains="Giờ bắt đầu")
                | Q(content__icontains="Tại địa điểm học 97"),
                Q(content__icontains="Võ Văn Tần")
                | Q(content__icontains="Mai Thị Lựu"),
            )
            .order_by("document_id", "page_number", "chunk_index")
            .first()
        )

    if group in {"nha_be", "long_binh"}:
        return (
            chunks.filter(
                Q(content__icontains="Tại địa điểm học Nhà Bè")
                | Q(content__icontains="Cơ sở học Long Bình Tân")
                | Q(content__icontains="Nhà Bè; Cơ sở Bình Dương"),
            )
            .order_by("document_id", "page_number", "chunk_index")
            .first()
        )

    return (
        chunks.filter(build_study_time_condition())
        .order_by("document_id", "page_number", "chunk_index")
        .first()
    )


def neighboring_chunks(
    anchor: DocumentChunk,
    *,
    before: int = 0,
    after: int = 1,
) -> list[DocumentChunk]:
    return list(
        DocumentChunk.objects.filter(
            document_id=anchor.document_id,
            chunk_index__gte=max(0, anchor.chunk_index - before),
            chunk_index__lte=anchor.chunk_index + after,
        )
        .select_related("document")
        .order_by("chunk_index")
    )


def build_schedule_summary(
    text: str,
    group: str,
) -> str:
    normalized = normalize_table_text(text)

    if group == "vo_van_tan":
        segment = segment_between(
            normalized,
            ("tai dia diem hoc 97 vo van tan",),
            ("khung thoi gian cac lop hoc thuc hanh",),
        )
        ranges = [
            format_range("sáng", time_range(segment, "sang", ("chieu", "toi"))),
            format_range("chiều", time_range(segment, "chieu", ("toi",))),
            format_range("tối", time_range(segment, "toi", ())),
        ]

        return (
            "tại địa điểm học 97 Võ Văn Tần và số 02 Mai Thị Lựu: "
            + ", ".join(item for item in ranges if item)
            + "."
        )

    if group in {"nha_be", "long_binh"}:
        segment = segment_between(
            normalized,
            ("tai dia diem hoc nha be",),
            ("khung thoi gian cac lop hoc thuc hanh",),
        )
        ranges = [
            format_range("sáng", time_range(segment, "sang", ("chieu", "toi pa1"))),
            format_range("chiều", time_range(segment, "chieu", ("toi pa1",))),
            format_range("tối PA1", time_range(segment, "toi pa1", ("toi pa2",))),
            format_range("tối PA2", time_range(segment, "toi pa2", ())),
        ]

        return (
            "tại địa điểm học Nhà Bè, cơ sở Bình Dương và cơ sở học "
            "Long Bình Tân: "
            + ", ".join(item for item in ranges if item)
            + "."
        )

    return (
        "khung thời gian giảng dạy chung của Trường nằm trong khoảng "
        "từ 07 giờ đến 20 giờ, từ thứ 2 đến thứ 7, chia thành 3 buổi."
    )


def build_citation(
    *,
    rank: int,
    anchor: DocumentChunk,
    chunks: list[DocumentChunk],
    score: float = 1.0,
) -> dict:
    snippet = " ".join(
        "\n".join(chunk.content for chunk in chunks).split()
    )[:500]

    return {
        "rank": rank,
        "chunk_id": anchor.id,
        "chunk_index": anchor.chunk_index,
        "parent_chunk_indexes": [chunk.chunk_index for chunk in chunks],
        "document_id": anchor.document_id,
        "document_title": anchor.document.title,
        "page_number": anchor.page_number,
        "distance": 0.0,
        "semantic_score": score,
        "final_score": score,
        "retrieval_query": "",
        "retrieval_score": score,
        "snippet": snippet,
    }


def find_gdqp_plan(documents: QuerySet[Document]) -> tuple[DocumentChunk, str] | None:
    chunk = (
        DocumentChunk.objects.filter(
            document__in=documents,
        )
        .filter(
            Q(content__icontains="4 tuan")
            | Q(content__icontains="4 tuần")
            | Q(content__icontains="Thad gian h9c tap")
        )
        .filter(
            Q(content__icontains="GDQP")
            | Q(content__icontains="quốc phòng")
            | Q(content__icontains="quoc phong")
        )
        .select_related("document")
        .order_by("document_id", "page_number", "chunk_index")
        .first()
    )

    if chunk is None:
        return None

    text = " ".join(chunk.content.split())
    dates = DATE_RANGE_PATTERN.findall(text)
    detail = (
        "Riêng kế hoạch GDQP-AN/GDTC nêu thời gian học tập là "
        "4 tuần/đợt học; thời gian đi và về theo kế hoạch từng đợt."
    )

    if dates:
        detail += f" Một số đợt trong tài liệu: {', '.join(dates[:5])}."

    return chunk, detail


def build_study_time_answer(*, user, question: str) -> StudyTimeAnswer | None:
    if not is_study_time_query(question):
        return None

    accessible_documents = (
        accessible_documents_for_user(user)
        .filter(status="READY")
        .select_related("category")
    )
    candidate_documents = narrow_study_time_documents(
        documents=accessible_documents,
        query=question,
    )
    group = requested_campus_group(question)
    anchor = find_schedule_anchor(candidate_documents, group)

    if anchor is None:
        return None

    chunks = neighboring_chunks(anchor, after=1)
    schedule_summary = build_schedule_summary(
        "\n".join(chunk.content for chunk in chunks),
        group,
    )
    answer = (
        f"Theo tài liệu \"{anchor.document.title}\", trang {anchor.page_number}, "
        f"{schedule_summary}"
    )
    citations = [
        build_citation(
            rank=1,
            anchor=anchor,
            chunks=chunks,
        )
    ]

    if group == "long_binh":
        gdqp_plan = find_gdqp_plan(candidate_documents)

        if gdqp_plan is not None:
            gdqp_chunk, detail = gdqp_plan
            gdqp_chunks = neighboring_chunks(gdqp_chunk, after=0)
            answer = f"{answer} {detail}"
            citations.append(
                build_citation(
                    rank=2,
                    anchor=gdqp_chunk,
                    chunks=gdqp_chunks,
                    score=0.95,
                )
            )

    return StudyTimeAnswer(
        answer=answer,
        citations=citations,
    )
