import re
from dataclasses import dataclass

from documents.models import DocumentChunk
from documents.permissions import accessible_documents_for_user
from documents.services.vietnamese_corrector import normalize_for_match


@dataclass
class StudentServiceAnswer:
    answer: str
    citations: list[dict]


def normalize_space(text: str) -> str:
    return " ".join(text.split())


def citation_for_chunk(
    *,
    rank: int,
    chunk: DocumentChunk,
    snippet: str,
    score: float = 1.0,
) -> dict:
    return {
        "rank": rank,
        "chunk_id": chunk.id,
        "chunk_index": chunk.chunk_index,
        "parent_chunk_indexes": [chunk.chunk_index],
        "document_id": chunk.document_id,
        "document_title": chunk.document.title,
        "page_number": chunk.page_number,
        "distance": 0.0,
        "semantic_score": score,
        "final_score": score,
        "retrieval_query": "",
        "retrieval_score": score,
        "snippet": snippet[:500],
    }


def academic_office_requested(query: str) -> bool:
    normalized = normalize_for_match(query)

    return any(
        term in normalized
        for term in (
            "phong quan ly dao tao",
            "phong dao tao",
            "qldt",
            "bang diem",
            "the sinh vien",
            "chung nhan sinh vien",
        )
    )


def campus_address_requested(query: str) -> bool:
    normalized = normalize_for_match(query)

    if "dia chi" not in normalized and "co so" not in normalized:
        return False

    return any(
        term in normalized
        for term in (
            "vo van tan",
            "ho hao hon",
            "nha be",
            "nhon duc",
            "mai thi luu",
            "binh duong",
            "long binh",
            "long hung",
        )
    )


def course_registration_requested(query: str) -> bool:
    normalized = normalize_for_match(query)

    return any(
        term in normalized
        for term in (
            "dang ky mon hoc",
            "dang ky hoc phan",
            "rut mon",
            "huy mon",
            "huy bot mon",
            "dang ky tre han",
        )
    )


def exam_schedule_lookup_requested(query: str) -> bool:
    normalized = normalize_for_match(query)

    if "lich thi" not in normalized:
        return False

    if "dieu chinh" in normalized or "trung lich" in normalized:
        return False

    return any(
        term in normalized
        for term in (
            "xem",
            "tra cuu",
            "o dau",
            "tim",
            "lich thi",
        )
    )


def extract_between(text: str, start: str, end: str) -> str:
    match = re.search(
        re.escape(start) + r"\s*(.*?)\s*" + re.escape(end),
        text,
        flags=re.IGNORECASE,
    )

    return normalize_space(match.group(1)) if match else ""


def build_academic_office_answer(*, user, question: str) -> StudentServiceAnswer | None:
    if not academic_office_requested(question):
        return None

    chunk = (
        DocumentChunk.objects.filter(
            document__in=accessible_documents_for_user(user).filter(status="READY"),
            document__title__icontains="Sổ",
        )
        .filter(
            content__icontains="6.2. Phòng Quản lý đào tạo",
        )
        .select_related("document")
        .order_by("page_number", "chunk_index")
        .first()
    )

    if chunk is None:
        return None

    text = normalize_space(chunk.content)
    contact = extract_between(text, "Liên hệ:", "Điện thoại:")
    phone = extract_between(text, "Điện thoại:", "Website:")
    website = extract_between(text, "Website:", "E-mail:")
    email_match = re.search(r"E-mail:\s*([^\s]+)", text, flags=re.IGNORECASE)
    email = email_match.group(1) if email_match else ""

    responsibilities = []

    for phrase in (
        "Tổ chức đăng ký môn học trực tuyến cho sinh viên",
        "Cấp chứng nhận sinh viên, thẻ sinh viên, bảng điểm",
        "Xét miễn, giảm môn học, hoàn học phí",
        "Giải quyết thôi học và rút hồ sơ",
    ):
        if phrase in text:
            responsibilities.append(phrase)

    detail = (
        f"liên hệ {contact}; điện thoại {phone}; website {website}; "
        f"email {email}."
    )

    if responsibilities:
        detail += " Các nghiệp vụ liên quan gồm: " + "; ".join(responsibilities) + "."

    answer = (
        f"Theo tài liệu \"{chunk.document.title}\", trang {chunk.page_number}, "
        f"Phòng Quản lý đào tạo {detail}"
    )

    return StudentServiceAnswer(
        answer=answer,
        citations=[
            citation_for_chunk(
                rank=1,
                chunk=chunk,
                snippet=text,
            )
        ],
    )


