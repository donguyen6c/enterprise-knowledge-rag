import json
from collections import defaultdict
from pathlib import Path
from statistics import fmean

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.models import User
from documents.models import Document
from documents.permissions import accessible_documents_for_user
from rag.retrieval_evaluation import (
    TOP_K_VALUES,
    RetrievalEvaluationCase,
    calculate_ranking_metrics,
    retrieval_evaluation_cases,
)
from rag.services.retrieval import retrieve_relevant_chunks


def resolve_expected_document_ids(case: RetrievalEvaluationCase, user: User,) -> tuple[set[int], list[str]]:
    document_ids = set(case.expected_document_ids)
    missing_titles = []

    for title in case.expected_document_titles:
        title_ids = set(
            Document.objects.filter(
                title=title,
                organization_id=user.organization_id,
            ).values_list("id", flat=True)
        )

        if not title_ids:
            missing_titles.append(title)

        document_ids.update(title_ids)

    return document_ids, missing_titles


def serialize_chunk(rank: int, chunk) -> dict:
    return {
        "rank": rank,
        "chunk_id": chunk.id,
        "document_id": chunk.document_id,
        "document_title": chunk.document.title,
        "page_number": chunk.page_number,
        "chunk_index": chunk.chunk_index,
        "semantic_score": round(float(chunk.semantic_score), 6),
        "final_score": round(float(chunk.final_score), 6),
        "retrieval_score": round(float(chunk.retrieval_score), 6),
        "retrieval_query": chunk.retrieval_query,
        "snippet": " ".join(chunk.content.split())[:300],
    }


def evaluate_case(
    case: RetrievalEvaluationCase,
    limit: int,
) -> dict:
    try:
        user = User.objects.get(email=case.email)
    except User.DoesNotExist:
        if case.optional:
            return {
                "id": case.id,
                "corpus": case.corpus,
                "category": case.category,
                "skipped": True,
                "skip_reason": f"optional user not found: {case.email}",
            }

        return {
            "id": case.id,
            "corpus": case.corpus,
            "category": case.category,
            "email": case.email,
            "question": case.question,
            "expected_document_ids": list(case.expected_document_ids),
            "expected_document_titles": list(case.expected_document_titles),
            "expected_pages_any": list(case.expected_pages_any),
            "skipped": False,
            "passed": False,
            "failures": [f"user not found: {case.email}"],
            "metrics": calculate_ranking_metrics(
                ranked_items=[],
                expected_document_ids=set(case.expected_document_ids),
                expected_pages_any=set(case.expected_pages_any),
            ),
            "retrieval_queries": [],
            "results": [],
        }

    expected_document_ids, missing_titles = resolve_expected_document_ids(
        case,
        user,
    )

    if missing_titles and case.optional:
        return {
            "id": case.id,
            "corpus": case.corpus,
            "category": case.category,
            "skipped": True,
            "skip_reason": (
                "optional document not found: " + ", ".join(missing_titles)
            ),
        }

    failures = []

    if missing_titles:
        failures.append("document title not found: " + ", ".join(missing_titles))

    if not expected_document_ids:
        failures.append("ground truth has no expected document")

    accessible_expected_ids = set(
        accessible_documents_for_user(user)
        .filter(
            id__in=expected_document_ids,
            status=Document.Status.READY,
        )
        .values_list("id", flat=True)
    )
    inaccessible_expected_ids = (
        expected_document_ids - accessible_expected_ids
    )

    if inaccessible_expected_ids:
        failures.append(
            "ground-truth document blocked before retrieval: "
            + ", ".join(str(item) for item in sorted(inaccessible_expected_ids))
        )

    retrieval = retrieve_relevant_chunks(
        user=user,
        question=case.question,
        limit=limit,
        parent_window=0,
    )
    ranked_items = [
        (chunk.document_id, chunk.page_number)
        for chunk in retrieval.chunks
    ]
    metrics = calculate_ranking_metrics(
        ranked_items=ranked_items,
        expected_document_ids=expected_document_ids,
        expected_pages_any=set(case.expected_pages_any),
    )
    passed = not failures and bool(metrics["hit_at"][max(TOP_K_VALUES)])

    if not metrics["hit_at"][max(TOP_K_VALUES)]:
        failures.append("no relevant document in top 5 chunks")

    return {
        "id": case.id,
        "corpus": case.corpus,
        "category": case.category,
        "email": case.email,
        "question": case.question,
        "expected_document_ids": sorted(expected_document_ids),
        "expected_document_titles": list(case.expected_document_titles),
        "expected_pages_any": list(case.expected_pages_any),
        "skipped": False,
        "passed": passed,
        "failures": failures,
        "metrics": metrics,
        "retrieval_queries": retrieval.queries,
        "results": [
            serialize_chunk(rank, chunk)
            for rank, chunk in enumerate(retrieval.chunks, start=1)
        ],
    }


