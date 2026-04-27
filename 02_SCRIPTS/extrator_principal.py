from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))

from extracao.pipeline import DocumentPipeline
from extracao.profiles import PROFILES
from extracao.logging_config import setup_logging


def build_parser() -> argparse.ArgumentParser:
    default_input = str(PROJECT_ROOT / "01_DATA_INPUT")
    default_output = str(PROJECT_ROOT / "03_OUTPUT" / "analise_consolidada.xlsx")

    parser = argparse.ArgumentParser(
        description="Extrai dados de PDFs jurídicos com sistema de fallback robusto (3 estratégias).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Estratégias de Extração (fallback automático):
  1. PdfPlumber     - Padrão, mantém geometria, extrai tabelas
  2. PyMuPDF (Fitz) - Alternativa confiável, menos geometria
  3. PDF2Image+OCR  - Último recurso, para PDFs escaneados (lento)

Exemplo de uso:
  python extrator_principal.py --input 01_DATA_INPUT --output 03_OUTPUT/resultado.xlsx --verbose
  python extrator_principal.py --input meu_pdf.pdf --reader fitz --no-ocr
        """,
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
        help="Estratégia preferida para começar (padrão: plumber). Fallback automático se falhar.",
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
        default=True,
        help="Ativa OCR como terceira estratégia (padrão: sim).",
    )
    parser.add_argument(
        "--no-ocr",
        action="store_true",
        help="Desativa OCR (desativa terceira estratégia).",
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
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Modo debug com logs detalhados.",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Salvar logs em arquivo (padrão: nenhum arquivo).",
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

    # Configurar logging
    log_file = Path(args.log_file) if args.log_file else None
    logger = setup_logging(
        name="extracao",
        verbose=args.verbose,
        log_file=log_file,
    )

    if log_file:
        logger.info(f"Logs sendo salvos em: {log_file}")

    configure_tesseract(args.tesseract_cmd)

    # Detectar se --no-ocr foi usado
    enable_ocr = args.ocr if not args.no_ocr else False

    pipeline = DocumentPipeline(
        prefer_reader=args.reader,
        model_path=model_path,
        profile=args.profile,
        enable_ocr=enable_ocr,
        extract_tables=not args.no_tables,
    )

    try:
        logger.info("\n" + "="*70)
        logger.info("INICIANDO EXTRAÇÃO COM SISTEMA DE FALLBACK")
        logger.info("="*70)
        logger.info(f"Entrada: {input_path}")
        logger.info(f"Saída: {output_path}")
        logger.info(f"Estratégia preferida: {args.reader}")
        logger.info(f"OCR habilitado: {enable_ocr}")
        logger.info("="*70 + "\n")

        result = pipeline.process_path(input_path)
        pipeline.export(result, output_path)

        logger.info("\n" + "="*70)
        logger.info("EXTRAÇÃO CONCLUÍDA COM SUCESSO!")
        logger.info("="*70)
        logger.info(f"Arquivos processados: {len(result.source_files)}")
        logger.info(f"Linhas exportadas: {len(result.records)}")
        logger.info(f"Tabelas extraídas: {len(result.tables)}")
        logger.info(f"Resultado salvo em: {output_path}")
        logger.info("="*70)

        return 0

    except Exception as e:
        logger.error(f"\nErro fatal durante extração: {e}", exc_info=args.verbose)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