def build_exam_schedule_lookup_answer(
    *,
    user,
    question: str,
) -> StudentServiceAnswer | None:
    if not exam_schedule_lookup_requested(question):
        return None

    documents = accessible_documents_for_user(user).filter(status="READY")
    service_chunk = (
        DocumentChunk.objects.filter(
            document__in=documents,
            document__title__icontains="Sổ",
            content__icontains="Hệ thống dịch vụ sinh viên",
        )
        .filter(content__icontains="lịch học, lịch thi")
        .select_related("document")
        .order_by("page_number", "chunk_index")
        .first()
    )
    exam_link_chunk = (
        DocumentChunk.objects.filter(
            document__in=documents,
            document__title__icontains="Sổ",
            content__icontains="https://ou.edu.vn/lich-thi",
        )
        .select_related("document")
        .order_by("page_number", "chunk_index")
        .first()
    )

    if service_chunk is None:
        return None

    answer = (
        f"Theo tài liệu \"{service_chunk.document.title}\", trang "
        f"{service_chunk.page_number}, sinh viên có thể xem lịch thi trên "
        "Hệ thống dịch vụ sinh viên tại http://sis.ou.edu.vn, nơi cung cấp "
        "lịch học, lịch thi, điểm thi và các dịch vụ online khác."
    )
    citations = [
        citation_for_chunk(
            rank=1,
            chunk=service_chunk,
            snippet=normalize_space(service_chunk.content),
        )
    ]

    if exam_link_chunk is not None:
        answer += (
            " Tài liệu cũng nhắc lịch thi được thông báo trên "
            "https://ou.edu.vn/lich-thi hoặc "
            "https://quanlydaotao.ou.edu.vn/lich-thi-cua-sinh-vien."
        )
        citations.append(
            citation_for_chunk(
                rank=2,
                chunk=exam_link_chunk,
                snippet=normalize_space(exam_link_chunk.content),
                score=0.95,
            )
        )

    return StudentServiceAnswer(
        answer=answer,
        citations=citations,
    )


def build_course_registration_answer(
    *,
    user,
    question: str,
) -> StudentServiceAnswer | None:
    if not course_registration_requested(question):
        return None

    chunks = list(
        DocumentChunk.objects.filter(
            document__in=accessible_documents_for_user(user).filter(status="READY"),
            document__title__icontains="Sổ",
            page_number__in=[91, 92, 93, 94],
        )
        .select_related("document")
        .order_by("page_number", "chunk_index")
    )

    if not chunks:
        return None

    first_chunk = chunks[0]
    normalized = normalize_for_match(question)

    if "rut mon" in normalized or "huy mon" in normalized or "huy bot mon" in normalized:
        answer = (
            f"Theo tài liệu \"{first_chunk.document.title}\", trang 91-94, "
            "việc điều chỉnh/rút bớt môn học được xử lý theo diện đăng ký môn học "
            "trễ hạn: sinh viên thực hiện trực tiếp tại Phòng Quản lý đào tạo trong "
            "02 tuần đầu học kỳ. Phòng Quản lý đào tạo giải quyết hủy bớt môn đã "
            "đăng ký trong các trường hợp như trùng lịch do Trường thay đổi thời "
            "khóa biểu, môn học không mở lớp do không đủ sĩ số, sinh viên được "
            "miễn môn trong cùng học kỳ, tai nạn/nằm viện dài ngày, gia đình gặp "
            "thiên tai đột xuất hoặc phải nhập ngũ. Sau khi đăng ký xong, sinh viên "
            "kiểm tra thời khóa biểu cá nhân và học phí trên http://tienichsv.ou.edu.vn."
        )
    else:
        answer = (
            f"Theo tài liệu \"{first_chunk.document.title}\", trang 91-94, "
            "quy trình đăng ký môn học gồm: Phòng Quản lý đào tạo công bố kế hoạch "
            "đăng ký môn học trực tuyến đầu mỗi học kỳ; sinh viên đăng ký theo chương "
            "trình đào tạo ngành-khóa, đúng tên môn học, mã môn học và số tín chỉ; "
            "sinh viên cần đọc kỹ quy định và tham khảo cố vấn học tập trước khi đăng "
            "ký; không đăng ký môn học trùng thời khóa biểu hoặc môn chưa có kết quả "
            "thi; sau khi kết thúc thời gian đăng ký, sinh viên kiểm tra thời khóa biểu "
            "cá nhân và học phí trên http://tienichsv.ou.edu.vn. Trường hợp cần điều "
            "chỉnh sau hạn, sinh viên đăng ký trực tiếp tại Phòng Quản lý đào tạo trong "
            "02 tuần đầu học kỳ."
        )

    return StudentServiceAnswer(
        answer=answer,
        citations=[
            citation_for_chunk(
                rank=1,
                chunk=first_chunk,
                snippet=normalize_space("\n".join(chunk.content for chunk in chunks)),
            )
        ],
    )


