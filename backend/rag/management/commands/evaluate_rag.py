import json

from django.core.management.base import BaseCommand, CommandError

from accounts.models import User
from documents.services.vietnamese_corrector import normalize_for_match
from rag.evaluation_cases import DEFAULT_EVALUATION_CASES, RagEvaluationCase
from rag.services.answering import answer_question


def contains_normalized(haystack: str, needle: str) -> bool:
    return normalize_for_match(needle) in normalize_for_match(haystack)


def citation_text(citations: list[dict]) -> str:
    parts = []

    for citation in citations:
        parts.extend(
            [
                str(citation.get("document_title", "")),
                str(citation.get("snippet", "")),
            ]
        )

    return " ".join(parts)


def evaluate_case(
    *,
    user,
    case: RagEvaluationCase,
    limit: int,
) -> dict:
    result = answer_question(
        user=user,
        question=case.question,
        limit=limit,
    )
    citations = result.citations
    citation_document_ids = {
        int(citation["document_id"])
        for citation in citations
        if citation.get("document_id") is not None
    }
    citation_pages = {
        int(citation["page_number"])
        for citation in citations
        if citation.get("page_number") is not None
    }
    missing_answer_terms = [
        term
        for term in case.expected_answer_terms
        if not contains_normalized(result.answer, term)
    ]
    missing_document_ids = [
        document_id
        for document_id in case.expected_document_ids
        if document_id not in citation_document_ids
    ]
    expected_pages_found = (
        not case.expected_pages_any
        or any(page in citation_pages for page in case.expected_pages_any)
    )
    missing_citation_terms = [
        term
        for term in case.expected_citation_terms
        if not contains_normalized(citation_text(citations), term)
    ]
    failures = []

    if missing_answer_terms:
        failures.append(
            "answer missing: " + ", ".join(missing_answer_terms)
        )

    if missing_document_ids:
        failures.append(
            "citation missing document id: "
            + ", ".join(str(document_id) for document_id in missing_document_ids)
        )

    if not expected_pages_found:
        failures.append(
            "citation missing any expected page: "
            + ", ".join(str(page) for page in case.expected_pages_any)
        )

    if missing_citation_terms:
        failures.append(
            "citation missing: " + ", ".join(missing_citation_terms)
        )

    return {
        "id": case.id,
        "category": case.category,
        "question": case.question,
        "passed": not failures,
        "failures": failures,
        "answer": result.answer,
        "citations": citations,
        "retrieval_queries": result.retrieval_queries,
    }


class Command(BaseCommand):
    help = "Chạy bộ câu hỏi chuẩn để kiểm tra chất lượng RAG."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            default="admin@ou.edu.vn",
            help="Email user dùng để kiểm tra RAG và RBAC.",
        )
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
            "--category",
            action="append",
            dest="categories",
            help="Chỉ chạy một hoặc nhiều category cụ thể.",
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
        cases = list(DEFAULT_EVALUATION_CASES)
        case_ids = set(options["case_ids"] or [])
        categories = set(options["categories"] or [])

        if case_ids:
            cases = [
                case
                for case in cases
                if case.id in case_ids
            ]

        if categories:
            cases = [
                case
                for case in cases
                if case.category in categories
            ]

        if not cases:
            raise CommandError("Không có evaluation case phù hợp.")

        if options["list"]:
            for case in cases:
                self.stdout.write(
                    f"{case.id} | {case.category} | {case.question}"
                )
            return

        try:
            user = User.objects.get(email=options["email"])
        except User.DoesNotExist as exc:
            raise CommandError("Không tìm thấy user.") from exc

        results = [
            evaluate_case(
                user=user,
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
                        f"{result['id']} | {result['category']}"
                    )
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
            raise CommandError("RAG evaluation failed.")
