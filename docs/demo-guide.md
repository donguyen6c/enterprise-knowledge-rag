# Hướng Dẫn Demo Đồ Án

File này dùng để chạy demo nhanh khi báo cáo hoặc kiểm thử project.

## 1. Khởi Động Hệ Thống

Backend:

```powershell
cd R:\JOB\enterprise-knowledge-rag\backend
..\.venv312\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Worker xử lý tài liệu, chạy ở terminal thứ hai:

```powershell
cd R:\JOB\enterprise-knowledge-rag\backend
..\.venv312\Scripts\python.exe -X utf8 manage.py run_document_worker --poll-interval 2
```

Frontend:

```powershell
cd R:\JOB\enterprise-knowledge-rag\frontend
npm.cmd run dev -- --hostname 127.0.0.1 --port 3001
```

Mở:

```text
http://127.0.0.1:3001
```

## 2. Demo Chat RAG

Đăng nhập bằng user có quyền truy cập tài liệu:

```text
admin@ou.edu.vn
```

Câu hỏi nên demo:

### Học phí và các khoản thu

```text
Học phí ngành Công nghệ thông tin khóa 2025 bao nhiêu?
Học phí ngành Tâm lý học khóa 2025 bao nhiêu?
Học phí ngành Tâm lý học khóa 2023 bao nhiêu?
Tiếng Anh căn bản bao nhiêu một tín chỉ?
Chi phí học GDQP-AN và GDTC tại Long Hưng gồm những gì?
Học phí chương trình tiên tiến khóa 2025 tính thế nào?
Học lại đóng bao nhiêu tiền?
Học vượt tính học phí thế nào?
Khi nào được hoàn học phí?
```

### Cơ sở, lịch học và GDQP

```text
Trường có bao nhiêu cơ sở?
Địa chỉ cơ sở Nhà Bè ở đâu?
Thời gian học tập của cơ sở Nhà Bè
Thời gian học tập của cơ sở Võ Văn Tần
Thời gian học tập của cơ sở Long Hưng GDQP
GDQP học ở đâu?
Học GDQP trong bao lâu?
Xem lịch học ở đâu?
```

### Đăng ký môn, thi và điểm

```text
Quy trình đăng ký môn học như thế nào?
Muốn rút môn học thì làm sao?
Muốn rút bớt môn thì làm sao?
Muốn phúc khảo điểm thi thì làm sao?
Xem lịch thi ở đâu?
Bị trùng lịch thi thì làm gì?
```

### Quy chế học tập

```text
Điều kiện xét tốt nghiệp là gì?
Khi nào bị cảnh báo học tập?
Trường hợp nào bị buộc thôi học?
Muốn bảo lưu kết quả học tập
```

### Hệ thống và dịch vụ sinh viên

```text
Số điện thoại Phòng Quản lý đào tạo là gì?
SIS là gì?
LMS đăng nhập ở đâu?
Email sinh viên dùng thế nào?
Thư viện ở đâu?
```

### Đời sống sinh viên

```text
Trường có những học bổng nào?
Sinh viên vi phạm gì sẽ bị kỷ luật?
Trường có ký túc xá không?
```

Điểm cần chỉ ra khi demo:

- Câu trả lời có trích dẫn nguồn.
- Citation có document id, trang, snippet.
- Câu hỏi học phí trả đúng số tiền và đúng tài liệu.
- Câu hỏi quy trình trả theo dạng hướng dẫn.
- Câu hỏi quy chế trả theo nguồn, không bịa ngoài tài liệu.

## 3. Demo Tab Tài Liệu

Trong sidebar, bấm tab **Tài liệu**.

Nội dung cần chỉ ra:

- Tổng số tài liệu user truy cập được.
- Số tài liệu `READY`.
- Trạng thái từng tài liệu.
- Số chunk của tài liệu.
- Nội dung chunk, số trang, token count, trạng thái embedding.
- Với tài khoản quản trị: nút **Xử lý lại** đưa tài liệu vào hàng đợi; giao
  diện tự cập nhật qua các trạng thái `UPLOADED`, `PROCESSING`, `READY` hoặc
  `FAILED`.

Mục đích của tab này là chứng minh cả vòng đời ingest và dữ liệu chunks mà
chatbot dùng để trả lời. Không bấm **Xử lý lại** khi chỉ muốn demo xem dữ liệu,
vì OCR tài liệu scan có thể mất thời gian.

## 4. Demo RBAC

Tài khoản KFC demo dùng chung mật khẩu `KfcDemo@2026`:

```text
admin.kfc.demo@example.com
operations.kfc.demo@example.com
people.kfc.demo@example.com
```

Thử lần lượt:

```text
operations.kfc.demo@example.com
-> "Mã buổi đào tạo cá nhân của Nguyễn Minh là gì?"
-> thấy KFC-DEMO-MINH-1509

people.kfc.demo@example.com
-> "Ứng tuyển nhân viên nhà hàng KFC gồm những bước nào?"
-> thấy tài liệu phòng Nhân sự

people.kfc.demo@example.com
-> không thể thấy checklist phòng Vận hành hoặc kế hoạch PRIVATE
```

Chạy command:

```powershell
cd R:\JOB\enterprise-knowledge-rag\backend
$env:PYTHONIOENCODING='utf-8'
..\.venv312\Scripts\python.exe manage.py evaluate_rbac --show-answer
```

Kỳ vọng:

```text
admin@ou.edu.vn        -> truy cập được tài liệu, trả lời có citation
donguyen6c@gmail.com   -> không thuộc organization, không thấy tài liệu
KFC Vận hành           -> thấy 5 tài liệu READY
KFC Nhân sự            -> thấy 4 tài liệu READY
```

Điểm cần nhấn mạnh:

RBAC được áp dụng trước retrieval, không phải tìm kiếm toàn bộ rồi mới lọc ở cuối.
Kết quả command hiện tại là `8/8 passed`.

## 5. Demo Evaluation

Chạy:

```powershell
cd R:\JOB\enterprise-knowledge-rag\backend
$env:PYTHONIOENCODING='utf-8'
..\.venv312\Scripts\python.exe manage.py evaluate_rag --show-answer
```

Kết quả hiện tại:

```text
Summary: 34/34 passed, 0 failed.
```

Đo riêng retrieval trên cả hai tổ chức:

```powershell
..\.venv312\Scripts\python.exe manage.py evaluate_retrieval
```

Kết quả hiện tại:

```text
23/23 đạt top 5
Hit@1=91,3%; Hit@3=100%; Hit@5=100%; MRR=0,9565
Page Hit@5=100%
```

Ý nghĩa:

- Bộ câu hỏi phủ học phí, quy chế, nghiệp vụ, tiện ích.
- Mỗi case kiểm tra nội dung trả lời và nguồn trích dẫn.
- Retrieval evaluation đo thứ hạng tài liệu/trang độc lập với câu trả lời.
- Giúp chứng minh hệ thống RAG hoạt động ổn định sau khi chỉnh OCR/retrieval/UI.

## 6. Các Lệnh Kiểm Tra Trước Khi Báo Cáo

Backend:

```powershell
..\.venv312\Scripts\python.exe manage.py check
..\.venv312\Scripts\python.exe manage.py test
..\.venv312\Scripts\python.exe manage.py evaluate_rag
..\.venv312\Scripts\python.exe manage.py evaluate_retrieval
..\.venv312\Scripts\python.exe manage.py evaluate_rbac
```

Frontend:

```powershell
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build
```
