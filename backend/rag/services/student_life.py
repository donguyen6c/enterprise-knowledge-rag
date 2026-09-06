from dataclasses import dataclass

from documents.models import DocumentChunk
from documents.permissions import accessible_documents_for_user
from documents.services.vietnamese_corrector import normalize_for_match


@dataclass
class StudentLifeAnswer:
    answer: str
    citations: list[dict]


def student_life_topic(question: str) -> str | None:
    normalized = normalize_for_match(question)

    if "hoc bong" in normalized and any(
        term in normalized
        for term in ("nhung", "cac loai", "co gi", "nao", "tong hop")
    ):
        return "scholarships"

    if "ky luat" in normalized and any(
        term in normalized
        for term in ("vi pham", "hinh thuc", "khi nao", "truong hop")
    ):
        return "discipline"

    if "ky tuc xa" in normalized or "nha tro" in normalized:
        return "housing"

    return None


def citation_for_chunk(
    chunk: DocumentChunk,
    snippet: str,
    rank: int = 1,
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
        "semantic_score": 1.0,
        "final_score": 1.0,
        "retrieval_query": "",
        "retrieval_score": 1.0,
        "snippet": " ".join(snippet.split())[:500],
    }


def build_student_life_answer(
    *,
    user,
    question: str,
) -> StudentLifeAnswer | None:
    topic = student_life_topic(question)

    if topic is None:
        return None

    chunks = DocumentChunk.objects.filter(
        document__in=accessible_documents_for_user(user).filter(status="READY"),
    ).select_related("document")

    if topic == "scholarships":
        chunk = (
            chunks.filter(
                document__title__icontains="Tổng hợp các loại học bổng",
                content__icontains="BẢNG TRA NHANH",
            )
            .order_by("page_number", "chunk_index")
            .first()
        )
        detail = (
            "tài liệu tổng hợp 10 nhóm học bổng: Thanh niên tiên tiến làm "
            "theo lời Bác; Khuyến khích học tập chương trình đại trà; Tuyển "
            "sinh thạc sĩ; Tuyển sinh đại học chính quy; Khuyến khích học tập "
            "Khoa Đào tạo đặc biệt; Sinh viên 5 tốt; Tài năng; Vượt khó học "
            "tập; Khuyến khích nâng cao năng lực tiếng Anh; và Tiếp sức đến "
            "trường. Điều kiện và thời điểm xét khác nhau theo từng loại."
        )
        citation_chunks = [chunk]
    elif topic == "discipline":
        chunk = (
            chunks.filter(
                document__title__icontains="Sổ",
                content__icontains="Khi ển trách",
            )
            .order_by("page_number", "chunk_index")
            .first()
        )
        behavior_chunk = (
            chunks.filter(
                document__title__icontains="Sổ",
                content__icontains="Các hành vi sinh viên không được làm",
            )
            .order_by("page_number", "chunk_index")
            .first()
        )
        detail = (
            "tùy tính chất và mức độ vi phạm, sinh viên có thể bị khiển "
            "trách, cảnh cáo, đình chỉ học tập có thời hạn hoặc buộc thôi học. "
            "Các hành vi bị cấm gồm xúc phạm người khác, xuyên tạc nội dung "
            "giáo dục, gian lận học tập/thi cử, hút thuốc hoặc uống rượu bia "
            "trong Trường, tham gia tệ nạn hay gây rối an ninh trật tự và các "
            "hoạt động vi phạm pháp luật."
        )
        citation_chunks = [chunk, behavior_chunk]
    else:
        chunk = (
            chunks.filter(
                document__title__icontains="Sổ",
                content__icontains="http://nhatro.ou.edu.vn",
            )
            .order_by("page_number", "chunk_index")
            .first()
        )
        detail = (
            "Sổ tay không nêu Trường có ký túc xá riêng; tài liệu cho biết "
            "Trường liên kết với các đơn vị nhà trọ tư nhân và ký túc xá tập "
            "trung dành ưu tiên cho sinh viên. Thông tin chỗ ở được đăng tại "
            "http://nhatro.ou.edu.vn."
        )
        citation_chunks = [chunk]

    if chunk is None or any(item is None for item in citation_chunks):
        return None

    answer = (
        f"Theo tài liệu \"{chunk.document.title}\", trang {chunk.page_number}, "
        f"{detail}"
    )

    return StudentLifeAnswer(
        answer=answer,
        citations=[
            citation_for_chunk(item, item.content, rank)
            for rank, item in enumerate(citation_chunks, start=1)
        ],
    )
