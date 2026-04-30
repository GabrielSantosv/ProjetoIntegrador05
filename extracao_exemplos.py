"""
Exemplos de uso do sistema de fallback de extração.

Execute com:
    python extracao_exemplos.py
"""

from pathlib import Path
import sys

# Adicionar raiz ao path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from extracao.extraction_strategies import FallbackExtractor
from extracao.pipeline import DocumentPipeline
from extracao.logging_config import setup_logging


def exemplo_1_fallback_basico():
    """Exemplo 1: Usar o FallbackExtractor diretamente."""
    print("\n" + "="*70)
    print("EXEMPLO 1: FallbackExtractor Básico")
    print("="*70)

    # Configurar logger
    logger = setup_logging(verbose=True)

    # Criar extrator com 3 estratégias
    extrator = FallbackExtractor(
        prefer_strategy="plumber",  # Começar com PdfPlumber
        enable_ocr=True,              # Permitir OCR como fallback
        extract_tables=True,          # Extrair tabelas
    )

    # Simular processamento de um PDF
    pdf_arquivo = PROJECT_ROOT / "01_DATA_INPUT" / "exemplo.pdf"

    if pdf_arquivo.exists():
        try:
            resultado = extrator.extract(pdf_arquivo)
            print(f"\n✓ Extração bem-sucedida!")
            print(f"  Arquivo: {resultado.file_path.name}")
            print(f"  Estratégia usada: {resultado.strategy_used}")
            print(f"  Total de páginas: {len(resultado.pages)}")
            print(f"  Fallbacks necessários: {resultado.fallback_count}")

            for page in resultado.pages:
                print(f"\n  Página {page.page_number}:")
                print(f"    Fonte: {page.source}")
                print(f"    Confiança: {page.text_confidence:.1%}")
                print(f"    Caracteres: {len(page.text)}")

        except Exception as e:
            print(f"\n✗ Falha na extração: {e}")
    else:
        print(f"\n⚠️ PDF não encontrado em: {pdf_arquivo}")


def exemplo_2_pipeline_completo():
    """Exemplo 2: Usar o pipeline completo com fallback."""
    print("\n" + "="*70)
    print("EXEMPLO 2: Pipeline Completo com Fallback")
    print("="*70)

    logger = setup_logging(verbose=True)

    # Criar pipeline que já usa o FallbackExtractor
    pipeline = DocumentPipeline(
        prefer_reader="plumber",  # Começa com PdfPlumber
        enable_ocr=True,           # Ativa OCR como fallback
        extract_tables=True,
    )

    # Processar um arquivo ou pasta
    input_path = PROJECT_ROOT / "01_DATA_INPUT"

    if input_path.exists():
        try:
            resultado = pipeline.process_path(input_path)

            print(f"\n✓ Processamento completo!")
            print(f"  Arquivos processados: {len(resultado.source_files)}")
            print(f"  Registros extraídos: {len(resultado.records)}")
            print(f"  Tabelas encontradas: {len(resultado.tables)}")

            # Mostrar metadados de estratégia de alguns registros
            for i, record in enumerate(resultado.records[:3]):
                print(f"\n  Registro {i+1}:")
                print(f"    Arquivo: {Path(record.source_file).name}")
                print(f"    Página: {record.page_number}")
                print(f"    Estratégia: {record.metadata.get('extraction_strategy', 'N/A')}")
                print(f"    Confiança: {record.metadata.get('text_confidence', 1.0):.1%}")

        except Exception as e:
            print(f"\n✗ Erro no processamento: {e}")
    else:
        print(f"\n⚠️ Pasta não encontrada: {input_path}")


def exemplo_3_deteccao_pdf_scaneado():
    """Exemplo 3: Detectar se um PDF é escaneado."""
    print("\n" + "="*70)
    print("EXEMPLO 3: Detectar PDFs Escaneados")
    print("="*70)

    logger = setup_logging()

    extrator = FallbackExtractor(enable_ocr=True)

    # Simular teste em um PDF
    pdf_arquivo = PROJECT_ROOT / "01_DATA_INPUT" / "exemplo.pdf"

    if pdf_arquivo.exists():
        is_scanned = extrator.is_scanned_pdf(pdf_arquivo)
        tipo = "ESCANEADO (imagem)" if is_scanned else "TEXTO NATIVO"
        print(f"\n{pdf_arquivo.name}:")
        print(f"  Tipo: {tipo}")
        print(f"  OCR necessário: {is_scanned}")
    else:
        print(f"\n⚠️ PDF não encontrado: {pdf_arquivo}")


