from fastapi import APIRouter, HTTPException, Response, Depends
from pydantic import BaseModel

from backend import database
from backend.auth_security import get_current_user


router = APIRouter(prefix="/api/folders", tags=["folders"], dependencies=[Depends(get_current_user)])


class FolderCreate(BaseModel):
    name: str


@router.get("/")
async def list_folders(current_user: dict = Depends(get_current_user)):
    database.ensure_schema()
    return database.list_folders(current_user["id"])


@router.post("/")
async def create_folder(payload: FolderCreate, current_user: dict = Depends(get_current_user)):
    database.ensure_schema()
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nome da pasta e obrigatorio")
    return database.create_folder(name, current_user["id"])


@router.get("/{folder_id}")
async def get_folder(folder_id: str, current_user: dict = Depends(get_current_user)):
    database.ensure_schema()
    folder = database.get_folder(folder_id, owner_id=current_user["id"])
    if not folder:
        raise HTTPException(status_code=404, detail="Pasta nao encontrada")
    return folder


@router.delete("/{folder_id}")
async def delete_folder(folder_id: str, current_user: dict = Depends(get_current_user)):
    database.ensure_schema()
    deleted = database.delete_folder(folder_id, current_user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Pasta nao encontrada")
    return Response(status_code=204)
