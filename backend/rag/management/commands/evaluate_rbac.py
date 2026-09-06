import json
from dataclasses import dataclass, field

from django.core.management.base import BaseCommand, CommandError

from accounts.models import User
from documents.models import Document
from documents.permissions import accessible_documents_for_user
from documents.services.vietnamese_corrector import normalize_for_match
from rag.services.answering import answer_question


@dataclass(frozen=True)
class RbacEvaluationCase:
    id: str
    email: str
    question: str
    should_answer: bool | None
    expected_answer_terms: tuple[str, ...] = field(default_factory=tuple)
    required_document_ids: tuple[int, ...] = field(default_factory=tuple)
    forbidden_document_ids: tuple[int, ...] = field(default_factory=tuple)
    required_document_titles: tuple[str, ...] = field(default_factory=tuple)
    forbidden_document_titles: tuple[str, ...] = field(default_factory=tuple)


DEFAULT_RBAC_CASES = (
    RbacEvaluationCase(
        id="org_admin_can_retrieve_org_document",
        email="admin@ou.edu.vn",
        question="Học phí ngành Công nghệ thông tin khóa 2025 bao nhiêu?",
        should_answer=True,
        expected_answer_terms=("Công nghệ thông tin", "925.000"),
        required_document_ids=(1,),
    ),
    RbacEvaluationCase(
        id="user_without_organization_is_denied",
        email="donguyen6c@gmail.com",
        question="Học phí ngành Công nghệ thông tin khóa 2025 bao nhiêu?",
        should_answer=False,
        expected_answer_terms=("chưa tìm thấy",),
        forbidden_document_ids=(1,),
    ),
)

KFC_DEMO_RBAC_CASES = (
    RbacEvaluationCase(
        id="kfc_private_owner_can_retrieve_training_plan",
        email="operations.kfc.demo@example.com",
        question="Mã buổi đào tạo cá nhân của Nguyễn Minh là gì?",
        should_answer=True,
        expected_answer_terms=("KFC-DEMO-MINH-1509",),
        required_document_titles=(
            "KFC Demo - Kế hoạch đào tạo cá nhân Nguyễn Minh",
        ),
    ),
    RbacEvaluationCase(
        id="kfc_people_department_can_retrieve_recruitment_summary",
        email="people.kfc.demo@example.com",
        question="Ứng tuyển nhân viên nhà hàng KFC gồm những bước nào?",
        should_answer=True,
        expected_answer_terms=("Bước 1",),
        required_document_titles=(
            "KFC Demo - Tóm tắt tiếp nhận ứng viên nhà hàng",
        ),
    ),
    RbacEvaluationCase(
        id="kfc_operations_department_can_retrieve_opening_checklist",
        email="operations.kfc.demo@example.com",
        question="Mã biểu mẫu checklist mở ca là gì?",
        should_answer=True,
        expected_answer_terms=("OPS-OPEN-DEMO-01",),
        required_document_titles=(
            "KFC Demo - Checklist mở ca nhà hàng",
        ),
    ),
    RbacEvaluationCase(
        id="kfc_employee_role_can_retrieve_support_handbook",
        email="people.kfc.demo@example.com",
        question="Mã nhóm hỗ trợ nhân viên KFC demo là gì?",
        should_answer=True,
        expected_answer_terms=("EMP-SUPPORT-DEMO",),
        required_document_titles=(
            "KFC Demo - Cẩm nang hỗ trợ nhân viên",
        ),
    ),
    RbacEvaluationCase(
        id="kfc_people_user_cannot_access_operations_or_private_documents",
        email="people.kfc.demo@example.com",
        question="Cho tôi thông tin OPS-OPEN-DEMO-01 và KFC-DEMO-MINH-1509.",
        should_answer=None,
        forbidden_document_titles=(
            "KFC Demo - Checklist mở ca nhà hàng",
            "KFC Demo - Kế hoạch đào tạo cá nhân Nguyễn Minh",
        ),
    ),
    RbacEvaluationCase(
        id="ou_admin_cannot_access_kfc_corpus",
        email="admin@ou.edu.vn",
        question="Hotline chăm sóc khách hàng KFC là số nào?",
        should_answer=None,
        forbidden_document_titles=(
            "KFC Việt Nam - Hướng dẫn xuất hóa đơn điện tử",
            "KFC Việt Nam - Thông tin liên hệ và đặt hàng",
        ),
    ),
)


def evaluation_cases() -> tuple[RbacEvaluationCase, ...]:
    required_emails = {
        case.email
        for case in KFC_DEMO_RBAC_CASES
        if case.email.endswith(".kfc.demo@example.com")
    }
    existing_email_count = User.objects.filter(
        email__in=required_emails
    ).count()

    if existing_email_count == len(required_emails):
        return DEFAULT_RBAC_CASES + KFC_DEMO_RBAC_CASES

    return DEFAULT_RBAC_CASES


def contains_normalized(haystack: str, needle: str) -> bool:
    return normalize_for_match(needle) in normalize_for_match(haystack)


def citation_document_ids(citations: list[dict]) -> set[int]:
    return {
        int(citation["document_id"])
        for citation in citations
        if citation.get("document_id") is not None
    }


