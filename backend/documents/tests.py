from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User, UserRole
from documents.models import (
    Document,
    DocumentCategory,
    DocumentPermission,
)
from documents.permissions import (
    CanModifyDocument,
    accessible_documents_for_user,
    user_can_download_document,
)
from documents.services.extractors import DocumentExtractionError
from documents.services.jobs import (
    DocumentQueueError,
    claim_next_document,
    queue_document,
)
from documents.services.media_paths import normalize_document_file_path
from documents.services.processor import (
    process_and_index_document,
    process_document,
)
from documents.services.vietnamese_corrector import (
    critical_values,
    normalize_vietnamese_ocr_text,
)
from organizations.models import Department, Organization


class OcrNormalizationTests(SimpleTestCase):
    def test_corrects_common_vietnamese_ocr_noise(self):
        raw_text = "Ngành Tam 17 h9c. 532.500d/tin chi."

        normalized = normalize_vietnamese_ocr_text(raw_text)

        self.assertEqual(
            normalized,
            "Ngành Tâm lý học. 532.500đ/tín chỉ.",
        )

    def test_preserves_critical_values_and_legal_codes(self):
        raw_text = (
            "Công ngh thông tin 925.000đ/tín chỉ; "
            "1572/TB-ĐHM; ngày 17/07/2025."
        )

        normalized = normalize_vietnamese_ocr_text(raw_text)

        self.assertEqual(critical_values(normalized), critical_values(raw_text))
        self.assertIn("1572/TB-ĐHM", normalized)
        self.assertIn("17/07/2025", normalized)


class DocumentAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organization = Organization.objects.create(name="Organization A")
        cls.other_organization = Organization.objects.create(name="Organization B")
        cls.department_a = Department.objects.create(
            organization=cls.organization,
            name="Department A",
        )
        cls.department_b = Department.objects.create(
            organization=cls.organization,
            name="Department B",
        )
        cls.employee_a = User.objects.create_user(
            username="employee-a",
            email="employee-a@example.com",
            organization=cls.organization,
            department=cls.department_a,
            role=UserRole.EMPLOYEE,
        )
        cls.employee_b = User.objects.create_user(
            username="employee-b",
            email="employee-b@example.com",
            organization=cls.organization,
            department=cls.department_b,
            role=UserRole.EMPLOYEE,
        )
        cls.org_admin = User.objects.create_user(
            username="org-admin",
            email="org-admin@example.com",
            organization=cls.organization,
            role=UserRole.ORG_ADMIN,
        )
        cls.other_employee = User.objects.create_user(
            username="other-employee",
            email="other-employee@example.com",
            organization=cls.other_organization,
            role=UserRole.EMPLOYEE,
        )
        cls.system_admin = User.objects.create_user(
            username="system-admin",
            email="system-admin@example.com",
            role=UserRole.SYSTEM_ADMIN,
        )
        cls.category = DocumentCategory.objects.create(
            organization=cls.organization,
            name="Policies",
        )
        cls.other_category = DocumentCategory.objects.create(
            organization=cls.other_organization,
            name="Other policies",
        )

        cls.organization_document = cls.create_document(
            title="Organization document",
            visibility=Document.Visibility.ORGANIZATION,
        )
        cls.department_a_document = cls.create_document(
            title="Department A document",
            visibility=Document.Visibility.DEPARTMENT,
        )
        DocumentPermission.objects.create(
            document=cls.department_a_document,
            department=cls.department_a,
            can_view=True,
            can_download=True,
        )
        cls.department_b_document = cls.create_document(
            title="Department B document",
            visibility=Document.Visibility.DEPARTMENT,
        )
        DocumentPermission.objects.create(
            document=cls.department_b_document,
            department=cls.department_b,
            can_view=True,
        )
        cls.role_document = cls.create_document(
            title="Employee role document",
            visibility=Document.Visibility.ROLE,
        )
        DocumentPermission.objects.create(
            document=cls.role_document,
            role=UserRole.EMPLOYEE,
            can_view=True,
            can_download=False,
        )
        cls.private_document = cls.create_document(
            title="Employee A private document",
            visibility=Document.Visibility.PRIVATE,
            uploaded_by=cls.employee_a,
        )
        cls.admin_private_document = cls.create_document(
            title="Admin private document",
            visibility=Document.Visibility.PRIVATE,
        )
        cls.inactive_document = cls.create_document(
            title="Inactive document",
            visibility=Document.Visibility.ORGANIZATION,
            is_active=False,
        )
        cls.other_document = Document.objects.create(
            organization=cls.other_organization,
            category=cls.other_category,
            uploaded_by=cls.other_employee,
            title="Other organization document",
            file="tests/other.pdf",
            status=Document.Status.READY,
        )

    @classmethod
    def create_document(
        cls,
        *,
        title: str,
        visibility: str,
        uploaded_by=None,
        is_active: bool = True,
    ) -> Document:
        return Document.objects.create(
            organization=cls.organization,
            category=cls.category,
            uploaded_by=uploaded_by or cls.org_admin,
            title=title,
            file=f"tests/{title}.pdf",
            status=Document.Status.READY,
            visibility=visibility,
            is_active=is_active,
        )

    @staticmethod
    def accessible_ids(user) -> set[int]:
        return set(
            accessible_documents_for_user(user).values_list("id", flat=True)
        )

    def test_employee_access_combines_org_department_role_and_private_rules(self):
        document_ids = self.accessible_ids(self.employee_a)

        self.assertSetEqual(
            document_ids,
            {
                self.organization_document.id,
                self.department_a_document.id,
                self.role_document.id,
                self.private_document.id,
            },
        )

    def test_department_and_tenant_boundaries_are_enforced(self):
        employee_b_ids = self.accessible_ids(self.employee_b)
        other_employee_ids = self.accessible_ids(self.other_employee)

        self.assertIn(self.department_b_document.id, employee_b_ids)
        self.assertNotIn(self.department_a_document.id, employee_b_ids)
        self.assertNotIn(self.private_document.id, employee_b_ids)
        self.assertSetEqual(other_employee_ids, {self.other_document.id})

    def test_system_admin_sees_active_documents_across_organizations(self):
        document_ids = self.accessible_ids(self.system_admin)

        self.assertIn(self.organization_document.id, document_ids)
        self.assertIn(self.other_document.id, document_ids)
        self.assertNotIn(self.inactive_document.id, document_ids)

    def test_org_admin_manages_org_documents_but_not_others_private_file(self):
        document_ids = self.accessible_ids(self.org_admin)

        self.assertSetEqual(
            document_ids,
            {
                self.organization_document.id,
                self.department_a_document.id,
                self.department_b_document.id,
                self.role_document.id,
                self.admin_private_document.id,
            },
        )
        self.assertNotIn(self.private_document.id, document_ids)
        self.assertNotIn(self.other_document.id, document_ids)

        self.assertTrue(
            user_can_download_document(
                self.org_admin,
                self.department_a_document,
            )
        )
        self.assertFalse(
            user_can_download_document(
                self.org_admin,
                self.private_document,
            )
        )

    def test_locked_organization_cannot_retrieve_documents(self):
        self.organization.is_active = False
        self.organization.save(update_fields=["is_active", "updated_at"])

        self.assertFalse(
            accessible_documents_for_user(self.employee_a).exists()
        )

    def test_safe_method_is_not_blocked_by_modify_permission(self):
        permission = CanModifyDocument()
        request = SimpleNamespace(user=self.employee_a, method="GET")

        self.assertTrue(
            permission.has_object_permission(
                request,
                view=None,
                document=self.organization_document,
            )
        )

    def test_employee_cannot_modify_and_org_admin_cannot_cross_tenant(self):
        permission = CanModifyDocument()
        employee_request = SimpleNamespace(user=self.employee_a, method="PATCH")
        admin_request = SimpleNamespace(user=self.org_admin, method="PATCH")

        self.assertFalse(
            permission.has_object_permission(
                employee_request,
                view=None,
                document=self.organization_document,
            )
        )
        self.assertTrue(
            permission.has_object_permission(
                admin_request,
                view=None,
                document=self.organization_document,
            )
        )
        self.assertFalse(
            permission.has_object_permission(
                admin_request,
                view=None,
                document=self.other_document,
            )
        )

    def test_download_permission_is_stricter_for_role_visibility(self):
        self.assertFalse(
            user_can_download_document(self.employee_a, self.role_document)
        )
        self.assertTrue(
            user_can_download_document(
                self.employee_a,
                self.department_a_document,
            )
        )

    def test_document_permission_requires_exactly_one_target(self):
        permission = DocumentPermission(
            document=self.department_a_document,
            department=self.department_a,
            role=UserRole.EMPLOYEE,
        )

        with self.assertRaises(ValidationError):
            permission.full_clean()