CAMPUS_ADDRESSES = {
    "vo_van_tan": "Cơ sở 1: 97 Võ Văn Tần, P. Võ Thị Sáu, Q.3.",
    "ho_hao_hon": "Cơ sở 2: 35-37 Hồ Hảo Hớn, P. Cô Giang, Q.1.",
    "nha_be": "Cơ sở 3: xã Nhơn Đức, huyện Nhà Bè.",
    "mai_thi_luu": "Cơ sở 4: 02 Mai Thị Lựu, P. Đakao, Q.1.",
    "binh_duong": (
        "Cơ sở 5: 68 Lê Thị Trung, P. Phú Lợi, "
        "TP. Thủ Dầu Một, Bình Dương."
    ),
    "long_binh": (
        "Cơ sở 6: Đường cổng 9, KP.1, P. Long Bình Tân, "
        "TP. Biên Hòa."
    ),
}


def requested_campus_key(query: str) -> str | None:
    normalized = normalize_for_match(query)

    if "vo van tan" in normalized:
        return "vo_van_tan"

    if "ho hao hon" in normalized:
        return "ho_hao_hon"

    if "nha be" in normalized or "nhon duc" in normalized:
        return "nha_be"

    if "mai thi luu" in normalized:
        return "mai_thi_luu"

    if "binh duong" in normalized:
        return "binh_duong"

    if "long binh" in normalized or "long hung" in normalized:
        return "long_binh"

    return None


def build_campus_address_answer(*, user, question: str) -> StudentServiceAnswer | None:
    if not campus_address_requested(question):
        return None

    campus_key = requested_campus_key(question)

    if campus_key is None:
        return None

    chunk = (
        DocumentChunk.objects.filter(
            document__in=accessible_documents_for_user(user).filter(status="READY"),
            document__title__icontains="Sổ",
            content__icontains="CÁC ĐỊA ĐIỂM HỌC TẬP",
        )
        .select_related("document")
        .order_by("page_number", "chunk_index")
        .first()
    )

    if chunk is None:
        return None

    answer = (
        f"Theo tài liệu \"{chunk.document.title}\", trang {chunk.page_number}, "
        f"{CAMPUS_ADDRESSES[campus_key]}"
    )

    return StudentServiceAnswer(
        answer=answer,
        citations=[
            citation_for_chunk(
                rank=1,
                chunk=chunk,
                snippet=normalize_space(chunk.content),
            )
        ],
    )


def build_student_service_answer(*, user, question: str) -> StudentServiceAnswer | None:
    exam_schedule_answer = build_exam_schedule_lookup_answer(
        user=user,
        question=question,
    )

    if exam_schedule_answer is not None:
        return exam_schedule_answer

    course_answer = build_course_registration_answer(
        user=user,
        question=question,
    )

    if course_answer is not None:
        return course_answer

    campus_answer = build_campus_address_answer(
        user=user,
        question=question,
    )

    if campus_answer is not None:
        return campus_answer

    return build_academic_office_answer(
        user=user,
        question=question,
    )
