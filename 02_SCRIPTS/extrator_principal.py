"""
extrator_principal.py — versão atualizada
Gera Excel com 3 abas: resumo (cards visuais) + pages + tables
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_ROOT  = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))

from extracao.pipeline        import DocumentPipeline
from extracao.profiles        import PROFILES
from extracao.exporter_cards  import exportar_com_cards   # ← novo


def build_parser() -> argparse.ArgumentParser:
    default_input  = str(PROJECT_ROOT / "01_DATA_INPUT")
    default_output = str(PROJECT_ROOT / "03_OUTPUT" / "analise_consolidada.xlsx")

    p = argparse.ArgumentParser(
        description="Extrai dados de PDFs jurídicos e gera planilha com cards visuais."
    )
    p.add_argument("--input",  default=default_input,
                   help="Pasta ou arquivo PDF de entrada.")
    p.add_argument("--output", default=default_output,
                   help="Arquivo de saída .xlsx.")
    p.add_argument("--reader", choices=["plumber", "fitz"], default="plumber")
    p.add_argument("--profile", choices=sorted(PROFILES.keys()), default="generic")
    p.add_argument("--ocr",      action="store_true",
                   help="Ativa OCR para PDFs escaneados.")
    p.add_argument("--no-tables", action="store_true",
                   help="Desativa extração de tabelas.")
    p.add_argument("--cpf-alvo", default=None,
                   help="CPF do titular para filtrar homônimos (ex: 977.326.998-15).")
    p.add_argument("--model",   default=None,
                   help="Caminho para modelo sklearn .pkl (opcional).")
    p.add_argument("--tesseract-cmd", default=None,
                   help="Caminho para o executável do Tesseract (Windows).")
    return p


def main() -> int:
    args        = build_parser().parse_args()
    input_path  = Path(args.input)
    output_path = Path(args.output)
    model_path  = Path(args.model) if args.model else None

    # Configura Tesseract no Windows se necessário
    if args.tesseract_cmd:
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = args.tesseract_cmd
        except ImportError:
            pass

    pipeline = DocumentPipeline(
        prefer_reader  = args.reader,
        model_path     = model_path,
        profile        = args.profile,
        enable_ocr     = args.ocr,
        extract_tables = not args.no_tables,
        cpf_alvo       = args.cpf_alvo,
    )

    print(f"Processando: {input_path}")
    result = pipeline.process_path(input_path)

    print(f"Arquivos processados : {len(result.source_files)}")
    print(f"Páginas extraídas    : {len(result.records)}")
    print(f"Tabelas extraídas    : {len(result.tables)}")

    print(f"Gerando Excel com cards visuais...")
    exportar_com_cards(result, output_path)

    print(f"Saída gerada em      : {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())