def summarize_results(results: list[dict]) -> dict:
    active_results = [result for result in results if not result["skipped"]]
    page_results = [
        result
        for result in active_results
        if result["expected_pages_any"]
    ]
    metric_summary = {
        "mrr": fmean(
            result["metrics"]["reciprocal_rank"]
            for result in active_results
        ) if active_results else 0.0,
        "page_mrr": fmean(
            result["metrics"]["page_reciprocal_rank"] or 0.0
            for result in page_results
        ) if page_results else None,
        "hit_at": {},
        "recall_at": {},
        "page_hit_at": {},
    }

    for k in TOP_K_VALUES:
        metric_summary["hit_at"][k] = (
            fmean(result["metrics"]["hit_at"][k] for result in active_results)
            if active_results
            else 0.0
        )
        metric_summary["recall_at"][k] = (
            fmean(
                result["metrics"]["recall_at"][k]
                for result in active_results
            )
            if active_results
            else 0.0
        )
        metric_summary["page_hit_at"][k] = (
            fmean(
                result["metrics"]["page_hit_at"][k]
                for result in page_results
            )
            if page_results
            else None
        )

    return {
        "case_count": len(active_results),
        "passed_count": sum(result["passed"] for result in active_results),
        "failed_count": sum(not result["passed"] for result in active_results),
        "skipped_count": sum(result["skipped"] for result in results),
        "page_case_count": len(page_results),
        "metrics": metric_summary,
    }


def grouped_summaries(results: list[dict], field: str) -> dict[str, dict]:
    groups = defaultdict(list)

    for result in results:
        groups[result[field]].append(result)

    return {
        name: summarize_results(group_results)
        for name, group_results in sorted(groups.items())
    }


def percentage(value: float | None) -> str:
    return "N/A" if value is None else f"{value * 100:.1f}%"


