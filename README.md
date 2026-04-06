# Projeto Integrador (PI) - Automacao da Analise de Documentos para Compra de Precatorios

## 1. Visao Geral
Este Projeto Integrador tem como objetivo demonstrar como Inteligencia Artificial pode automatizar parte da analise documental no processo de compra de precatorios.

O foco principal e comparar duas abordagens de extracao de dados em documentos PDF:

- OCR tradicional com regras (Tesseract + Regex)
- Modelo de IA Donut (Vision Encoder-Decoder)

## Estrutura do Projeto
A organização de arquivos foi atualizada para suportar um fluxo mais claro de dados, scripts e resultados:

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

O novo layout separa os arquivos PDF originais, os scripts de processamento e os resultados finais.

O foco principal e comparar duas abordagens de extracao de dados em documentos PDF:

1. OCR tradicional com regras (Tesseract + Regex)
2. Modelo de IA Donut (Vision Encoder-Decoder)

> Observacao: o arquivo/notebook de extracao com Donut foi desenvolvido como teste solicitado pelo professor dentro do contexto deste projeto.

## 2. Problema Atual
Hoje, o fluxo de trabalho e majoritariamente manual e repetitivo, com alto consumo de tempo e risco de erro humano.

Fluxo atual:

1. Cliente entra em contato via WhatsApp com interesse na venda/compra de precatorio.
2. E feita analise inicial do processo judicial para validar elegibilidade.
3. Dados do processo sao organizados em planilha e enviados para calculo financeiro.
4. Setor comercial apresenta proposta ao cliente.
5. Se houver aceite, o cliente envia documentos (RG, dados bancarios, comprovante de residencia, certidao de casamento, contrato com advogado etc.).
6. Uma pessoa analisa os documentos manualmente, copia dados e preenche sites para emissao de certidoes (ESAJ, CNDT, TRF3, TRT15, certidoes estaduais/federais/municipais).
7. Em seguida, verifica existencia de processos vinculados e analisa detalhes (situacao, valor, tipo da acao, pagamento ja realizado etc.).
8. Com base nisso, decide-se se o precatorio pode ou nao ser comprado.

## 3. Objetivo do Projeto
Desenvolver uma prova de conceito para automacao da leitura e interpretacao de documentos com IA, produzindo evidencias tecnicas e comparativas para relatorio academico.

## 4. Escopo do Sistema (MVP Academico)
Este projeto NAO tem foco em sistema completo de producao. O foco e:

1. Processar documentos PDF enviados para analise.
2. Extrair dados relevantes automaticamente.
3. Comparar tecnicas diferentes de extracao.
4. Avaliar qualidade dos resultados em cenarios reais de documentos.

## 5. Requisitos Principais

### 5.1 Funcionais
1. Permitir upload/leitura de documentos PDF.
2. Converter PDF em imagem para processamento.
3. Executar OCR com regras para extracao de entidades (nome, CPF, endereco, etc.).
4. Executar modelo Donut para extracao orientada por IA.
5. Gerar saida estruturada (JSON/dicionario) para ambas as abordagens.
6. Comparar resultados lado a lado.
7. Registrar evidencias (prints, logs, tabelas, exemplos de saida) para relatorio.

### 5.2 Experimentais (prioridade alta)
1. Demonstrar diferencas praticas entre OCR tradicional e Donut.
2. Levantar vantagens e desvantagens de cada metodo.
3. Medir impacto da qualidade do documento (resolucao, ruido, inclinacao, baixa nitidez, cortes).

## 6. Metodologia de Comparacao
Para cada documento testado:

1. Executar pipeline OCR (pdf2image -> preprocessamento opcional -> pytesseract -> regex).
2. Executar pipeline Donut (pdf2image -> imagem -> inferencia com transformers).
3. Normalizar saidas para o mesmo formato.
4. Comparar os campos extraidos.

Criterios sugeridos:

1. Precisao por campo (ex.: CPF correto/incorreto).
2. Completude (quantos campos esperados foram encontrados).
3. Tempo medio de processamento por pagina/documento.
4. Robustez em documentos de baixa qualidade.
5. Qualidade semantica da extracao (texto bruto vs informacao estruturada).

## 7. Tecnologias Sugeridas
1. Python
2. Google Colab
3. pytesseract
4. pdf2image
5. transformers (Donut)
6. Pillow
7. Regex

