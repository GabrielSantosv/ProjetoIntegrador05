from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))

from extracao.pipeline import DocumentPipeline
from extracao.profiles import PROFILES


def build_parser() -> argparse.ArgumentParser:
    default_input = str(PROJECT_ROOT / "01_DATA_INPUT")
    default_output = str(PROJECT_ROOT / "03_OUTPUT" / "analise_consolidada.xlsx")

    parser = argparse.ArgumentParser(
        description="Extrai dados de PDFs jurídicos e gera uma planilha consolidada."
    )
    parser.add_argument(
        "--input",
        default=default_input,
        help="Arquivo PDF individual ou pasta contendo PDFs de entrada.",
    )
    parser.add_argument(
        "--output",
        default=default_output,
        help="Arquivo de saída .csv ou .xlsx.",
    )
    parser.add_argument(
        "--reader",
        choices=["plumber", "fitz"],
        default="plumber",
        help="Leitor de PDF preferido.",
    )
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILES.keys()),
        default="generic",
        help="Perfil de documento para extração de campos.",
    )
    parser.add_argument(
        "--ocr",
        action="store_true",
        help="Ativa OCR para páginas que não retornam texto diretamente.",
    )
    parser.add_argument(
        "--no-tables",
        action="store_true",
        help="Desativa a extração de tabelas.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Caminho opcional para modelo sklearn serializado com joblib.",
    )
    parser.add_argument(
        "--tesseract-cmd",
        default=None,
        help="Caminho para o executável do Tesseract no Windows.",
    )
    return parser


def configure_tesseract(tesseract_cmd: str | None) -> None:
    if not tesseract_cmd:
        return

    try:
        import pytesseract
    except Exception:
        return

    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd


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
