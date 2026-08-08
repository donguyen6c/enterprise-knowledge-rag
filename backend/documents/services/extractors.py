import re
import pymupdf

from dataclasses import dataclass
from pathlib import Path
from docx import Document as DocxDocument
from pypdf import PdfReader
from documents.services.ocr import ocr_pdf


class UnsupportedDocumentTypeError(Exception):
    pass


class DocumentExtractionError(Exception):
    pass


@dataclass
class ExtractedPage:
    page_number: int | None
    content: str
    metadata: dict | None = None

VIETNAMESE_COMMON_WORDS = {
    "học",
    "phí",
    "sinh",
    "viên",
    "đại",
    "trường",
    "thành",
    "phố",
    "đào",
    "tạo",
    "ngành",
    "chính",
    "quy",
    "năm",
    "thông",
    "báo",
}


def calculate_text_quality(text: str) -> float:
    """
    Trả về điểm chất lượng từ 0 đến 1.

    Đây là heuristic để phát hiện text bị lỗi font như:
    h9c, C6ng, DVC, VIVI', ...
    """
    if not text or len(text.strip()) < 30:
        return 0.0

    words = re.findall(
        r"[A-Za-zÀ-ỹĐđ0-9']+",
        text.lower(),
    )

    if not words:
        return 0.0

    alphabetic_words = [
        word for word in words
        if any(character.isalpha() for character in word)
    ]

    if not alphabetic_words:
        return 0.0

    suspicious_words = 0

    for word in alphabetic_words:
        # Số chen vào giữa chữ thường là dấu hiệu lỗi font:
        # h9c, C6ng, kh6a, d4i...
        if re.search(r"[a-zà-ỹđ]\d+[a-zà-ỹđ]", word):
            suspicious_words += 1
            continue

        # Nhiều ký tự lạ trong một từ.
        if word.count("'") >= 2:
            suspicious_words += 1

    suspicious_ratio = suspicious_words / len(alphabetic_words)

    common_word_hits = sum(
        1
        for word in alphabetic_words
        if word in VIETNAMESE_COMMON_WORDS
    )

    common_word_score = min(
        common_word_hits / 10,
        1.0,
    )

    quality = (
        (1.0 - suspicious_ratio) * 0.8
        + common_word_score * 0.2
    )

    return max(0.0, min(quality, 1.0))

def extract_pdf_with_pymupdf(
    file_path: Path,
) -> list[ExtractedPage]:
    try:
        pdf_document = pymupdf.open(file_path)
    except Exception as exc:
        raise DocumentExtractionError(
            f"PyMuPDF không thể mở PDF: {exc}"
        ) from exc

    pages = []

    try:
        for index, page in enumerate(
            pdf_document,
            start=1,
        ):
            raw_text = page.get_text(
                "text",
                sort=True,
            )

            pages.append(
                ExtractedPage(
                    page_number=index,
                    content=normalize_text(raw_text),
                )
            )
    finally:
        pdf_document.close()

    return pages

def normalize_text(text: str) -> str:
    lines = []

    for line in text.splitlines():
        cleaned_line = " ".join(line.split())

        if cleaned_line:
            lines.append(cleaned_line)

    return "\n".join(lines).strip()


def join_page_text( pages: list[ExtractedPage],) -> str:
    return "\n".join( page.content for page in pages if page.content)

def extract_pdf_with_pypdf( file_path: Path,) -> list[ExtractedPage]:
    try:
        reader = PdfReader(str(file_path))
    except Exception as exc:
        raise DocumentExtractionError(f"pypdf không thể mở PDF: {exc}") from exc

    pages = []

    for index, page in enumerate(
        reader.pages,
        start=1,
    ):
        try:
            raw_text = page.extract_text() or ""
        except Exception as exc:
            raise DocumentExtractionError(
                f"Không thể đọc trang {index}: {exc}"
            ) from exc

        pages.append(
            ExtractedPage(
                page_number=index,
                content=normalize_text(raw_text),
            )
        )

    return pages

def has_broken_font_patterns(text: str) -> bool:
    suspicious_patterns = re.findall(r"[A-Za-zÀ-ỹĐđ]\d[A-Za-zÀ-ỹĐđ]", text,)

    word_count = max(1, len(text.split()))
    suspicious_ratio = len(suspicious_patterns) / word_count

    return suspicious_ratio >= 0.01

def extract_pdf(file_path: Path) -> list[ExtractedPage]:
    pypdf_pages = extract_pdf_with_pypdf(file_path)
    pypdf_text = join_page_text(pypdf_pages)

    requires_ocr = (
        not pypdf_text.strip()
        or has_broken_font_patterns(pypdf_text)
    )

    if not requires_ocr:
        return pypdf_pages

    return extract_pdf_with_paddle_ocr(file_path)

def extract_docx(file_path: Path) -> list[ExtractedPage]:
    try:
        docx_file = DocxDocument(str(file_path))
    except Exception as exc:
        raise DocumentExtractionError( f"Không thể mở DOCX: {exc}" ) from exc

    paragraphs = []

    for paragraph in docx_file.paragraphs:
        content = normalize_text(paragraph.text)

        if content:
            paragraphs.append(content)

    return [ ExtractedPage(page_number=None, content="\n".join(paragraphs),) ]


def extract_document(file_path: Path) -> list[ExtractedPage]:
    extension = file_path.suffix.lower()

    if extension == ".pdf":
        return extract_pdf(file_path)

    if extension == ".docx":
        return extract_docx(file_path)

    raise UnsupportedDocumentTypeError(f"Không hỗ trợ định dạng {extension}")

def extract_pdf_with_paddle_ocr( file_path: Path,) -> list[ExtractedPage]:
    from documents.services.vietnamese_corrector import normalize_vietnamese_ocr_text

    ocr_pages = ocr_pdf(file_path=file_path)

    return [
        ExtractedPage(
            page_number=page_number,
            content=normalize_text(
                normalize_vietnamese_ocr_text(text)
            ),
            metadata={
                "source": "paddle_ocr",
                "raw_ocr_text": text,
            },
        )
        for page_number, text in ocr_pages
    ]
