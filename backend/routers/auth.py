from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from backend.auth_db import ensure_users_table, create_user, get_user_by_email, verify_password, email_exists
from backend.auth_security import create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str


@router.post("/register/", status_code=201)
async def register(body: RegisterRequest):
    try:
        ensure_users_table()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Banco de dados indisponível: {exc}")

    if not body.email or "@" not in body.email:
        raise HTTPException(status_code=400, detail="E-mail inválido.")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="A senha deve ter pelo menos 6 caracteres.")

    try:
        if email_exists(body.email):
            raise HTTPException(status_code=409, detail="E-mail já cadastrado.")
        user = create_user(body.email, body.password)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao criar usuário: {exc}")

    access = create_access_token(user["id"], user["email"])
    return {"access": access, "refresh": "", "email": user["email"]}


@router.post("/token/")
async def login(body: LoginRequest):
    try:
        ensure_users_table()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Banco de dados indisponível: {exc}")

    try:
        user = get_user_by_email(body.email)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Erro ao consultar banco: {exc}")

    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos.",
        )

    access = create_access_token(user["id"], user["email"])
    return {"access": access, "refresh": "", "email": user["email"]}


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user
