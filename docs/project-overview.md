# Tổng Quan Dự Án

Tên đề tài:

**Xây dựng hệ thống quản lý tri thức đa tổ chức tích hợp chatbot RAG, tìm kiếm ngữ nghĩa và kiểm soát truy cập theo vai trò.**

## Mục Tiêu

Xây dựng nền tảng cho phép tổ chức quản lý tài liệu nội bộ và cung cấp chatbot hỏi đáp dựa trên những tài liệu mà người dùng được phép truy cập.

Hệ thống tập trung vào ba điểm chính:

- quản lý tài liệu theo tổ chức, phòng ban, vai trò;
- tìm kiếm ngữ nghĩa và hỏi đáp RAG có nguồn trích dẫn;
- lọc quyền truy cập trước retrieval để bảo vệ dữ liệu.

## Đối Tượng Sử Dụng

- System Admin: quản lý toàn hệ thống.
- Organization Admin: quản lý tài liệu và người dùng trong tổ chức.
- Employee: tìm kiếm, hỏi đáp và xem tài liệu được cấp quyền.

## Công Nghệ

- Backend: Django REST Framework.
- Frontend: Next.js App Router, React, TypeScript.
- Database: PostgreSQL + pgvector.
- Authentication: JWT bằng `djangorestframework-simplejwt`.
- Document processing: PyMuPDF, pypdf, PaddleOCR.
- Chunking: LangChain Text Splitters.
- Retrieval: sentence-transformers + hybrid ranking + pgvector.

## Dữ Liệu Thử Nghiệm

Corpus thứ nhất là các tài liệu công khai của Trường Đại học Mở TP.HCM, gồm:

- thông báo học phí;
- chi phí GDQP-AN/GDTC;
- quy chế đào tạo;
- quy định đăng ký môn học;
- quy định thi/lịch thi;
- học bổng;
- Sổ Tay Sinh Viên 2024.

Corpus thứ hai là **KFC Việt Nam - Demo học thuật**, gồm:

- hai tài liệu công khai chính thức về liên hệ, đặt hàng và xuất hóa đơn;
- một bản tóm tắt tuyển dụng có URL nguồn;
- ba tài liệu nội bộ mô phỏng để kiểm tra `DEPARTMENT`, `ROLE`, `PRIVATE`.

Trạng thái hiện tại: 36 tài liệu `READY`, thuộc hai tổ chức; sáu tài liệu KFC
demo có 31 chunks và embedding đầy đủ.

## Tính Năng Đã Có

- Đăng nhập JWT.
- Chat RAG có lịch sử phiên chat.
- Citation gồm document, trang, chunk, snippet.
- Tab quản trị tài liệu để xem trạng thái/chunks, xử lý lại tài liệu và theo
  dõi worker cập nhật trạng thái.
- Hàng đợi nhẹ dựa trên PostgreSQL, có khóa `skip_locked` để nhiều worker không
  nhận cùng một tài liệu.
- Semantic Search lọc RBAC trước retrieval.
- Bộ evaluation RAG: 16/16 pass.
- Bộ evaluation retrieval đa tổ chức: 23/23 đạt top 5, MRR 0,9565.
- Bộ evaluation RBAC: 8/8 pass, gồm kiểm tra chéo hai tổ chức.
- 34 unit test kiểm tra ma trận visibility, OCR, media, token embedding và
  vòng đời queue/worker.

## Hạn Hoàn Thành

30/08/2026
