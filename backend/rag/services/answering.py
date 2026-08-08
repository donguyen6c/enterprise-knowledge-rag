import re
from dataclasses import dataclass

from langchain_core.documents import Document as LangChainDocument

from documents.models import DocumentChunk
from documents.permissions import accessible_documents_for_user
from rag.services.intents import (
    QueryIntent,
    classify_query_intent,
)
from rag.services.retrieval import retrieve_relevant_chunks
from rag.services.search import narrow_candidate_documents, normalize_query
from rag.services.student_services import build_student_service_answer
from rag.services.study_time import build_study_time_answer
from rag.services.tuition import (
    extract_requested_major,
    find_tuition_match,
    is_tuition_query,
)


@dataclass
class RagResult:
    answer: str
    citations: list[dict]
    retrieval_queries: list[str]


@dataclass
class TuitionAnswer:
    answer: str
    citation: dict


def chunk_to_langchain_document(chunk) -> LangChainDocument:
    return LangChainDocument(
        page_content=getattr(chunk, "parent_content", chunk.content),
        metadata={
            "chunk_id": chunk.id,
            "chunk_index": chunk.chunk_index,
            "parent_chunk_indexes": getattr(
                chunk,
                "parent_chunk_indexes",
                [chunk.chunk_index],
            ),
            "document_id": chunk.document_id,
            "document_title": chunk.document.title,
            "page_number": chunk.page_number,
            "distance": float(chunk.distance),
            "semantic_score": float(chunk.semantic_score),
            "final_score": float(getattr(chunk, "final_score", chunk.semantic_score)),
            "retrieval_query": getattr(chunk, "retrieval_query", ""),
            "retrieval_score": float(getattr(chunk, "retrieval_score", 0.0)),
            "chunk_content": chunk.content,
        },
    )


def build_citation(rank: int, document: LangChainDocument) -> dict:
    chunk_content = document.metadata.get("chunk_content", "")
    source = document.page_content
    anchor = chunk_content.strip()[:120]
    start = source.find(anchor)

    if start >= 0:
        source = source[start:]

    snippet = " ".join(source.split())[:500]

    return {
        "rank": rank,
        "chunk_id": document.metadata["chunk_id"],
        "chunk_index": document.metadata["chunk_index"],
        "parent_chunk_indexes": document.metadata["parent_chunk_indexes"],
        "document_id": document.metadata["document_id"],
        "document_title": document.metadata["document_title"],
        "page_number": document.metadata["page_number"],
        "distance": document.metadata["distance"],
        "semantic_score": document.metadata["semantic_score"],
        "final_score": document.metadata["final_score"],
        "retrieval_query": document.metadata["retrieval_query"],
        "retrieval_score": document.metadata["retrieval_score"],
        "snippet": snippet,
    }


def build_tuition_page_groups(user, question: str):
    accessible_documents = (
        accessible_documents_for_user(user)
        .filter(status="READY")
        .select_related("category")
    )
    candidate_documents = narrow_candidate_documents(
        documents=accessible_documents,
        query=normalize_query(question),
    )
    chunks = (
        DocumentChunk.objects.filter(
            document__in=candidate_documents,
        )
        .select_related("document")
        .order_by("document_id", "page_number", "chunk_index")
    )
    page_groups = {}

    for chunk in chunks:
        key = (chunk.document_id, chunk.page_number)
        group = page_groups.setdefault(
            key,
            {
                "document": chunk.document,
                "page_number": chunk.page_number,
                "chunks": [],
            },
        )
        group["chunks"].append(chunk)

    return page_groups.values()


def build_tuition_citation(
    *,
    rank: int,
    group: dict,
    match,
) -> dict:
    chunks = group["chunks"]
    chunk = chunks[0]

    for candidate in chunks:
        if match.amount in candidate.content or match.display_major in candidate.content:
            chunk = candidate
            break

    return {
        "rank": rank,
        "chunk_id": chunk.id,
        "chunk_index": chunk.chunk_index,
        "parent_chunk_indexes": [candidate.chunk_index for candidate in chunks],
        "document_id": group["document"].id,
        "document_title": group["document"].title,
        "page_number": group["page_number"],
        "distance": 0.0,
        "semantic_score": match.score,
        "final_score": match.score,
        "retrieval_query": "",
        "retrieval_score": match.score,
        "snippet": match.snippet,
    }


