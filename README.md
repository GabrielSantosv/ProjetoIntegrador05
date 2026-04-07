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
ProjetoIntegrador05/
├── 01_DATA_INPUT/          ← PDFs de entrada (TJSP, TRT15, CNDT, Federal, etc)
├── 02_SCRIPTS/
│   └── extrator_principal.py    ← CLI principal
├── 03_OUTPUT/              ← Resultados (Excel/CSV)
└── extracao/               ← Pacote Python
    ├── pipeline.py         ← Orquestra fluxo
    ├── readers.py          ← Lê PDFs
    ├── parser.py           ← Extrai campos
    ├── classifier.py       ← Classifica tipo
    └── exporter.py         ← Exporta resultados
```

## Instalar

```bash
# Clone o repositório
cd ProjetoIntegrador05

# Crie ambiente virtual
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate    # Linux/Mac

# Instale dependências
pip install -r requirements.txt
```

### OCR (Opcional - Tesseract)

Para processar PDFs escaneados:

1. Baixe: [Tesseract-OCR Release](https://github.com/UB-Mannheim/tesseract/wiki)
2. Instale com caminho padrão: `C:\Program Files\Tesseract-OCR`

## Uso Rápido

```bash
# Processar pasta inteira (padrão: 01_DATA_INPUT/)
python 02_SCRIPTS/extrator_principal.py

# Processar com OCR
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
