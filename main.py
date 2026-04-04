from __future__ import annotations

import argparse
from pathlib import Path

from extracao.pipeline import DocumentPipeline
from extracao.profiles import PROFILES


def configure_tesseract(tesseract_cmd: str | None) -> None:
    if not tesseract_cmd:
        return

    try:
        import pytesseract
    except Exception:
        return

    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extrai dados de PDFs jurídicos.")
    parser.add_argument("--input", required=True, help="Arquivo PDF ou pasta com PDFs")
    parser.add_argument("--output", required=True, help="Arquivo de saída .csv ou .xlsx")
    parser.add_argument(
        "--reader",
        choices=["plumber", "fitz"],
        default="plumber",
        help="Leitor principal de PDF",
    )
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILES.keys()),
        default="generic",
        help="Perfil de documento para campos específicos",
    )
    parser.add_argument(
        "--ocr",
        action="store_true",
        help="Ativa OCR para páginas escaneadas",
    )
    parser.add_argument(
        "--no-tables",
        action="store_true",
        help="Desativa a extração de tabelas",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Caminho opcional para modelo sklearn serializado com joblib",
    )
    parser.add_argument(
        "--tesseract-cmd",
        default=None,
        help="Caminho completo para o executável do Tesseract no Windows",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    model_path = Path(args.model) if args.model else None
    configure_tesseract(args.tesseract_cmd)

    pipeline = DocumentPipeline(
        prefer_reader=args.reader,
        model_path=model_path,
        profile=args.profile,
        enable_ocr=args.ocr,
        extract_tables=not args.no_tables,
    )
    result = pipeline.process_path(input_path)
    pipeline.export(result, output_path)

    print(f"Arquivos processados: {len(result.source_files)}")
    print(f"Linhas exportadas: {len(result.records)}")
    print(f"Tabelas extraídas: {len(result.tables)}")
    print(f"Saída gerada em: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
