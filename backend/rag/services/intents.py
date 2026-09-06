from enum import StrEnum

from django.db.models import Q, QuerySet

from documents.models import Document
from documents.services.vietnamese_corrector import normalize_for_match


class QueryIntent(StrEnum):
    POLICY = "policy"
    PROCEDURE = "procedure"
    UTILITY = "utility"
    GENERAL = "general"


PROCEDURE_ALIASES = (
    "thu tuc",
    "quy trinh",
    "huong dan",
    "cac buoc",
    "cach",
    "nop don",
    "ho so",
    "bieu mau",
    "dang ky hoc phan",
    "dang ky mon hoc",
    "rut mon",
    "huy mon",
    "xin bang diem",
    "cap bang diem",
    "lam the sinh vien",
    "cap lai the sinh vien",
    "phuc khao",
    "phuc tra",
    "khieu nai diem",
)

POLICY_ALIASES = (
    "quy che",
    "quy dinh",
    "hoc vu",
    "thoi hoc",
    "buoc thoi hoc",
    "canh bao hoc tap",
    "canh cao hoc tap",
    "dieu kien tot nghiep",
    "xet tot nghiep",
    "tot nghiep",
    "mien giam hoc phi",
    "mien giam mon hoc",
    "mien hoc",
    "ky luat",
    "bao luu",
    "tam dung hoc",
    "nghi hoc tam thoi",
)

UTILITY_ALIASES = (
    "lich thi",
    "thoi gian bieu",
    "khung thoi gian",
    "gio hoc",
    "ca hoc",
    "ra vao lop",
    "dia chi",
    "co so",
    "so dien thoai",
    "hotline",
    "lien he",
    "phong dao tao",
    "phong quan ly dao tao",
    "cau lac bo",
    "clb",
    "thu vien",
    "phong doc",
)


TOPIC_GROUPS = (
    {
        "aliases": ("tot nghiep", "xet tot nghiep", "dieu kien tot nghiep"),
        "content_terms": (
            "tốt nghiệp",
            "xét tốt nghiệp",
            "điều kiện xét tốt nghiệp",
            "Sinh viên được Trường xét",
            "cong nhan tot nghiep",
        ),
    },
    {
        "aliases": ("canh bao hoc tap", "canh cao hoc tap", "hoc luc yeu"),
        "content_terms": (
            "cảnh báo học tập",
            "canh bao hoc tap",
            "buộc thôi học",
            "buoc thoi hoc",
        ),
    },
    {
        "aliases": ("thoi hoc", "buoc thoi hoc", "nghi hoc", "tam dung hoc"),
        "content_terms": (
            "thôi học",
            "buộc thôi học",
            "nghỉ học tạm thời",
            "tạm dừng học tập",
            "bao lưu kết quả",
        ),
    },
    {
        "aliases": ("mien giam hoc phi", "mien giam mon hoc", "mien hoc"),
        "content_terms": (
            "miễn giảm học phí",
            "miễn, giảm học phí",
            "miễn, giảm môn học",
            "miễn học",
            "chế độ chính sách",
        ),
    },
    {
        "aliases": ("dang ky hoc phan", "dang ky mon hoc", "rut mon", "huy mon"),
        "content_terms": (
            "đăng ký môn học",
            "đăng ký học tập",
            "điều chỉnh khối lượng học tập",
            "rút môn",
            "hủy môn",
        ),
    },
    {
        "aliases": ("bang diem", "xin bang diem", "cap bang diem"),
        "content_terms": (
            "bảng điểm",
            "cấp bảng điểm",
            "xác nhận kết quả học tập",
            "phòng quản lý đào tạo",
        ),
    },
    {
        "aliases": ("the sinh vien", "lam the", "cap lai the"),
        "content_terms": (
            "thẻ sinh viên",
            "cấp lại thẻ sinh viên",
            "mã số sinh viên",
            "phòng công tác sinh viên",
        ),
    },
    {
        "aliases": ("phuc khao", "phuc tra", "khieu nai diem"),
        "content_terms": (
            "phúc khảo",
            "phúc tra",
            "khiếu nại điểm",
            "xem lại kết quả",
        ),
    },
    {
        "aliases": ("lich thi", "lich kiem tra"),
        "content_terms": (
            "lịch thi",
            "kỳ thi",
            "thi kết thúc môn học",
            "điều chỉnh lịch thi",
        ),
    },
    {
        "aliases": ("dia chi", "co so", "vo van tan", "nha be", "long binh"),
        "content_terms": (
            "địa chỉ",
            "các địa điểm học tập",
            "Võ Văn Tần",
            "Nhà Bè",
            "Long Bình",
        ),
    },
    {
        "aliases": ("so dien thoai", "hotline", "lien he", "phong dao tao"),
        "content_terms": (
            "điện thoại",
            "hotline",
            "liên hệ",
            "Phòng Quản lý đào tạo",
        ),
    },
    {
        "aliases": ("cau lac bo", "clb", "doi nhom"),
        "content_terms": (
            "câu lạc bộ",
            "CLB",
            "đội nhóm",
            "Đoàn Thanh niên",
            "Hội Sinh viên",
        ),
    },
)