def evaluate_case(
    *,
    case: RbacEvaluationCase,
    limit: int,
) -> dict:
    try:
        user = User.objects.get(email=case.email)
    except User.DoesNotExist:
        return {
            "id": case.id,
            "email": case.email,
            "passed": False,
            "failures": ["user not found"],
        }

    accessible_documents = accessible_documents_for_user(user).filter(status="READY")
    accessible_document_ids = set(
        accessible_documents.values_list("id", flat=True)
    )
    result = answer_question(
        user=user,
        question=case.question,
        limit=limit,
    )
    cited_document_ids = citation_document_ids(result.citations)
    failures = []

    required_document_ids = set(case.required_document_ids)
    forbidden_document_ids = set(case.forbidden_document_ids)

    for title in case.required_document_titles:
        document_ids = set(
            Document.objects.filter(title=title).values_list("id", flat=True)
        )

        if not document_ids:
            failures.append(f"required document title not found: {title}")

        required_document_ids.update(document_ids)

    for title in case.forbidden_document_titles:
        document_ids = set(
            Document.objects.filter(title=title).values_list("id", flat=True)
        )

        if not document_ids:
            failures.append(f"forbidden document title not found: {title}")

        forbidden_document_ids.update(document_ids)

    if case.should_answer is True and not result.citations:
        failures.append("expected citations, got none")

    if case.should_answer is False and result.citations:
        failures.append("expected no citations, got citations")

    missing_accessible_documents = [
        document_id
        for document_id in required_document_ids
        if document_id not in accessible_document_ids
    ]

    if missing_accessible_documents:
        failures.append(
            "required document not accessible before retrieval: "
            + ", ".join(
                str(document_id)
                for document_id in missing_accessible_documents
            )
        )

    missing_cited_documents = [
        document_id
        for document_id in required_document_ids
        if document_id not in cited_document_ids
    ]

    if missing_cited_documents:
        failures.append(
            "required document not cited after retrieval: "
            + ", ".join(
                str(document_id)
                for document_id in missing_cited_documents
            )
        )

    accessible_forbidden_documents = [
        document_id
        for document_id in forbidden_document_ids
        if document_id in accessible_document_ids
    ]

    if accessible_forbidden_documents:
        failures.append(
            "forbidden document accessible before retrieval: "
            + ", ".join(
                str(document_id)
                for document_id in accessible_forbidden_documents
            )
        )

    cited_forbidden_documents = [
        document_id
        for document_id in forbidden_document_ids
        if document_id in cited_document_ids
    ]

    if cited_forbidden_documents:
        failures.append(
            "forbidden document cited after retrieval: "
            + ", ".join(
                str(document_id)
                for document_id in cited_forbidden_documents
            )
        )

    missing_answer_terms = [
        term
        for term in case.expected_answer_terms
        if not contains_normalized(result.answer, term)
    ]

    if missing_answer_terms:
        failures.append(
            "answer missing: " + ", ".join(missing_answer_terms)
        )

    return {
        "id": case.id,
        "email": case.email,
        "role": user.role,
        "organization_id": user.organization_id,
        "department_id": user.department_id,
        "question": case.question,
        "passed": not failures,
        "failures": failures,
        "accessible_ready_document_count": accessible_documents.count(),
        "accessible_document_ids": sorted(accessible_document_ids),
        "answer": result.answer,
        "citations": result.citations,
        "retrieval_queries": result.retrieval_queries,
    }


class Command(BaseCommand):
    help = "Kiểm tra RBAC trước retrieval và sau khi RAG trả lời."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=5,
            help="Số citation/retrieval chunks dùng cho mỗi câu hỏi.",
        )
        parser.add_argument(
            "--case",
            action="append",
            dest="case_ids",
            help="Chỉ chạy một hoặc nhiều case id cụ thể.",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="Liệt kê các case mà không chạy RAG.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="In kết quả dạng JSON.",
        )
        parser.add_argument(
            "--show-answer",
            action="store_true",
            help="In đáp án rút gọn của từng case.",
        )
        parser.add_argument(
            "--no-fail",
            action="store_true",
            help="Không trả exit code lỗi khi có case fail.",
        )

    def handle(self, *args, **options):
        cases = list(evaluation_cases())
        case_ids = set(options["case_ids"] or [])

        if case_ids:
            cases = [
                case
                for case in cases
                if case.id in case_ids
            ]

        if not cases:
            raise CommandError("Không có RBAC evaluation case phù hợp.")

        if options["list"]:
            for case in cases:
                self.stdout.write(
                    f"{case.id} | {case.email} | {case.question}"
                )
            return

        results = [
            evaluate_case(
                case=case,
                limit=options["limit"],
            )
            for case in cases
        ]
        passed_count = sum(1 for result in results if result["passed"])
        failed_results = [
            result
            for result in results
            if not result["passed"]
        ]

        if options["json"]:
            self.stdout.write(
                json.dumps(
                    {
                        "total": len(results),
                        "passed": passed_count,
                        "failed": len(failed_results),
                        "results": results,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            for result in results:
                style = self.style.SUCCESS if result["passed"] else self.style.ERROR
                self.stdout.write(
                    style(
                        f"{'PASS' if result['passed'] else 'FAIL'} "
                        f"{result['id']} | {result['email']}"
                    )
                )
                self.stdout.write(
                    "  access: "
                    f"role={result.get('role')} "
                    f"org={result.get('organization_id')} "
                    f"ready_docs={result.get('accessible_ready_document_count')}"
                )

                if result["failures"]:
                    for failure in result["failures"]:
                        self.stdout.write(f"  - {failure}")

                if options["show_answer"]:
                    answer = " ".join(result["answer"].split())
                    self.stdout.write(f"  answer: {answer[:260]}")

            self.stdout.write("")
            self.stdout.write(
                f"Summary: {passed_count}/{len(results)} passed, "
                f"{len(failed_results)} failed."
            )

        if failed_results and not options["no_fail"]:
            raise CommandError("RBAC evaluation failed.")
