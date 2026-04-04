from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import fitz  # PyMuPDF
import pdfplumber
import pytesseract
from PIL import Image
from pypdf import PdfReader, PdfWriter


@dataclass
class PageText:
    page_number: int
    text: str
    tables: list[list[list[str | None]]] | None = None
    source: str = "text"


class PDFReader(Protocol):
    def read_pages(self, pdf_path: Path) -> list[PageText]:
        ...


class PdfPlumberReader:
    def __init__(self, extract_tables: bool = True) -> None:
        self.extract_tables = extract_tables

    def read_pages(self, pdf_path: Path) -> list[PageText]:
        pages: list[PageText] = []
        with pdfplumber.open(pdf_path) as pdf:
            for index, page in enumerate(pdf.pages, start=1):
                text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
                tables = page.extract_tables() if self.extract_tables else []
                pages.append(PageText(page_number=index, text=text, tables=tables, source="plumber"))
        return pages


class PyMuPDFReader:
    def read_pages(self, pdf_path: Path) -> list[PageText]:
        pages: list[PageText] = []
        with fitz.open(pdf_path) as doc:
            for index, page in enumerate(doc, start=1):
                text = page.get_text("text") or ""
                pages.append(PageText(page_number=index, text=text, tables=[], source="fitz"))
        return pages


class HybridReader:
    def __init__(self, prefer: str = "plumber", enable_ocr: bool = False, ocr_language: str = "por+eng", extract_tables: bool = True) -> None:
        self.prefer = prefer
        self.enable_ocr = enable_ocr
        self.ocr_language = ocr_language
        self.plumber = PdfPlumberReader(extract_tables=extract_tables)
        self.fitz_reader = PyMuPDFReader()

    def read_pages(self, pdf_path: Path) -> list[PageText]:
        primary = self.plumber if self.prefer == "plumber" else self.fitz_reader
        secondary = self.fitz_reader if primary is self.plumber else self.plumber

        try:
            pages = primary.read_pages(pdf_path)
        except Exception:
            pages = secondary.read_pages(pdf_path)

        if not any(page.text.strip() for page in pages):
            pages = secondary.read_pages(pdf_path)

        if self.enable_ocr:
            pages = [self._maybe_ocr_page(pdf_path, page) for page in pages]

        return pages

    def _maybe_ocr_page(self, pdf_path: Path, page: PageText) -> PageText:
        if len(page.text.strip()) >= 25:
            return page

        ocr_text = self._ocr_page(pdf_path, page.page_number)
        if not ocr_text.strip():
            return page

        merged_text = page.text.strip()
        if merged_text:
            merged_text = f"{merged_text}\n{ocr_text.strip()}"
        else:
            merged_text = ocr_text.strip()
        return PageText(page_number=page.page_number, text=merged_text, tables=page.tables, source=f"{page.source}+ocr")

    def _ocr_page(self, pdf_path: Path, page_number: int) -> str:
        try:
            with fitz.open(pdf_path) as doc:
                page = doc[page_number - 1]
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
                return pytesseract.image_to_string(image, lang=self.ocr_language)
        except Exception:
            return ""


class PDFToolkit:
    @staticmethod
    def merge(files: list[Path], output_path: Path) -> Path:
        writer = PdfWriter()
        for file_path in files:
            reader = PdfReader(str(file_path))
            for page in reader.pages:
                writer.add_page(page)
        with output_path.open("wb") as handle:
            writer.write(handle)
        return output_path

    @staticmethod
    def split(pdf_path: Path, output_dir: Path) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        reader = PdfReader(str(pdf_path))
        output_files: list[Path] = []
        for index, page in enumerate(reader.pages, start=1):
            writer = PdfWriter()
            writer.add_page(page)
            output_path = output_dir / f"{pdf_path.stem}_p{index}.pdf"
            with output_path.open("wb") as handle:
                writer.write(handle)
            output_files.append(output_path)
        return output_files
