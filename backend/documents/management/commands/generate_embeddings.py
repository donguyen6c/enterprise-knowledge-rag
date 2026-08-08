from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from documents.models import DocumentChunk
from rag.services.embeddings import embed_documents


class Command(BaseCommand):
    help = "Tạo embedding cho các DocumentChunk."

    def add_arguments(self, parser):
        parser.add_argument("--document-id", type=int, help="Chỉ tạo embedding cho một Document.",)
        parser.add_argument("--all", action="store_true", help="Tạo embedding cho tất cả chunk chưa có vector.",)
        parser.add_argument("--force", action="store_true", help="Tạo lại cả những chunk đã có embedding.",)
        parser.add_argument("--batch-size", type=int, default=16, help="Số chunk xử lý trong mỗi batch.", )

    def handle(self, *args, **options):
        document_id = options["document_id"]
        process_all = options["all"]
        force = options["force"]
        batch_size = options["batch_size"]

        if not document_id and not process_all:
            raise CommandError("Phải truyền --document-id hoặc --all.")

        if batch_size <= 0:
            raise CommandError("--batch-size phải lớn hơn 0.")

        queryset = DocumentChunk.objects.filter( document__status="READY", document__is_active=True,).order_by("id")

        if document_id:
            queryset = queryset.filter( document_id=document_id,)

        if not force:
            queryset = queryset.filter( embedding__isnull=True,)

        total = queryset.count()

        if total == 0:
            self.stdout.write(
                self.style.WARNING( "Không có chunk nào cần tạo embedding.")
            )
            return

        self.stdout.write( f"Chuẩn bị tạo embedding cho {total} chunk.")

        processed = 0

        while True:
            chunks = list( queryset[:batch_size])

            if not chunks:
                break

            texts = [ self._build_embedding_text(chunk) for chunk in chunks ]

            vectors = embed_documents(texts)

            with transaction.atomic():
                for chunk, vector in zip( chunks, vectors, strict=True,):
                    chunk.embedding = vector

                DocumentChunk.objects.bulk_update( chunks,["embedding"], batch_size=batch_size,)

            processed += len(chunks)

            self.stdout.write(
                self.style.SUCCESS( f"Đã xử lý {processed}/{total} chunk.")
            )

            # Khi --force được bật, queryset vẫn chứa các chunk vừa xử lý.
            # Vì vậy cần dịch theo ID để tránh vòng lặp vô hạn.
            if force:
                last_id = chunks[-1].id
                queryset = queryset.filter(id__gt=last_id)

        self.stdout.write(
            self.style.SUCCESS(f"Hoàn tất tạo embedding cho {processed} chunk.")
        )

    @staticmethod
    def _build_embedding_text(chunk):
        """
        Ghép thêm tiêu đề và section để vector có ngữ cảnh tốt hơn.
        """
        parts = [ f"Tài liệu: {chunk.document.title}",]

        if chunk.section_title:
            parts.append( f"Mục: {chunk.section_title}")

        parts.append(chunk.content)

        return "\n".join(parts)
