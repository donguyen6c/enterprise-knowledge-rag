from dataclasses import dataclass

from django.db.models import Q

from documents.models import DocumentChunk
from documents.permissions import accessible_documents_for_user
from documents.services.vietnamese_corrector import normalize_for_match


@dataclass
class AcademicPolicyAnswer:
    answer: str
    citations: list[dict]


def academic_policy_kind(question: str) -> str | None:
    normalized = normalize_for_match(question)

    if any(
        term in normalized
        for term in ("canh bao hoc tap", "canh cao hoc tap", "canh bao ket qua")
    ):
        return "warning"

    if any(
        term in normalized
        for term in ("buoc thoi hoc", "buoc nghi hoc", "duoi hoc")
    ):
        return "dismissal"

    if any(
        term in normalized
        for term in (
            "nghi hoc tam thoi",
            "tam nghi hoc",
            "tam dung hoc",
            "bao luu ket qua hoc tap",
            "bao luu ket qua",
        )
    ):
        return "temporary_leave"

    return None


def policy_anchor(user, anchor: str) -> DocumentChunk | None:
    documents = accessible_documents_for_user(user).filter(status="READY")
    policy_documents = documents.filter(
        Q(title__icontains="hệ thống tín chỉ")
        | Q(title__icontains="Quy chế đào tạo")
    )

    if policy_documents.exists():
        documents = policy_documents

    return (
        DocumentChunk.objects.filter(
            document__in=documents,
            content__icontains=anchor,
        )
        .select_related("document")
        .order_by("document_id", "page_number", "chunk_index")
        .first()
    )


def neighboring_chunks(anchor: DocumentChunk, after: int = 1) -> list[DocumentChunk]:
    return list(
        DocumentChunk.objects.filter(
            document_id=anchor.document_id,
            chunk_index__gte=anchor.chunk_index,
            chunk_index__lte=anchor.chunk_index + after,
        )
        .select_related("document")
        .order_by("chunk_index")
    )


def citation_for_policy(anchor: DocumentChunk, chunks: list[DocumentChunk]) -> dict:
    return {
        "rank": 1,
        "chunk_id": anchor.id,
        "chunk_index": anchor.chunk_index,
        "parent_chunk_indexes": [chunk.chunk_index for chunk in chunks],
        "document_id": anchor.document_id,
        "document_title": anchor.document.title,
        "page_number": anchor.page_number,
        "distance": 0.0,
        "semantic_score": 1.0,
        "final_score": 1.0,
        "retrieval_query": "",
        "retrieval_score": 1.0,
        "snippet": " ".join(
            "\n".join(chunk.content for chunk in chunks).split()
        )[:500],
    }


def build_academic_policy_answer(
    *,
    user,
    question: str,
) -> AcademicPolicyAnswer | None:
    kind = academic_policy_kind(question)

    if kind is None:
        return None

    if kind == "warning":
        anchor_text = "Điều 13. Cảnh báo kết quả học tập"
        detail = (
            "sinh viên bị cảnh báo kết quả học tập khi tổng số tín chỉ của "
            "các môn trong chương trình có điểm dưới 4,0 còn tồn đọng từ đầu "
            "khóa vượt quá 24 tín chỉ. Việc cảnh báo được xét theo từng học kỳ."
        )
    elif kind == "dismissal":
        anchor_text = "Điều 14. Buộc thôi học"
        detail = (
            "sinh viên bị buộc thôi học khi đã hết thời gian đào tạo, kể cả "
            "thời gian kéo dài, nhưng chưa đủ điều kiện tốt nghiệp; hoặc vi "
            "phạm kỷ luật đến mức buộc thôi học. Quy chế cũng quy định buộc "
            "nghỉ học tạm thời khi tự ý bỏ học một học kỳ, chưa hoàn thành "
            "nghĩa vụ học phí hoặc vi phạm kỷ luật đến mức tương ứng."
        )
    else:
        anchor_text = "Điều 12. Nghỉ học tạm thời"
        detail = (
            "sinh viên có thể xin nghỉ học tạm thời và bảo lưu kết quả khi "
            "được điều động vào lực lượng vũ trang, bị bệnh hoặc tai nạn phải "
            "điều trị dài hơn một học kỳ, hoặc vì nhu cầu cá nhân. Trường hợp "
            "vì nhu cầu cá nhân phải đã học ít nhất một học kỳ và không thuộc "
            "diện buộc thôi học; hồ sơ xin tạm nghỉ phải làm trước khi kết thúc "
            "đăng ký môn học bình thường ít nhất một tuần. Khi học lại, sinh "
            "viên làm thủ tục ít nhất một tuần trước học kỳ mới."
        )

    anchor = policy_anchor(user, anchor_text)

    if anchor is None:
        return None

    chunks = neighboring_chunks(anchor)
    last_page = chunks[-1].page_number if chunks else anchor.page_number
    page_label = (
        str(anchor.page_number)
        if last_page == anchor.page_number
        else f"{anchor.page_number}-{last_page}"
    )
    answer = (
        f"Theo tài liệu \"{anchor.document.title}\", trang {page_label}, "
        f"{detail}"
    )

    return AcademicPolicyAnswer(
        answer=answer,
        citations=[citation_for_policy(anchor, chunks)],
    )
