import re
from dataclasses import dataclass

from django.db.models import Q

from documents.models import DocumentChunk
from documents.permissions import accessible_documents_for_user
from documents.services.vietnamese_corrector import normalize_for_match


@dataclass
class StudentServiceAnswer:
    answer: str
    citations: list[dict]
    merge_retrieval_citations: bool = False


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
            "xac nhan sinh vien",
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


def campus_count_requested(query: str) -> bool:
    normalized = normalize_for_match(query)

    return (
        "co so" in normalized
        and any(term in normalized for term in ("may", "bao nhieu"))
    )


def defense_location_requested(query: str) -> bool:
    normalized = normalize_for_match(query)
    defense_terms = (
        "gdqp",
        "gdqpan",
        "giao duc quoc phong",
        "quoc phong an ninh",
    )
    location_terms = (
        "o dau",
        "tai dau",
        "co so nao",
        "dia diem nao",
    )

    return (
        any(term in normalized for term in defense_terms)
        and any(term in normalized for term in location_terms)
    )


def course_registration_requested(query: str) -> bool:
    normalized = normalize_for_match(query)

    return any(
        term in normalized
        for term in (
            "dang ky mon hoc",
            "dang ky hoc phan",
            "rut mon",
            "rut bot mon",
            "huy mon",
            "huy bot mon",
            "dang ky tre han",
        )
    )


