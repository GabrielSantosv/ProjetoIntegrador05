# Projeto Integrador (PI) - Automacao da Analise de Documentos para Compra de Precatorios

## 1. Visao Geral
Este Projeto Integrador tem como objetivo demonstrar como Inteligencia Artificial pode automatizar parte da analise documental no processo de compra de precatorios.

O foco principal e comparar duas abordagens de extracao de dados em documentos PDF:

- OCR tradicional com regras (Tesseract + Regex)
- Modelo de IA Donut (Vision Encoder-Decoder)

## Estrutura do Projeto
A organização de arquivos foi atualizada para suportar um fluxo mais claro de dados, scripts e resultados:

```
Projeto raiz/
├── 01_DATA_INPUT/
│   ├── 01_TJSP/
│   ├── 02_TRT15/
│   ├── 03_CNDT/
│   ├── 04_FEDERAL/
│   └── 05_DOCUMENTOS/
├── 02_SCRIPTS/
│   ├── benchmark_bibliotecas.py
│   ├── extrator_principal.py
│   ├── ia_huggingface.py
│   └── Extracao_Atestados_Donut_OCR_Organizado_corrigido (1) (1).ipynb
├── 03_OUTPUT/
│   ├── analise_consolidada.xlsx
│   ├── relatorio_benchmark.csv
│   └── txt_extraidos/
└── requirements.txt
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