# ProjetoIntegrador05

Sistema para upload de PDFs juridicos, extracao de texto, classificacao, analise simples e visualizacao no dashboard.

## Stack atual

- Frontend: React 18, TypeScript 5, Vite 5, Tailwind e Zustand.
- Backend: FastAPI, Uvicorn, PostgreSQL via `psycopg`, leitura de `.env` e extração com `pdfplumber`, `PyMuPDF` e OCR opcional.
- Banco: PostgreSQL `Projeto_integrador`.

## Como rodar

1. Garanta que o arquivo `backend/.env` exista com as credenciais do PostgreSQL.

2. Instale as dependências do backend:

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
```

3. Inicie o backend:

```powershell
.\.venv\Scripts\python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

4. Inicie o frontend:

```powershell
cd frontend
npm install
npm run dev
```

Ou use o arquivo [start_all.bat](start_all.bat) na raiz do projeto.

## Endpoints principais

- `GET /health`: verifica se a API está no ar.
- `GET /api/documents/`: lista documentos.
- `POST /api/documents/`: envia PDF em multipart form.
- `GET /api/documents/{id}`: consulta os detalhes de um documento.

## Estrutura atual

```text
api/        # FastAPI em uso
frontend/   # React/Vite
backend/    # apenas configuração de ambiente (.env)
media/      # uploads salvos
```
