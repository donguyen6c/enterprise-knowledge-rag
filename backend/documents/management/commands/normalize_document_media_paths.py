from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from documents.models import Document
from documents.services.media_paths import normalize_document_file_path


class Command(BaseCommand):
    help = (
        "Chuẩn hóa đường dẫn media và đồng bộ kích thước file của Document."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--document-id",
            type=int,
            help="Chỉ kiểm tra hoặc chuẩn hóa một Document.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Thực sự copy file, cập nhật DB và xóa file cũ.",
        )
        parser.add_argument(
            "--keep-old",
            action="store_true",
            help="Giữ lại file cũ sau khi copy và cập nhật DB.",
        )
        parser.add_argument(
            "--replace-existing",
            action="store_true",
            help="Ghi đè file đích nếu đường dẫn chuẩn đã tồn tại.",
        )
        parser.add_argument(
            "--prune-empty-dirs",
            action="store_true",
            help="Xóa thư mục rỗng sau khi apply.",
        )
        parser.add_argument(
            "--delete-orphans",
            action="store_true",
            help="Xóa file trong media documents nhưng không còn được DB tham chiếu.",
        )

    def handle(self, *args, **options):
        document_id = options["document_id"]
        apply_changes = options["apply"]
        keep_old = options["keep_old"]
        replace_existing = options["replace_existing"]
        prune_empty_dirs = options["prune_empty_dirs"]
        delete_orphans = options["delete_orphans"]

        if keep_old and prune_empty_dirs:
            raise CommandError("Không dùng đồng thời --keep-old và --prune-empty-dirs.")

        queryset = (
            Document.objects.exclude(file="")
            .select_related("organization")
            .order_by("id")
        )

        if document_id:
            queryset = queryset.filter(id=document_id)

        if not queryset.exists():
            raise CommandError("Không tìm thấy Document có file phù hợp.")

        checked = 0
        path_changed = 0
        applied = 0
        skipped = 0
        metadata_changed = 0
        metadata_applied = 0
        affected_organization_ids = set()
        action = "APPLY" if apply_changes else "DRY-RUN"

        self.stdout.write(f"{action}: kiểm tra media của Document.")

        for document in queryset:
            checked += 1
            result = normalize_document_file_path(
                document,
                apply=apply_changes,
                keep_source=keep_old,
                replace_target=replace_existing,
            )

            if not result.source_exists:
                skipped += 1
                self.stdout.write(
                    f"{self.style.ERROR('MISSING')} #{document.id}: "
                    f"{result.current_name}"
                )
                continue

            if result.changed:
                path_changed += 1
                affected_organization_ids.add(document.organization_id)

                if result.applied:
                    applied += 1
                    prefix = self.style.SUCCESS("MOVED")
                elif result.target_exists:
                    skipped += 1
                    prefix = self.style.WARNING("TARGET_EXISTS")
                else:
                    prefix = self.style.WARNING("WILL_MOVE")

                self.stdout.write(
                    f"{prefix} #{document.id}: "
                    f"{result.current_name} -> {result.target_name}"
                )

            current_file_name = document.file.name
            actual_file_size = document.file.storage.size(current_file_name)

            if document.file_size != actual_file_size:
                previous_file_size = document.file_size or 0
                metadata_changed += 1

                if apply_changes:
                    Document.objects.filter(pk=document.pk).update(
                        file_size=actual_file_size
                    )
                    document.file_size = actual_file_size
                    metadata_applied += 1

                prefix = "SYNCED" if apply_changes else "WILL_SYNC"
                self.stdout.write(
                    f"{prefix} #{document.id}: file_size "
                    f"{previous_file_size} -> {actual_file_size} bytes"
                )

        if delete_orphans:
            orphan_count, orphan_organization_ids = self.clean_orphan_files(
                apply_changes
            )
            affected_organization_ids.update(orphan_organization_ids)
            self.stdout.write(
                f"{'Đã xóa' if apply_changes else 'Sẽ xóa'} "
                f"{orphan_count} orphan file."
            )

        if apply_changes and prune_empty_dirs:
            removed_count = self.prune_empty_document_dirs(affected_organization_ids)
            self.stdout.write(f"Đã xóa {removed_count} thư mục rỗng.")

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Hoàn tất: checked={checked}, path_changed={path_changed}, "
                f"path_applied={applied}, metadata_changed={metadata_changed}, "
                f"metadata_applied={metadata_applied}, skipped={skipped}."
            )
        )

        if not apply_changes and (path_changed or metadata_changed):
            self.stdout.write(
                "Đây mới là dry-run. Chạy lại với --apply để cập nhật thật."
            )

    def clean_orphan_files(self, apply_changes: bool) -> tuple[int, set[int]]:
        media_root = Path(settings.MEDIA_ROOT).resolve()
        referenced_names = set(
            Document.objects.exclude(file="").values_list("file", flat=True)
        )
        base_dir = media_root / "organizations"

        if not base_dir.exists():
            return 0, set()

        orphan_count = 0
        organization_ids = set()

        for file_path in base_dir.rglob("*"):
            if not file_path.is_file():
                continue

            relative_name = file_path.resolve().relative_to(media_root).as_posix()

            if "/documents/" not in relative_name:
                continue

            if relative_name in referenced_names:
                continue

            orphan_count += 1
            parts = relative_name.split("/")

            if len(parts) > 1 and parts[0] == "organizations" and parts[1].isdigit():
                organization_ids.add(int(parts[1]))

            prefix = "DELETE" if apply_changes else "ORPHAN"
            self.stdout.write(f"{prefix}: {relative_name}")

            if apply_changes:
                file_path.unlink()

        return orphan_count, organization_ids

    @staticmethod
    def prune_empty_document_dirs(organization_ids: set[int]) -> int:
        removed_count = 0
        media_root = Path(settings.MEDIA_ROOT).resolve()

        for organization_id in organization_ids:
            base_dir = (
                media_root
                / "organizations"
                / str(organization_id)
                / "documents"
            ).resolve()

            if not base_dir.exists() or not base_dir.is_dir():
                continue

            if not base_dir.is_relative_to(media_root):
                raise CommandError("Đường dẫn media không hợp lệ.")

            directories = sorted(
                (
                    path
                    for path in base_dir.rglob("*")
                    if path.is_dir()
                ),
                key=lambda path: len(path.parts),
                reverse=True,
            )

            for directory in directories:
                if directory == base_dir:
                    continue

                try:
                    next(directory.iterdir())
                except StopIteration:
                    directory.rmdir()
                    removed_count += 1

        return removed_count