def build_tuition_answer(*, user, question: str) -> TuitionAnswer | None:
    if not is_tuition_query(question):
        return None

    requested_major = extract_requested_major(question)

    if not requested_major:
        return None

    best_result = None

    for group in build_tuition_page_groups(user, question):
        page_text = "\n".join(
            chunk.content
            for chunk in group["chunks"]
        )
        match = find_tuition_match(
            text=page_text,
            requested_major=requested_major,
        )

        if match is None:
            continue

        score = match.score

        if best_result is None or score > best_result[0]:
            best_result = (score, group, match)

    if best_result is None:
        return None

    _, group, match = best_result
    citation = build_tuition_citation(
        rank=1,
        group=group,
        match=match,
    )
    answer = (
        "Theo tài liệu "
        f"\"{group['document'].title}\""
        f", trang {group['page_number']}, học phí ngành {match.display_major} "
        f"là {match.amount}."
    )

    return TuitionAnswer(
        answer=answer,
        citation=citation,
    )


def merge_citations(
    tuition_citation: dict,
    retrieval_citations: list[dict],
) -> list[dict]:
    return merge_primary_citations([tuition_citation], retrieval_citations)


def merge_primary_citations(
    primary_citations: list[dict],
    retrieval_citations: list[dict],
) -> list[dict]:
    merged = []
    seen = set()

    for citation in primary_citations:
        updated = {
            **citation,
            "rank": len(merged) + 1,
        }
        merged.append(updated)
        seen.add(
            (
                citation["document_id"],
                citation["page_number"],
                citation["chunk_index"],
            )
        )

    for citation in retrieval_citations:
        key = (
            citation["document_id"],
            citation["page_number"],
            citation["chunk_index"],
        )

        if key in seen:
            continue

        updated = {
            **citation,
            "rank": len(merged) + 1,
        }
        merged.append(updated)
        seen.add(key)

    return merged


def build_context_answer(
    documents: list[LangChainDocument],
    citations: list[dict],
    question: str,
) -> str:
    if not documents:
        return (
            "Mình chưa tìm thấy thông tin phù hợp trong các tài liệu "
            "mà bạn có quyền truy cập."
        )

    citation = citations[0]
    intent = classify_query_intent(question)
    excerpt = focused_excerpt(
        document=documents[0],
        question=question,
        intent=intent,
    )

    if len(excerpt) > 900:
        excerpt = excerpt[:900].rsplit(" ", 1)[0] + "..."

    if intent == QueryIntent.POLICY:
        return (
            "Mình tra cứu theo quy chế và chỉ trả lời theo đoạn có nguồn "
            f"trong tài liệu \"{citation['document_title']}\", "
            f"trang {citation['page_number']}:\n\n"
            f"{excerpt}"
        )

    if intent == QueryIntent.PROCEDURE:
        procedure_lines = extract_procedure_lines(excerpt)

        if procedure_lines:
            steps = "\n".join(
                f"- {line}"
                for line in procedure_lines
            )

            return (
                "Mình tìm thấy hướng dẫn nghiệp vụ liên quan trong tài liệu "
                f"\"{citation['document_title']}\""
                f", trang {citation['page_number']}:\n\n"
                f"{steps}"
            )

        return (
            "Mình tìm thấy hướng dẫn nghiệp vụ liên quan trong tài liệu "
            f"\"{citation['document_title']}\""
            f", trang {citation['page_number']}:\n\n"
            f"{excerpt}"
        )

    if intent == QueryIntent.UTILITY:
        return (
            "Mình tìm thấy thông tin tiện ích liên quan trong tài liệu "
            f"\"{citation['document_title']}\""
            f", trang {citation['page_number']}:\n\n"
            f"{excerpt}"
        )

    return (
        "Mình tìm thấy thông tin liên quan nhất trong tài liệu "
        f"\"{citation['document_title']}\""
        f", trang {citation['page_number']}:\n\n"
        f"{excerpt}"
    )


