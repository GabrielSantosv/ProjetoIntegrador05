from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))


def list_pdfs(input_dir: Path) -> list[Path]:
    return sorted(input_dir.rglob("*.pdf"))


def benchmark_pdfplumber(pdf_path: Path) -> tuple[int, float]:
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError("Instale pdfplumber para executar este benchmark.") from exc

    start = time.perf_counter()
    with pdfplumber.open(pdf_path) as pdf:
        text = "".join(page.extract_text(x_tolerance=2, y_tolerance=2) or "" for page in pdf.pages)
    duration = time.perf_counter() - start
    return len(text), duration


def benchmark_pymupdf(pdf_path: Path) -> tuple[int, float]:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("Instale pymupdf para executar este benchmark.") from exc

    start = time.perf_counter()
    with fitz.open(pdf_path) as doc:
        text = "".join(page.get_text("text") or "" for page in doc)
    duration = time.perf_counter() - start
    return len(text), duration


def benchmark_ocr(pdf_path: Path) -> tuple[int, float]:
    try:
        import fitz
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Instale fitz, pytesseract e pillow para executar o benchmark OCR.") from exc

    start = time.perf_counter()
    with fitz.open(pdf_path) as doc:
        text = ""
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text += pytesseract.image_to_string(image, lang="por")
    duration = time.perf_counter() - start
    return len(text), duration


def count_pdf_pages(pdf_path: Path) -> int | str:
    try:
        import fitz
        with fitz.open(pdf_path) as doc:
            return len(doc)
    except Exception:
        return "unknown"


def write_csv(rows: list[dict[str, str | int | float]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["file", "method", "pages", "text_chars", "duration_seconds"]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    input_dir = PROJECT_ROOT / "01_DATA_INPUT"
    output_path = PROJECT_ROOT / "03_OUTPUT" / "relatorio_benchmark.csv"

    pdf_files = list_pdfs(input_dir)
    if not pdf_files:
        print(f"Nenhum PDF encontrado em {input_dir}.")
        return 1

    rows: list[dict[str, str | int | float]] = []
    for pdf_path in pdf_files:
        print(f"Benchmarking {pdf_path.name}")
        for method_name, runner in (
            ("pdfplumber", benchmark_pdfplumber),
            ("pymupdf", benchmark_pymupdf),
            ("ocr", benchmark_ocr),
        ):
            try:
                text_chars, duration = runner(pdf_path)
                rows.append(
                    {
                        "file": pdf_path.name,
                        "method": method_name,
                        "pages": count_pdf_pages(pdf_path),
                        "text_chars": text_chars,
                        "duration_seconds": round(duration, 4),
                    }
                )
                print(f"  {method_name}: {duration:.3f}s, {text_chars} chars")
            except Exception as exc:
                print(f"  {method_name} falhou: {exc}")

    write_csv(rows, output_path)
    print(f"Relatório gravado em {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