## 8. Saidas Esperadas
1. Texto extraido dos documentos.
2. Dados estruturados (nome, CPF, endereco etc.).
3. Resultado do modelo Donut.
4. Comparativo entre OCR e Donut.
5. Evidencias para relatorio academico.

Exemplo de estrutura de saida:

```json
{
  "documento": "exemplo.pdf",
  "ocr": {
    "nome": "...",
    "cpf": "...",
    "endereco": "..."
  },
  "donut": {
    "nome": "...",
    "cpf": "...",
    "endereco": "..."
  },
  "comparacao": {
    "cpf_igual": true,
    "campos_preenchidos_ocr": 2,
    "campos_preenchidos_donut": 3,
    "observacoes": "Donut capturou mais contexto em documento com ruido."
  }
}
```

## 9. Estrutura Sugerida no Google Colab
1. Setup de dependencias.
2. Upload de PDFs.
3. Conversao PDF -> imagem.
4. Extracao por OCR + Regex.
5. Extracao por Donut.
6. Pos-processamento e normalizacao.
7. Comparacao de resultados.
8. Exportacao de evidencias (CSV/JSON/imagens).

## 10. Evidencias para o Relatorio
Recomenda-se incluir:

1. Prints das entradas (documentos/imagens).
2. Saida textual do OCR.
3. Saida estruturada do Donut.
4. Tabela comparativa por campo e por documento.
5. Analise critica dos resultados (acertos, erros e causas provaveis).
6. Conclusao sobre viabilidade da automacao.

## 11. Limites e Riscos
1. Documentos com baixa qualidade podem reduzir performance de ambos os metodos.
2. Regex depende de padroes e pode falhar em formatos muito variados.
3. Donut pode exigir ajuste de prompt/modelo conforme tipo documental.
4. Custos computacionais e tempo de inferencia devem ser observados.

## 12. Proximos Passos
1. Consolidar conjunto de documentos de teste com diferentes niveis de qualidade.
2. Definir gabarito (ground truth) para avaliar precisao por campo.
3. Padronizar metricas e tabela de comparacao.
4. Executar bateria de testes no Colab.
5. Finalizar analise comparativa e conclusoes academicas.

---

Se desejar, a proxima etapa pode ser a criacao de um notebook base no Google Colab com todo o pipeline (upload, OCR, Donut, comparacao e exportacao de resultados).

---

## 13. Como Funciona a Extracao de Texto dos PDFs

Esta secao descreve o processo real de extracao implementado no modulo `extracao/readers.py`.

### 13.1 Visao Geral das Tres Abordagens

| # | Abordagem | Converte para imagem? | Biblioteca principal | Quando usar |
|---|-----------|----------------------|----------------------|-------------|
| 1 | Extracao direta (pdfplumber) | **Nao** | `pdfplumber` | PDFs digitais com texto embutido |
| 2 | Extracao direta (PyMuPDF) | **Nao** | `PyMuPDF (fitz)` | Fallback rapido quando pdfplumber falha |
| 3 | OCR sobre imagem | **Sim** | `PyMuPDF + pytesseract` | PDFs escaneados ou com texto como imagem |
| 4 | Donut (IA) | **Sim** | `pdf2image + transformers` | Extracao orientada por IA (script separado) |

---

### 13.2 Abordagem 1 e 2: Extracao Direta de Texto (sem imagem)

**O arquivo PDF NAO e convertido em imagem.** O texto e lido diretamente da estrutura interna do PDF.

#### Como funciona (pdfplumber):
```
Arquivo PDF
  └─► pdfplumber.open()
        └─► page.extract_text()   ← interpreta operadores graficos do PDF
              └─► texto posicionado por coordenadas de cada caractere
        └─► page.extract_tables() ← detecta bordas e agrupa celulas
```
- Classe: `PdfPlumberReader`
- Resultado: texto corrido + tabelas estruturadas

#### Como funciona (PyMuPDF / fitz):
```
Arquivo PDF
  └─► fitz.open()
        └─► page.get_text("text") ← le o stream /Contents do PDF
              └─► texto extraido da estrutura interna
```
- Classe: `PyMuPDFReader`
- Resultado: texto corrido (sem tabelas)

**Resumo:** Nenhuma imagem e criada. O texto ja existe no arquivo PDF e e extraido diretamente.

---

### 13.3 Abordagem 3: OCR com Conversao para Imagem

