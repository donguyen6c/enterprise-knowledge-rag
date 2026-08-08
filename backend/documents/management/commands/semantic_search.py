from django.core.management.base import BaseCommand, CommandError

from accounts.models import User
from rag.services.search import semantic_search

class Command(BaseCommand):
    help = "Thử Semantic Search trên DocumentChunk."

    def add_arguments(self, parser):
        parser.add_argument(
            "query",
            type=str,
            help="Câu hỏi hoặc nội dung cần tìm.",
        )

        parser.add_argument(
            "--email",
            required=True,
            help="Email user dùng để kiểm tra RBAC.",
        )

        parser.add_argument(
            "--limit",
            type=int,
            default=5,
        )

    def handle(self, *args, **options):
        try:
            user = User.objects.get(email=options["email"])
        except User.DoesNotExist as exc:
            raise CommandError( "Không tìm thấy user.") from exc

        results = semantic_search( user=user, query=options["query"], limit=options["limit"],)

        if not results:
            self.stdout.write(self.style.WARNING("Không tìm thấy kết quả phù hợp."))
            return

        for position, chunk in enumerate( results, start=1,):
            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    f"#{position}"
                    f" | distance={chunk.distance:.4f}"
                    f" | semantic={chunk.semantic_score:.4f}"
                    f" | final={chunk.final_score:.4f}"
                )
            )
            self.stdout.write(f"Document: {chunk.document.title}")
            self.stdout.write(f"Trang: {chunk.page_number}")
            self.stdout.write(f"Mục: {chunk.section_title}")
            self.stdout.write(chunk.content[:700])