def study_schedule_lookup_requested(query: str) -> bool:
    normalized = normalize_for_match(query)

    return (
        any(term in normalized for term in ("lich hoc", "thoi khoa bieu"))
        and any(term in normalized for term in ("xem", "tra cuu", "o dau", "tim"))
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


def grade_review_requested(query: str) -> bool:
    normalized = normalize_for_match(query)

    return any(
        term in normalized
        for term in (
            "phuc khao",
            "phuc tra",
            "khieu nai diem",
            "xem lai diem",
            "xem lai ket qua",
            "thac mac diem",
        )
    )


def exam_adjustment_requested(query: str) -> bool:
    normalized = normalize_for_match(query)

    return any(
        term in normalized
        for term in (
            "trung lich thi",
            "dieu chinh lich thi",
            "doi lich thi",
            "xin doi ca thi",
        )
    )


def refund_requested(query: str) -> bool:
    normalized = normalize_for_match(query)

    return any(
        term in normalized
        for term in ("hoan hoc phi", "hoan tra hoc phi", "rut hoc phi")
    )


def requested_online_system(query: str) -> str | None:
    normalized = normalize_for_match(query)

    if "sis" in normalized or "he thong dich vu sinh vien" in normalized:
        return "sis"

    if any(term in normalized for term in ("lms", "learn ou", "hoc truc tuyen")):
        return "lms"

    if any(
        term in normalized
        for term in ("email sinh vien", "email truong", "thu dien tu sinh vien")
    ):
        return "email"

    return None


def library_requested(query: str) -> bool:
    return "thu vien" in normalize_for_match(query)


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


def build_study_schedule_lookup_answer(
    *,
    user,
    question: str,
) -> StudentServiceAnswer | None:
    if not study_schedule_lookup_requested(question):
        return None

    chunk = (
        DocumentChunk.objects.filter(
            document__in=accessible_documents_for_user(user).filter(status="READY"),
            document__title__icontains="Sổ",
            content__icontains="Hệ thống dịch vụ sinh viên tại địa chỉ",
        )
        .filter(content__icontains="lịch học, lịch thi")
        .select_related("document")
        .order_by("page_number", "chunk_index")
        .first()
    )

    if chunk is None:
        return None

    answer = (
        f"Theo tài liệu \"{chunk.document.title}\", trang {chunk.page_number}, "
        "sinh viên xem lịch học và thời khóa biểu tại Hệ thống dịch vụ sinh "
        "viên http://sis.ou.edu.vn bằng mã số sinh viên và mật khẩu."
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
        merge_retrieval_citations=False,
    )


def build_grade_review_answer(
    *,
    user,
    question: str,
) -> StudentServiceAnswer | None:
    if not grade_review_requested(question):
        return None

    documents = accessible_documents_for_user(user).filter(status="READY")
    anchor = (
        DocumentChunk.objects.filter(
            document__in=documents,
            document__title__icontains="Sổ",
        )
        .filter(
            Q(content__icontains="Phúc tra và khiếu nại điểm")
            | Q(content__icontains="Phúc tra")
            | Q(content__icontains="khiếu nại điểm")
        )
        .select_related("document")
        .order_by("page_number", "chunk_index")
        .first()
    )

    if anchor is None:
        anchor = (
            DocumentChunk.objects.filter(
                document__in=documents,
                document__title__icontains="Quy chế đào tạo",
            )
            .filter(
                Q(content__icontains="Phúc tra")
                | Q(content__icontains="khieu nai diem")
                | Q(content__icontains="xem lai ket qua")
            )
            .select_related("document")
            .order_by("page_number", "chunk_index")
            .first()
        )

    if anchor is None:
        return None

    chunks = list(
        DocumentChunk.objects.filter(
            document_id=anchor.document_id,
            chunk_index__gte=anchor.chunk_index,
            chunk_index__lte=anchor.chunk_index + 1,
        )
        .select_related("document")
        .order_by("chunk_index")
    )
    page_label = str(anchor.page_number)

    if chunks and chunks[-1].page_number != anchor.page_number:
        page_label = f"{anchor.page_number}-{chunks[-1].page_number}"

    answer = (
        f"Theo tài liệu \"{anchor.document.title}\", trang {page_label}, "
        "đối với điểm quá trình, sinh viên khiếu nại trực tiếp với giảng viên "
        "khi công bố điểm trên lớp hoặc trên LMS. Nếu phát hiện điểm đã công bố "
        "khác với điểm được nhập/lưu trong hệ thống quản lý học vụ, sinh viên "
        "thông báo và yêu cầu Phòng Khảo thí kiểm tra lại cột điểm tương ứng. "
        "Đối với điểm đánh giá cuối kỳ, sinh viên làm đơn đề nghị xem lại kết "
        "quả chấm thi kết thúc môn học và nộp tại Phòng Thanh tra - Pháp chế."
    )

    return StudentServiceAnswer(
        answer=answer,
        citations=[
            citation_for_chunk(
                rank=1,
                chunk=anchor,
                snippet=normalize_space(
                    "\n".join(chunk.content for chunk in chunks)
                ),
            )
        ],
    )


def build_exam_adjustment_answer(
    *,
    user,
    question: str,
) -> StudentServiceAnswer | None:
    if not exam_adjustment_requested(question):
        return None

    documents = accessible_documents_for_user(user).filter(status="READY")
    condition_chunk = (
        DocumentChunk.objects.filter(
            document__in=documents,
            document__title__icontains="Sổ",
            content__icontains="Điều kiện được xét điều chỉnh lịch thi",
        )
        .select_related("document")
        .order_by("page_number", "chunk_index")
        .first()
    )
    procedure_chunk = (
        DocumentChunk.objects.filter(
            document__in=documents,
            document__title__icontains="Sổ",
            content__icontains="Trình tự, thủ tục xin điều chỉnh lịch thi",
        )
        .select_related("document")
        .order_by("page_number", "chunk_index")
        .first()
    )

    if condition_chunk is None or procedure_chunk is None:
        return None

    answer = (
        f"Theo tài liệu \"{condition_chunk.document.title}\", trang "
        f"{condition_chunk.page_number}-{procedure_chunk.page_number}, sinh viên "
        "bị trùng lịch thi thuộc diện được đề nghị điều chỉnh. Hồ sơ gồm Phiếu "
        "đề nghị điều chỉnh lịch thi và giấy tờ minh chứng liên quan; nộp tại "
        "Bộ phận tiếp sinh viên thuộc Phòng Quản lý đào tạo. Trường phản hồi qua "
        "email sinh viên trong tối đa 3 ngày làm việc. Với trường hợp trùng lịch "
        "thi, hạn nộp là một tuần kể từ ngày thông báo lịch thi."
    )

    return StudentServiceAnswer(
        answer=answer,
        citations=[
            citation_for_chunk(
                rank=1,
                chunk=condition_chunk,
                snippet=normalize_space(condition_chunk.content),
            ),
            citation_for_chunk(
                rank=2,
                chunk=procedure_chunk,
                snippet=normalize_space(procedure_chunk.content),
                score=0.98,
            ),
        ],
        merge_retrieval_citations=False,
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

    if any(
        term in normalized
        for term in ("rut mon", "rut bot mon", "huy mon", "huy bot mon")
    ):
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


def build_refund_answer(*, user, question: str) -> StudentServiceAnswer | None:
    if not refund_requested(question):
        return None

    documents = accessible_documents_for_user(user).filter(status="READY")
    eligibility_chunk = (
        DocumentChunk.objects.filter(
            document__in=documents,
            content__icontains="hoàn học phí trước 2/3 thời gian học",
        )
        .select_related("document")
        .order_by("document_id", "page_number", "chunk_index")
        .first()
    )
    procedure_chunk = (
        DocumentChunk.objects.filter(
            document__in=documents,
            document__title__icontains="Sổ",
            content__icontains="Thủ tục hoàn học phí như sau",
        )
        .select_related("document")
        .order_by("page_number", "chunk_index")
        .first()
    )

    if eligibility_chunk is None or procedure_chunk is None:
        return None

    answer = (
        f"Theo tài liệu \"{eligibility_chunk.document.title}\", trang "
        f"{eligibility_chunk.page_number}, trường hợp sinh viên được Trường cho "
        "phép miễn giảm môn học phải làm thủ tục hoàn học phí trước 2/3 thời "
        "gian học của môn. Sinh viên chính quy liên hệ Phòng Quản lý đào tạo "
        "(P.005); khi đến Phòng Tài chính - Kế toán cần có Phiếu hoàn học phí, "
        "thẻ sinh viên hoặc CMND, bản chính và một bản photo biên lai có môn "
        "học được hoàn."
    )

    return StudentServiceAnswer(
        answer=answer,
        citations=[
            citation_for_chunk(
                rank=1,
                chunk=eligibility_chunk,
                snippet=normalize_space(eligibility_chunk.content),
            ),
            citation_for_chunk(
                rank=2,
                chunk=procedure_chunk,
                snippet=normalize_space(procedure_chunk.content),
                score=0.98,
            ),
        ],
        merge_retrieval_citations=False,
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


def build_campus_count_answer(*, user, question: str) -> StudentServiceAnswer | None:
    if not campus_count_requested(question):
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

    campuses = "; ".join(CAMPUS_ADDRESSES.values())
    answer = (
        f"Theo tài liệu \"{chunk.document.title}\", trang {chunk.page_number}, "
        f"Trường có 6 cơ sở học tập: {campuses}"
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
        merge_retrieval_citations=False,
    )


def build_defense_location_answer(
    *,
    user,
    question: str,
) -> StudentServiceAnswer | None:
    if not defense_location_requested(question):
        return None

    chunk = (
        DocumentChunk.objects.filter(
            document__in=accessible_documents_for_user(user).filter(status="READY"),
        )
        .filter(
            Q(document__title__icontains="GDQP")
            & Q(document__title__icontains="Long Hưng")
        )
        .select_related("document")
        .order_by("page_number", "chunk_index")
        .first()
    )

    if chunk is None:
        return None

    answer = (
        f"Theo tài liệu \"{chunk.document.title}\", trang {chunk.page_number}, "
        "sinh viên học Giáo dục Quốc phòng - An ninh tại cơ sở Long Hưng."
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
        merge_retrieval_citations=False,
    )


def build_online_system_answer(
    *,
    user,
    question: str,
) -> StudentServiceAnswer | None:
    system = requested_online_system(question)

    if system is None:
        return None

    chunks = DocumentChunk.objects.filter(
        document__in=accessible_documents_for_user(user).filter(status="READY"),
        document__title__icontains="Sổ",
    ).select_related("document")

    if system == "sis":
        chunk = chunks.filter(
            content__icontains="Hệ thống dịch vụ sinh viên tại địa chỉ",
        ).first()
        detail = (
            "SIS là Hệ thống dịch vụ sinh viên tại http://sis.ou.edu.vn, "
            "dùng để xem lịch học, lịch thi, điểm thi, tình trạng khóa mã số "
            "sinh viên và các dịch vụ online; đăng nhập bằng mã số sinh viên "
            "và mật khẩu."
        )
    elif system == "lms":
        chunk = chunks.filter(
            content__icontains="http://learn.ou.edu.vn",
        ).first()
        detail = (
            "sinh viên chính quy truy cập cổng học tập trực tuyến tại "
            "http://learn.ou.edu.vn để vào lớp, lấy tài liệu, xem thông báo "
            "của giảng viên và tham gia diễn đàn học tập."
        )
    else:
        chunk = chunks.filter(
            content__icontains="Điều 4. Tên miền của hộp thư điện tử",
        ).first()
        detail = (
            "sinh viên chính quy được cấp hộp thư có tên miền ou.edu.vn khi "
            "nhập học và phải dùng hộp thư này để trao đổi việc học tập, rèn "
            "luyện với Trường. Khi mất quyền truy cập, sinh viên thông báo "
            "Trung tâm Quản lý hệ thống thông tin để được hỗ trợ."
        )

    if chunk is None:
        return None

    answer = (
        f"Theo tài liệu \"{chunk.document.title}\", trang {chunk.page_number}, "
        f"{detail}"
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
        merge_retrieval_citations=False,
    )


def build_library_answer(*, user, question: str) -> StudentServiceAnswer | None:
    if not library_requested(question):
        return None

    chunk = (
        DocumentChunk.objects.filter(
            document__in=accessible_documents_for_user(user).filter(status="READY"),
            document__title__icontains="Sổ",
            content__icontains="6.8. Thư viện",
        )
        .select_related("document")
        .order_by("page_number", "chunk_index")
        .first()
    )

    if chunk is None:
        return None

    answer = (
        f"Theo tài liệu \"{chunk.document.title}\", trang {chunk.page_number}, "
        "Thư viện chính ở Phòng 504, lầu 5, 97 Võ Văn Tần, Quận 3. Trường "
        "cũng có phòng đọc tại 02 Mai Thị Lựu, Nhơn Đức, Bình Dương, Ninh "
        "Hòa và Long Bình. Website: https://thuvien.ou.edu.vn; điện thoại: "
        "(028) 39300209; email: thuviendhm@ou.edu.vn."
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
        merge_retrieval_citations=False,
    )


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
    defense_location_answer = build_defense_location_answer(
        user=user,
        question=question,
    )

    if defense_location_answer is not None:
        return defense_location_answer

    campus_count_answer = build_campus_count_answer(
        user=user,
        question=question,
    )

    if campus_count_answer is not None:
        return campus_count_answer

    online_system_answer = build_online_system_answer(
        user=user,
        question=question,
    )

    if online_system_answer is not None:
        return online_system_answer

    library_answer = build_library_answer(
        user=user,
        question=question,
    )

    if library_answer is not None:
        return library_answer

    refund_answer = build_refund_answer(
        user=user,
        question=question,
    )

    if refund_answer is not None:
        return refund_answer

    exam_adjustment_answer = build_exam_adjustment_answer(
        user=user,
        question=question,
    )

    if exam_adjustment_answer is not None:
        return exam_adjustment_answer

    grade_review_answer = build_grade_review_answer(
        user=user,
        question=question,
    )

    if grade_review_answer is not None:
        return grade_review_answer

    exam_schedule_answer = build_exam_schedule_lookup_answer(
        user=user,
        question=question,
    )

    if exam_schedule_answer is not None:
        return exam_schedule_answer

    study_schedule_answer = build_study_schedule_lookup_answer(
        user=user,
        question=question,
    )

    if study_schedule_answer is not None:
        return study_schedule_answer

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
