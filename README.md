# ProjetoIntegrador05

Sistema para upload de PDFs jurídicos, extração de texto, classificação, análise de risco e visualização em dashboard.

## Stack

- **Frontend:** React 18, TypeScript 5, Vite 5, Tailwind CSS e Zustand.
- **Backend:** FastAPI, Uvicorn, Python 3.11+, extração com `pdfplumber`, `PyMuPDF` e OCR opcional (Tesseract).
- **Banco:** PostgreSQL por padrão, usando o banco `Projeto oficial`.

## Como rodar

A forma mais simples é usar o script na raiz:

```powershell
.\start_all.bat
```

O script verifica dependências, instala o que falta e abre o projeto em `http://localhost:5173`.

### Inicialização manual

1. Configure `backend/.env` (copie de `backend/.env.example`):

```env
DB_BACKEND=postgresql
DB_NAME="Projeto oficial"
DB_USER=postgres
DB_PASSWORD=postgres
MEDIA_ROOT=./media
OCR_LANGUAGE=por+eng
```

2. Instale as dependências Python e inicie o backend:

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

3. Instale as dependências do frontend e inicie:

```powershell
cd frontend
npm install
npm run dev
```

## OCR para PDFs escaneados

PDFs com texto selecionável são processados automaticamente com `pdfplumber`/`PyMuPDF`.
PDFs escaneados (apenas imagem) precisam do Tesseract OCR instalado no Windows.
Após instalar, configure em `backend/.env`:

```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
OCR_LANGUAGE=por+eng
```

Sem Tesseract, o sistema salva o PDF e usa classificação por nome, mas extração completa de texto,
entidades e análise jurídica ficam limitados.

## Endpoints principais

- `GET /health` — verifica se a API está no ar.
- `GET /api/documents/` — lista documentos.
- `POST /api/documents/` — envia PDF em multipart form.
- `GET /api/documents/{id}` — consulta detalhes de um documento.

## Estrutura

```text
backend/        # FastAPI (main.py, services.py, database.py, routers/)
frontend/       # React/Vite (src/, index.html, vite.config.mjs)
data/           # arquivos locais temporários e banco SQLite legado, se usado
media/          # uploads salvos (documents/, rg/, processes/)
docs/           # diagramas e documentação
tests/          # testes automatizados
01_DATA_INPUT/  # PDFs de exemplo para testes manuais
scripts/        # scripts de desenvolvimento (start-dev.ps1, stop-dev.ps1)
```
