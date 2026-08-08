from django.core.management.base import ( BaseCommand, CommandError,)

from documents.models import Document
from documents.services.processor import process_document


class Command(BaseCommand):
    help = "Trích xuất và chia chunk cho các Document."

    def add_arguments(self, parser):
        parser.add_argument( "--document-id", type=int, help="Chỉ xử lý một Document.",)

        parser.add_argument("--all", action="store_true",
            help="Xử lý tất cả Document trạng thái UPLOADED.",)

        parser.add_argument( "--reprocess",
            action="store_true", help="Xử lý lại cả Document READY hoặc FAILED.", )

    def handle(self, *args, **options):
        document_id = options.get("document_id")
        process_all = options.get("all")
        reprocess = options.get("reprocess")

        if not document_id and not process_all:
            raise CommandError( "Phải truyền --document-id hoặc --all.")

        queryset = Document.objects.filter( is_active=True, )

        if document_id:
            queryset = queryset.filter(id=document_id)
        elif not reprocess:
            queryset = queryset.filter(status="UPLOADED")

        if not queryset.exists():
            self.stdout.write( self.style.WARNING( "Không có tài liệu phù hợp để xử lý."))
            return

        success_count = 0
        failed_count = 0

        for document in queryset:
            self.stdout.write(f"Đang xử lý #{document.id}: {document.title}")

            try:
                chunk_count = process_document(document)
                success_count += 1
                self.stdout.write(self.style.SUCCESS(f"Thành công: tạo {chunk_count} chunk." ))

            except Exception as exc:
                failed_count += 1

                self.stdout.write(self.style.ERROR(f"Thất bại: {exc}"))

        self.stdout.write("")

        self.stdout.write( self.style.SUCCESS(f"Hoàn tất: thành công {success_count}, "f"thất bại {failed_count}." ))