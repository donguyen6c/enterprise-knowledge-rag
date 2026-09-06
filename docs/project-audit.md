# Rà Soát Phạm Vi Đồ Án

Ngày rà soát: 11/08/2026

## Kết Luận

Project đang đi đúng hướng với tên đề tài **Hệ thống quản lý tri thức đa tổ
chức tích hợp chatbot RAG, Semantic Search và Role-Based Access Control**.
Các thành phần cốt lõi đã nối được thành một luồng chạy hoàn chỉnh: xác thực,
lọc quyền, xử lý tài liệu, embedding, retrieval, trả lời có nguồn và giao diện
chat.

Hệ thống hiện phù hợp để trình bày như một **RAG hướng trích xuất có lớp trả
lời xác định**. Nó chưa nên được mô tả là chatbot sinh câu trả lời bằng LLM,
vì tầng trả lời hiện dùng đoạn trích, template và parser theo miền dữ liệu.

## Đối Chiếu Phạm Vi

| Hạng mục | Trạng thái | Bằng chứng trong project |
| --- | --- | --- |
| Quản lý đa tổ chức | Đã có nền tảng | `Organization`, `Department`, `User.organization` |
| RBAC trước retrieval | Đã có | `accessible_documents_for_user()` được gọi trước truy vấn `DocumentChunk` |
| Bốn mức visibility | Đã có code và unit test | `ORGANIZATION`, `DEPARTMENT`, `ROLE`, `PRIVATE` |
| Xác thực và phiên đăng nhập | Đã có | JWT access/refresh, blacklist khi logout |
| Ingest PDF/DOCX | Đã có | pypdf, PyMuPDF, python-docx và PaddleOCR |
| Hậu xử lý OCR tiếng Việt | Đã có, còn sai số | Giữ raw OCR, bảo vệ số tiền/ngày/mã văn bản |
| LangChain | Đã dùng thực chất | Chia chunk và cửa sổ embedding bằng `RecursiveCharacterTextSplitter`; chuẩn hóa nguồn bằng `LangChainDocument` |
| Semantic Search | Đã có | Sentence Transformers, pgvector, cosine distance và hybrid ranking |
| Chatbot RAG có citation | Đã có | Trả document, trang, chunk và snippet |
| Lịch sử phiên chat | Đã có | `ChatSession`, `ChatMessage` và giao diện phiên chat |
| Quản trị tài liệu | Đã có ở mức đồ án | Django Admin, tab tài liệu/chunk, API queue/retry và worker nền |
| Evaluation tự động | Đã có | 16 case câu trả lời, 23 case retrieval OU + KFC, 8 case RBAC và unit test ma trận quyền |

## Những Điểm Đã Sửa Sau Rà Soát

- Không còn để `DEBUG` dưới dạng chuỗi luôn đúng; cấu hình đọc từ biến môi
  trường và có `ALLOWED_HOSTS` rõ ràng.
- `EMPLOYEE` có thể xem chi tiết tài liệu được phép; quyền sửa vẫn chỉ dành
  cho quản trị viên.
- Tổ chức bị khóa không thể đăng nhập hoặc retrieval tài liệu.
- Kiểm tra phòng ban, danh mục và tài liệu phải thuộc cùng tổ chức.
- Khi thay file, đường dẫn media chuẩn được cập nhật và nội dung cũ được thay
  đúng; tài liệu trở lại trạng thái `UPLOADED` để tránh dùng chunk cũ.
- Trạng thái `FAILED` được lưu thật khi xử lý lỗi, thay vì bị transaction
  rollback.
- Chunk mới dùng số token của model. Chunk cũ vượt giới hạn 128 token được
  chia cửa sổ trước khi embedding để không âm thầm mất phần cuối.
- Bổ sung unit test cho bốn visibility, tenant boundary, khóa tổ chức, OCR,
  parser học phí, đường dẫn media và giới hạn token.
- Bổ sung hàng đợi nhẹ dùng trạng thái tài liệu trong PostgreSQL. Worker khóa
  công việc bằng `select_for_update(skip_locked=True)` và chỉ đặt `READY` sau
  khi hoàn tất cả chunking lẫn embedding.
- Organization Admin/System Admin có thể đưa tài liệu vào hàng đợi xử lý lại
  từ frontend; Employee chỉ được xem.
- `sentence-transformers`, `transformers`, PaddleOCR và LangChain splitter
  được nạp lười. Các command Django nhẹ và worker rỗng khởi động nhanh hơn;
  model chỉ được tải khi có truy vấn, chunking hoặc job OCR/embedding đầu tiên.

## Giới Hạn Cần Nói Thẳng Trong Báo Cáo

1. Corpus KFC dùng hai tài liệu công khai thật và bốn tài liệu dẫn xuất/mô
   phỏng để minh họa quyền. Các tài liệu mô phỏng không đại diện cho chính
   sách hoặc quy trình nội bộ thật của KFC Việt Nam.
2. Bộ 16 câu trả lời và 23 case retrieval là regression suite trên corpus hiện
   tại. Kết quả pass không đồng nghĩa độ chính xác 100% đối với mọi câu hỏi
   hoặc tài liệu mới.
3. Một số câu trả lời cần số liệu chính xác dùng parser/template theo miền
   trường học. Khi triển khai cho doanh nghiệp khác, core RAG và RBAC giữ
   nguyên nhưng lớp quy tắc miền phải được cấu hình hoặc thay thế.
4. OCR có thể còn lỗi ở PDF scan, font nhúng lỗi hoặc bảng phức tạp. Raw OCR
   được giữ để đối chiếu; hệ thống không được tự sửa số liệu thiếu căn cứ.
5. Hàng đợi hiện dùng PostgreSQL và management-command worker, phù hợp phạm vi
   đồ án nhưng chưa có retry theo lịch, giám sát phân tán hoặc broker chuyên
   dụng như Celery/RQ cho tải production lớn.
6. Frontend lưu JWT trong `localStorage`; phù hợp demo nội bộ nhưng production
   nên chuyển refresh token sang cookie `HttpOnly` và dùng HTTPS.

## Mức Hoàn Thiện Hợp Lý

Nếu tính theo phạm vi đồ án đã nêu, project ở khoảng **94%**:

- phần lõi backend/RAG/RBAC và giao diện demo đã hoàn thành;
- phần còn lại chủ yếu là đóng gói triển khai production, quan sát worker và
  hoàn thiện báo cáo/slide;
- việc tích hợp LLM generator chỉ cần nếu yêu cầu hội đồng bắt buộc câu trả lời
  phải do mô hình sinh, thay vì RAG trích xuất có kiểm soát như hiện tại.

## Việc Nên Làm Trước Khi Bảo Vệ

1. Chạy kịch bản đăng nhập OU, KFC Vận hành và KFC Nhân sự để quay/chụp minh
   chứng RBAC đa tổ chức.
2. Đưa báo cáo `Hit@k`, `MRR`, `Recall@k` và `Page Hit@k` đã xuất vào chương
   thực nghiệm, tách khỏi độ đúng của câu trả lời.
3. Chụp lại luồng upload -> process -> embedding -> chat -> citation.
4. Chuẩn bị một slide nói rõ LangChain nằm ở đâu và vì sao không dùng agent.
5. Không tuyên bố OCR hay chatbot chính xác tuyệt đối; trình bày cơ chế kiểm
   soát sai số và từ chối khi không đủ nguồn.
