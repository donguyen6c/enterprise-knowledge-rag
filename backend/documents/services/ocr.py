from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory

import pymupdf
from paddleocr import PaddleOCR


class OcrError(Exception):
    pass

@lru_cache(maxsize=1)
def get_ocr_engine() -> PaddleOCR:
    return PaddleOCR(
        lang="vi",

        text_detection_model_name="PP-OCRv6_medium_det",

        text_recognition_model_name="PP-OCRv6_medium_rec",

        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,

        device="cpu",
    )


def render_pdf_page_to_image(
    page: pymupdf.Page,
    output_path: Path,
    dpi: int = 250,
) -> None:
    zoom = dpi / 72
    matrix = pymupdf.Matrix(zoom, zoom)

    pixmap = page.get_pixmap(
        matrix=matrix,
        alpha=False,
    )

    pixmap.save(str(output_path))


def extract_text_from_ocr_result(result) -> str:
    """
    Chuẩn hóa kết quả PaddleOCR thành text.

    PaddleOCR 3.x có thể thay đổi cấu trúc result tùy pipeline,
    nên hàm này hỗ trợ một số dạng phổ biến.
    """
    lines: list[str] = []

    if result is None:
        return ""

    items = result if isinstance(result, list) else [result]

    for item in items:
        if hasattr(item, "json"):
            data = item.json
        elif isinstance(item, dict):
            data = item
        else:
            data = None

        if isinstance(data, dict):
            result_data = data.get("res", data)

            texts = (
                result_data.get("rec_texts")
                or result_data.get("texts")
                or []
            )

            lines.extend(
                str(text).strip()
                for text in texts
                if str(text).strip()
            )

    return "\n".join(lines).strip()


def ocr_pdf(
    file_path: Path,
    dpi: int = 300,
    page_numbers: set[int] | None = None,
) -> list[tuple[int, str]]:
    engine = get_ocr_engine()
    extracted_pages: list[tuple[int, str]] = []

    try:
        pdf = pymupdf.open(file_path)
    except Exception as exc:
        raise OcrError(
            f"Không thể mở PDF để OCR: {exc}"
        ) from exc

    try:
        with TemporaryDirectory() as temporary_directory:
            temp_dir = Path(temporary_directory)

            for page_index, page in enumerate(
                pdf,
                start=1,
            ):
                if page_numbers is not None and page_index not in page_numbers:
                    continue

                image_path = temp_dir / f"page_{page_index}.png"

                render_pdf_page_to_image(
                    page=page,
                    output_path=image_path,
                    dpi=dpi,
                )

                try:
                    result = engine.predict(
                        input=str(image_path),
                    )
                except Exception as exc:
                    raise OcrError(
                        f"OCR thất bại tại trang {page_index}: {exc}"
                    ) from exc

                text = extract_text_from_ocr_result(result)

                extracted_pages.append(
                    (page_index, text)
                )
    finally:
        pdf.close()

    return extracted_pages
