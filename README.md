# Enterprise Knowledge RAG

Đồ án: **Hệ thống quản lý tri thức đa tổ chức tích hợp chatbot RAG, Semantic Search và Role-Based Access Control**.

Hệ thống cho phép quản lý tài liệu theo tổ chức/phòng ban/vai trò, trích xuất nội dung PDF/DOCX, chia chunk, tạo embedding với `sentence-transformers`, lưu vector bằng `pgvector`, và hỏi đáp bằng RAG có nguồn trích dẫn. Retrieval luôn lọc quyền bằng RBAC trước khi tìm kiếm.

Phiên bản hiện tại là RAG hướng trích xuất: câu trả lời được tạo từ đoạn nguồn, parser và template có kiểm soát. Project chưa tích hợp một LLM sinh văn bản tự do.

## Công nghệ

- Backend: Django REST Framework, JWT, PostgreSQL, pgvector
- Document processing: PyMuPDF, pypdf, PaddleOCR, LangChain Text Splitters
- RAG: sentence-transformers, hybrid semantic ranking, LangChain Document wrapper
- Frontend: Next.js App Router, React, TypeScript

## Chạy Backend

```powershell
cd R:\JOB\enterprise-knowledge-rag\backend
..\.venv312\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

API root:

```text
http://127.0.0.1:8000/
```

Chạy worker xử lý tài liệu ở một terminal backend khác:

```powershell
cd R:\JOB\enterprise-knowledge-rag\backend
..\.venv312\Scripts\python.exe -X utf8 manage.py run_document_worker --poll-interval 2
```

Worker lấy lần lượt các tài liệu `UPLOADED`, trích xuất/chia chunk, tạo
embedding rồi mới chuyển sang `READY`. Nếu một bước lỗi, tài liệu được chuyển
sang `FAILED` và lưu thông báo lỗi để quản trị viên thử lại.

## Chạy Frontend

```powershell
cd R:\JOB\enterprise-knowledge-rag\frontend
npm.cmd run dev -- --hostname 127.0.0.1 --port 3001
```

Mở:

```text
http://127.0.0.1:3001
```

Nếu port `3001` bận, đổi sang `3000` hoặc port khác.

## Tài khoản Demo OU

```text
admin@ou.edu.vn
```

User này thuộc organization 1 và có quyền truy cập corpus tài liệu demo.

## Tổ Chức Demo KFC

Corpus thứ hai dùng nguồn công khai của KFC Việt Nam và tài liệu nội bộ mô
phỏng có gắn nhãn rõ. Tạo hoặc cập nhật dữ liệu bằng:

```powershell
cd R:\JOB\enterprise-knowledge-rag\backend
..\.venv312\Scripts\python.exe -X utf8 manage.py seed_kfc_demo
```

Tài khoản KFC demo:

```text
admin.kfc.demo@example.com
operations.kfc.demo@example.com
people.kfc.demo@example.com
```

Mật khẩu dùng chung: `KfcDemo@2026`.

Chi tiết nguồn và câu hỏi thử nằm tại
[`sample-data/kfc-demo/README.md`](sample-data/kfc-demo/README.md).

## Luồng Chính

1. Đăng nhập bằng JWT.
2. Frontend gọi API qua proxy `/backend/*`.
3. Backend lọc tài liệu bằng `accessible_documents_for_user(user)`.
4. Semantic Search tìm top chunks trong phạm vi user được phép xem.
5. RAG trả lời kèm citations: document, page, chunk, snippet.
6. Tab Tài liệu cho phép xem trạng thái, chunks và đưa tài liệu vào hàng đợi
   xử lý lại theo quyền quản trị.

## API Quan Trọng

```text
POST /api/auth/login/
GET  /api/chats/sessions/
POST /api/chats/ask/
GET  /api/documents/
GET  /api/documents/{id}/chunks/
GET  /api/documents/{id}/download/
POST /api/documents/{id}/process/
```

Frontend proxy:

```text
/backend/api/chats/ask/ -> http://127.0.0.1:8000/api/chats/ask/
```

## Kiểm Tra Hệ Thống

Backend:

```powershell
cd R:\JOB\enterprise-knowledge-rag\backend
$env:PYTHONIOENCODING='utf-8'
..\.venv312\Scripts\python.exe manage.py check
..\.venv312\Scripts\python.exe manage.py test
..\.venv312\Scripts\python.exe manage.py evaluate_rag
..\.venv312\Scripts\python.exe manage.py evaluate_retrieval
..\.venv312\Scripts\python.exe manage.py evaluate_rbac
```

Frontend:

```powershell
cd R:\JOB\enterprise-knowledge-rag\frontend
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build
```

Kết quả hiện tại:

```text
unit tests        : 34/34 passed
evaluate_rag      : 16/16 passed
evaluate_retrieval: 23/23 passed at Hit@5
evaluate_rbac     : 8/8 passed
```

Retrieval hiện đạt `Hit@1 = 91,3%`, `Hit@3 = Hit@5 = 100%`,
`MRR = 0,9565` và `Page Hit@5 = 100%` trên 23 case OU + KFC. Báo cáo chi
tiết nằm tại [`docs/results/retrieval-evaluation.md`](docs/results/retrieval-evaluation.md).

## Xử Lý Tài Liệu

Đưa tài liệu vào hàng đợi từ giao diện bằng nút **Xử lý lại** hoặc gọi:

```text
POST /api/documents/{id}/process/
```

Worker phải đang chạy để nhận công việc. Khi cần chạy đồng bộ một tài liệu từ
terminal:

```powershell
cd R:\JOB\enterprise-knowledge-rag\backend
..\.venv312\Scripts\python.exe manage.py process_documents --document-id 1 --reprocess
```

Lệnh trên đã thực hiện cả chunking và embedding. `generate_embeddings` chỉ cần
dùng riêng khi muốn phục hồi vector mà không trích xuất lại tài liệu.

Không nên reprocess toàn bộ corpus nếu không cần, vì OCR/PaddleOCR có thể chạy lâu.

## Tài Liệu Bổ Sung

- [Guide toàn bộ hệ thống: frontend, backend, RAG, OCR, RBAC và cách debug](docs/system-guide.md)
- [Tổng quan dự án](docs/project-overview.md)
- [Yêu cầu chức năng](docs/functional-requirements.md)
- [Hướng dẫn demo](docs/demo-guide.md)
- [Đánh giá RAG, retrieval và RBAC](docs/evaluation.md)
- [Rà soát phạm vi đồ án](docs/project-audit.md)
- [Tài liệu tham khảo](docs/references.md)

 .\.venv312\Scripts\Activate.ps1 