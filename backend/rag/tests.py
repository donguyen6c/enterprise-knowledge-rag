from django.test import SimpleTestCase
from langchain_core.documents import Document as LangChainDocument

from rag.services.answering import (
    build_context_answer,
    filter_answerable_documents,
    focused_excerpt,
)
from rag.services.academic_policies import academic_policy_kind
from rag.services.embeddings import (
    EMBEDDING_WINDOW_TOKEN_LIMIT,
    embedding_token_count,
    split_text_for_embedding,
)
from rag.services.fees import repeat_study_fee_requested
from rag.services.intents import (
    QueryIntent,
    classify_query_intent,
    topic_condition_for_query,
)
from rag.services.query_transform import build_query_variants
from rag.services.search import document_title_matches_query_topic
from rag.services.student_services import (
    campus_count_requested,
    course_registration_requested,
    defense_location_requested,
    exam_adjustment_requested,
    library_requested,
    requested_online_system,
    study_schedule_lookup_requested,
)
from rag.services.student_life import student_life_topic
from rag.services.study_time import is_study_time_query
from rag.services.tuition import find_tuition_match
from rag.retrieval_evaluation import calculate_ranking_metrics


class RagRuleTests(SimpleTestCase):
    def test_common_student_question_variants_are_recognized(self):
        self.assertTrue(repeat_study_fee_requested("Học lại đóng bao nhiêu?"))
        self.assertTrue(
            repeat_study_fee_requested("Học vượt tính học phí thế nào?")
        )
        self.assertTrue(course_registration_requested("Muốn rút bớt môn"))
        self.assertTrue(study_schedule_lookup_requested("Xem lịch học ở đâu?"))
        self.assertTrue(exam_adjustment_requested("Bị trùng lịch thi"))
        self.assertTrue(library_requested("Thư viện nằm ở đâu?"))
        self.assertEqual(requested_online_system("SIS là gì?"), "sis")
        self.assertEqual(requested_online_system("Vào LMS ở đâu?"), "lms")
        self.assertEqual(
            requested_online_system("Email sinh viên dùng thế nào?"),
            "email",
        )

    def test_common_academic_policy_questions_map_to_their_rules(self):
        self.assertEqual(
            academic_policy_kind("Khi nào bị cảnh báo học tập?"),
            "warning",
        )
        self.assertEqual(
            academic_policy_kind("Trường hợp nào bị buộc thôi học?"),
            "dismissal",
        )
        self.assertEqual(
            academic_policy_kind("Muốn bảo lưu kết quả học tập"),
            "temporary_leave",
        )

    def test_schedule_lookup_is_distinct_from_study_duration(self):
        self.assertFalse(is_study_time_query("Xem lịch học ở đâu?"))
        self.assertTrue(is_study_time_query("Học GDQP trong bao lâu?"))

    def test_common_student_life_questions_map_to_their_sources(self):
        self.assertEqual(
            student_life_topic("Trường có những học bổng nào?"),
            "scholarships",
        )
        self.assertEqual(
            student_life_topic("Vi phạm gì thì bị kỷ luật?"),
            "discipline",
        )
        self.assertEqual(
            student_life_topic("Trường có ký túc xá không?"),
            "housing",
        )

    def test_unanswerable_context_is_filtered_by_semantic_score(self):
        documents = [
            LangChainDocument(
                page_content="Đoạn gần từ khóa nhưng không trả lời câu hỏi.",
                metadata={"semantic_score": 0.49},
            ),
            LangChainDocument(
                page_content="Đoạn đủ liên quan để dùng làm câu trả lời.",
                metadata={"semantic_score": 0.50},
            ),
        ]

        filtered = filter_answerable_documents(documents)

        self.assertEqual(filtered, [documents[1]])

    def test_campus_count_and_defense_location_questions_are_recognized(self):
        self.assertTrue(campus_count_requested("Trường có mấy cơ sở?"))
        self.assertTrue(campus_count_requested("Có bao nhiêu cơ sở học tập?"))
        self.assertFalse(campus_count_requested("Cơ sở Nhà Bè ở đâu?"))
        self.assertTrue(defense_location_requested("GDQP ở đâu?"))
        self.assertTrue(
            defense_location_requested(
                "Học Giáo dục Quốc phòng - An ninh tại cơ sở nào?"
            )
        )

    def test_intent_classifier_covers_main_question_groups(self):
        self.assertEqual(
            classify_query_intent("Điều kiện xét tốt nghiệp là gì?"),
            QueryIntent.POLICY,
        )
        self.assertEqual(
            classify_query_intent("Quy trình rút môn như thế nào?"),
            QueryIntent.PROCEDURE,
        )
        self.assertEqual(
            classify_query_intent("Địa chỉ cơ sở Nhà Bè ở đâu?"),
            QueryIntent.UTILITY,
        )

    def test_query_variants_expand_common_acronyms(self):
        variants = build_query_variants("HP ngành CNTT K25 bao nhiêu?")

        self.assertIn(
            "học phí ngành công nghệ thông tin K25 bao nhiêu?",
            variants,
        )

    def test_tuition_parser_works_for_major_not_bound_to_one_test_case(self):
        match = find_tuition_match(
            "Ngành Kỹ thuật phần mềm. 925.000đ/tín chỉ",
            "kỹ thuật phần mềm",
        )

        self.assertIsNotNone(match)
        self.assertEqual(match.display_major, "Kỹ thuật phần mềm")
        self.assertEqual(match.amount, "925.000đ/tín chỉ")

    def test_long_embedding_text_is_split_below_model_limit(self):
        text = " ".join(
            f"Nội dung quy định học vụ số {index}."
            for index in range(120)
        )

        parts = split_text_for_embedding(text)

        self.assertGreater(len(parts), 1)
        self.assertTrue(
            all(
                embedding_token_count(part) <= EMBEDDING_WINDOW_TOKEN_LIMIT
                for part in parts
            )
        )

    def test_context_answer_omits_page_label_for_docx_chunks(self):
        answer = build_context_answer(
            documents=[
                LangChainDocument(
                    page_content="Mã hỗ trợ thử nghiệm là DEMO-01.",
                    metadata={},
                )
            ],
            citations=[
                {
                    "document_title": "Cẩm nang thử nghiệm",
                    "page_number": None,
                }
            ],
            question="Mã hỗ trợ thử nghiệm là gì?",
        )

        self.assertIn("Cẩm nang thử nghiệm", answer)
        self.assertNotIn("trang None", answer)

    def test_focused_excerpt_uses_phrases_from_unseen_domain_question(self):
        excerpt = focused_excerpt(
            document=LangChainDocument(
                page_content=(
                    "Giới thiệu tài liệu. Nhân viên gửi yêu cầu tại cổng demo. "
                    "Mã nhóm hỗ trợ dùng để kiểm thử là EMP-SUPPORT-DEMO."
                ),
                metadata={"chunk_content": "Giới thiệu tài liệu."},
            ),
            question="Mã nhóm hỗ trợ nhân viên là gì?",
            intent=QueryIntent.GENERAL,
        )

        self.assertTrue(excerpt.startswith("Mã nhóm hỗ trợ"))
        self.assertIn("EMP-SUPPORT-DEMO", excerpt)

    def test_retrieval_metrics_measure_rank_recall_and_page(self):
        metrics = calculate_ranking_metrics(
            ranked_items=[
                (99, 1),
                (10, 2),
                (10, 3),
                (20, 8),
                (30, 1),
            ],
            expected_document_ids={10, 20},
            expected_pages_any={8},
        )

        self.assertEqual(metrics["first_relevant_rank"], 2)
        self.assertEqual(metrics["reciprocal_rank"], 0.5)
        self.assertEqual(metrics["hit_at"], {1: 0, 3: 1, 5: 1})
        self.assertEqual(metrics["recall_at"][3], 0.5)
        self.assertEqual(metrics["recall_at"][5], 1.0)
        self.assertEqual(metrics["first_relevant_page_rank"], 4)
        self.assertEqual(metrics["page_hit_at"], {1: 0, 3: 0, 5: 1})

    def test_tuition_topic_can_match_an_accented_document_title(self):
        self.assertTrue(
            document_title_matches_query_topic(
                "Mức thu tiếng Anh căn bản và các chương trình chuẩn đầu ra",
                "Học phí tiếng Anh căn bản năm học 2025-2026 bao nhiêu?",
            )
        )
        self.assertFalse(
            document_title_matches_query_topic(
                "Mức thu học phí ĐHCQ khóa 2025",
                "Học phí tiếng Anh căn bản năm học 2025-2026 bao nhiêu?",
            )
        )

    def test_exam_lookup_topic_requires_an_access_channel(self):
        condition = str(topic_condition_for_query("xem lịch thi ở đâu?"))

        self.assertIn("http", condition)
        self.assertNotIn("điều chỉnh lịch thi", condition)

    def test_grade_review_topic_is_not_expanded_to_every_exam_chunk(self):
        condition = str(
            topic_condition_for_query("muốn phúc khảo điểm thi thì làm sao?")
        )

        self.assertIn("Phúc tra", condition)
        self.assertNotIn("điều chỉnh lịch thi", condition)
