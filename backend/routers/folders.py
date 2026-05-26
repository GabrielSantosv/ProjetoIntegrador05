from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from backend import database


router = APIRouter(prefix="/api/folders", tags=["folders"])


class FolderCreate(BaseModel):
    name: str


@router.get("/")
async def list_folders():
    database.ensure_schema()
    return database.list_folders()


@router.post("/")
async def create_folder(payload: FolderCreate):
    database.ensure_schema()
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nome da pasta e obrigatorio")
    return database.create_folder(name)


@router.get("/{folder_id}")
async def get_folder(folder_id: str):
    database.ensure_schema()
    folder = database.get_folder(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Pasta nao encontrada")
    return folder


@router.delete("/{folder_id}")
async def delete_folder(folder_id: str):
    database.ensure_schema()
    deleted = database.delete_folder(folder_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Pasta nao encontrada")
    return Response(status_code=204)
