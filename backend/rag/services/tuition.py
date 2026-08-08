import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from documents.services.vietnamese_corrector import (
    normalize_for_match,
    normalize_for_ocr_phrase_match,
)


MONEY_PATTERN = re.compile(
    r"\d{1,3}(?:\.\d{3})+"
    r"\s*(?:đ|d|đồng)"
    r"\s*/\s*"
    r"(?:tín\s*chỉ|tin\s*chi|sinh\s*viên|sinh\s+vien)",
    flags=re.IGNORECASE,
)

NOISE_PHRASES = (
    "chuong trinh chat luong cao",
    "chat luong cao",
    "chuong trinh tien tien",
    "tien tien",
    "chuong trinh chuan",
    "dai hoc chinh quy",
    "lien thong dai hoc chinh quy",
    "khoa dao tao dac biet",
    "tai khoa dao tao dac biet",
    "nam hoc",
    "hoc phi",
    "muc thu",
    "bao nhieu",
    "tin chi",
    "sinh vien",
    "muc",
    "co",
    "nganh",
    "cua",
    "cho",
    "la",
    "ve",
    "hp",
    "dhcq",
    "clc",
)

STOPWORD_TOKENS = {
    "va",
    "cac",
    "mon",
    "khong",
    "chuyen",
    "nganh",
    "co",
}


@dataclass(frozen=True)
class LineMajorMatch:
    score: float
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class TuitionMatch:
    amount: str
    display_major: str
    score: float
    snippet: str


def normalize_money(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"\s*(?:đ|d|đồng)\s*/\s*", "đ/", value, flags=re.IGNORECASE)
    value = re.sub(r"tin\s*chi", "tín chỉ", value, flags=re.IGNORECASE)
    value = re.sub(r"sinh\s+vien", "sinh viên", value, flags=re.IGNORECASE)

    return value


def is_tuition_query(question: str) -> bool:
    normalized = normalize_for_match(question)

    return "hoc phi" in normalized or "muc thu" in normalized or "hp" in normalized


