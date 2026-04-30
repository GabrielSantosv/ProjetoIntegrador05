"""PDF text extraction with layered fallbacks and page geometry."""
from dataclasses import dataclass
from pathlib import Path

import fitz
import pdfplumber
import pytesseract
from pdf2image import convert_from_path


@dataclass
class ExtractedPdf:
    text: str
    pages: list[dict]
    extraction_method: str
    raw_ocr_text: str = ""


def extract_pdf_text(file_path: str) -> ExtractedPdf:
    """Extract text and page coordinates using pdfplumber, PyMuPDF and OCR fallback."""
    path = Path(file_path)
    extracted = _extract_with_pdfplumber(path)
    if len(extracted.text.strip()) >= 25:
        return extracted

    fallback = _extract_with_pymupdf(path)
    if len(fallback.text.strip()) >= 25:
        return fallback

    ocr_text = _extract_with_tesseract(path)
    return ExtractedPdf(
        text=ocr_text,
        pages=[{"page": 1, "words": []}],
        extraction_method="tesseract_ocr",
        raw_ocr_text=ocr_text,
    )


def _extract_with_pdfplumber(path: Path) -> ExtractedPdf:
    pages: list[dict] = []
    text_parts: list[str] = []
    try:
        with pdfplumber.open(path) as pdf:
            for index, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text() or ""
                words = page.extract_words(
                    keep_blank_chars=False,
                    use_text_flow=True,
                    extra_attrs=["fontname", "size"],
                )
                pages.append({
                    "page": index,
                    "width": page.width,
                    "height": page.height,
                    "words": [_normalize_pdfplumber_word(word) for word in words],
                })
                text_parts.append(page_text)
    except Exception:
        return ExtractedPdf(text="", pages=[], extraction_method="pdfplumber_failed")
    return ExtractedPdf(text="\n\n".join(text_parts), pages=pages, extraction_method="pdfplumber")


def _extract_with_pymupdf(path: Path) -> ExtractedPdf:
    pages: list[dict] = []
    text_parts: list[str] = []
    try:
        with fitz.open(path) as doc:
            for index, page in enumerate(doc, start=1):
                text_parts.append(page.get_text("text") or "")
                words = []
                for word in page.get_text("words"):
                    x0, y0, x1, y1, text, *_rest = word
                    words.append({
                        "text": text,
                        "x0": float(x0),
                        "top": float(y0),
                        "x1": float(x1),
                        "bottom": float(y1),
                    })
                rect = page.rect
                pages.append({
                    "page": index,
                    "width": rect.width,
                    "height": rect.height,
                    "words": words,
                })
    except Exception:
        return ExtractedPdf(text="", pages=[], extraction_method="pymupdf_failed")
    return ExtractedPdf(text="\n\n".join(text_parts), pages=pages, extraction_method="pymupdf")


def _extract_with_tesseract(path: Path) -> str:
    try:
        images = convert_from_path(path, dpi=300)
        return "\n\n".join(pytesseract.image_to_string(image, lang="por") for image in images)
    except Exception as exc:
        return f"OCR indisponivel ou falhou: {exc}"


def _normalize_pdfplumber_word(word: dict) -> dict:
    return {
        "text": word.get("text", ""),
        "x0": float(word.get("x0", 0)),
        "top": float(word.get("top", 0)),
        "x1": float(word.get("x1", 0)),
        "bottom": float(word.get("bottom", 0)),
        "fontname": word.get("fontname", ""),
        "size": word.get("size", 0),
    }
