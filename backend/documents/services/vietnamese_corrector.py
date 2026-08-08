import re
import unicodedata
from difflib import SequenceMatcher


CRITICAL_VALUE_PATTERN = re.compile(
    r"""
    \b\d{1,3}(?:\.\d{3})+\b
    |\b\d{1,2}/\d{1,2}/\d{2,4}\b
    |\b\d{1,2}\s+tháng\s+\d{1,2}\s+năm\s+\d{4}\b
    |\b\d{4}-\d{4}\b
    |\b\d+(?:[,.]\d+)?%
    |\b\d+/\d{4}/[A-ZĐ]+(?:-[A-ZĐ]+)*\b
    |\b\d+/[A-ZĐ]+(?:-[A-ZĐ]+)*\b
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)

PROTECTED_CODE_PATTERN = re.compile(
    r"[A-ZĐ]{2,}(?:-[A-ZĐ]{2,})+",
)

MONEY_UNIT_PATTERN = re.compile(
    r"(?P<amount>\d{1,3}(?:\.\d{3})+)\s*(?:đ|d)\s*/\s*t[ií]n\s+chi\b",
    flags=re.IGNORECASE,
)

MONEY_PER_STUDENT_PATTERN = re.compile(
    r"(?P<amount>\d{1,3}(?:\.\d{3})+)\s*(?:đ|d)\s*/\s*sinh\s+vien\b",
    flags=re.IGNORECASE,
)

OCR_PHRASES = (
    "Công nghệ thông tin",
    "Hệ thống thông tin quản lý",
    "Khoa học máy tính",
    "Khoa học dữ liệu",
    "Trí tuệ nhân tạo",
    "Kỹ thuật phần mềm",
    "Tin học không chuyên",
    "Công nghệ kỹ thuật công trình xây dựng",
    "Quản lý xây dựng",
    "Công nghệ sinh học",
    "Công nghệ thực phẩm",
    "Công nghệ tài chính",
    "Ngoại ngữ không chuyên",
    "Ngôn ngữ Trung Quốc",
    "Ngôn ngữ Nhật",
    "Ngôn ngữ Hàn Quốc",
    "Ngôn ngữ Anh",
    "Hàn Quốc",
    "Quản lý",
    "xây dựng",
    "Thời gian áp dụng",
    "Năm học",
    "Trân trọng",
    "Nơi nhận",
    "Hiệu trưởng",
    "Phó hiệu trưởng",
    "triển khai",
    "đơn vị",
    "thuộc Trường",
)

ADDITIONAL_OCR_PHRASES = (
    "Bộ Giáo dục và Đào tạo",
    "Cộng hòa Xã hội Chủ nghĩa Việt Nam",
    "Trường Đại học Mở",
    "Thành phố Hồ Chí Minh",
    "Độc lập - Tự do - Hạnh phúc",
    "Thông báo",
    "mức thu học phí",
    "đại học chính quy",
    "liên thông đại học chính quy",
    "Căn cứ",
    "Nghị định",
    "Chính phủ",
    "quy định",
    "cơ chế thu",
    "quản lý học phí",
    "cơ sở giáo dục",
    "hệ thống giáo dục quốc dân",
    "chính sách miễn, giảm học phí",
    "hỗ trợ chi phí học tập",
    "giá dịch vụ",
    "lĩnh vực giáo dục, đào tạo",
    "Hội đồng trường",
    "Quyết định",
    "ban hành",
    "hệ đại học chính quy",
    "mức học phí",
    "theo tín chỉ",
    "Ngành",
    "Các môn",
    "Toán",
    "Giáo dục quốc phòng - An ninh",
    "Giáo dục thể chất",
    "Lý luận chính trị",
    "Xã hội học",
    "Công tác xã hội",
    "Đông Nam Á học",
    "Tâm lý học",
    "Kinh tế",
    "Quản lý công",
    "Tài chính - Ngân hàng",
    "Bảo hiểm",
    "Kế toán",
    "Kiểm toán",
    "Luật",
    "Luật kinh tế",
    "Quản trị kinh doanh",
    "Kinh doanh Quốc tế",
    "Quản trị",
    "Quản trị nhân lực",
    "nhân lực",
    "Quản lý chuỗi cung ứng",
    "Marketing",
    "Logistics và Quản lý chuỗi cung ứng",
    "Du lịch",
    "Các môn Ngoại ngữ không chuyên",
    "Tin học không chuyên",
    "Sinh viên đăng ký môn học",
)

OCR_PHRASES = tuple(dict.fromkeys(OCR_PHRASES + ADDITIONAL_OCR_PHRASES))
_PHRASE_CANDIDATES_BY_FIRST: dict[str, tuple] | None = None
OCR_DIGIT_TRANSLATION = str.maketrans(
    {
        "0": "o",
        "1": "l",
        "4": "l",
        "7": "y",
        "9": "o",
    }
)


def strip_vietnamese_marks(text: str) -> str:
    text = text.replace("Đ", "D").replace("đ", "d")

    return "".join(
        character
        for character in unicodedata.normalize("NFD", text)
        if unicodedata.category(character) != "Mn"
    )


def normalize_for_match(text: str) -> str:
    text = strip_vietnamese_marks(text).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)

    return " ".join(text.split())


def normalize_for_ocr_phrase_match(text: str) -> str:
    return normalize_for_match(text.translate(OCR_DIGIT_TRANSLATION))


def minimum_phrase_score(target_width: int) -> float:
    if target_width >= 5:
        return 0.76

    if target_width >= 3:
        return 0.80

    return 0.92


def phrase_candidates_by_first() -> dict[str, tuple]:
    global _PHRASE_CANDIDATES_BY_FIRST

    if _PHRASE_CANDIDATES_BY_FIRST is not None:
        return _PHRASE_CANDIDATES_BY_FIRST

    candidates: dict[str, list[tuple]] = {}

    for phrase in OCR_PHRASES:
        phrase_tokens = phrase.split()
        first = normalize_for_match(phrase_tokens[0])[:1]

        if not first:
            continue

        target_width = len(phrase_tokens)
        candidates.setdefault(first, []).append(
            (
                phrase,
                phrase_tokens,
                target_width,
                normalize_for_match(phrase),
                minimum_phrase_score(target_width),
            )
        )

    _PHRASE_CANDIDATES_BY_FIRST = {
        first: tuple(first_candidates)
        for first, first_candidates in candidates.items()
    }

    return _PHRASE_CANDIDATES_BY_FIRST


def critical_values(text: str) -> list[str]:
    return CRITICAL_VALUE_PATTERN.findall(text)


def is_protected_token(token: str) -> bool:
    if re.search(r"\d|%", token):
        return True

    return bool(PROTECTED_CODE_PATTERN.search(token))


def is_ocr_letter_digit_noise(token: str) -> bool:
    """
    Một số OCR lỗi biến chữ thành số trong từ ngắn như h9c, II4nh.

    Các token có dấu phân tách của số liệu/mã văn bản vẫn được bảo vệ.
    """
    core = token_core(token)

    if not re.search(r"[A-Za-zÀ-ỹĐđ]", core):
        return False

    if not re.search(r"\d", core):
        return False

    if re.search(r"[./\\:%-]", core):
        return False

    if len(core) > 8:
        return False

    return bool(re.fullmatch(r"[A-Za-zÀ-ỹĐđ0-9'`]+", core))


def is_short_numeric_ocr_noise(token: str) -> bool:
    core = token_core(token)

    if not core.isdigit():
        return False

    return len(core) <= 2


def token_core(token: str) -> str:
    match = re.match(r"^\W*(.*?)\W*$", token, flags=re.UNICODE)

    return match.group(1) if match else token


def merge_phrase_with_original_edges(
    original_tokens: list[str],
    phrase: str,
) -> str:
    leading = re.match(r"^\W*", original_tokens[0], flags=re.UNICODE).group(0)
    trailing = re.search(r"\W*$", original_tokens[-1], flags=re.UNICODE).group(0)

    return f"{leading}{phrase}{trailing}"


def has_compatible_edges(
    original_tokens: list[str],
    phrase_tokens: list[str],
) -> bool:
    original_first = normalize_for_match(token_core(original_tokens[0]))
    original_last = normalize_for_match(token_core(original_tokens[-1]))
    phrase_first = normalize_for_match(phrase_tokens[0])
    phrase_last = normalize_for_match(phrase_tokens[-1])

    if not original_first or not original_last:
        return False

    first_ok = (
        original_first[0] == phrase_first[0]
        or SequenceMatcher(None, original_first, phrase_first).ratio() >= 0.70
    )
    last_ok = (
        original_last[0] == phrase_last[0]
        or SequenceMatcher(None, original_last, phrase_last).ratio() >= 0.70
    )

    return first_ok and last_ok


def best_phrase_match(tokens: list[str], start: int):
    best_match = None
    first = normalize_for_match(token_core(tokens[start]))[:1]

    if not first:
        return None

    for (
        phrase,
        phrase_tokens,
        target_width,
        target,
        minimum_score,
    ) in phrase_candidates_by_first().get(first, ()):

        for width in range(
            max(1, target_width - 1),
            min(len(tokens) - start, target_width + 2) + 1,
        ):
            window = tokens[start : start + width]
            has_letter_digit_noise = any(
                is_ocr_letter_digit_noise(token)
                for token in window
            )

            if any(
                is_protected_token(token)
                and not is_ocr_letter_digit_noise(token)
                and not (
                    has_letter_digit_noise
                    and is_short_numeric_ocr_noise(token)
                )
                for token in window
            ):
                continue

            if not has_compatible_edges(window, phrase_tokens):
                continue

            source = normalize_for_ocr_phrase_match(" ".join(window))

            if not source or not target:
                continue

            score = SequenceMatcher(None, source, target).ratio()

            if score < minimum_score:
                continue

            if best_match is None or score > best_match[0]:
                best_match = (score, width, phrase)

    return best_match


def correct_ocr_line(line: str) -> str:
    tokens = line.split()

    if len(tokens) < 2:
        return line

    corrected_tokens = tokens[:]
    index = 0

    while index < len(corrected_tokens):
        match = best_phrase_match(corrected_tokens, index)

        if match is None:
            index += 1
            continue

        _, width, phrase = match
        original_window = corrected_tokens[index : index + width]

        corrected_tokens[index : index + width] = [
            merge_phrase_with_original_edges(
                original_tokens=original_window,
                phrase=phrase,
            )
        ]
        index += 1

    corrected_line = " ".join(corrected_tokens)

    if critical_values(corrected_line) != critical_values(line):
        return line

    return corrected_line


def normalize_money_units(text: str) -> str:
    text = MONEY_UNIT_PATTERN.sub(
        lambda match: f"{match.group('amount')}đ/tín chỉ",
        text,
    )
    text = MONEY_PER_STUDENT_PATTERN.sub(
        lambda match: f"{match.group('amount')}đ/sinh viên",
        text,
    )

    return text


def normalize_vietnamese_ocr_text(text: str) -> str:
    """
    Chuẩn hóa OCR tiếng Việt theo hướng bảo toàn dữ liệu quan trọng.

    Hàm này chỉ sửa các cụm từ học vụ có độ khớp cao và các đơn vị tiền
    phổ biến. Số tiền, ngày tháng, phần trăm và mã văn bản phải giữ nguyên.
    """
    if not text:
        return ""

    before_values = critical_values(text)

    corrected_lines = [
        correct_ocr_line(line)
        for line in text.splitlines()
    ]
    corrected_text = "\n".join(corrected_lines)
    corrected_text = normalize_money_units(corrected_text)

    if critical_values(corrected_text) != before_values:
        return text

    return corrected_text