def contains_any(normalized_query: str, aliases: tuple[str, ...]) -> bool:
    return any(alias in normalized_query for alias in aliases)


def classify_query_intent(query: str) -> QueryIntent:
    normalized = normalize_for_match(query)

    if contains_any(normalized, PROCEDURE_ALIASES):
        return QueryIntent.PROCEDURE

    if contains_any(normalized, POLICY_ALIASES):
        return QueryIntent.POLICY

    if contains_any(normalized, UTILITY_ALIASES):
        return QueryIntent.UTILITY

    return QueryIntent.GENERAL


def field_contains(field_name: str, value: str) -> Q:
    return Q(**{f"{field_name}__icontains": value})


def any_field_contains(field_names: tuple[str, ...], values: tuple[str, ...]) -> Q:
    condition = None

    for field_name in field_names:
        for value in values:
            part = field_contains(field_name, value)
            condition = part if condition is None else condition | part

    return condition or Q()


def document_condition_for_intent(
    intent: QueryIntent,
    *,
    chunk_relation: bool = False,
) -> Q | None:
    if intent == QueryIntent.GENERAL:
        return None

    prefix = "document__" if chunk_relation else ""
    title = f"{prefix}title"
    category = f"{prefix}category__name"

    if intent == QueryIntent.POLICY:
        return any_field_contains(
            (title, category),
            (
                "Quy chế",
                "Quy định",
                "Công tác sinh viên",
                "Miễn",
                "Thi và đánh giá",
                "Đăng ký môn học",
                "Sổ Tay",
                "Sổ",
            ),
        )

    if intent == QueryIntent.PROCEDURE:
        return any_field_contains(
            (title, category),
            (
                "Sổ Tay",
                "Sổ",
                "Quy định đăng ký",
                "Đăng ký môn học",
                "Điều chỉnh lịch thi",
                "Thi và đánh giá",
                "Công tác sinh viên",
                "Quy chế đào tạo",
            ),
        )

    if intent == QueryIntent.UTILITY:
        return any_field_contains(
            (title, category),
            (
                "Sổ Tay",
                "Sổ",
                "Thi và đánh giá",
                "GDQP",
                "GDTC",
                "Long Hưng",
                "Dịch vụ trực tuyến",
                "Công tác sinh viên",
            ),
        )

    return None


def narrow_documents_for_intent(
    documents: QuerySet[Document],
    intent: QueryIntent,
) -> QuerySet[Document]:
    condition = document_condition_for_intent(intent)

    if condition is None:
        return documents

    narrowed = documents.filter(condition)

    return narrowed if narrowed.exists() else documents


def chunk_condition_for_intent(intent: QueryIntent) -> Q | None:
    if intent == QueryIntent.POLICY:
        return any_field_contains(
            ("content",),
            (
                "Điều ",
                "Quy định",
                "điều kiện",
                "không được",
                "được xem xét",
                "buộc thôi học",
                "cảnh báo học tập",
                "tốt nghiệp",
                "miễn",
                "giảm",
            ),
        )

    if intent == QueryIntent.PROCEDURE:
        return any_field_contains(
            ("content",),
            (
                "thủ tục",
                "trình tự",
                "hồ sơ",
                "nộp",
                "liên hệ",
                "phòng",
                "mẫu",
                "đăng ký",
                "đơn",
                "thời hạn",
            ),
        )

    if intent == QueryIntent.UTILITY:
        return any_field_contains(
            ("content",),
            (
                "địa chỉ",
                "điện thoại",
                "hotline",
                "liên hệ",
                "lịch",
                "khung thời gian",
                "giờ bắt đầu",
                "câu lạc bộ",
                "CLB",
                "fanpage",
            ),
        )

    return None