def exemplo_4_processar_especifico():
    """Exemplo 4: Processar um arquivo específico com controle fine-tuned."""
    print("\n" + "="*70)
    print("EXEMPLO 4: Processamento com Controle Fine-tuned")
    print("="*70)

    logger = setup_logging(verbose=True)

    pipeline = DocumentPipeline(
        prefer_reader="fitz",      # Começar com Fitz ao invés de plumber
        enable_ocr=False,          # Sem OCR (mais rápido)
        extract_tables=True,
    )

    pdf_arquivo = PROJECT_ROOT / "01_DATA_INPUT" / "exemplo.pdf"

    if pdf_arquivo.exists():
        try:
            records, tables = pipeline.process_file(pdf_arquivo)

            print(f"\n✓ Arquivo processado!")
            print(f"  Registros: {len(records)}")
            print(f"  Tabelas: {len(tables)}")

            # Mostrar informações de extração
            for record in records[:1]:  # Primeira página
                print(f"\n  Resultado (página {record.page_number}):")
                print(f"    Tipo: {record.document_type}")
                print(f"    Risco: {record.nivel_risco}")
                print(f"    CPF: {record.cpf}")
                print(f"    Processo: {record.process_number}")
                print(f"    Estratégia: {record.metadata.get('extraction_strategy')}")

        except Exception as e:
            print(f"\n✗ Erro: {e}")
    else:
        print(f"\n⚠️ PDF não encontrado: {pdf_arquivo}")


def exemplo_5_uso_direto_estrategias():
    """Exemplo 5: Usar estratégias diretamente."""
    print("\n" + "="*70)
    print("EXEMPLO 5: Usar Estratégias Individualmente")
    print("="*70)

    from extracao.extraction_strategies import (
        PdfPlumberStrategy,
        PyMuPDFStrategy,
        PDF2ImageOCRStrategy,
    )

    logger = setup_logging()

    pdf_arquivo = PROJECT_ROOT / "01_DATA_INPUT" / "exemplo.pdf"

    if not pdf_arquivo.exists():
        print(f"\n⚠️ PDF não encontrado: {pdf_arquivo}")
        return

    # Testar cada estratégia individualmente
    estrategias = [
        PdfPlumberStrategy(),
        PyMuPDFStrategy(),
    ]

    for estrategia in estrategias:
        print(f"\nTestando {estrategia.get_name()}...")
        try:
            pages = estrategia.extract(pdf_arquivo, extract_tables=True)
            print(f"  ✓ Sucesso! {len(pages)} páginas extraídas")
            print(f"    Primeira página tem {len(pages[0].text)} caracteres")
        except Exception as e:
            print(f"  ✗ Falhou: {str(e)[:60]}...")


# =========================================================================
# Executar exemplos
# =========================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("EXEMPLOS DE USO - SISTEMA DE FALLBACK")
    print("="*70)
    print("Os próximos exemplos demonstram como usar o sistema de fallback")
    print("de extração com 3 estratégias progressivas.")
    print("="*70)

    # Executar exemplos (descomente os que quer testar)
    try:
        exemplo_1_fallback_basico()
    except Exception as e:
        print(f"⚠️ Exemplo 1 não funcionou (talvez falta PDF): {e}")

    try:
        exemplo_2_pipeline_completo()
    except Exception as e:
        print(f"⚠️ Exemplo 2 não funcionou: {e}")

    try:
        exemplo_3_deteccao_pdf_scaneado()
    except Exception as e:
        print(f"⚠️ Exemplo 3 não funcionou: {e}")

    try:
        exemplo_4_processar_especifico()
    except Exception as e:
        print(f"⚠️ Exemplo 4 não funcionou: {e}")

    try:
        exemplo_5_uso_direto_estrategias()
    except Exception as e:
        print(f"⚠️ Exemplo 5 não funcionou: {e}")

    print("\n" + "="*70)
    print("EXEMPLOS CONCLUÍDOS")
    print("="*70)
    print("\nPróximos passos:")
    print("1. Leia FALLBACK_SYSTEM.md para documentação técnica completa")
    print("2. Leia README_FALLBACK_PT.md para guia em português")
    print("3. Execute: python 02_SCRIPTS/extrator_principal.py --input seu_pdf.pdf --verbose")
    print("="*70 + "\n")
