from pathlib import Path

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from documents.models import Document
from documents.services.ocr import ocr_pdf
from documents.services.vietnamese_corrector import normalize_vietnamese_ocr_text


class Command(BaseCommand):
    help = "Chạy thử PaddleOCR cho một Document, không cập nhật database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--document-id",
            type=int,
            required=True,
        )

        parser.add_argument(
            "--dpi",
            type=int,
            default=300,
        )

        parser.add_argument(
            "--page",
            action="append",
            type=int,
            help="Chỉ OCR một trang cụ thể. Có thể truyền nhiều lần.",
        )

        parser.add_argument(
            "--normalized",
            action="store_true",
            help="In thêm bản hậu xử lý OCR tiếng Việt.",
        )

    def handle(self, *args, **options):
        document_id = options["document_id"]
        dpi = options["dpi"]
        page_numbers = set(options["page"] or [])

        try:
            document = Document.objects.get(
                id=document_id,
            )
        except Document.DoesNotExist as exc:
            raise CommandError(
                "Không tìm thấy Document."
            ) from exc

        if not document.file:
            raise CommandError(
                "Document chưa có file."
            )

        file_path = Path(document.file.path)

        if file_path.suffix.lower() != ".pdf":
            raise CommandError(
                "Command này hiện chỉ hỗ trợ PDF."
            )

        self.stdout.write(
            f"Đang OCR #{document.id}: {document.title}"
        )

        pages = ocr_pdf(
            file_path=file_path,
            dpi=dpi,
            page_numbers=page_numbers or None,
        )

        for page_number, text in pages:
            self.stdout.write("")
            self.stdout.write("=" * 80)
            self.stdout.write(f"TRANG {page_number}")
            self.stdout.write("=" * 80)
            self.stdout.write(text[:5000])

            if options["normalized"]:
                self.stdout.write("")
                self.stdout.write("-" * 80)
                self.stdout.write("SAU HẬU XỬ LÝ OCR")
                self.stdout.write("-" * 80)
                self.stdout.write(
                    normalize_vietnamese_ocr_text(text)[:5000]
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nHoàn tất OCR {len(pages)} trang."
            )
        )
