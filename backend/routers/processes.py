from fastapi import APIRouter, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
import asyncio
import os
import re
import unicodedata
import uuid
from pathlib import Path
from urllib.parse import quote

from backend import database
from backend.process_service import analyze_process_text
from backend.services import extract_pdf_text


router = APIRouter(prefix="/api/processes", tags=["processes"])

MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "./media"))
PROCESS_DIR = MEDIA_ROOT / "processes"
PROCESS_DIR.mkdir(parents=True, exist_ok=True)


def _safe_storage_filename(filename: str) -> str:
    original = Path(filename).name
    suffix = Path(original).suffix.lower() or ".pdf"
    stem = Path(original).stem.strip() or "processo"
    normalized = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", normalized).strip("._-") or "processo"
    return f"{uuid.uuid4().hex}_{slug[:80]}{suffix}"


def _preview_url(process_doc_id: int) -> str:
    return f"/api/processes/{process_doc_id}/file"


def _to_response(doc: dict) -> dict:
    return {
        "id": doc["id"],
        "folder_id": doc["folder_id"],
        "process_number": doc["process_number"],
        "source_document_id": doc.get("source_document_id"),
        "original_filename": doc["original_filename"],
        "file_url": f"/media/processes/{quote(Path(doc['file_path']).name)}",
        "preview_url": _preview_url(doc["id"]),
        "status": doc["status"],
        "extraction_method": doc.get("extraction_method", ""),
        "analysis_data": doc.get("analysis_data") or {},
        "summary": doc.get("summary", ""),
        "error_message": doc.get("error_message", ""),
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
    }


async def _process_case_pdf_async(process_doc_id: int, file_path: str, process_number: str) -> None:
    try:
        print(f"[PROCESS_CASE] started id={process_doc_id} process={process_number} file={file_path}", flush=True)
        if not Path(file_path).exists():
            database.update_process_document(
                process_doc_id,
                status="failed",
                error_message=f"Arquivo nao encontrado em disco: {file_path}",
            )
            return

        text, method = await asyncio.to_thread(extract_pdf_text, file_path)
        if method == "failed" or not text.strip() or text == "Failed to extract text":
            message = (
                "Nao foi possivel extrair texto selecionavel deste PDF processual. "
                "Verifique se o arquivo e uma imagem digitalizada e se o OCR esta configurado."
            )
            database.update_process_document(
                process_doc_id,
                status="needs_ocr",
                extraction_method=method,
                extracted_text=text or "",
                analysis_data={"summary": message, "timeline": [], "important_decisions": []},
                summary=message,
                error_message=message,
            )
            return

        analysis = await asyncio.to_thread(analyze_process_text, text, process_number)
        database.update_process_document(
            process_doc_id,
            status="done",
            extraction_method=method,
            extracted_text=text,
            analysis_data=analysis,
            summary=analysis.get("summary", ""),
            error_message="",
        )
        print(f"[PROCESS_CASE] done id={process_doc_id} method={method}", flush=True)
    except Exception as exc:
        import traceback
        print(f"[PROCESS_CASE] error id={process_doc_id}: {exc}\n{traceback.format_exc()}", flush=True)
        database.update_process_document(process_doc_id, status="failed", error_message=str(exc))


@router.get("/")
async def list_process_documents(
    folder_id: str | None = Query(None),
    process_number: str | None = Query(None),
):
    database.ensure_schema()
    return [_to_response(doc) for doc in database.list_process_documents(folder_id, process_number)]


@router.post("/")
async def upload_process_document(
    folder_id: str = Form(...),
    process_number: str = Form(...),
    source_document_id: int | None = Form(None),
    file: UploadFile = File(...),
) -> JSONResponse:
    database.ensure_schema()
    if not database.get_folder(folder_id):
        raise HTTPException(status_code=404, detail="Pasta nao encontrada")
    if not process_number.strip():
        raise HTTPException(status_code=400, detail="Numero do processo e obrigatorio")
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nome do arquivo ausente")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Envie um arquivo PDF")

    safe_name = _safe_storage_filename(file.filename)
    file_path = PROCESS_DIR / safe_name
    content = await file.read()
    file_path.write_bytes(content)

    process_doc_id = database.create_process_document(
        folder_id=folder_id,
        process_number=process_number.strip(),
        source_document_id=source_document_id,
        original_filename=file.filename,
        file_path=str(file_path),
    )
    asyncio.create_task(_process_case_pdf_async(process_doc_id, str(file_path), process_number.strip()))
    doc = database.get_process_document(process_doc_id)
    return JSONResponse(_to_response(doc), status_code=201)


@router.get("/{process_doc_id}")
async def get_process_document(process_doc_id: int):
    database.ensure_schema()
    doc = database.get_process_document(process_doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Analise de processo nao encontrada")
    return _to_response(doc)


@router.get("/{process_doc_id}/file")
async def get_process_document_file(process_doc_id: int):
    database.ensure_schema()
    doc = database.get_process_document(process_doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Analise de processo nao encontrada")
    path = Path(doc["file_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Arquivo fisico nao encontrado no servidor")
    return FileResponse(
        str(path),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{quote(path.name)}"'},
    )


@router.delete("/{process_doc_id}")
async def delete_process_document(process_doc_id: int):
    database.ensure_schema()
    deleted = database.delete_process_document(process_doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Analise de processo nao encontrada")
    return Response(status_code=204)
