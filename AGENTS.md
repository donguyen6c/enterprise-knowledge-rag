# Enterprise Knowledge RAG — Project Instructions

## Project overview

Đây là đồ án:

"Hệ thống quản lý tri thức đa tổ chức tích hợp chatbot RAG,
Semantic Search và Role-Based Access Control".

Mục tiêu là xây dựng hệ thống quản lý tài liệu doanh nghiệp theo tổ chức,
phòng ban và vai trò. Người dùng chỉ được tìm kiếm và hỏi đáp trên những
tài liệu mà họ có quyền truy cập.

Dữ liệu thử nghiệm hiện tại là các quy chế, thông báo học phí, học bổng
và quy định của Trường Đại học Mở TP.HCM.

## Technology stack

Backend:
- Django REST Framework
- PostgreSQL
- pgvector
- JWT bằng djangorestframework-simplejwt
- PaddleOCR
- PyMuPDF và pypdf
- sentence-transformers

Frontend:
- Next.js, chưa phải trọng tâm hiện tại.

Python environment chính thức hiện tại:

`R:\JOB\enterprise-knowledge-rag\.venv312`

Python version:
- Python 3.12

Luôn chạy lệnh backend bằng môi trường `.venv312`.

## Project structure

```text
enterprise-knowledge-rag/
├── .venv312/
├── backend/
│   ├── accounts/
│   ├── organizations/
│   ├── documents/
│   │   ├── services/
│   │   │   ├── extractors.py
│   │   │   ├── chunker.py
│   │   │   ├── processor.py
│   │   │   └── ocr.py
│   │   └── management/commands/
│   ├── rag/
│   │   ├── services/
│   │   │   ├── embeddings.py
│   │   │   └── search.py
│   │   └── management/commands/
│   ├── chats/
│   ├── config/
│   └── manage.py
├── frontend/
└── sample-data/

# Enterprise Knowledge RAG — Project Instructions

## Project overview

Đây là đồ án:

"Hệ thống quản lý tri thức đa tổ chức tích hợp chatbot RAG,
Semantic Search và Role-Based Access Control".

Mục tiêu là xây dựng hệ thống quản lý tài liệu doanh nghiệp theo tổ chức,
phòng ban và vai trò. Người dùng chỉ được tìm kiếm và hỏi đáp trên những
tài liệu mà họ có quyền truy cập.

Dữ liệu thử nghiệm hiện tại là các quy chế, thông báo học phí, học bổng
và quy định của Trường Đại học Mở TP.HCM.

## Technology stack

Backend:
- Django REST Framework
- PostgreSQL
- pgvector
- JWT bằng djangorestframework-simplejwt
- PaddleOCR
- PyMuPDF và pypdf
- sentence-transformers

Frontend:
- Next.js, chưa phải trọng tâm hiện tại.

Python environment chính thức hiện tại:

`R:\JOB\enterprise-knowledge-rag\.venv312`

Python version:
- Python 3.12

Luôn chạy lệnh backend bằng môi trường `.venv312`.

## Project structure

```text
enterprise-knowledge-rag/
├── .venv312/
├── backend/
│   ├── accounts/
│   ├── organizations/
│   ├── documents/
│   │   ├── services/
│   │   │   ├── extractors.py
│   │   │   ├── chunker.py
│   │   │   ├── processor.py
│   │   │   └── ocr.py
│   │   └── management/commands/
│   ├── rag/
│   │   ├── services/
│   │   │   ├── embeddings.py
│   │   │   └── search.py
│   │   └── management/commands/
│   ├── chats/
│   ├── config/
│   └── manage.py
├── frontend/
└── sample-data/
Authorization model

Roles:

SYSTEM_ADMIN
ORG_ADMIN
EMPLOYEE

Document visibility:

ORGANIZATION
DEPARTMENT
ROLE
PRIVATE

Semantic Search và RAG phải lọc quyền bằng:

accessible_documents_for_user(user)

Quyền phải được lọc trước retrieval. Không được tìm kiếm trên toàn bộ
DocumentChunk rồi mới kiểm tra quyền ở cuối.

Current database state

Các model chính đã có:

Organization
Department
User
DocumentCategory
Document
DocumentPermission
DocumentChunk

DocumentChunk có:

document
chunk_index
content
page_number
section_title
token_count
metadata
embedding VectorField 384 chiều

PostgreSQL đã bật extension pgvector.

Current document-processing state

Pipeline hiện tại:

UPLOADED
→ PROCESSING
→ extract PDF/DOCX
→ chunk
→ embedding
→ READY

Nếu xử lý lỗi:

PROCESSING → FAILED

Kết quả gần nhất:

19 Document xử lý thành công.
9 Document FAILED do PDF scan hoặc không có text hợp lệ.
Tạm thời chưa xử lý lại 9 tài liệu FAILED.

Không tự động OCR hoặc reprocess toàn bộ corpus nếu chưa được yêu cầu.

Embedding and retrieval

Embedding model hiện tại:

sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

Embedding dimensions:

384

Semantic Search hiện là hybrid ranking:

cosine similarity;
lọc tài liệu theo chủ đề;
ưu tiên khóa học;
ưu tiên chunk có tên ngành;
ưu tiên chunk chứa mức tiền;
RBAC trước retrieval.

Câu kiểm thử chính:

"Học phí ngành Công nghệ thông tin khóa 2025 bao nhiêu?"

Kết quả đúng phải lấy Document ID 1, trang 2, với mức:

925.000 đồng/tín chỉ

Semantic Search hiện đã tìm đúng Document và đúng chunk.

Không chỉnh rag/services/search.py trừ khi có lỗi retrieval mới được chứng minh.

OCR state

