# Yêu Cầu Chức Năng

## System Admin

- Quản lý tổ chức.
- Khóa hoặc mở tổ chức.
- Xem danh sách người dùng.
- Truy cập toàn bộ tài liệu khi cần quản trị hệ thống.

## Organization Admin

- Quản lý thông tin tổ chức.
- Quản lý phòng ban.
- Quản lý nhân viên.
- Tải tài liệu PDF và DOCX.
- Phân loại tài liệu.
- Phân quyền truy cập tài liệu theo organization, department, role hoặc private.
- Xem và quản trị mọi tài liệu không phải `PRIVATE` trong tổ chức; tài liệu
  `PRIVATE` của người khác vẫn được bảo vệ.
- Xem trạng thái xử lý tài liệu.
- Xem chunks đã trích xuất từ tài liệu.
- Đưa tài liệu lỗi hoặc đã xử lý vào hàng đợi để xử lý lại.

## Employee

- Đăng nhập.
- Xem tài liệu được phép truy cập.
- Hỏi chatbot trên phạm vi tài liệu được cấp quyền.
- Xem nguồn trích dẫn của câu trả lời.
- Xem lịch sử phiên chat.

## Hệ Thống Xử Lý Tài Liệu

- Trích xuất nội dung PDF/DOCX.
- OCR PDF scan bằng PaddleOCR khi cần.
- Chuẩn hóa OCR tiếng Việt theo hướng an toàn.
- Chia chunk bằng LangChain Text Splitters.
- Tạo embedding 384 chiều.
- Lưu vector vào PostgreSQL/pgvector.
- Ghi trạng thái `UPLOADED`, `PROCESSING`, `READY`, `FAILED`.
- Worker nhận tài liệu `UPLOADED` với khóa PostgreSQL `skip_locked`.
- Chỉ chuyển sang `READY` sau khi mọi chunk đã có embedding; lưu `FAILED` và
  thông báo lỗi nếu pipeline không hoàn tất.

## Hệ Thống RAG

- Nhận câu hỏi từ người dùng.
- Phân tích intent ở mức tổng quát: quy chế, nghiệp vụ, tiện ích, học phí.
- Lọc tài liệu bằng `accessible_documents_for_user(user)` trước retrieval.
- Tìm top-k chunks bằng semantic search kết hợp lexical/ranking rules.
- Tạo câu trả lời dựa trên chunks được truy xuất.
- Trả lời kèm citation.
- Từ chối trả lời khi không tìm thấy thông tin trong tài liệu được phép truy cập.

## Đánh Giá

- Có bộ kiểm thử RAG bằng `evaluate_rag`.
- Có bộ đo retrieval bằng `evaluate_retrieval`: Hit@k, MRR, Recall@k và Page Hit@k.
- Có bộ kiểm thử RBAC bằng `evaluate_rbac`.
- Có câu hỏi mẫu trải dài nhiều nhóm tài liệu để phục vụ báo cáo thực nghiệm.
