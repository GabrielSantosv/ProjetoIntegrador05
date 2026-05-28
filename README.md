# Projeto Integrador 05

Sistema web feito para organizar e analisar documentos juridicos em PDF.

A ideia do projeto e ajudar no envio dos arquivos, extracao das informacoes principais e visualizacao dos dados em uma tela simples, com filtros, detalhes dos documentos e acompanhamento por dashboard.

## O que o sistema faz

- Cadastro e login de usuarios.
- Upload de documentos em PDF.
- Organizacao dos arquivos por pastas.
- Extracao de texto e dados dos documentos.
- Consulta de RGs e processos.
- Visualizacao dos documentos enviados.
- Dashboard com informacoes resumidas.

## Tecnologias

**Backend**

- Python
- FastAPI
- Uvicorn
- PostgreSQL
- Bibliotecas para leitura de PDF e OCR

**Frontend**

- React
- TypeScript
- Vite
- Tailwind CSS

## Como rodar o projeto

Na raiz do projeto, execute:

```powershell
.\scripts\start-dev.ps1
```

Esse script inicia o backend e o frontend. Depois disso, acesse:

```text
http://127.0.0.1:5173
```

A API fica disponivel em:

```text
http://127.0.0.1:8000
```

## Rodando manualmente

Caso prefira iniciar separado:

### Backend

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

## Configuracao

O backend usa variaveis de ambiente. Existe um exemplo em:

```text
backend/.env.example
```

Crie um arquivo `.env` dentro da pasta `backend` seguindo esse modelo e ajuste os dados do banco conforme o seu ambiente.

## Estrutura do projeto

```text
backend/    API, rotas, banco de dados e regras do sistema
frontend/   telas da aplicacao
media/      arquivos enviados pelos usuarios
docs/       diagramas e documentacao
scripts/    scripts para iniciar e parar o projeto
tests/      testes automatizados
```

## Observacao

Para PDFs escaneados, a extracao completa depende de OCR. No Windows, o projeto pode usar Tesseract ou o OCR nativo quando estiver disponivel.
