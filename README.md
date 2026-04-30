# MVP - Processamento de Documentos Juridicos

Sistema full stack para upload de PDFs juridicos, extracao de dados, classificacao, parecer via HuggingFace e exportacao para Excel/Word.

## Stack

- Frontend: React 18, TypeScript 5, Vite 5, Tailwind, shadcn/ui base, Lucide, Zustand, TanStack Query, Axios, React Hook Form, Zod, React Router e Recharts.
- Backend: Django 5, DRF, Simple JWT, CORS, Celery, Redis, PostgreSQL, pdfplumber, PyMuPDF, Tesseract OCR, openpyxl e python-docx.
- IA/NLP: HuggingFace Inference API para Mistral, BERTimbau e LenerBR. Sem token, o MVP usa fallbacks deterministicos para continuar funcionando.

## Como rodar

1. Crie os arquivos de ambiente:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

2. Se você tiver Postgres e Redis, suba-os com:

```bash
docker compose up -d postgres redis
```

Se você ainda não tem Postgres, pode deixar `backend/.env` com `DATABASE_URL=` e o backend será executado com SQLite local.

Tambem e possivel subir todos os servicos com Docker:

```bash
docker compose up --build
```

3. Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

4. Worker Celery, em outro terminal:

```bash
cd backend
.venv\Scripts\activate
celery -A legal_docs worker -l info
```

5. Frontend:

```bash
cd frontend
npm install
npm run dev
```

Abra `http://localhost:5173` e entre com o superusuario criado no Django.

## Endpoints principais

- `POST /api/auth/token/`: obtem JWT.
- `GET /api/documents/`: lista documentos do usuario autenticado.
- `POST /api/documents/`: envia PDF em multipart form.
- `GET /api/documents/{id}/`: consulta resultado.
- `GET /api/documents/{id}/export_excel/`: exporta XLSX.
- `GET /api/documents/{id}/export_word/`: exporta DOCX.
- `GET /api/documents/summary/`: metricas para dashboard.
- `GET /api/docs/`: Swagger/OpenAPI.

## Observacoes de OCR e IA

- O OCR depende de `tesseract-ocr`, idioma `por` e `poppler-utils`. O Dockerfile do backend ja instala esses pacotes.
- `pdfplumber` extrai texto e coordenadas. Se o texto for insuficiente, o pipeline tenta `PyMuPDF`; se ainda falhar, tenta OCR com Tesseract.
- Configure `HUGGINGFACE_API_TOKEN` em `backend/.env` para habilitar Mistral, BERTimbau e NER via HTTP.

## Qualidade

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

Backend:

```bash
cd backend
python manage.py check
python manage.py test
```

## Estrutura

```text
backend/
  documents/
    services/
      pdf.py          # extracao pdfplumber, PyMuPDF e OCR
      parser.py       # campos juridicos e risco
      classifier.py   # tipo de certidao
      ner.py          # PESSOA, LOCAL, TEMPO
      ai.py           # parecer via Mistral
      exporters.py    # Excel e Word
frontend/
  src/
    components/
    pages/
    lib/api.ts
    store/auth.ts
```
