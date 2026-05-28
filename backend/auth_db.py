"""User authentication database — PostgreSQL, MySQL or SQLite."""
from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

import psycopg

load_dotenv(Path(__file__).resolve().parent / ".env")

AUTH_BACKEND  = os.getenv("AUTH_DB_BACKEND", "sqlite").lower()
AUTH_HOST     = os.getenv("AUTH_DB_HOST", "localhost")
AUTH_PORT     = int(os.getenv("AUTH_DB_PORT", 3306))
AUTH_NAME     = os.getenv("AUTH_DB_NAME", "Projeto oficial")
AUTH_USER     = os.getenv("AUTH_DB_USER", "root")
AUTH_PASSWORD = os.getenv("AUTH_DB_PASSWORD", "")
AUTH_SQLITE   = Path(os.getenv("AUTH_SQLITE_PATH", "./data/auth.db"))

# Rastreia qual backend está realmente sendo usado (pode mudar para sqlite se MySQL/PostgreSQL falhar)
_active_backend = AUTH_BACKEND


def _ph() -> str:
    return "%s" if _active_backend in {"mysql", "postgresql"} else "?"


@contextmanager
def _connection():
    global _active_backend

    if AUTH_BACKEND == "postgresql":
        conn = psycopg.connect(
            host=AUTH_HOST,
            port=AUTH_PORT,
            dbname=AUTH_NAME,
            user=AUTH_USER,
            password=AUTH_PASSWORD,
            connect_timeout=5,
        )
        _active_backend = "postgresql"
        try:
            yield conn
        finally:
            conn.close()
        return

    if AUTH_BACKEND == "mysql":
        try:
            import pymysql  # type: ignore
            conn = pymysql.connect(
                host=AUTH_HOST,
                port=AUTH_PORT,
                database=AUTH_NAME,
                user=AUTH_USER,
                password=AUTH_PASSWORD,
                charset="utf8mb4",
                autocommit=False,
            )
            _active_backend = "mysql"
            try:
                yield conn
            finally:
                conn.close()
            return
        except Exception as exc:
            print(f"[AUTH] MySQL indisponível ({exc}) — usando SQLite como fallback.")
            _active_backend = "sqlite"

    # SQLite fallback
    AUTH_SQLITE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(AUTH_SQLITE)
    try:
        yield conn
    finally:
        conn.close()


def ensure_users_table() -> None:
    with _connection() as conn:
        cur = conn.cursor()
        if _active_backend == "mysql":
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
                    email         VARCHAR(254) NOT NULL UNIQUE,
                    password_hash VARCHAR(200) NOT NULL,
                    created_at    DATETIME NOT NULL,
                    updated_at    DATETIME NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
        elif _active_backend == "postgresql":
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id            BIGSERIAL PRIMARY KEY,
                    email         VARCHAR(254) NOT NULL UNIQUE,
                    password_hash VARCHAR(200) NOT NULL,
                    created_at    TIMESTAMP NOT NULL,
                    updated_at    TIMESTAMP NOT NULL
                )
            """)
        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    email         TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at    TEXT NOT NULL,
                    updated_at    TEXT NOT NULL
                )
            """)
        conn.commit()
        cur.close()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
    return f"pbkdf2:sha256:{salt}:{dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, _, salt, stored_hex = stored.split(":")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
        return dk.hex() == stored_hex
    except Exception:
        return False


def create_user(email: str, password: str) -> dict:
    now = datetime.utcnow()
    ph = hash_password(password)
    p = _ph()
    now_val = now if _active_backend in {"mysql", "postgresql"} else now.isoformat()
    with _connection() as conn:
        cur = conn.cursor()
        if _active_backend == "postgresql":
            cur.execute(
                f"INSERT INTO users (email, password_hash, created_at, updated_at) VALUES ({p},{p},{p},{p}) RETURNING id",
                (email.lower(), ph, now_val, now_val),
            )
            user_id = cur.fetchone()[0]
        else:
            cur.execute(
                f"INSERT INTO users (email, password_hash, created_at, updated_at) VALUES ({p},{p},{p},{p})",
                (email.lower(), ph, now_val, now_val),
            )
            user_id = cur.lastrowid
        conn.commit()
        cur.close()
    return {"id": user_id, "email": email.lower()}


def get_user_by_email(email: str) -> Optional[dict]:
    p = _ph()
    with _connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT id, email, password_hash FROM users WHERE email = {p}",
            (email.lower(),),
        )
        row = cur.fetchone()
        cur.close()
    if not row:
        return None
    return {"id": row[0], "email": row[1], "password_hash": row[2]}


def email_exists(email: str) -> bool:
    return get_user_by_email(email) is not None


def sync_user_to_app_db(user_id: int, email: str) -> None:
    """Ensure the authenticated user exists in the main application database."""
    from backend import database as app_database

    app_database.ensure_schema()
    username = email.split("@", 1)[0] or email

    with app_database.get_connection() as conn:
        with app_database.get_cursor(conn) as cur:
            if app_database.DB_BACKEND == "sqlite":
                cur.execute(
                    """
                    INSERT OR REPLACE INTO auth_user (id, username, email)
                    VALUES (?, ?, ?)
                    """,
                    (user_id, username, email.lower()),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO auth_user (id, username, email)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        username = EXCLUDED.username,
                        email = EXCLUDED.email
                    """,
                    (user_id, username, email.lower()),
                )
            conn.commit()