def topic_condition_for_query(query: str) -> Q | None:
    normalized = normalize_for_match(query)
    condition = None
    exam_schedule_lookup = (
        "lich thi" in normalized
        and any(
            phrase in normalized
            for phrase in ("xem", "o dau", "tra cuu", "tim")
        )
    )

    def add(part: Q) -> None:
        nonlocal condition
        condition = part if condition is None else condition | part

    if "tot nghiep" in normalized:
        add(
            (
                Q(content__icontains="Điều kiện xét tốt nghiệp")
                | Q(content__icontains="Sinh viên được Trường xét")
            )
            & (
                Q(content__icontains="công nhận tốt nghiệp")
                | Q(content__icontains="đủ các điều kiện")
            )
        )

    if "bang diem" in normalized:
        add(
            Q(content__icontains="bảng điểm")
            & (
                Q(content__icontains="Cấp chứng nhận")
                | Q(content__icontains="cấp bảng điểm")
                | Q(content__icontains="đề nghị Trường cấp")
                | Q(content__icontains="Phòng Quản lý đào tạo")
            )
        )

    if (
        "phuc khao" in normalized
        or "phuc tra" in normalized
        or "khieu nai diem" in normalized
    ):
        add(
            (
                Q(content__icontains="Phúc tra")
                | Q(content__icontains="khiếu nại điểm")
                | Q(content__icontains="xem lại kết quả")
            )
            & (
                Q(content__icontains="làm đơn")
                | Q(content__icontains="Phòng Thanh tra")
                | Q(content__icontains="Phòng Khảo thí")
                | Q(content__icontains="giảng viên")
            )
        )

    if exam_schedule_lookup:
        add(
            Q(content__icontains="lịch thi")
            & (
                Q(content__icontains="http")
                | Q(content__icontains="website")
                | Q(content__icontains="hệ thống")
                | Q(content__icontains="tra cứu")
            )
        )

    if "phong quan ly dao tao" in normalized or "phong dao tao" in normalized:
        add(
            Q(content__icontains="Phòng Quản lý đào tạo")
            & (
                Q(content__icontains="Điện thoại")
                | Q(content__icontains="Liên hệ")
                | Q(content__icontains="quanlydaotao")
            )
        )

    if "vo van tan" in normalized:
        add(
            Q(content__icontains="Võ Văn Tần")
            & (
                Q(content__icontains="địa chỉ")
                | Q(content__icontains="CÁC ĐỊA ĐIỂM HỌC TẬP")
                | Q(content__icontains="Cơ sở 1")
                | Q(content__icontains="Liên hệ")
            )
        )

    if "nha be" in normalized or "nhon duc" in normalized:
        add(
            (
                Q(content__icontains="Nhà Bè")
                | Q(content__icontains="Nhơn Đức")
            )
            & (
                Q(content__icontains="địa chỉ")
                | Q(content__icontains="CÁC ĐỊA ĐIỂM HỌC TẬP")
                | Q(content__icontains="khung thời gian")
            )
        )

    if "cau lac bo" in normalized or "clb" in normalized:
        add(
            Q(content__icontains="Câu lạc bộ - Đội")
            | Q(content__icontains="TÊN CLB")
            | Q(content__icontains="Câu lạc bộ")
        )

    for group in TOPIC_GROUPS:
        aliases = group["aliases"]

        if not any(alias in normalized for alias in aliases):
            continue

        alias_set = set(aliases)

        if "tot nghiep" in alias_set and "tot nghiep" in normalized:
            continue

        if "bang diem" in alias_set and "bang diem" in normalized:
            continue

        if (
            "phuc khao" in alias_set
            and (
                "phuc khao" in normalized
                or "phuc tra" in normalized
                or "khieu nai diem" in normalized
            )
        ):
            continue

        if "lich thi" in alias_set and exam_schedule_lookup:
            continue

        if (
            "so dien thoai" in alias_set
            and (
                "phong quan ly dao tao" in normalized
                or "phong dao tao" in normalized
            )
        ):
            continue

        if "dia chi" in alias_set and "vo van tan" in normalized:
            continue

        if (
            "cau lac bo" in alias_set
            and ("cau lac bo" in normalized or "clb" in normalized)
        ):
            continue

        part = any_field_contains(("content",), group["content_terms"])
        add(part)

    return condition


def intent_answer_label(intent: QueryIntent) -> str:
    if intent == QueryIntent.POLICY:
        return "tra cứu quy chế"

    if intent == QueryIntent.PROCEDURE:
        return "hướng dẫn nghiệp vụ"

    if intent == QueryIntent.UTILITY:
        return "tiện ích sinh viên"

    return "hỏi đáp"
