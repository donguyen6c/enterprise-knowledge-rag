from django.core.management.base import BaseCommand, CommandError

from documents.models import DocumentChunk
from documents.services.indexing import generate_chunk_embeddings


class Command(BaseCommand):
    help = "Tạo embedding cho các DocumentChunk."

    def add_arguments(self, parser):
        parser.add_argument(
            "--document-id",
            type=int,
            help="Chỉ tạo embedding cho một Document.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Tạo embedding cho tất cả chunk chưa có vector.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Tạo lại cả những chunk đã có embedding.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=16,
            help="Số chunk xử lý trong mỗi batch.",
        )

    def handle(self, *args, **options):
        document_id = options["document_id"]
        process_all = options["all"]
        force = options["force"]
        batch_size = options["batch_size"]

        if not document_id and not process_all:
            raise CommandError("Phải truyền --document-id hoặc --all.")

        if batch_size <= 0:
            raise CommandError("--batch-size phải lớn hơn 0.")

        queryset = DocumentChunk.objects.filter(
            document__status="READY",
            document__is_active=True,
        ).order_by("id")

        if document_id:
            queryset = queryset.filter(document_id=document_id)

        if not force:
            queryset = queryset.filter(embedding__isnull=True)

        total = queryset.count()

        if total == 0:
            self.stdout.write(
                self.style.WARNING("Không có chunk nào cần tạo embedding.")
            )
            return

        self.stdout.write(f"Chuẩn bị tạo embedding cho {total} chunk.")

        processed = generate_chunk_embeddings(
            queryset,
            batch_size=batch_size,
        )

        self.stdout.write(
            self.style.SUCCESS(f"Hoàn tất tạo embedding cho {processed} chunk.")
        )
