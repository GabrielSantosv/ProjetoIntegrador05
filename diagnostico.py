"""
Script de Diagnóstico - Verifica se tudo está instalado corretamente
para o sistema de fallback de extração.

Execute com: python diagnostico.py
"""

import sys
from pathlib import Path

print("\n" + "="*70)
print("DIAGNÓSTICO DO SISTEMA DE FALLBACK")
print("="*70)

# =========================================================================
# Teste 1: Dependências Core
# =========================================================================
print("\n[1/5] Verificando dependências CORE...")

dependencias_core = {
    "pdfplumber": "Extração com PdfPlumber",
    "pymupdf": "Extração com PyMuPDF (Fitz)",
    "PIL": "Manipulação de imagens",
    "pandas": "Exportação Excel/CSV",
    "openpyxl": "Escrita Excel",
}

core_ok = True
for modulo, desc in dependencias_core.items():
    try:
        __import__(modulo)
        print(f"  ✓ {modulo:<15} - {desc}")
    except ImportError:
        print(f"  ✗ {modulo:<15} - {desc} [FALTA]")
        core_ok = False

# =========================================================================
# Teste 2: Dependências OCR (Opcional)
# =========================================================================
print("\n[2/5] Verificando dependências OCR (opcional)...")

dependencias_ocr = {
    "pytesseract": "Interface com Tesseract",
    "pdf2image": "Conversão PDF→Imagem",
}

ocr_ok = True
for modulo, desc in dependencias_ocr.items():
    try:
        __import__(modulo)
        print(f"  ✓ {modulo:<15} - {desc}")
    except ImportError:
        print(f"  ⚠ {modulo:<15} - {desc} [FALTA - OCR desabilitado]")
        ocr_ok = False

# Verificar Tesseract no sistema
if ocr_ok:
    try:
        import pytesseract
        pytesseract.pytesseract.get_tesseract_version()
        print(f"  ✓ Tesseract     - Executável detectado no sistema")
    except Exception as e:
        print(f"  ✗ Tesseract     - Não encontrado no PATH")
        print(f"      Windows: https://github.com/UB-Mannheim/tesseract/wiki")
        print(f"      Linux:   sudo apt install tesseract-ocr")
        print(f"      MacOS:   brew install tesseract")
        ocr_ok = False

# =========================================================================
# Teste 3: Módulos do Projeto
# =========================================================================
print("\n[3/5] Verificando módulos do projeto...")

projeto_root = Path(__file__).parent
sys.path.insert(0, str(projeto_root))

modulos_projeto = {
    "extracao.extraction_strategies": "Sistema Fallback",
    "extracao.logging_config": "Logging centralizado",
    "extracao.pipeline": "Pipeline principal",
    "extracao.parser": "Parser de dados",
    "extracao.classifier": "Classificador",
    "extracao.exporter": "Exportador",
}

projeto_ok = True
for modulo, desc in modulos_projeto.items():
    try:
        __import__(modulo)
        print(f"  ✓ {modulo:<40} - {desc}")
    except ImportError as e:
        print(f"  ✗ {modulo:<40} - {desc}")
        print(f"      Erro: {str(e)[:60]}")
        projeto_ok = False

# =========================================================================
# Teste 4: Arquivos Necessários
# =========================================================================
print("\n[4/5] Verificando arquivos do projeto...")

arquivos_obrigatorios = {
    "01_DATA_INPUT": "Pasta de entrada",
    "03_OUTPUT": "Pasta de saída",
    "extracao": "Pacote Python",
    "02_SCRIPTS": "Scripts de processamento",
}

arquivos_ok = True
for arquivo, desc in arquivos_obrigatorios.items():
    caminho = projeto_root / arquivo
    if caminho.exists():
        tipo = "📁 pasta" if caminho.is_dir() else "📄 arquivo"
        print(f"  ✓ {arquivo:<30} - {tipo}")
    else:
        print(f"  ✗ {arquivo:<30} - NÃO ENCONTRADO")
        arquivos_ok = False

# =========================================================================
# Teste 5: Performance Test
# =========================================================================
print("\n[5/5] Teste de Performance...")

try:
    import pdfplumber
    import time
    
    # Tentar encontrar um PDF de teste
    pdf_teste = None
    for pdf in (projeto_root / "01_DATA_INPUT").rglob("*.pdf"):
        pdf_teste = pdf
        break
    
    if pdf_teste:
        print(f"  Testando com: {pdf_teste.name}")
        
        inicio = time.time()
        with pdfplumber.open(pdf_teste) as pdf:
            page = pdf.pages[0]
            texto = page.extract_text()
            tabelas = page.extract_tables()
        tempo = time.time() - inicio
        
        print(f"  ✓ PdfPlumber responde em {tempo:.3f}s")
        print(f"    Página 1: {len(texto) if texto else 0} caracteres")
        print(f"    Tabelas encontradas: {len(tabelas) if tabelas else 0}")
    else:
        print(f"  ⚠ Nenhum PDF encontrado em 01_DATA_INPUT para teste")

except Exception as e:
    print(f"  ✗ Erro no teste de performance: {str(e)[:60]}")

# =========================================================================
# RESUMO FINAL
# =========================================================================
print("\n" + "="*70)
print("RESUMO DO DIAGNÓSTICO")
print("="*70)

status_dict = {
    "Dependências Core": core_ok,
    "Dependências OCR": ocr_ok,
    "Módulos Projeto": projeto_ok,
    "Arquivos Necessários": arquivos_ok,
}

total_ok = sum(status_dict.values())
total = len(status_dict)

for componente, ok in status_dict.items():
    simbolo = "✓" if ok else "✗"
    print(f"  {simbolo} {componente}")

print("\n" + "-"*70)

if total_ok == total:
    print("✓ TUDO OK! Sistema pronto para usar.")
    print("\nPróximos passos:")
    print("  1. python 02_SCRIPTS/extrator_principal.py --input 01_DATA_INPUT --verbose")
    print("  2. Leia FALLBACK_SYSTEM.md para documentação completa")
    print("  3. Execute: python extracao_exemplos.py")
    exit_code = 0

else:
    print(f"⚠ ALGUNS COMPONENTES FALTAM ({total_ok}/{total} OK)")
    print("\nResolva os problemas acima:")
    
    if not core_ok:
        print("  • pip install -r requirements.txt")
    
    if not ocr_ok:
        print("  • Instale Tesseract (veja instruções acima)")
        print("  • Ou use --no-ocr para desativar OCR")
    
    if not projeto_ok:
        print("  • Verifique se extracao/ está no lugar certo")
    
    if not arquivos_ok:
        print("  • Crie pastas 01_DATA_INPUT e 03_OUTPUT")
    
    exit_code = 1

print("="*70 + "\n")
sys.exit(exit_code)
