from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from documents.models import DocumentChunk
from documents.services.chunker import estimate_token_count
from documents.services.vietnamese_corrector import normalize_vietnamese_ocr_text


class Command(BaseCommand):
    help = "Chuẩn hóa lại nội dung chunk đã OCR mà không chạy OCR lại."

    def add_arguments(self, parser):
        parser.add_argument(
            "--document-id",
            type=int,
            help="Chỉ chuẩn hóa chunk của một Document.",
        )
        parser.add_argument(
            "--all-ocr",
            action="store_true",
            help="Chuẩn hóa tất cả chunk có metadata source=paddle_ocr.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Chỉ đếm chunk sẽ thay đổi, không ghi database.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Số chunk kiểm tra trong mỗi batch.",
        )

    def handle(self, *args, **options):
        document_id = options["document_id"]
        all_ocr = options["all_ocr"]
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        if not document_id and not all_ocr:
            raise CommandError("Phải truyền --document-id hoặc --all-ocr.")

        if batch_size <= 0:
            raise CommandError("--batch-size phải lớn hơn 0.")

        queryset = (
            DocumentChunk.objects.filter(
                document__status="READY",
                document__is_active=True,
            )
            .select_related("document")
            .order_by("id")
        )

        if document_id:
            queryset = queryset.filter(document_id=document_id)

        if all_ocr:
            queryset = queryset.filter(metadata__source="paddle_ocr")

        total = queryset.count()

        if total == 0:
            self.stdout.write(
                self.style.WARNING("Không có chunk OCR phù hợp để chuẩn hóa.")
            )
            return

        checked = 0
        changed = 0
        changed_document_ids: set[int] = set()
        pending_updates = []

        self.stdout.write(f"Đang kiểm tra {total} chunk OCR.")

        for chunk in queryset.iterator(chunk_size=batch_size):
            checked += 1
            normalized_content = normalize_vietnamese_ocr_text(chunk.content)

            if normalized_content == chunk.content:
                continue

            changed += 1
            changed_document_ids.add(chunk.document_id)

            if dry_run:
                continue

            chunk.content = normalized_content
            chunk.token_count = estimate_token_count(normalized_content)
            chunk.embedding = None
            pending_updates.append(chunk)

            if len(pending_updates) >= batch_size:
                self._bulk_update(pending_updates, batch_size)
                pending_updates = []

        if pending_updates:
            self._bulk_update(pending_updates, batch_size)

        action = "Sẽ chuẩn hóa" if dry_run else "Đã chuẩn hóa"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} {changed}/{checked} chunk."
            )
        )

        if changed_document_ids:
            document_ids = ", ".join(
                str(document_id)
                for document_id in sorted(changed_document_ids)
            )
            self.stdout.write(f"Document cần tạo lại embedding: {document_ids}")

    @staticmethod
    def _bulk_update(chunks, batch_size):
        with transaction.atomic():
            DocumentChunk.objects.bulk_update(
                chunks,
                ["content", "token_count", "embedding"],
                batch_size=batch_size,
            )
