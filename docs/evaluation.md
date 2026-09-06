# Đánh Giá RAG, Retrieval Và RBAC

## Mục Tiêu

Phần đánh giá dùng để chứng minh chatbot không chỉ "trả lời được", mà còn:

- trả đúng nội dung quan trọng;
- lấy đúng tài liệu nguồn;
- trích đúng trang;
- không truy cập tài liệu ngoài quyền của user;
- không trả lời khi user không có quyền truy cập corpus.

## RAG Evaluation

Command:

```powershell
cd R:\JOB\enterprise-knowledge-rag\backend
$env:PYTHONIOENCODING='utf-8'
..\.venv312\Scripts\python.exe manage.py evaluate_rag --show-answer
```

Nguồn test nằm ở:

```text
backend/rag/evaluation_cases.py
backend/rag/management/commands/evaluate_rag.py
```

Mỗi case gồm:

- câu hỏi;
- nhóm câu hỏi;
- các cụm từ bắt buộc có trong đáp án;
- document id kỳ vọng;
- trang kỳ vọng.

Ví dụ:

```text
Câu hỏi:
Học phí ngành Công nghệ thông tin khóa 2025 bao nhiêu?

Kỳ vọng:
- đáp án có "Công nghệ thông tin";
- đáp án có "925.000";
- citation có Document ID 1;
- citation có trang 2.
```

Nhóm câu hỏi hiện có:

- học phí chương trình chuẩn;
- phí tiếng Anh căn bản;
- chi phí GDQP-AN/GDTC Long Hưng;
- thời gian học tập ở các cơ sở;
- đăng ký/rút môn học;
- phúc khảo/khiếu nại điểm;
- lịch thi;
- liên hệ Phòng Quản lý đào tạo;
- địa chỉ cơ sở;
- điều kiện xét tốt nghiệp.

Kết quả hiện tại:

```text
Summary: 16/16 passed, 0 failed.
```

## Retrieval Evaluation

Command này đo riêng chất lượng tìm kiếm, không dùng nội dung câu trả lời để
tính điểm:

```powershell
cd R:\JOB\enterprise-knowledge-rag\backend
$env:PYTHONIOENCODING='utf-8'
..\.venv312\Scripts\python.exe manage.py evaluate_retrieval `
  --output-json ..\docs\results\retrieval-evaluation.json `
  --output-markdown ..\docs\results\retrieval-evaluation.md
```

Luồng được đo là luồng production gồm query transformation, lọc RBAC trước
retrieval, hybrid ranking và gộp thứ hạng chunk. Bộ ground truth gồm 16 case
OU và 7 case KFC demo, trải trên học phí, quy trình, tiện ích, quy chế và tài
liệu private.

Kết quả ngày 11/08/2026:

```text
Cases       : 23/23 đạt top 5
Hit@1       : 91,3%
Hit@3       : 100,0%
Hit@5       : 100,0%
MRR         : 0,9565
Recall@5    : 97,8%
Page Hit@5  : 100,0%
```

Hai case có tài liệu đúng ở hạng 2 được giữ nguyên trong báo cáo thay vì thêm
quy tắc ép hạng. `Recall@5` thấp hơn 100% vì một case có nhiều tài liệu nguồn
hợp lệ nhưng top 5 không chứa đủ mọi tài liệu đó. Xem bảng từng case tại
[`results/retrieval-evaluation.md`](results/retrieval-evaluation.md) và dữ
liệu máy đọc tại
[`results/retrieval-evaluation.json`](results/retrieval-evaluation.json).

## RBAC Evaluation

Command:

```powershell
cd R:\JOB\enterprise-knowledge-rag\backend
$env:PYTHONIOENCODING='utf-8'
..\.venv312\Scripts\python.exe manage.py evaluate_rbac --show-answer
```

Nguồn test nằm ở:

```text
backend/rag/management/commands/evaluate_rbac.py
```

Các nhóm case hiện tại:

```text
admin@ou.edu.vn
-> thuộc organization 1
-> thấy 30 tài liệu READY
-> hỏi học phí CNTT K2025 trả đúng Document 1

donguyen6c@gmail.com
-> không thuộc organization
-> thấy 0 tài liệu READY
-> chatbot trả "chưa tìm thấy"

operations.kfc.demo@example.com
-> thấy tài liệu ORGANIZATION, ROLE, phòng Vận hành và PRIVATE của chính mình

people.kfc.demo@example.com
-> thấy tài liệu ORGANIZATION, ROLE và phòng Nhân sự
-> không thấy checklist Vận hành hoặc kế hoạch PRIVATE của Nguyễn Minh

admin@ou.edu.vn
-> không thể truy cập hoặc trích dẫn corpus KFC
```

Kết quả hiện tại:

```text
Summary: 8/8 passed, 0 failed.
```

## Ý Nghĩa Trong Báo Cáo

Có thể trình bày phần này trong chương thực nghiệm:

1. Xây dựng bộ câu hỏi kiểm thử theo nhóm intent.
2. Với mỗi câu hỏi, xác định đáp án và nguồn kỳ vọng.
3. Chạy tự động bằng management command.
4. Ghi nhận tỷ lệ pass.
5. Kiểm thử RBAC bằng user thuộc hai tổ chức và hai phòng ban khác nhau.

Điểm quan trọng:

RAG evaluation kiểm tra chất lượng trả lời, retrieval evaluation đo thứ hạng
nguồn, còn RBAC evaluation kiểm tra an toàn truy cập.

## Unit Test Quy Tắc Nền

Ngoài các case phụ thuộc corpus, chạy:

```powershell
..\.venv312\Scripts\python.exe manage.py test
```

Bộ này dùng database test độc lập để kiểm tra đủ bốn mức visibility,
tenant boundary, quyền Organization Admin, tổ chức bị khóa, trạng thái xử lý
lỗi, chuẩn hóa OCR, đường dẫn media và giới hạn token embedding.

Các kết quả trên là regression result của corpus và ground truth hiện tại,
không phải cam kết độ chính xác 100% cho mọi câu hỏi hoặc mọi tài liệu mới.
