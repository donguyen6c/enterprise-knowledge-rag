import time

from django.core.management.base import BaseCommand, CommandError

from documents.services.jobs import claim_next_document
from documents.services.processor import process_and_index_document


class Command(BaseCommand):
    help = "Chạy worker xử lý các Document đang chờ ở trạng thái UPLOADED."

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="Xử lý tối đa một tài liệu rồi thoát.",
        )
        parser.add_argument(
            "--max-jobs",
            type=int,
            default=0,
            help="Số job tối đa; 0 nghĩa là chạy liên tục.",
        )
        parser.add_argument(
            "--poll-interval",
            type=float,
            default=2.0,
            help="Số giây chờ khi hàng đợi trống.",
        )

    def handle(self, *args, **options):
        once = options["once"]
        max_jobs = options["max_jobs"]
        poll_interval = options["poll_interval"]

        if max_jobs < 0:
            raise CommandError("--max-jobs không được âm.")

        if poll_interval <= 0:
            raise CommandError("--poll-interval phải lớn hơn 0.")

        processed = 0
        self.stdout.write("Document worker đã sẵn sàng.")

        while True:
            document = claim_next_document()

            if document is None:
                if once or (max_jobs and processed >= max_jobs):
                    break

                time.sleep(poll_interval)
                continue

            self.stdout.write(
                f"Nhận job #{document.id}: {document.title}"
            )

            try:
                chunk_count, embedding_count = process_and_index_document(
                    document
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"READY #{document.id}: {chunk_count} chunk, "
                        f"{embedding_count} embedding."
                    )
                )
            except Exception as exc:
                self.stdout.write(
                    self.style.ERROR(f"FAILED #{document.id}: {exc}")
                )

            processed += 1

            if once or (max_jobs and processed >= max_jobs):
                break

        self.stdout.write(f"Worker kết thúc sau {processed} job.")
