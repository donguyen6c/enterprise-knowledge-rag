from dataclasses import dataclass, field

from rag.evaluation_cases import DEFAULT_EVALUATION_CASES


TOP_K_VALUES = (1, 3, 5)


@dataclass(frozen=True)
class RetrievalEvaluationCase:
    id: str
    corpus: str
    category: str
    email: str
    question: str
    expected_document_ids: tuple[int, ...] = field(default_factory=tuple)
    expected_document_titles: tuple[str, ...] = field(default_factory=tuple)
    expected_pages_any: tuple[int, ...] = field(default_factory=tuple)
    optional: bool = False


KFC_RETRIEVAL_CASES = (
    RetrievalEvaluationCase(
        id="kfc_invoice_bill_fields",
        corpus="kfc_demo",
        category="procedure",
        email="people.kfc.demo@example.com",
        question="Muốn tìm hóa đơn KFC bằng bill cần nhập những thông tin gì?",
        expected_document_titles=(
            "KFC Việt Nam - Hướng dẫn xuất hóa đơn điện tử",
        ),
        expected_pages_any=(1,),
        optional=True,
    ),
    RetrievalEvaluationCase(
        id="kfc_invoice_qr_code",
        corpus="kfc_demo",
        category="procedure",
        email="people.kfc.demo@example.com",
        question="Có thể xuất hóa đơn KFC bằng mã QR trên bill không?",
        expected_document_titles=(
            "KFC Việt Nam - Hướng dẫn xuất hóa đơn điện tử",
        ),
        expected_pages_any=(2,),
        optional=True,
    ),
    RetrievalEvaluationCase(
        id="kfc_customer_hotline",
        corpus="kfc_demo",
        category="utility",
        email="people.kfc.demo@example.com",
        question="Hotline chăm sóc khách hàng KFC là số nào?",
        expected_document_titles=(
            "KFC Việt Nam - Hướng dẫn xuất hóa đơn điện tử",
            "KFC Việt Nam - Thông tin liên hệ và đặt hàng",
        ),
        optional=True,
    ),
    RetrievalEvaluationCase(
        id="kfc_recruitment_steps",
        corpus="kfc_demo",
        category="procedure",
        email="people.kfc.demo@example.com",
        question="Ứng tuyển nhân viên nhà hàng KFC gồm những bước nào?",
        expected_document_titles=(
            "KFC Demo - Tóm tắt tiếp nhận ứng viên nhà hàng",
        ),
        optional=True,
    ),
    RetrievalEvaluationCase(
        id="kfc_opening_checklist_code",
        corpus="kfc_demo",
        category="procedure",
        email="operations.kfc.demo@example.com",
        question="Mã biểu mẫu checklist mở ca là gì?",
        expected_document_titles=(
            "KFC Demo - Checklist mở ca nhà hàng",
        ),
        optional=True,
    ),
    RetrievalEvaluationCase(
        id="kfc_employee_support_code",
        corpus="kfc_demo",
        category="utility",
        email="people.kfc.demo@example.com",
        question="Mã nhóm hỗ trợ nhân viên KFC demo là gì?",
        expected_document_titles=(
            "KFC Demo - Cẩm nang hỗ trợ nhân viên",
        ),
        optional=True,
    ),
    RetrievalEvaluationCase(
        id="kfc_private_training_code",
        corpus="kfc_demo",
        category="private",
        email="operations.kfc.demo@example.com",
        question="Mã buổi đào tạo cá nhân của Nguyễn Minh là gì?",
        expected_document_titles=(
            "KFC Demo - Kế hoạch đào tạo cá nhân Nguyễn Minh",
        ),
        optional=True,
    ),
)


def retrieval_evaluation_cases() -> tuple[RetrievalEvaluationCase, ...]:
    ou_cases = tuple(
        RetrievalEvaluationCase(
            id=case.id,
            corpus="ou",
            category=case.category,
            email="admin@ou.edu.vn",
            question=case.question,
            expected_document_ids=case.expected_document_ids,
            expected_pages_any=case.expected_pages_any,
        )
        for case in DEFAULT_EVALUATION_CASES
    )

    return ou_cases + KFC_RETRIEVAL_CASES


def calculate_ranking_metrics(*, ranked_items: list[tuple[int, int | None]], expected_document_ids: set[int], expected_pages_any: set[int], k_values: tuple[int, ...] = TOP_K_VALUES,) -> dict:
    relevant_ranks = [
        rank
        for rank, (document_id, _) in enumerate(ranked_items, start=1)
        if document_id in expected_document_ids
    ]
    first_relevant_rank = relevant_ranks[0] if relevant_ranks else None
    page_relevant_ranks = [
        rank
        for rank, (document_id, page_number) in enumerate(
            ranked_items,
            start=1,
        )
        if (
            document_id in expected_document_ids
            and page_number in expected_pages_any
        )
    ]
    first_relevant_page_rank = (
        page_relevant_ranks[0]
        if page_relevant_ranks
        else None
    )
    hit_at = {}
    recall_at = {}
    page_hit_at = {}

    for k in k_values:
        top_document_ids = {
            document_id
            for document_id, _ in ranked_items[:k]
        }
        matched_document_count = len(
            top_document_ids & expected_document_ids
        )
        hit_at[k] = int(matched_document_count > 0)
        recall_at[k] = (
            matched_document_count / len(expected_document_ids)
            if expected_document_ids
            else 0.0
        )
        page_hit_at[k] = (
            int(
                first_relevant_page_rank is not None
                and first_relevant_page_rank <= k
            )
            if expected_pages_any
            else None
        )

    return {
        "first_relevant_rank": first_relevant_rank,
        "reciprocal_rank": (
            1.0 / first_relevant_rank
            if first_relevant_rank is not None
            else 0.0
        ),
        "first_relevant_page_rank": first_relevant_page_rank,
        "page_reciprocal_rank": (
            1.0 / first_relevant_page_rank
            if first_relevant_page_rank is not None
            else None
        ),
        "hit_at": hit_at,
        "recall_at": recall_at,
        "page_hit_at": page_hit_at,
    }