Ativada automaticamente quando `enable_ocr=True` e uma pagina retorna **menos de 25 caracteres** de texto (pagina escaneada ou com texto armazenado como imagem).

**Fluxo completo:**
```
Arquivo PDF
  └─► PyMuPDF (fitz.open)
        └─► page.get_pixmap(matrix=fitz.Matrix(2, 2))
              ↓
              Imagem em escala 2x (~144 DPI) — formato Pixmap
              ↓
        └─► PIL Image.frombytes("RGB", ...)
              ↓
              Imagem RGB na memoria
              ↓
        └─► pytesseract.image_to_string(image, lang="por+eng")
              ↓
              Texto reconhecido pelo OCR (Tesseract)
```
- Classe: `HybridReader._ocr_page()`
- Escala: 2x (largura e altura dobradas) para melhorar qualidade do OCR
- Idioma: portugues + ingles por padrao (`"por+eng"`)
- Resultado: texto via reconhecimento optico de caracteres

---

### 13.4 Abordagem 4: Modelo de IA Donut (script separado)

Implementada em `02_SCRIPTS/ia_huggingface.py`. Diferente das abordagens anteriores, usa um modelo de visao computacional (Vision Encoder-Decoder) que **sempre converte o PDF em imagem** antes de processar.

**Fluxo:**
```
Arquivo PDF
  └─► pdf2image.convert_from_path(dpi=300)
        ↓
        Imagem PNG em alta resolucao (300 DPI)
        ↓
  └─► PIL Image.open() → .convert("RGB")
        ↓
  └─► DonutProcessor (tokenizer + feature extractor)
        ↓
        pixel_values (tensor para o modelo)
        ↓
  └─► VisionEncoderDecoderModel.generate()
        ↓
        Texto gerado pela IA (resposta a uma pergunta sobre o documento)
```
- Modelo: `naver-clova-ix/donut-base-finetuned-docvqa`
- Resolucao: 300 DPI para maxima qualidade
- Resultado: resposta estruturada em linguagem natural

---

### 13.5 Logica do HybridReader (pipeline padrao)

O `HybridReader` (usado pelo `DocumentPipeline`) combina as abordagens 1, 2 e 3 automaticamente:

```
                    HybridReader.read_pages(pdf_path)
                              │
                    Tenta leitor primario
                    (padrao: pdfplumber)
                              │
               ┌──────────────┴──────────────┐
           Sucesso                          Falha (excecao)
               │                              │
        Tem texto?                    Usa leitor secundario
        (alguma pagina                     (PyMuPDF)
         nao vazia)
               │
      ┌─────────┴─────────┐
      Sim                 Nao
      │                   │
      │          Usa leitor secundario
      │               (PyMuPDF)
      │
OCR habilitado? (enable_ocr=True)
      │
  ┌───┴───┐
  Sim     Nao
  │       │
  │    Retorna paginas
  │    com texto direto
  │
Para cada pagina:
  Tem >= 25 chars?
  ┌──────┴──────┐
  Sim          Nao
  │             │
  Retorna     Converte para imagem
  como esta   (PyMuPDF Pixmap 2x)
                │
              PIL Image RGB
                │
              Tesseract OCR
                │
              Mescla com texto
              original (se houver)
```

**Campo `source` no `PageText`** indica qual metodo foi usado:
- `"plumber"` — texto direto via pdfplumber
- `"fitz"` — texto direto via PyMuPDF
- `"plumber+ocr"` — pdfplumber + Tesseract OCR
- `"fitz+ocr"` — PyMuPDF + Tesseract OCR

---

### 13.6 Resumo das Bibliotecas por Papel

| Biblioteca | Papel no projeto | Converte para imagem? |
|------------|-----------------|----------------------|
| `pdfplumber` | Extrai texto e tabelas diretamente do PDF | Nao |
| `PyMuPDF (fitz)` | Extrai texto direto; tambem renderiza paginas como imagem para OCR | Nao (texto) / Sim (OCR) |
| `pytesseract` | Reconhece texto em imagens via Tesseract | — (recebe imagem) |
| `Pillow (PIL)` | Converte Pixmap do PyMuPDF em imagem RGB para o Tesseract | — (manipulacao) |
| `pdf2image` | Converte PDF em imagens PNG (usado apenas no pipeline Donut) | Sim |
| `transformers` | Executa o modelo Donut para extracao por IA | — (recebe imagem) |
| `pypdf` | Mescla e divide arquivos PDF (PDFToolkit) | Nao |