PaddleOCR đã cài và chạy được.

PaddlePaddle cần giữ phiên bản đang tương thích với Windows/Python 3.12.
Không tự nâng phiên bản PaddlePaddle.

OCR test command:

python manage.py test_paddle_ocr --document-id 1 --dpi 300

PaddleOCR đọc đúng:

tên ngành tương đối;
số tiền;
vị trí bảng tương đối.

Nhưng OCR vẫn làm mất nhiều dấu tiếng Việt, ví dụ:

Công nghệ thông tin
→ Công ngh thông tin

Hệ thống thông tin quản lý
→ H thng thông tin qun lý

Đây là vấn đề hiện tại cần giải quyết.

Không dùng hàng loạt text.replace() để sửa từng từ vì có thể làm sai:

văn bản pháp lý;
tên ngành;
số tiền;
ngày tháng;
số quyết định;
mã văn bản.

Mọi bước chuẩn hóa OCR phải bảo toàn tuyệt đối:

925.000đ/tín chỉ;
ngày tháng;
phần trăm;
số quyết định;
mã như 1572/TB-ĐHM;
mã như 81/2021/NĐ-CP.
Current task

Nhiệm vụ tiếp theo là nghiên cứu và triển khai bước hậu xử lý OCR tiếng Việt.

Mục tiêu:

PaddleOCR raw text
→ safe Vietnamese OCR normalization
→ DocumentChunk content
→ embedding

Yêu cầu:

Giữ nguyên raw OCR để đối chiếu.
Không sửa số liệu bằng mô hình hoặc quy tắc không an toàn.
Chỉ kiểm thử với Document ID 1.
Không chạy xử lý lại tất cả Document.
Không tạo migration nếu chưa thật sự cần.
Hỏi người dùng trước khi cài package mới.
Trình bày kế hoạch trước khi chỉnh code.
Sau khi chỉnh phải hiển thị diff.
Không xóa dữ liệu hiện tại.
Không thay đổi các file không liên quan.
Safe test workflow

Kích hoạt môi trường:

cd R:\JOB\enterprise-knowledge-rag
.\.venv312\Scripts\Activate.ps1
cd backend

Kiểm tra Django:

python manage.py check

Kiểm thử OCR mà không cập nhật database:

python manage.py test_paddle_ocr --document-id 1 --dpi 300

Chỉ sau khi OCR đạt yêu cầu mới chạy:

python manage.py process_documents --document-id 1 --reprocess
python manage.py generate_embeddings --document-id 1

Kiểm thử Semantic Search:

python manage.py semantic_search `
  "Học phí ngành Công nghệ thông tin khóa 2025 bao nhiêu?" `
  --email "admin@ou.edu.vn" `
  --limit 5
Rules for Codex

Trước khi sửa:

Đọc các file liên quan.
Tóm tắt pipeline thực tế từ code.
Đưa kế hoạch ngắn.
Chờ xác nhận nếu cần thay đổi kiến trúc hoặc cài package.

Trong khi sửa:

Chỉ sửa phạm vi tối thiểu.
Không giả định tên field hoặc API.
Dựa trên code thật trong repository.
Không chạy migration tự động.
Không chạy toàn bộ corpus.
Không ghi đè dữ liệu cũ ngoài Document ID 1.

Sau khi sửa:

Chạy test nhỏ nhất cần thiết.
Hiển thị các file đã thay đổi.
Hiển thị diff.
Nêu rõ lệnh nào đã chạy.
Nêu rõ phần nào chưa được giải quyết.

---

## 3. Tạo thêm file ghi trạng thái ngắn

Bạn có thể tạo:

```powershell
notepad PROJECT_STATUS.md

Dán:

# Current Project Status

Updated: 2026-08-01

## Completed

- Django project and PostgreSQL database.
- Custom User, Organization and Department.
- Document RBAC.
- JWT authentication.
- Document APIs.
- PDF/DOCX extraction.
- DocumentChunk creation.
- pgvector embedding.
- Semantic Search.
- PaddleOCR installation.
- Retrieval currently finds the correct tuition document and chunk.

## Current confirmed answer

For Document ID 1:

Question:
"Học phí ngành Công nghệ thông tin khóa 2025 bao nhiêu?"

Correct source:
- Document: Mức thu học phí ĐHCQ khóa 2025 – năm học 2025–2026
- Page: 2
- Tuition: 925.000 đồng/tín chỉ

## Current issue

PaddleOCR preserves numbers but frequently drops Vietnamese diacritics.

Example:

```text
Ngành Công nghệ thông tin
→ Ngành Công ngh thông tin

The next task is safe OCR post-processing or a better Vietnamese
recognition strategy without corrupting legal identifiers and numbers.

Do not modify semantic ranking until OCR quality has been addressed.


---

## 4. Sau khi tạo project, gửi prompt này cho Codex

```text
Đọc AGENTS.md và PROJECT_STATUS.md trước.

Sau đó đọc code thật trong các file:

- backend/documents/services/ocr.py
- backend/documents/services/extractors.py
- backend/documents/services/processor.py
- backend/rag/services/search.py
- backend/documents/management/commands/test_paddle_ocr.py

Chưa sửa code.

Hãy:
1. Tóm tắt pipeline hiện tại.
2. So sánh pipeline thực tế với AGENTS.md.
3. Xác định chính xác nơi phù hợp để cải thiện lỗi mất dấu tiếng Việt.
4. Đề xuất phương án tối thiểu.
5. Bảo toàn số liệu, ngày tháng và mã văn bản.
6. Không đề xuất text.replace thủ công.
7. Không chạy lại toàn bộ tài liệu.
8. Chỉ lập kế hoạch, chờ tôi xác nhận trước khi sửa.