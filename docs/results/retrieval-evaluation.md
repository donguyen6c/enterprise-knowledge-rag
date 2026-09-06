# Báo Cáo Đánh Giá Retrieval

Thời điểm chạy: `2026-08-11T09:41:45.802771+00:00`

Luồng được đo là luồng production: query transformation, lọc RBAC, hybrid retrieval và gộp thứ hạng chunk. Chất lượng câu trả lời không được dùng để tính các chỉ số dưới đây.

## Chỉ Số Tổng Hợp

| Chỉ số | Kết quả |
| --- | ---: |
| Số case | 23 |
| Pass top 5 | 23/23 |
| Hit@1 | 91.3% |
| Hit@3 | 100.0% |
| Hit@5 | 100.0% |
| MRR | 0.9565 |
| Recall@5 | 97.8% |
| Page Hit@5 | 100.0% |
| Page MRR | 0.6833 |

## Theo Corpus

| Corpus | Cases | Hit@1 | Hit@3 | Hit@5 | MRR | Recall@5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| kfc_demo | 7 | 100.0% | 100.0% | 100.0% | 1.0000 | 100.0% |
| ou | 16 | 87.5% | 100.0% | 100.0% | 0.9375 | 96.9% |

## Kết Quả Từng Case

| Case | Corpus | Category | First rank | Hit@5 | Page rank |
| --- | --- | --- | ---: | ---: | ---: |
| tuition_it_k2025 | ou | tuition | 1 | 1 | 1 |
| tuition_psychology_k2025 | ou | tuition | 1 | 1 | 1 |
| tuition_psychology_k2023 | ou | tuition | 1 | 1 | 1 |
| fee_english_basic | ou | fees | 1 | 1 | 1 |
| fee_gdqp_gdtc_long_hung | ou | fees | 1 | 1 | 2 |
| fee_advanced_program_k2025 | ou | fees | 1 | 1 | 1 |
| study_time_nha_be | ou | utility | 1 | 1 | 2 |
| study_time_vo_van_tan | ou | utility | 1 | 1 | 2 |
| study_time_long_hung_gdqp | ou | utility | 1 | 1 | - |
| procedure_course_registration | ou | procedure | 2 | 1 | 3 |
| procedure_course_withdrawal | ou | procedure | 2 | 1 | 3 |
| procedure_grade_review | ou | procedure | 1 | 1 | 1 |
| utility_exam_schedule | ou | utility | 1 | 1 | 1 |
| utility_academic_office_contact | ou | utility | 1 | 1 | 2 |
| utility_campus_nha_be | ou | utility | 1 | 1 | 2 |
| policy_graduation_conditions | ou | policy | 1 | 1 | 1 |
| kfc_invoice_bill_fields | kfc_demo | procedure | 1 | 1 | 5 |
| kfc_invoice_qr_code | kfc_demo | procedure | 1 | 1 | 4 |
| kfc_customer_hotline | kfc_demo | utility | 1 | 1 | - |
| kfc_recruitment_steps | kfc_demo | procedure | 1 | 1 | - |
| kfc_opening_checklist_code | kfc_demo | procedure | 1 | 1 | - |
| kfc_employee_support_code | kfc_demo | utility | 1 | 1 | - |
| kfc_private_training_code | kfc_demo | private | 1 | 1 | - |

## Cách Diễn Giải

- `Hit@k`: tỷ lệ câu hỏi có ít nhất một tài liệu đúng trong top-k chunks.
- `MRR`: trung bình nghịch đảo thứ hạng của chunk đúng đầu tiên.
- `Recall@k`: tỷ lệ tài liệu ground-truth xuất hiện trong top-k.
- `Page Hit@k`: tỷ lệ case có ground-truth trang tìm đúng trang trong top-k.
- Kết quả chỉ đại diện cho bộ câu hỏi và corpus tại thời điểm chạy.