class DocumentProcessingTests(TestCase):
    def test_processing_error_persists_failed_status(self):
        organization = Organization.objects.create(name="Processing test")
        uploader = User.objects.create_user(
            username="processor",
            email="processor@example.com",
            organization=organization,
            role=UserRole.ORG_ADMIN,
        )
        document = Document.objects.create(
            organization=organization,
            uploaded_by=uploader,
            title="Missing source file",
            file="tests/file-does-not-exist.pdf",
        )

        with self.assertRaises(DocumentExtractionError):
            process_document(document)

        document.refresh_from_db()
        self.assertEqual(document.status, Document.Status.FAILED)
        self.assertIn("không tồn tại", document.error_message)

    def test_pipeline_only_marks_ready_after_embeddings_succeed(self):
        organization = Organization.objects.create(name="Pipeline test")
        uploader = User.objects.create_user(
            username="pipeline-admin",
            email="pipeline-admin@example.com",
            organization=organization,
            role=UserRole.ORG_ADMIN,
        )
        document = Document.objects.create(
            organization=organization,
            uploaded_by=uploader,
            title="Pipeline document",
            file="tests/pipeline.pdf",
            status=Document.Status.PROCESSING,
        )

        with (
            patch(
                "documents.services.processor.process_document",
                return_value=2,
            ),
            patch(
                "documents.services.processor.generate_document_embeddings",
                return_value=2,
            ),
        ):
            result = process_and_index_document(document)

        document.refresh_from_db()
        self.assertEqual(result, (2, 2))
        self.assertEqual(document.status, Document.Status.READY)

    def test_embedding_error_marks_pipeline_failed(self):
        organization = Organization.objects.create(name="Embedding failure")
        uploader = User.objects.create_user(
            username="embedding-admin",
            email="embedding-admin@example.com",
            organization=organization,
            role=UserRole.ORG_ADMIN,
        )
        document = Document.objects.create(
            organization=organization,
            uploaded_by=uploader,
            title="Embedding failure document",
            file="tests/embedding-failure.pdf",
            status=Document.Status.PROCESSING,
        )

        with (
            patch(
                "documents.services.processor.process_document",
                return_value=1,
            ),
            patch(
                "documents.services.processor.generate_document_embeddings",
                side_effect=RuntimeError("embedding unavailable"),
            ),
            self.assertRaises(RuntimeError),
        ):
            process_and_index_document(document)

        document.refresh_from_db()
        self.assertEqual(document.status, Document.Status.FAILED)
        self.assertIn("embedding unavailable", document.error_message)


class DocumentQueueTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Queue test")
        self.admin = User.objects.create_user(
            username="queue-admin",
            email="queue-admin@example.com",
            organization=self.organization,
            role=UserRole.ORG_ADMIN,
        )
        self.document = Document.objects.create(
            organization=self.organization,
            uploaded_by=self.admin,
            title="Queued document",
            file="tests/queued.pdf",
            status=Document.Status.FAILED,
            error_message="Previous failure",
        )

    def test_queue_and_claim_document(self):
        queue_document(self.document)
        self.document.refresh_from_db()

        self.assertEqual(self.document.status, Document.Status.UPLOADED)
        self.assertEqual(self.document.error_message, "")

        claimed = claim_next_document()

        self.assertIsNotNone(claimed)
        self.assertEqual(claimed.id, self.document.id)
        self.assertEqual(claimed.status, Document.Status.PROCESSING)

    def test_archived_document_cannot_be_queued(self):
        self.document.status = Document.Status.ARCHIVED
        self.document.save(update_fields=["status", "updated_at"])

        with self.assertRaises(DocumentQueueError):
            queue_document(self.document)


class DocumentQueueApiTests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Queue API")
        self.admin = User.objects.create_user(
            username="queue-api-admin",
            email="queue-api-admin@example.com",
            organization=self.organization,
            role=UserRole.ORG_ADMIN,
        )
        self.employee = User.objects.create_user(
            username="queue-api-employee",
            email="queue-api-employee@example.com",
            organization=self.organization,
            role=UserRole.EMPLOYEE,
        )
        self.document = Document.objects.create(
            organization=self.organization,
            uploaded_by=self.admin,
            title="Retry through API",
            file="tests/retry-api.pdf",
            status=Document.Status.FAILED,
        )
        self.url = f"/api/documents/{self.document.id}/process/"

    def test_org_admin_can_queue_failed_document(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data["status"], Document.Status.UPLOADED)

    def test_employee_cannot_queue_document(self):
        self.client.force_authenticate(user=self.employee)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_processing_document_returns_conflict(self):
        self.document.status = Document.Status.PROCESSING
        self.document.save(update_fields=["status", "updated_at"])
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)


class DocumentMediaPathTests(TestCase):
    def test_replacing_upload_overwrites_canonical_file_safely(self):
        organization = Organization.objects.create(name="Media test")
        uploader = User.objects.create_user(
            username="media-admin",
            email="media-admin@example.com",
            organization=organization,
            role=UserRole.ORG_ADMIN,
        )

        with TemporaryDirectory() as media_root, self.settings(
            MEDIA_ROOT=media_root
        ):
            document = Document.objects.create(
                organization=organization,
                uploaded_by=uploader,
                title="Media document",
                original_filename="first.pdf",
                file=SimpleUploadedFile("first.pdf", b"first version"),
            )
            first_result = normalize_document_file_path(
                document,
                apply=True,
                replace_target=True,
            )

            self.assertTrue(first_result.applied)
            self.assertEqual(
                document.file.name,
                f"organizations/{organization.id}/documents/"
                f"{document.id}/original.pdf",
            )

            document.file.save(
                "second.pdf",
                SimpleUploadedFile("second.pdf", b"second version"),
                save=True,
            )
            second_result = normalize_document_file_path(
                document,
                apply=True,
                replace_target=True,
            )

            self.assertTrue(second_result.applied)
            canonical_path = Path(media_root) / document.file.name
            self.assertEqual(canonical_path.read_bytes(), b"second version")
