# Projeto Integrador (PI) - Automação de Análise de Documentos Jurídicos

Automatiza a extração e classificação de dados em PDFs jurídicos (precatórios, certidões, CND). Extrai CPF, processo, valor, data e classifica documentos por tipo e risco.

## Funcionalidades

✅ Leitura de PDFs com texto ou escaneados (OCR via Tesseract)  
✅ Classificação automática (cível, criminal, trabalhista, federal, CND, etc.)  
✅ Extração de campos: CPF, nome, processo, data, valor, tipo de ação  
✅ Detecção de homônimos (ignora pessoas diferentes com mesmo nome)  
✅ Extração de tabelas estruturadas  
✅ Análise de risco por documento  
✅ Exportação em Excel com múltiplas abas  

## Estrutura

```
📦 ProjetoIntegrador05/
├── 📁 01_DATA_INPUT/              ← PDFs de entrada organizados por tipo
│   ├── 01_TJSP/      (Precatórios TJ São Paulo)
│   ├── 02_TRT15/     (Precatórios Trabalhistas)
│   ├── 03_CNDT/      (Certidões Negativas)
│   ├── 04_FEDERAL/   (Federais - TRF3)
│   └── 05_DOCUMENTOS/(RGs e genéricos)
│
├── 📁 02_SCRIPTS/                 ← Scripts de processamento
│   ├── extrator_principal.py      ← CLI principal
│   ├── ia_huggingface.py
│   ├── benchmark_bibliotecas.py
│   └── Jupyter Notebook (Donut tests)
│
├── 📁 03_OUTPUT/                  ← Resultados gerados
│   ├── analise_consolidada.xlsx
│   └── txt_extraidos/
│
├── 📁 extracao/                   ← Pacote Python principal
│   ├── __init__.py
│   ├── pipeline.py         ← Orquestra todo o fluxo
│   ├── readers.py          ← Lê PDFs (pdfplumber + PyMuPDF)
│   ├── parser.py           ← Extrai campos com regex
│   ├── classifier.py       ← Classifica tipo documento
│   ├── exporter.py         ← Exporta resultado (CSV/XLSX)
│   ├── models.py           ← Dataclasses dos dados
│   └── profiles.py         ← Perfis document patterns
│
├── requirements.txt
├── README.md
└── .git/
```

## Instalar

### Pré-requisitos
- Python 3.10 ou superior
- Git

### Instalação Básica

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/ProjetoIntegrador05.git
cd ProjetoIntegrador05

# 2. Crie ambiente virtual
python -m venv venv

# 3. Ative o ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. Instale as dependências
pip install -r requirements.txt
```

### Instalação Manual (Alternativa)

Se preferir instalar biblioteca por biblioteca:

```bash
pip install pdfplumber>=0.11.4
pip install pymupdf>=1.24.9
pip install pytesseract>=0.3.13
pip install pillow>=11.0.0
pip install pandas>=2.2.2
pip install openpyxl>=3.1.5
pip install scikit-learn>=1.5.1
pip install joblib>=1.4.2
pip install transformers>=4.40.0
pip install torch>=2.0.0
pip install pdf2image>=1.16.0
pip install sentencepiece>=0.1.98
```

### OCR (Opcional - Tesseract)

Para processar PDFs escaneados:

1. **Baixe o Tesseract:**
   - [Tesseract-OCR Release](https://github.com/UB-Mannheim/tesseract/wiki)
   - Versão recomendada: `tesseract-ocr-w64-setup-v5.x.x.exe`

2. **Instale** com opções padrão (caminho: `C:\Program Files\Tesseract-OCR`)

3. **Teste a instalação:**
   ```bash
   tesseract --version
   ```

## Como Rodar

### Uso Básico

```bash
# Ative o ambiente virtual primeiro
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Processar pasta inteira (padrão: 01_DATA_INPUT/)
python 02_SCRIPTS/extrator_principal.py

# Resultado será salvo em: 03_OUTPUT/analise_consolidada.xlsx
```

### Exemplos de Uso

```bash
# Processar com OCR (PDFs escaneados)
python 02_SCRIPTS/extrator_principal.py --ocr --tesseract-cmd "C:\Program Files\Tesseract-OCR\tesseract.exe"

# Processar arquivo único
python 02_SCRIPTS/extrator_principal.py --input "01_DATA_INPUT/exemplo.pdf"

# Salvar resultado em local específico
python 02_SCRIPTS/extrator_principal.py --output "03_OUTPUT/resultado.xlsx"

# Usar perfil específico (tj, trt, alvara, generic)
python 02_SCRIPTS/extrator_principal.py --profile tj

