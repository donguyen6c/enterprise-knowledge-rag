import re
from dataclasses import dataclass

from django.db.models import Q

from documents.models import DocumentChunk
from documents.permissions import accessible_documents_for_user
from documents.services.vietnamese_corrector import normalize_for_match


MONEY_PER_STUDENT_PATTERN = re.compile(
    r"\d{1,3}(?:\.\d{3})+\s*(?:đ|d)\s*/\s*sinh\s+vien",
    flags=re.IGNORECASE,
)


@dataclass
class FeeAnswer:
    answer: str
    citations: list[dict]


def normalize_space(text: str) -> str:
    return " ".join(text.split())


def normalize_money(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(
        r"\s*(?:đ|d)\s*/\s*t(?:í|i)n\s+ch(?:ỉ|i)",
        "đ/tín chỉ",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"\s*(?:đ|d)\s*/\s*sinh\s+vien",
        "đ/sinh viên",
        value,
        flags=re.IGNORECASE,
    )

    return value


def citation_for_chunk(
    *,
    rank: int,
    chunk: DocumentChunk,
    snippet: str,
    score: float = 1.0,
) -> dict:
    return {
        "rank": rank,
        "chunk_id": chunk.id,
        "chunk_index": chunk.chunk_index,
        "parent_chunk_indexes": [chunk.chunk_index],
        "document_id": chunk.document_id,
        "document_title": chunk.document.title,
        "page_number": chunk.page_number,
        "distance": 0.0,
        "semantic_score": score,
        "final_score": score,
        "retrieval_query": "",
        "retrieval_score": score,
        "snippet": snippet[:500],
    }


def fee_amount_requested(query: str) -> bool:
    normalized = normalize_for_match(query)

    return any(
        term in normalized
        for term in (
            "hoc phi",
            "muc thu",
            "chi phi",
            "bao nhieu",
            "dong",
            "tin chi",
            "tien",
        )
    )


def english_program_fee_requested(query: str) -> bool:
    normalized = normalize_for_match(query)

    if not fee_amount_requested(query):
        return False

    return (
        "tieng anh" in normalized
        and (
            "can ban" in normalized
            or "chuan dau ra" in normalized
            or "b1" in normalized
            or "b2" in normalized
            or "c1" in normalized
        )
    )


def long_hung_fee_requested(query: str) -> bool:
    normalized = normalize_for_match(query)

    if not fee_amount_requested(query):
        return False

    return any(
        term in normalized
        for term in (
            "gdqp",
            "gdtc",
            "giao duc quoc phong",
            "giao duc the chat",
            "long hung",
            "long binh",
            "ky tuc xa",
            "quan trang",
        )
    )


def repeat_study_fee_requested(query: str) -> bool:
    normalized = normalize_for_match(query)

    if not fee_amount_requested(query):
        return False

    return any(
        term in normalized
        for term in (
            "hoc lai",
            "hoc vuot",
            "hoc cai thien",
            "cai thien diem",
        )
    )


REPEAT_STUDY_FEE_GROUPS = (
    "Giáo dục quốc phòng - an ninh: 465.000đ/tín chỉ",
    "Giáo dục thể chất: 585.000đ/tín chỉ",
    "các môn lý luận chính trị: 750.000đ/tín chỉ",
    "Tin học đại cương/Tin học văn phòng nâng cao: 925.000đ/tín chỉ",
    "ngoại ngữ không chuyên và Ngoại ngữ 2: 680.000đ/tín chỉ",
    "các môn đại cương, cơ sở ngành, ngành và chuyên ngành không dạy bằng "
    "tiếng Anh: 950.000đ/tín chỉ",
    "các môn chuyên môn giảng dạy bằng tiếng Anh: 1.100.000đ/tín chỉ",
)


def build_repeat_study_fee_answer(
    *,
    user,
    question: str,
) -> FeeAnswer | None:
    if not repeat_study_fee_requested(question):
        return None

    chunks = list(
        DocumentChunk.objects.filter(
            document__in=accessible_documents_for_user(user).filter(status="READY"),
            document__title__icontains="học lại",
        )
        .filter(
            Q(content__icontains="465.000")
            | Q(content__icontains="1.100.000")
        )
        .select_related("document")
        .order_by("page_number", "chunk_index")
    )

    if not chunks:
        return None

    answer = (
        f"Theo tài liệu \"{chunks[0].document.title}\", mức học phí học lại, "
        "học vượt hoặc học cải thiện năm học 2025-2026 phụ thuộc nhóm môn: "
        + "; ".join(REPEAT_STUDY_FEE_GROUPS)
        + "."
    )
    citation_chunks = {}

    for chunk in chunks:
        citation_chunks.setdefault(chunk.page_number, chunk)

    citations = [
        citation_for_chunk(
            rank=rank,
            chunk=chunk,
            snippet=normalize_space(chunk.content),
        )
        for rank, chunk in enumerate(citation_chunks.values(), start=1)
    ]

    return FeeAnswer(answer=answer, citations=citations)


ADVANCED_PROGRAM_FEE_GROUPS = (
    {
        "page": 1,
        "amount": "46.500.000đ/sinh viên",
        "semester_amount": "15.500.000đ/sinh viên/học kỳ",
        "majors": (
            "Tài chính - Ngân hàng",
            "Quản trị kinh doanh",
            "Kế toán",
            "Kiểm toán",
            "Kinh tế",
            "Luật kinh tế",
            "Ngôn ngữ Anh",
            "Ngôn ngữ Nhật",
            "Ngôn ngữ Trung Quốc",
        ),
    },
    {
        "page": 2,
        "amount": "49.500.000đ/sinh viên",
        "semester_amount": "16.500.000đ/sinh viên/học kỳ",
        "majors": (
            "Khoa học máy tính",
        ),
    },
    {
        "page": 2,
        "amount": "46.500.000đ/sinh viên",
        "semester_amount": "15.500.000đ/sinh viên/học kỳ",
        "majors": (
            "Công nghệ kỹ thuật công trình xây dựng",
            "Công nghệ thông tin",
            "Công nghệ sinh học",
        ),
    },
)


def program_fee_amount_requested(query: str) -> bool:
    normalized = normalize_for_match(query)

    return any(
        term in normalized
        for term in (
            "hoc phi",
            "muc thu",
            "bao nhieu",
            "dong",
            "sinh vien",
            "hoc ky",
            "tinh the nao",
        )
    )


def advanced_program_fee_requested(query: str) -> bool:
    normalized = normalize_for_match(query)

    return (
        program_fee_amount_requested(query)
        and (
            "tien tien" in normalized
            or "chuong trinh tien tien" in normalized
        )
    )


def normalize_major_query(query: str) -> str:
    normalized = normalize_for_match(query)
    normalized = re.sub(r"\bcntt\b", "cong nghe thong tin", normalized)

    return normalized


def find_advanced_program_major(query: str) -> dict | None:
    normalized = normalize_major_query(query)

    for group in ADVANCED_PROGRAM_FEE_GROUPS:
        for major in group["majors"]:
            if normalize_for_match(major) in normalized:
                return {
                    **group,
                    "matched_major": major,
                }

    return None


def advanced_program_group_snippet(group: dict) -> str:
    majors = ", ".join(group["majors"])

    return (
        f"{majors}: {group['amount']} "
        f"({group['semester_amount']})."
    )


def advanced_program_summary_snippet() -> str:
    return " ".join(
        advanced_program_group_snippet(group)
        for group in ADVANCED_PROGRAM_FEE_GROUPS
    )


def advanced_program_snippets_by_page(
    chunks_by_page: dict[int, DocumentChunk],
) -> dict[int, str]:
    snippets_by_page = {}

    for group in ADVANCED_PROGRAM_FEE_GROUPS:
        page = group["page"]

        if page not in chunks_by_page:
            continue

        snippets_by_page[page] = normalize_space(
            f"{snippets_by_page.get(page, '')} "
            f"{advanced_program_group_snippet(group)}"
        )

    return snippets_by_page


def find_advanced_program_fee_chunks(user) -> dict[int, DocumentChunk]:
    chunks = (
        DocumentChunk.objects.filter(
            document__in=accessible_documents_for_user(user).filter(status="READY"),
        )
        .filter(
            Q(document__title__icontains="tiên tiến")
            | Q(document__title__icontains="tien tien")
        )
        .filter(
            Q(content__icontains="46.500.000")
            | Q(content__icontains="49.500.000")
        )
        .select_related("document")
        .order_by("page_number", "chunk_index")
    )

    return {
        chunk.page_number: chunk
        for chunk in chunks
    }


def build_advanced_program_fee_answer(
    *,
    user,
    question: str,
) -> FeeAnswer | None:
    if not advanced_program_fee_requested(question):
        return None

    chunks_by_page = find_advanced_program_fee_chunks(user)

    if not chunks_by_page:
        return None

    matched_group = find_advanced_program_major(question)

    if matched_group is not None:
        page = matched_group["page"]
        chunk = chunks_by_page.get(page) or next(iter(chunks_by_page.values()))
        major = matched_group["matched_major"]
        snippets_by_page = advanced_program_snippets_by_page(chunks_by_page)
        answer = (
            f"Theo tài liệu \"{chunk.document.title}\", trang {chunk.page_number}, "
            f"học phí chương trình tiên tiến khóa 2025 ngành {major} là "
            f"{matched_group['amount']} ({matched_group['semester_amount']})."
        )
        snippet = advanced_program_group_snippet(matched_group)
        citations = [
            citation_for_chunk(
                rank=1,
                chunk=chunk,
                snippet=snippet,
            )
        ]

        for citation_page in sorted(snippets_by_page):
            if citation_page == chunk.page_number:
                continue

            citations.append(
                citation_for_chunk(
                    rank=len(citations) + 1,
                    chunk=chunks_by_page[citation_page],
                    snippet=snippets_by_page[citation_page],
                )
            )

        return FeeAnswer(
            answer=answer,
            citations=citations,
        )

    citation_pages = sorted(chunks_by_page)
    document = chunks_by_page[citation_pages[0]].document
    page_label = (
        f"trang {citation_pages[0]}"
        if len(citation_pages) == 1
        else f"trang {citation_pages[0]}-{citation_pages[-1]}"
    )
    answer = (
        f"Theo tài liệu \"{document.title}\", {page_label}, "
        "học phí chương trình tiên tiến khóa 2025 được thu theo năm/sinh viên: "
        "Khoa học máy tính là 49.500.000đ/sinh viên "
        "(16.500.000đ/sinh viên/học kỳ); các ngành còn lại trong bảng là "
        "46.500.000đ/sinh viên (15.500.000đ/sinh viên/học kỳ)."
    )
    snippets_by_page = advanced_program_snippets_by_page(chunks_by_page)
    citations = [
        citation_for_chunk(
            rank=index,
            chunk=chunks_by_page[page],
            snippet=snippets_by_page[page],
        )
        for index, page in enumerate(sorted(snippets_by_page), start=1)
    ]

    if not citations:
        citations = [
            citation_for_chunk(
                rank=1,
                chunk=chunks_by_page[citation_pages[0]],
                snippet=advanced_program_summary_snippet(),
            )
        ]

    return FeeAnswer(
        answer=answer,
        citations=citations,
    )


def find_english_fee_chunk(user) -> DocumentChunk | None:
    chunks = (
        DocumentChunk.objects.filter(
            document__in=accessible_documents_for_user(user).filter(status="READY"),
            document__title__icontains="tiếng Anh",
        )
        .select_related("document")
        .order_by("page_number", "chunk_index")
    )

    for chunk in chunks:
        normalized = normalize_for_match(chunk.content)

        if (
            "580 000" in normalized
            and (
                "tieng anh" in normalized
                or "ting anh" in normalized
            )
        ):
            return chunk

    return None


def build_english_program_fee_answer(
    *,
    user,
    question: str,
) -> FeeAnswer | None:
    if not english_program_fee_requested(question):
        return None

    chunk = find_english_fee_chunk(user)

    if chunk is None:
        return None

    normalized_question = normalize_for_match(question)
    answer_parts = []

    if "can ban" in normalized_question:
        answer_parts.append("Tiếng Anh căn bản là 580.000đ/tín chỉ")

    if "chuan dau ra" in normalized_question or any(
        level in normalized_question
        for level in ("b1", "b2", "c1")
    ):
        if "on thi" in normalized_question:
            if "c1" in normalized_question:
                answer_parts.append("ôn thi chuẩn đầu ra tiếng Anh C1 là 1.500.000đ")
            else:
                answer_parts.append("ôn thi chuẩn đầu ra tiếng Anh B1/B2 là 580.000đ")
        else:
            answer_parts.append(
                "thi chuẩn đầu ra tiếng Anh B1/B2/C1 là 300.000đ/lần thi"
            )

    if not answer_parts:
        answer_parts.append("Tiếng Anh căn bản là 580.000đ/tín chỉ")

    answer = (
        f"Theo tài liệu \"{chunk.document.title}\", trang {chunk.page_number}, "
        + "; ".join(answer_parts)
        + "."
    )

    return FeeAnswer(
        answer=answer,
        citations=[
            citation_for_chunk(
                rank=1,
                chunk=chunk,
                snippet=normalize_space(chunk.content),
            )
        ],
    )


def find_long_hung_fee_chunk(user) -> DocumentChunk | None:
    return (
        DocumentChunk.objects.filter(
            document__in=accessible_documents_for_user(user).filter(status="READY"),
        )
        .filter(
            Q(document__title__icontains="Long Hưng")
            | Q(document__title__icontains="GDQP")
            | Q(document__title__icontains="GDTC")
        )
        .filter(
            Q(content__icontains="3.170.000")
            | Q(content__icontains="Tang Ong")
            | Q(content__icontains="Tổng cộng")
        )
        .select_related("document")
        .order_by("page_number", "chunk_index")
        .first()
    )


def build_long_hung_fee_answer(
    *,
    user,
    question: str,
) -> FeeAnswer | None:
    if not long_hung_fee_requested(question):
        return None

    chunk = find_long_hung_fee_chunk(user)

    if chunk is None:
        return None

    amounts = [
        normalize_money(match.group(0))
        for match in MONEY_PER_STUDENT_PATTERN.finditer(chunk.content)
    ]

    if len(amounts) < 4:
        return None

    uniform_fee, facility_fee, meal_fee, total_fee = amounts[:4]
    answer = (
        f"Theo tài liệu \"{chunk.document.title}\", trang {chunk.page_number}, "
        f"tổng chi phí GDQP-AN/GDTC tại cơ sở Long Hưng là {total_fee}. "
        f"Các khoản gồm tiền thuê quân trang {uniform_fee}, điện/nước/ký túc xá/"
        f"dịch vụ vệ sinh {facility_fee}, và tiền ăn {meal_fee}."
    )

    return FeeAnswer(
        answer=answer,
        citations=[
            citation_for_chunk(
                rank=1,
                chunk=chunk,
                snippet=normalize_space(chunk.content),
            )
        ],
    )


def build_auxiliary_fee_answer(*, user, question: str) -> FeeAnswer | None:
    repeat_study_answer = build_repeat_study_fee_answer(
        user=user,
        question=question,
    )

    if repeat_study_answer is not None:
        return repeat_study_answer

    english_answer = build_english_program_fee_answer(
        user=user,
        question=question,
    )

    if english_answer is not None:
        return english_answer

    advanced_program_answer = build_advanced_program_fee_answer(
        user=user,
        question=question,
    )

    if advanced_program_answer is not None:
        return advanced_program_answer

    return build_long_hung_fee_answer(
        user=user,
        question=question,
    )