def build_markdown_report(payload: dict) -> str:
    summary = payload["summary"]
    metrics = summary["metrics"]
    lines = [
        "# Báo Cáo Đánh Giá Retrieval",
        "",
        f"Thời điểm chạy: `{payload['generated_at']}`",
        "",
        "Luồng được đo là luồng production: query transformation, lọc RBAC, "
        "hybrid retrieval và gộp thứ hạng chunk. Chất lượng câu trả lời không "
        "được dùng để tính các chỉ số dưới đây.",
        "",
        "## Chỉ Số Tổng Hợp",
        "",
        "| Chỉ số | Kết quả |",
        "| --- | ---: |",
        f"| Số case | {summary['case_count']} |",
        f"| Pass top 5 | {summary['passed_count']}/{summary['case_count']} |",
        f"| Hit@1 | {percentage(metrics['hit_at'][1])} |",
        f"| Hit@3 | {percentage(metrics['hit_at'][3])} |",
        f"| Hit@5 | {percentage(metrics['hit_at'][5])} |",
        f"| MRR | {metrics['mrr']:.4f} |",
        f"| Recall@5 | {percentage(metrics['recall_at'][5])} |",
        f"| Page Hit@5 | {percentage(metrics['page_hit_at'][5])} |",
        f"| Page MRR | {metrics['page_mrr']:.4f} |"
        if metrics["page_mrr"] is not None
        else "| Page MRR | N/A |",
        "",
        "## Theo Corpus",
        "",
        "| Corpus | Cases | Hit@1 | Hit@3 | Hit@5 | MRR | Recall@5 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for corpus, corpus_summary in payload["by_corpus"].items():
        corpus_metrics = corpus_summary["metrics"]
        lines.append(
            f"| {corpus} | {corpus_summary['case_count']} | "
            f"{percentage(corpus_metrics['hit_at'][1])} | "
            f"{percentage(corpus_metrics['hit_at'][3])} | "
            f"{percentage(corpus_metrics['hit_at'][5])} | "
            f"{corpus_metrics['mrr']:.4f} | "
            f"{percentage(corpus_metrics['recall_at'][5])} |"
        )

    lines.extend(
        [
            "",
            "## Kết Quả Từng Case",
            "",
            "| Case | Corpus | Category | First rank | Hit@5 | Page rank |",
            "| --- | --- | --- | ---: | ---: | ---: |",
        ]
    )

    for result in payload["results"]:
        if result["skipped"]:
            lines.append(
                f"| {result['id']} | {result['corpus']} | "
                f"{result['category']} | skipped | - | - |"
            )
            continue

        case_metrics = result["metrics"]
        first_rank = case_metrics["first_relevant_rank"] or "-"
        page_rank = case_metrics["first_relevant_page_rank"] or "-"
        lines.append(
            f"| {result['id']} | {result['corpus']} | "
            f"{result['category']} | {first_rank} | "
            f"{case_metrics['hit_at'][5]} | {page_rank} |"
        )

    failed_results = [
        result
        for result in payload["results"]
        if not result["skipped"] and not result["passed"]
    ]

    lines.extend(
        [
            "",
            "## Cách Diễn Giải",
            "",
            "- `Hit@k`: tỷ lệ câu hỏi có ít nhất một tài liệu đúng trong top-k chunks.",
            "- `MRR`: trung bình nghịch đảo thứ hạng của chunk đúng đầu tiên.",
            "- `Recall@k`: tỷ lệ tài liệu ground-truth xuất hiện trong top-k.",
            "- `Page Hit@k`: tỷ lệ case có ground-truth trang tìm đúng trang trong top-k.",
            "- Kết quả chỉ đại diện cho bộ câu hỏi và corpus tại thời điểm chạy.",
        ]
    )

    if failed_results:
        lines.extend(["", "## Case Chưa Đạt", ""])

        for result in failed_results:
            retrieved = ", ".join(
                f"#{item['rank']} Doc {item['document_id']} p.{item['page_number']}"
                for item in result["results"]
            )
            lines.append(
                f"- `{result['id']}`: {'; '.join(result['failures'])}. "
                f"Retrieved: {retrieved}."
            )

    return "\n".join(lines) + "\n"


class Command(BaseCommand):
    help = "Đo Hit@1/3/5, MRR, Recall@k và Page Hit cho retrieval."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=5,
            help="Số chunks lấy cho mỗi case; phải từ 5 trở lên.",
        )
        parser.add_argument(
            "--case",
            action="append",
            dest="case_ids",
            help="Chỉ chạy một hoặc nhiều case id.",
        )
        parser.add_argument(
            "--corpus",
            action="append",
            dest="corpora",
            help="Chỉ chạy corpus, ví dụ ou hoặc kfc_demo.",
        )
        parser.add_argument(
            "--category",
            action="append",
            dest="categories",
            help="Chỉ chạy một hoặc nhiều category.",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="Liệt kê case mà không chạy retrieval.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="In toàn bộ kết quả JSON ra console.",
        )
        parser.add_argument(
            "--output-json",
            help="Ghi kết quả JSON vào đường dẫn trong project.",
        )
        parser.add_argument(
            "--output-markdown",
            help="Ghi báo cáo Markdown vào đường dẫn trong project.",
        )
        parser.add_argument(
            "--no-fail",
            action="store_true",
            help="Không trả exit code lỗi khi có case trượt Hit@5.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]

        if limit < max(TOP_K_VALUES):
            raise CommandError("--limit phải từ 5 trở lên để tính Hit@5.")

        cases = list(retrieval_evaluation_cases())
        case_ids = set(options["case_ids"] or [])
        corpora = set(options["corpora"] or [])
        categories = set(options["categories"] or [])

        if case_ids:
            cases = [case for case in cases if case.id in case_ids]

        if corpora:
            cases = [case for case in cases if case.corpus in corpora]

        if categories:
            cases = [case for case in cases if case.category in categories]

        if not cases:
            raise CommandError("Không có retrieval evaluation case phù hợp.")

        if options["list"]:
            for case in cases:
                self.stdout.write(
                    f"{case.id} | {case.corpus} | {case.category} | "
                    f"{case.email} | {case.question}"
                )
            return

        results = [evaluate_case(case, limit) for case in cases]
        summary = summarize_results(results)
        payload = {
            "generated_at": timezone.now().isoformat(),
            "top_k_values": list(TOP_K_VALUES),
            "summary": summary,
            "by_corpus": grouped_summaries(results, "corpus"),
            "by_category": grouped_summaries(results, "category"),
            "results": results,
        }

        if options["output_json"]:
            output_path = self.output_path(options["output_json"])
            output_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.stdout.write(f"JSON: {output_path}")

        if options["output_markdown"]:
            output_path = self.output_path(options["output_markdown"])
            output_path.write_text(
                build_markdown_report(payload),
                encoding="utf-8",
            )
            self.stdout.write(f"Markdown: {output_path}")

        if options["json"]:
            self.stdout.write(
                json.dumps(payload, ensure_ascii=False, indent=2)
            )
        else:
            for result in results:
                if result["skipped"]:
                    self.stdout.write(
                        self.style.WARNING(
                            f"SKIP {result['id']} | {result['skip_reason']}"
                        )
                    )
                    continue

                style = self.style.SUCCESS if result["passed"] else self.style.ERROR
                first_rank = result["metrics"]["first_relevant_rank"] or "-"
                self.stdout.write(
                    style(
                        f"{'PASS' if result['passed'] else 'FAIL'} "
                        f"{result['id']} | {result['corpus']} | rank={first_rank}"
                    )
                )

                for failure in result["failures"]:
                    self.stdout.write(f"  - {failure}")

            metrics = summary["metrics"]
            self.stdout.write("")
            self.stdout.write(
                "Summary: "
                f"{summary['passed_count']}/{summary['case_count']} passed, "
                f"Hit@1={percentage(metrics['hit_at'][1])}, "
                f"Hit@3={percentage(metrics['hit_at'][3])}, "
                f"Hit@5={percentage(metrics['hit_at'][5])}, "
                f"MRR={metrics['mrr']:.4f}, "
                f"Recall@5={percentage(metrics['recall_at'][5])}, "
                f"PageHit@5={percentage(metrics['page_hit_at'][5])}."
            )

        if summary["failed_count"] and not options["no_fail"]:
            raise CommandError("Retrieval evaluation failed.")

    @staticmethod
    def output_path(value: str) -> Path:
        project_root = settings.BASE_DIR.parent.resolve()
        output_path = Path(value)

        if not output_path.is_absolute():
            output_path = (Path.cwd() / output_path).resolve()
        else:
            output_path = output_path.resolve()

        if not output_path.is_relative_to(project_root):
            raise CommandError("Chỉ được ghi report bên trong project.")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path