# Desativar extração de tabelas
python 02_SCRIPTS/extrator_principal.py --no-tables

# Usar modelo sklearn customizado
python 02_SCRIPTS/extrator_principal.py --model /caminho/modelo.pkl

# Combinar múltiplas opções
python 02_SCRIPTS/extrator_principal.py \
  --input 01_DATA_INPUT/01_TJSP \
  --output 03_OUTPUT/tjsp.xlsx \
  --profile tj \
  --ocr \
  --tesseract-cmd "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

### Verificar Instalação

```bash
# Teste se tudo está funcionando
python -c "import pdfplumber, pytesseract, pandas; print('✅ Todas as bibliotecas instaladas!')"

# Teste o script principal
python 02_SCRIPTS/extrator_principal.py --help
```

# Processar arquivo único
python 02_SCRIPTS/extrator_principal.py --input "01_DATA_INPUT/exemplo.pdf"

# Salvar resultado em local específico
python 02_SCRIPTS/extrator_principal.py --output "03_OUTPUT/resultado.xlsx"

# Usar perfil específico (tj, trt, alvara, generic)
python 02_SCRIPTS/extrator_principal.py --profile tj

# Desativar extração de tabelas
python 02_SCRIPTS/extrator_principal.py --no-tables

# Usar modelo sklearn customizado
python 02_SCRIPTS/extrator_principal.py --model /caminho/modelo.pkl
```

## Opções da CLI

| Opção | Padrão | Descrição |
|-------|--------|-----------|
| `--input` | `01_DATA_INPUT/` | Pasta ou arquivo PDF |
| `--output` | `03_OUTPUT/analise_consolidada.xlsx` | Arquivo de saída |
| `--profile` | `generic` | Tipo documento: generic, tj, trt, alvara |
| `--reader` | `plumber` | Leitor: plumber ou fitz |
| `--ocr` | Inativo | Ativa OCR para PDFs escaneados |
| `--no-tables` | Tabelas ativas | Desativa extração de tabelas |
| `--model` | - | Caminho modelo sklearn (.pkl) |
| `--tesseract-cmd` | Auto-detect | Path Tesseract Windows |

## Resultado

**Arquivo Excel com 2 abas:**

**Aba "pages"** - Uma linha por página:
- source_file, page_number, document_type, name, cpf, process_number, date, value, status, risk_level, ...

**Aba "tables"** - Tabelas estruturadas:
- source_file, page_number, table_index, table_data

## Uso em Python

```python
from pathlib import Path
from extracao import DocumentPipeline

# Criar pipeline
pipeline = DocumentPipeline(
    prefer_reader="plumber",
    profile="tj",
    enable_ocr=True,
    extract_tables=True
)

# Processar
result = pipeline.process_path(Path("01_DATA_INPUT"))

# Exportar
pipeline.export(result, Path("03_OUTPUT/resultado.xlsx"))

# Acessar dados
for record in result.records:
    print(f"{record.cpf} | {record.process_number} | {record.document_type}")
```

## Tipos de Documento (Classificação Automática)

| Tipo | Risco | Descrição |
|------|-------|-----------|
| `civel_estadual` | 🔴 Máximo | TJSP - Ação Cível |
| `criminal_estadual` | 🟡 Médio | TJSP - Ação Criminal |
| `cnd_federal` | 🔴 Máximo | Certidão Negativa Federal |
| `civel_federal` | 🔴 Máximo | Federal - Cível |
| `cndt` | 🟡 Médio | Certidão Negativa Trabalhista |
| `trf3` | 🟢 Informativo | Tribunal Regional Federal |
| `criminal_federal` | 🟡 Médio | Federal - Criminal |
| `ceat` | 🟢 Informativo | Certidão Trabalhista |

## Campos Extraídos

- **name** - Nome da pessoa
- **cpf** - CPF formatado (XXX.XXX.XXX-XX)
- **process_number** - Número do processo (XXXXXXXX-DD.YYYY.D.DD.YYYY)
- **date** - Data (DD/MM/YYYY)
- **value** - Valor monetário (R$ X.XXX,XX)
- **tipo_acao** - Tipo de ação judicial
- **situacao_processual** - Situação (Julgada, Aguardando, etc)
- **vara** - Vara judiciária
- **foro** - Foro
- **status** - NADA CONSTAR ou POSITIVA
- **processes_from_geometry** - Processos por marcador visual "»"

## Tecnologias

- **pdfplumber, PyMuPDF** - Leitura de PDFs
- **pytesseract** - OCR
- **pandas, openpyxl** - Exportação Excel
- **scikit-learn** - Classificação (opcional)
- **transformers, torch** - Modelos IA (Donut)
- **pillow** - Processamento de imagens
