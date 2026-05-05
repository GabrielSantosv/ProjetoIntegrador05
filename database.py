"""PostgreSQL connection helpers for the PDF processing scripts."""
from __future__ import annotations

import os
from contextlib import contextmanager

from dotenv import load_dotenv

try:
    import psycopg
except ImportError:  # pragma: no cover - fallback for older environments.
    psycopg = None

try:
    import psycopg2
except ImportError:  # pragma: no cover - fallback for environments using psycopg v3.
    psycopg2 = None


load_dotenv()


def get_connection():
    """Create a new PostgreSQL connection using environment variables."""
    if psycopg is not None:
        return psycopg.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )

    if psycopg2 is not None:
        return psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )

    raise RuntimeError("Nenhum driver PostgreSQL disponível. Instale psycopg[binary] ou psycopg2-binary.")


@contextmanager
def get_cursor():
    """Yield a cursor and cleanly close connection resources afterwards."""
    connection = get_connection()
    cursor = connection.cursor()
    try:
        yield cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()