def extract_requested_major(question: str) -> str:
    if not is_tuition_query(question):
        return ""

    normalized = normalize_for_match(question)
    normalized = re.sub(r"\bcntt\b", "cong nghe thong tin", normalized)
    normalized = re.sub(r"\bhp\b", "hoc phi", normalized)

    # Remove cohort/year markers before removing generic filler words.
    normalized = re.sub(
        r"\b(?:khoa|k)\s*(?:20\d{2}|\d{2})\b",
        " ",
        normalized,
    )
    normalized = re.sub(r"\b20\d{2}(?:\s+20\d{2})?\b", " ", normalized)

    for phrase in sorted(NOISE_PHRASES, key=len, reverse=True):
        normalized = re.sub(rf"\b{re.escape(phrase)}\b", " ", normalized)

    # "khoa" can mean faculty in casual questions, but keep "khoa hoc ..."
    # for majors such as "Khoa học máy tính".
    normalized = re.sub(r"\bkhoa\s+(?!hoc\b)", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    return normalized


def major_search_terms(major: str) -> list[str]:
    terms = []

    for token in major.split():
        if token in STOPWORD_TOKENS:
            continue

        if len(token) < 2:
            continue

        terms.append(token)

    return terms[:5]


def token_matches_with_spans(line: str):
    return list(re.finditer(r"[A-Za-zÀ-ỹĐđ0-9']+", line))


def minimum_major_match_score(token_count: int) -> float:
    if token_count <= 1:
        return 0.82

    if token_count == 2:
        return 0.78

    return 0.70


def match_major_on_line(line: str, requested_major: str) -> LineMajorMatch | None:
    target_tokens = requested_major.split()

    if not target_tokens:
        return None

    token_matches = token_matches_with_spans(line)

    if not token_matches:
        return None

    source_tokens = [
        normalize_for_ocr_phrase_match(match.group(0))
        for match in token_matches
    ]
    target = " ".join(target_tokens)
    target_width = len(target_tokens)
    best_match = None

    for start in range(len(source_tokens)):
        if not source_tokens[start]:
            continue

        first_score = SequenceMatcher(
            None,
            source_tokens[start],
            target_tokens[0],
        ).ratio()

        if source_tokens[start][0] != target_tokens[0][0] and first_score < 0.65:
            continue

        max_width = 1 if target_width == 1 else target_width + 2
        min_width = 1 if target_width == 1 else max(1, target_width - 1)

        for width in range(
            min_width,
            min(len(source_tokens) - start, max_width) + 1,
        ):
            window_tokens = source_tokens[start : start + width]

            if not all(window_tokens):
                continue

            last_score = SequenceMatcher(
                None,
                window_tokens[-1],
                target_tokens[-1],
            ).ratio()

            if last_score < 0.55:
                continue

            source = " ".join(window_tokens)
            score = SequenceMatcher(None, source, target).ratio()

            if score < minimum_major_match_score(target_width):
                continue

            if best_match is None or score > best_match.score:
                start_offset = token_matches[start].start()
                end_offset = token_matches[start + width - 1].end()
                best_match = LineMajorMatch(
                    score=score,
                    start=start_offset,
                    end=end_offset,
                    text=line[start_offset:end_offset].strip(" ,.;:-"),
                )

    return best_match


def starts_new_tuition_group(line: str) -> bool:
    normalized = normalize_for_match(line)

    return normalized.startswith(
        (
            "nganh ",
            "cac mon ",
            "giao duc ",
        )
    )


def find_amount_after(line: str, offset: int) -> str | None:
    match = MONEY_PATTERN.search(line[offset:])

    if match:
        return normalize_money(match.group(0))

    return None


def previous_line_allows_continuation(lines: list[str], index: int) -> bool:
    if index < 2:
        return False

    if not MONEY_PATTERN.search(lines[index - 1]):
        return False

    return lines[index - 2].rstrip().endswith(",")


def starts_with_ocr_tail_fragment(line: str) -> bool:
    return bool(re.match(r"^[A-Za-zÀ-ỹĐđ]{1,3},\s+", line))


def find_previous_amount(lines: list[str], index: int) -> str | None:
    if MONEY_PATTERN.search(lines[index]):
        return None

    normalized_line = normalize_for_match(lines[index])

    if normalized_line.startswith(("nganh ", "cac mon ", "giao duc ")):
        return None

    if len(normalized_line.split()) > 14:
        return None

    if not (
        previous_line_allows_continuation(lines, index)
        or starts_with_ocr_tail_fragment(lines[index])
    ):
        return None

    match = MONEY_PATTERN.search(lines[index - 1])

    if match:
        return normalize_money(match.group(0))

    return None


def find_following_amount(lines: list[str], index: int) -> str | None:
    for next_line in lines[index + 1 : index + 7]:
        if starts_new_tuition_group(next_line):
            return None

        match = MONEY_PATTERN.search(next_line)

        if match:
            return normalize_money(match.group(0))

    return None


def build_snippet(lines: list[str], index: int) -> str:
    start = max(0, index - 2)
    end = min(len(lines), index + 7)

    while start < index and len(lines[start]) > 350:
        start += 1

    return " ".join(" ".join(lines[start:end]).split())[:500]


def clean_display_major(value: str, fallback: str) -> str:
    value = re.sub(r"^(ngành|nganh|các môn|cac mon)\s+", "", value, flags=re.I)
    value = " ".join(value.strip(" ,.;:-").split())

    if value:
        return value

    return fallback


def find_tuition_match(text: str, requested_major: str) -> TuitionMatch | None:
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]
    best_match = None

    for index, line in enumerate(lines):
        major_match = match_major_on_line(line, requested_major)

        if major_match is None:
            continue

        if (
            index + 1 < len(lines)
            and match_major_on_line(lines[index + 1], requested_major) is not None
        ):
            continue

        amount = (
            find_amount_after(line, major_match.end)
            or find_previous_amount(lines, index)
            or find_following_amount(lines, index)
        )

        if not amount:
            continue

        display_major = clean_display_major(
            major_match.text,
            requested_major,
        )
        candidate = TuitionMatch(
            amount=amount,
            display_major=display_major,
            score=major_match.score,
            snippet=build_snippet(lines, index),
        )

        if best_match is None or candidate.score > best_match.score:
            best_match = candidate

    return best_match
