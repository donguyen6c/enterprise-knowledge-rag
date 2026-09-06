from django.core.management.base import BaseCommand, CommandError

from documents.models import Document
from documents.services.processor import process_and_index_document


class Command(BaseCommand):
    help = "Trích xuất, chia chunk và tạo embedding cho Document."

    def add_arguments(self, parser):
        parser.add_argument(
            "--document-id",
            type=int,
            help="Chỉ xử lý một Document.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Xử lý tất cả Document trạng thái UPLOADED.",
        )
        parser.add_argument(
            "--reprocess",
            action="store_true",
            help="Xử lý lại cả Document READY hoặc FAILED.",
        )
    def handle(self, *args, **options):
        document_id = options["document_id"]
        process_all = options["all"]
        reprocess = options["reprocess"]

        if not document_id and not process_all:
            raise CommandError("Phải truyền --document-id hoặc --all.")

        queryset = Document.objects.filter(is_active=True).exclude(
            status__in=[
                Document.Status.PROCESSING,
                Document.Status.ARCHIVED,
            ]
        )

        if document_id:
            queryset = queryset.filter(id=document_id)

        if not reprocess:
            queryset = queryset.filter(status=Document.Status.UPLOADED)

        if not queryset.exists():
            self.stdout.write(
                self.style.WARNING("Không có tài liệu phù hợp để xử lý.")
            )
            return

        success_count = 0
        failed_count = 0

        for document in queryset:
            self.stdout.write(f"Đang xử lý #{document.id}: {document.title}")

            try:
                chunk_count, embedding_count = process_and_index_document(
                    document
                )

                success_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Thành công: {chunk_count} chunk, "
                        f"{embedding_count} embedding."
                    )
                )
            except Exception as exc:
                failed_count += 1
                self.stdout.write(self.style.ERROR(f"Thất bại: {exc}"))

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Hoàn tất: thành công {success_count}, "
                f"thất bại {failed_count}."
            )
        )