def focus_terms(question: str, intent: QueryIntent) -> list[str]:
    normalized = question.lower()
    terms = []

    if "tốt nghiệp" in normalized:
        terms.extend(
            [
                "Điều 27. Điều kiện xét tốt nghiệp",
                "Điều kiện xét tốt nghiệp",
                "Sinh viên được Trường xét",
            ]
        )

    if "cảnh báo" in normalized or "cảnh cáo" in normalized:
        terms.extend(
            [
                "Điều 13. Cảnh báo",
                "Cảnh báo kết quả học tập",
                "Cảnh báo học tập",
            ]
        )

    if "miễn" in normalized or "giảm" in normalized:
        terms.extend(
            [
                "miễn, giảm",
                "miễn giảm",
                "Điều 22. Bảo lưu kết quả và miễn giảm",
            ]
        )

    if "phúc khảo" in normalized or "phúc tra" in normalized or "khiếu nại điểm" in normalized:
        terms.extend(
            [
                "Điều 23. Phúc tra",
                "Phúc tra và khiếu nại điểm",
                "khiếu nại điểm",
            ]
        )

    if "bảng điểm" in normalized:
        terms.extend(
            [
                "Phòng Quản lý đào tạo",
                "Cấp chứng nhận sinh viên, thẻ sinh viên, bảng điểm",
                "bảng điểm",
            ]
        )

    if "câu lạc bộ" in normalized or "clb" in normalized:
        terms.extend(
            [
                "6.2 CÂU LẠC BỘ",
                "Câu lạc bộ - Đội",
                "TÊN CLB",
            ]
        )

    if intent == QueryIntent.PROCEDURE:
        terms.extend(
            [
                "Trình tự, thủ tục",
                "Hồ sơ",
                "Sinh viên nộp",
            ]
        )

    return terms


def focused_excerpt(
    *,
    document: LangChainDocument,
    question: str,
    intent: QueryIntent,
    window: int = 900,
) -> str:
    source = " ".join(document.page_content.split())
    chunk_content = " ".join(document.metadata.get("chunk_content", "").split())
    candidates = [source]

    if chunk_content and chunk_content != source:
        candidates.insert(0, chunk_content)

    for candidate in candidates:
        for term in focus_terms(question, intent):
            index = candidate.lower().find(term.lower())

            if index < 0:
                continue

            return candidate[index:index + window]

    return candidates[0]


def extract_procedure_lines(excerpt: str) -> list[str]:
    text = re.sub(r"\s+(?=[-•+]\s)", "\n", excerpt)
    text = re.sub(r"\s+(?=\d+\.\s)", "\n", text)
    markers = (
        "nộp",
        "liên hệ",
        "phòng",
        "đăng ký",
        "đơn",
        "hồ sơ",
        "thời hạn",
        "email",
        "website",
        "thủ tục",
        "trình tự",
    )
    lines = []

    for raw_line in text.splitlines():
        line = raw_line.strip(" -•+\t")

        if len(line) < 20:
            continue

        lowered = line.lower()

        if not any(marker in lowered for marker in markers):
            continue

        if len(line) > 260:
            line = line[:260].rsplit(" ", 1)[0] + "..."

        if line not in lines:
            lines.append(line)

        if len(lines) >= 6:
            break

    return lines


def answer_question(
    *,
    user,
    question: str,
    limit: int = 5,
    conversation_history=None,
) -> RagResult:
    retrieval_result = retrieve_relevant_chunks(
        user=user,
        question=question,
        limit=limit,
        conversation_history=conversation_history,
    )
    documents = [
        chunk_to_langchain_document(chunk)
        for chunk in retrieval_result.chunks
    ]
    citations = [
        build_citation(rank, document)
        for rank, document in enumerate(documents, start=1)
    ]
    study_time_answer = build_study_time_answer(
        user=user,
        question=question,
    )
    student_service_answer = build_student_service_answer(
        user=user,
        question=question,
    )
    tuition_answer = build_tuition_answer(
        user=user,
        question=question,
    )

    if study_time_answer is not None:
        answer = study_time_answer.answer
        citations = merge_primary_citations(
            primary_citations=study_time_answer.citations,
            retrieval_citations=citations,
        )
    elif student_service_answer is not None:
        answer = student_service_answer.answer
        citations = merge_primary_citations(
            primary_citations=student_service_answer.citations,
            retrieval_citations=citations,
        )
    elif tuition_answer is not None:
        answer = tuition_answer.answer
        citations = merge_citations(
            tuition_citation=tuition_answer.citation,
            retrieval_citations=citations,
        )
    else:
        answer = build_context_answer(
            documents=documents,
            citations=citations,
            question=question,
        )

    return RagResult(
        answer=answer,
        citations=citations,
        retrieval_queries=retrieval_result.queries,
    )
