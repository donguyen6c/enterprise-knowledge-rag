# KFC Việt Nam - Dữ Liệu Demo Học Thuật

Thư mục này phục vụ kịch bản minh họa tổ chức thứ hai cho đồ án. Đây không
phải corpus nội bộ chính thức của KFC Việt Nam.

## Phân loại dữ liệu

- `Nguồn công khai`: nội dung lấy hoặc tóm tắt từ website chính thức của KFC
  Việt Nam, có URL và ngày truy cập trong từng tài liệu.
- `Dữ liệu mô phỏng`: tài liệu được tự xây dựng để kiểm thử quyền
  `DEPARTMENT`, `ROLE` và `PRIVATE`. Nội dung luôn có cảnh báo và không được
  xem là quy trình, chính sách hay cam kết thật của KFC Việt Nam.

## Nguồn công khai

1. Trang chủ và thông tin liên hệ:
   <https://www.kfcvietnam.com.vn/>
2. Chính sách hoạt động và đặt hàng:
   <https://www.kfcvietnam.com.vn/privacy-policy>
3. Hướng dẫn ứng tuyển nhân viên nhà hàng:
   <https://tuyendung.kfcvietnam.com.vn/huong-dan-ung-tuyen-1>
4. Hướng dẫn xuất hóa đơn điện tử:
   <https://hddt.kfcvietnam.com.vn/Content/Images/DEFeJJi4Poy6L6zyXn51AtsdurlnBSMnLdM6iRB8nVkB8%3D.pdf>

SHA-256 của PDF đã lưu:
`029C7632D6A508939FF6996ADBE197B7804C9061BC2B97F588F8FDAF0E3A31F6`.

Ngày đối chiếu nguồn: 11/08/2026.

## Tạo dữ liệu

```powershell
cd R:\JOB\enterprise-knowledge-rag\backend
..\.venv312\Scripts\python.exe -X utf8 manage.py seed_kfc_demo
```

Command có tính lặp lại: chạy lại sẽ cập nhật đúng các tài liệu demo thay vì
tạo bản sao. Xóa riêng dữ liệu này bằng:

```powershell
..\.venv312\Scripts\python.exe -X utf8 manage.py seed_kfc_demo --remove
```

## Câu hỏi kiểm thử

- `Hotline chăm sóc khách hàng KFC là số nào?`
- `Muốn xuất hóa đơn KFC cần thông tin gì trên bill?`
- `Ứng tuyển nhân viên nhà hàng KFC gồm những bước nào?`
- `Checklist mở ca của bộ phận vận hành gồm những gì?`
- `Nhân viên KFC demo dùng kênh nào để yêu cầu hỗ trợ?`
- `Mã buổi đào tạo cá nhân của Nguyễn Minh là gì?`

Câu cuối chỉ tài khoản chủ sở hữu tài liệu `PRIVATE` mới được phép tìm thấy.
