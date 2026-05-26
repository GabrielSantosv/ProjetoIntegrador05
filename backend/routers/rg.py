from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Response, Query
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Optional
import asyncio
import os
import re
import uuid
import unicodedata
from pathlib import Path

from backend import database
from backend.rg_service import process_rg_document

router = APIRouter(prefix="/api/rg", tags=["rg"])

MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "./media"))
RG_DIR = MEDIA_ROOT / "rg"
RG_DIR.mkdir(parents=True, exist_ok=True)

_ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp", ".pdf"}


def _safe_filename(filename: str) -> str:
    stem = Path(filename).stem
    suffix = Path(filename).suffix.lower() or ".png"
    normalized = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", normalized).strip("._-") or "rg"
    return f"{uuid.uuid4().hex}_{slug[:60]}{suffix}"


async def _process_rg_async(rg_id: int, path1: str, path2: Optional[str]) -> None:
    try:
        print(f"[RG] processing id={rg_id}")
        fields, method, raw_text, lado_detectado = await asyncio.to_thread(
            process_rg_document, path1, path2
        )

        if not any(fields.values()):
            database.update_rg(rg_id, status="failed",
                               error_message="Não foi possível extrair informações do documento.")
            return

        database.update_rg(rg_id, status="done", ocr_method=method,
                           raw_text=raw_text, lado_detectado=lado_detectado, **fields)
        print(f"[RG] done id={rg_id} method={method} lado={lado_detectado}")
    except Exception as exc:
        import traceback
        print(f"[RG] error id={rg_id}: {exc}\n{traceback.format_exc()}")
        database.update_rg(rg_id, status="failed", error_message=str(exc))


@router.post("/")
async def upload_rg(folder_id: str = Form(""), files: List[UploadFile] = File(...)) -> JSONResponse:
    if not files:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado")

    database.ensure_schema()
    if folder_id and not database.get_folder(folder_id):
        raise HTTPException(status_code=404, detail="Pasta nao encontrada")

    saved: list[tuple[str, str]] = []  # (path, original_filename)
    for upload in files[:2]:
        if not upload.filename:
            continue
        if Path(upload.filename).suffix.lower() not in _ALLOWED_EXTENSIONS:
            continue
        safe_name = _safe_filename(upload.filename)
        save_path = RG_DIR / safe_name
        with open(save_path, "wb") as f:
            f.write(await upload.read())
        saved.append((str(save_path), upload.filename))

    if not saved:
        raise HTTPException(status_code=400, detail="Envie uma imagem (PNG, JPG, BMP) ou PDF")

    path1, fname1 = saved[0]
    path2_str = saved[1][0] if len(saved) > 1 else ""

    rg_id = database.create_rg(
        original_filename=fname1,
        image_path=path1,
        image_path_verso=path2_str,
        folder_id=folder_id,
    )
    asyncio.create_task(_process_rg_async(rg_id, path1, path2_str or None))
    return JSONResponse({"id": rg_id, "status": "processing"}, status_code=201)


@router.get("/")
async def list_rgs(folder_id: str | None = Query(None)):
    database.ensure_schema()
    return database.list_rgs(folder_id=folder_id)


@router.get("/{rg_id}")
async def get_rg(rg_id: int):
    database.ensure_schema()
    doc = database.get_rg(rg_id)
    if not doc:
        raise HTTPException(status_code=404, detail="RG não encontrado")
    return doc


def _serve_image(path_str: str):
    path = Path(path_str)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Imagem não encontrada no servidor")
    suffix = path.suffix.lower()
    media_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".bmp": "image/bmp"}
    return FileResponse(str(path), media_type=media_types.get(suffix, "image/png"))


def _get_pdf_preview(pdf_path: Path) -> Path:
    """Return a cached PNG preview for a PDF, generating it if needed."""
    preview = pdf_path.parent / (pdf_path.stem + "_page.png")
    if not preview.exists():
        from backend.rg_service import _pdf_to_image
        rendered = _pdf_to_image(str(pdf_path), zoom=2.0)
        preview = Path(rendered)
    return preview


@router.get("/{rg_id}/image")
async def get_rg_image(rg_id: int):
    doc = database.get_rg(rg_id)
    if not doc:
        raise HTTPException(status_code=404, detail="RG não encontrado")
    path = Path(doc["image_path"])
    if path.suffix.lower() == ".pdf":
        preview = _get_pdf_preview(path)
        if not preview.exists():
            raise HTTPException(status_code=404, detail="Preview do PDF não disponível")
        return FileResponse(str(preview), media_type="image/png")
    return _serve_image(doc["image_path"])


@router.get("/{rg_id}/image_verso")
async def get_rg_image_verso(rg_id: int):
    doc = database.get_rg(rg_id)
    if not doc:
        raise HTTPException(status_code=404, detail="RG não encontrado")
    if not doc.get("image_path_verso"):
        raise HTTPException(status_code=404, detail="Imagem verso não disponível")
    return _serve_image(doc["image_path_verso"])


@router.delete("/{rg_id}")
async def delete_rg(rg_id: int):
    database.ensure_schema()
    ok = database.delete_rg(rg_id)
    if not ok:
        raise HTTPException(status_code=404, detail="RG não encontrado")
    return Response(status_code=204)
