import psycopg
import sqlite3
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from contextlib import contextmanager
import os
from pathlib import Path
from dotenv import load_dotenv
from decimal import Decimal
import uuid

load_dotenv(Path(__file__).resolve().parent / '.env')

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', 5432))
DB_NAME = os.getenv('DB_NAME', 'Projeto_integrador')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'admin')
DB_BACKEND = os.getenv('DB_BACKEND', 'sqlite').lower()
SQLITE_PATH = Path(os.getenv('SQLITE_PATH', './data/app.db'))


def _json_value(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return value


def _risk_value(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        value = float(value)
    value = float(value)
    return round(value * 100, 2) if 0 < value <= 1 else round(value, 2)


def _frontend_status(status: str) -> str:
    return 'done' if status == 'completed' else status


@contextmanager
def get_connection():
    if DB_BACKEND == 'sqlite':
        SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
        return

    conn = psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        connect_timeout=5,
    )
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_cursor(conn):
    cur = conn.cursor()
    try:
        yield cur
    finally:
        cur.close()


def ensure_schema() -> None:
    """Create the minimal tables used by this standalone FastAPI app."""
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            if DB_BACKEND == 'sqlite':
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS auth_user (
                        id integer PRIMARY KEY,
                        username text NOT NULL,
                        email text DEFAULT ''
                    )
                """)
                cur.execute("""
                    INSERT OR IGNORE INTO auth_user (id, username, email)
                    VALUES (1, 'demo', 'demo@example.com')
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS folders (
                        id text PRIMARY KEY,
                        name text NOT NULL,
                        created_at text NOT NULL,
                        updated_at text NOT NULL
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS documents_document (
                        id integer PRIMARY KEY AUTOINCREMENT,
                        owner_id integer,
                        title text NOT NULL,
                        file text NOT NULL,
                        status text NOT NULL,
                        document_type text,
                        extracted_text text,
                        extracted_data text DEFAULT '{}',
                        entities text DEFAULT '[]',
                        legal_opinion text,
                        risk_score real DEFAULT 0,
                        error_message text,
                        created_at text NOT NULL,
                        updated_at text NOT NULL
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS rg_documents (
                        id integer PRIMARY KEY AUTOINCREMENT,
                        original_filename text NOT NULL,
                        image_path text NOT NULL,
                        status text NOT NULL DEFAULT 'processing',
                        ocr_method text DEFAULT '',
                        nome text DEFAULT '',
                        rg text DEFAULT '',
                        cpf text DEFAULT '',
                        data_nascimento text DEFAULT '',
                        municipio text DEFAULT '',
                        nome_mae text DEFAULT '',
                        nome_pai text DEFAULT '',
                        raw_text text DEFAULT '',
                        error_message text DEFAULT '',
                        created_at text NOT NULL,
                        updated_at text NOT NULL,
                        image_path_verso text DEFAULT '',
                        lado_detectado text DEFAULT ''
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS process_documents (
                        id integer PRIMARY KEY AUTOINCREMENT,
                        folder_id text NOT NULL DEFAULT '',
                        process_number text NOT NULL,
                        source_document_id integer,
                        original_filename text NOT NULL,
                        file_path text NOT NULL,
                        status text NOT NULL DEFAULT 'processing',
                        extraction_method text DEFAULT '',
                        extracted_text text DEFAULT '',
                        analysis_data text DEFAULT '{}',
                        summary text DEFAULT '',
                        error_message text DEFAULT '',
                        created_at text NOT NULL,
                        updated_at text NOT NULL
                    )
                """)
                for col_sql in [
                    "ALTER TABLE documents_document ADD COLUMN folder_id text DEFAULT ''",
                    "ALTER TABLE rg_documents ADD COLUMN image_path_verso text DEFAULT ''",
                    "ALTER TABLE rg_documents ADD COLUMN lado_detectado text DEFAULT ''",
                    "ALTER TABLE rg_documents ADD COLUMN folder_id text DEFAULT ''",
                ]:
                    try:
                        cur.execute(col_sql)
                    except Exception:
                        pass
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_documents_folder_id
                    ON documents_document(folder_id)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_rg_documents_folder_id
                    ON rg_documents(folder_id)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_process_documents_folder_process
                    ON process_documents(folder_id, process_number)
                """)
                conn.commit()
                return

            cur.execute("""
                CREATE TABLE IF NOT EXISTS auth_user (
                    id integer PRIMARY KEY,
                    username varchar(150) NOT NULL,
                    email varchar(254) DEFAULT ''
                )
            """)
            cur.execute("""
                INSERT INTO auth_user (id, username, email)
                VALUES (1, 'demo', 'demo@example.com')
                ON CONFLICT (id) DO NOTHING
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS folders (
                    id varchar(64) PRIMARY KEY,
                    name varchar(255) NOT NULL,
                    created_at timestamp NOT NULL,
                    updated_at timestamp NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS documents_document (
                    id bigserial PRIMARY KEY,
                    owner_id integer REFERENCES auth_user(id),
                    title varchar(255) NOT NULL,
                    file varchar(500) NOT NULL,
                    status varchar(50) NOT NULL,
                    document_type varchar(100),
                    extracted_text text,
                    extracted_data jsonb DEFAULT '{}'::jsonb,
                    entities jsonb DEFAULT '[]'::jsonb,
                    legal_opinion text,
                    risk_score numeric DEFAULT 0,
                    error_message text,
                    created_at timestamp NOT NULL,
                    updated_at timestamp NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS rg_documents (
                    id bigserial PRIMARY KEY,
                    original_filename varchar(500) NOT NULL,
                    image_path varchar(500) NOT NULL,
                    status varchar(50) NOT NULL DEFAULT 'processing',
                    ocr_method varchar(50) DEFAULT '',
                    nome text DEFAULT '',
                    rg varchar(30) DEFAULT '',
                    cpf varchar(20) DEFAULT '',
                    data_nascimento varchar(20) DEFAULT '',
                    municipio text DEFAULT '',
                    nome_mae text DEFAULT '',
                    nome_pai text DEFAULT '',
                    raw_text text DEFAULT '',
                    error_message text DEFAULT '',
                    created_at timestamp NOT NULL,
                    updated_at timestamp NOT NULL,
                    image_path_verso varchar(500) DEFAULT '',
                    lado_detectado varchar(20) DEFAULT ''
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS process_documents (
                    id bigserial PRIMARY KEY,
                    folder_id varchar(64) NOT NULL DEFAULT '',
                    process_number varchar(80) NOT NULL,
                    source_document_id bigint,
                    original_filename varchar(500) NOT NULL,
                    file_path varchar(500) NOT NULL,
                    status varchar(50) NOT NULL DEFAULT 'processing',
                    extraction_method varchar(80) DEFAULT '',
                    extracted_text text DEFAULT '',
                    analysis_data jsonb DEFAULT '{}'::jsonb,
                    summary text DEFAULT '',
                    error_message text DEFAULT '',
                    created_at timestamp NOT NULL,
                    updated_at timestamp NOT NULL
                )
            """)
            for col_sql in [
                "ALTER TABLE documents_document ADD COLUMN IF NOT EXISTS folder_id varchar(64) DEFAULT ''",
                "ALTER TABLE rg_documents ADD COLUMN IF NOT EXISTS image_path_verso varchar(500) DEFAULT ''",
                "ALTER TABLE rg_documents ADD COLUMN IF NOT EXISTS lado_detectado varchar(20) DEFAULT ''",
                "ALTER TABLE rg_documents ADD COLUMN IF NOT EXISTS folder_id varchar(64) DEFAULT ''",
            ]:
                try:
                    cur.execute(col_sql)
                except Exception:
                    pass
            cur.execute("CREATE INDEX IF NOT EXISTS idx_documents_folder_id ON documents_document(folder_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_rg_documents_folder_id ON rg_documents(folder_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_process_documents_folder_process ON process_documents(folder_id, process_number)")
            conn.commit()


def create_folder(name: str, folder_id: str | None = None) -> Dict[str, Any]:
    now = datetime.utcnow()
    folder_id = folder_id or uuid.uuid4().hex
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            if DB_BACKEND == 'sqlite':
                cur.execute("""
                    INSERT INTO folders (id, name, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (folder_id, name, now.isoformat(), now.isoformat()))
            else:
                cur.execute("""
                    INSERT INTO folders (id, name, created_at, updated_at)
                    VALUES (%s, %s, %s, %s)
                """, (folder_id, name, now, now))
            conn.commit()
    return {'id': folder_id, 'name': name, 'created_at': now.isoformat(), 'updated_at': now.isoformat()}


def list_folders() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            cur.execute("SELECT id, name, created_at, updated_at FROM folders ORDER BY created_at DESC")
            return [
                {
                    'id': row[0],
                    'name': row[1],
                    'created_at': row[2].isoformat() if hasattr(row[2], 'isoformat') else row[2],
                    'updated_at': row[3].isoformat() if hasattr(row[3], 'isoformat') else row[3],
                }
                for row in cur.fetchall()
            ]


def get_folder(folder_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            ph = "?" if DB_BACKEND == 'sqlite' else "%s"
            cur.execute(f"SELECT id, name, created_at, updated_at FROM folders WHERE id = {ph}", (folder_id,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                'id': row[0],
                'name': row[1],
                'created_at': row[2].isoformat() if hasattr(row[2], 'isoformat') else row[2],
                'updated_at': row[3].isoformat() if hasattr(row[3], 'isoformat') else row[3],
            }


def delete_folder(folder_id: str) -> bool:
    if not get_folder(folder_id):
        return False

    documents, _ = list_documents(limit=10000, offset=0, folder_id=folder_id)
    for doc in documents:
        delete_document(doc['id'])

    for rg in list_rgs(folder_id=folder_id):
        delete_rg(rg['id'])

    for process_doc in list_process_documents(folder_id=folder_id):
        delete_process_document(process_doc['id'])

    with get_connection() as conn:
        with get_cursor(conn) as cur:
            ph = "?" if DB_BACKEND == 'sqlite' else "%s"
            cur.execute(f"DELETE FROM folders WHERE id = {ph}", (folder_id,))
            conn.commit()
            return cur.rowcount > 0


def create_document(filename: str, file_path: str, extraction_method: str = 'hybrid', folder_id: str = '') -> int:
    """Create document record and return ID"""
    from datetime import datetime
    
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            now = datetime.utcnow()
            values = (
                filename, 
                file_path, 
                'processing', 
                'documentojuridico',
                '',  # extracted_text
                json.dumps({}),  # extracted_data as JSON
                json.dumps([]),  # entities as JSON array
                '',  # legal_opinion
                0,  # risk_score
                '',  # error_message
                now,  # created_at
                now,  # updated_at
                1,  # owner_id=1 (demo user)
                folder_id or '',
            )
            if DB_BACKEND == 'sqlite':
                cur.execute("""
                    INSERT INTO documents_document
                    (title, file, status, document_type, extracted_text, extracted_data, entities, legal_opinion, risk_score, error_message, created_at, updated_at, owner_id, folder_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, values)
                doc_id = cur.lastrowid
            else:
                cur.execute("""
                    INSERT INTO documents_document 
                    (title, file, status, document_type, extracted_text, extracted_data, entities, legal_opinion, risk_score, error_message, created_at, updated_at, owner_id, folder_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, values)
                doc_id = cur.fetchone()[0]
            conn.commit()
            return doc_id


def get_document(doc_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve document with all related data"""
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            placeholder = "?" if DB_BACKEND == 'sqlite' else "%s"
            cur.execute(f"""
                SELECT id, title, file, status, document_type,
                       extracted_text, extracted_data, entities, legal_opinion, risk_score,
                       error_message, created_at, updated_at, folder_id
                FROM documents_document
                WHERE id = {placeholder}
            """, (doc_id,))
            
            row = cur.fetchone()
            if not row:
                return None
            
            return {
                'id': row[0],
                'filename': row[1],  # title
                'file_path': row[2],  # file field contains path
                'status': _frontend_status(row[3]),
                'extraction_method': 'hybrid',  # Default method since not stored in Django
                'document_type': row[4],
                'extracted_text': row[5],
                'extracted_data': _json_value(row[6], {}),
                'entities': _json_value(row[7], []),
                'legal_opinion': row[8],
                'risk_score': _risk_value(row[9]),
                'error_message': row[10],
                'created_at': row[11].isoformat() if hasattr(row[11], 'isoformat') else row[11],
                'updated_at': row[12].isoformat() if hasattr(row[12], 'isoformat') else row[12],
                'folder_id': row[13] or '',
            }


def list_documents(limit: int = 50, offset: int = 0, folder_id: str | None = None) -> tuple[List[Dict[str, Any]], int]:
    """List documents with pagination"""
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            # Get total count
            ph = "?" if DB_BACKEND == 'sqlite' else "%s"
            params: list[Any] = []
            where = ""
            if folder_id is not None:
                where = f" WHERE folder_id = {ph}"
                params.append(folder_id)

            cur.execute(f"SELECT COUNT(*) FROM documents_document{where}", params)
            total = cur.fetchone()[0]
            
            # Get paginated results (extracted_data + entities included for ProcessosPage)
            if DB_BACKEND == 'sqlite':
                cur.execute(f"""
                    SELECT id, title, file, document_type, risk_score, status, created_at, updated_at, error_message,
                           extracted_data, entities, folder_id
                    FROM documents_document
                    {where}
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (*params, limit, offset))
            else:
                cur.execute("""
                    SELECT id, title, file, document_type, risk_score, status, created_at, updated_at, error_message,
                           extracted_data, entities, folder_id
                    FROM documents_document
                    """ + where + """
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, (*params, limit, offset))

            rows = cur.fetchall()
            documents = []
            for row in rows:
                documents.append({
                    'id': row[0],
                    'filename': row[1],
                    'file_path': row[2],
                    'document_type': row[3],
                    'risk_score': _risk_value(row[4]),
                    'status': _frontend_status(row[5]),
                    'created_at': row[6].isoformat() if hasattr(row[6], 'isoformat') else row[6],
                    'updated_at': row[7].isoformat() if hasattr(row[7], 'isoformat') else row[7],
                    'error_message': row[8] or '',
                    'extracted_data': _json_value(row[9], {}),
                    'entities': _json_value(row[10], []),
                    'folder_id': row[11] or '',
                })
            
            return documents, total


def get_summary(folder_id: str | None = None) -> Dict[str, Any]:
    """Return dashboard counters expected by the React frontend."""
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            ph = "?" if DB_BACKEND == 'sqlite' else "%s"
            params: list[Any] = []
            where = ""
            if folder_id is not None:
                where = f" WHERE folder_id = {ph}"
                params.append(folder_id)
            if DB_BACKEND == 'sqlite':
                cur.execute(f"""
                    SELECT
                        COUNT(*) AS total,
                        SUM(CASE WHEN status IN ('done', 'completed') THEN 1 ELSE 0 END) AS done,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed,
                        SUM(CASE WHEN status = 'needs_ocr' THEN 1 ELSE 0 END) AS needs_ocr,
                        SUM(CASE WHEN status IN ('pending', 'processing') THEN 1 ELSE 0 END) AS processing,
                        COALESCE(AVG(CASE WHEN status IN ('done', 'completed') THEN risk_score END), 0) AS avg_risk
                    FROM documents_document
                    {where}
                """, params)
                row = cur.fetchone()
                return {
                    'total': row[0],
                    'done': row[1] or 0,
                    'failed': row[2] or 0,
                    'needs_ocr': row[3] or 0,
                    'processing': row[4] or 0,
                    'avg_risk': _risk_value(row[5]),
                }

            cur.execute(f"""
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE status IN ('done', 'completed')) AS done,
                    COUNT(*) FILTER (WHERE status = 'failed') AS failed,
                    COUNT(*) FILTER (WHERE status = 'needs_ocr') AS needs_ocr,
                    COUNT(*) FILTER (WHERE status IN ('pending', 'processing')) AS processing,
                    COALESCE(AVG(risk_score) FILTER (WHERE status IN ('done', 'completed')), 0) AS avg_risk
                FROM documents_document
                {where}
            """, params)
            row = cur.fetchone()
            return {
                'total': row[0],
                'done': row[1],
                'failed': row[2],
                'needs_ocr': row[3],
                'processing': row[4],
                'avg_risk': _risk_value(row[5]),
            }


def update_document_status(doc_id: int, status: str, **kwargs) -> bool:
    """Update document status and optional fields"""
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            # Build dynamic update
            fields = ['status = %s', 'updated_at = %s']
            values = [status, datetime.now().isoformat() if DB_BACKEND == 'sqlite' else datetime.now()]
            
            if 'document_type' in kwargs:
                fields.append('document_type = %s')
                values.append(kwargs['document_type'])
            if 'extracted_text' in kwargs:
                fields.append('extracted_text = %s')
                values.append(kwargs['extracted_text'])
            if 'extracted_data' in kwargs:
                fields.append('extracted_data = %s')
                values.append(json.dumps(kwargs['extracted_data']))
            if 'entities' in kwargs:
                fields.append('entities = %s')
                values.append(json.dumps(kwargs['entities']))
            if 'legal_opinion' in kwargs:
                fields.append('legal_opinion = %s')
                values.append(kwargs['legal_opinion'])
            if 'risk_score' in kwargs:
                fields.append('risk_score = %s')
                values.append(kwargs['risk_score'])
            if 'error_message' in kwargs:
                fields.append('error_message = %s')
                values.append(kwargs['error_message'])
            
            values.append(doc_id)
            
            if DB_BACKEND == 'sqlite':
                query = f"UPDATE documents_document SET {', '.join(field.replace('%s', '?') for field in fields)} WHERE id = ?"
            else:
                query = f"UPDATE documents_document SET {', '.join(fields)} WHERE id = %s"
            cur.execute(query, values)
            conn.commit()
            return cur.rowcount > 0


# ─── RG CRUD ──────────────────────────────────────────────────────────────────

_RG_FIELDS = ["nome", "rg", "cpf", "data_nascimento", "municipio", "nome_mae", "nome_pai",
               "ocr_method", "raw_text", "error_message", "image_path_verso", "lado_detectado"]


def _rg_row_to_dict(row) -> Dict[str, Any]:
    return {
        "id": row[0],
        "original_filename": row[1],
        "image_path": row[2],
        "status": row[3],
        "ocr_method": row[4] or "",
        "nome": row[5] or "",
        "rg": row[6] or "",
        "cpf": row[7] or "",
        "data_nascimento": row[8] or "",
        "municipio": row[9] or "",
        "nome_mae": row[10] or "",
        "nome_pai": row[11] or "",
        "error_message": row[12] or "",
        "created_at": row[13].isoformat() if hasattr(row[13], "isoformat") else row[13],
        "updated_at": row[14].isoformat() if hasattr(row[14], "isoformat") else row[14],
        "image_path_verso": row[15] if len(row) > 15 else "",
        "lado_detectado": row[16] if len(row) > 16 else "",
        "folder_id": row[17] if len(row) > 17 else "",
    }


def create_rg(original_filename: str, image_path: str, image_path_verso: str = "", folder_id: str = "") -> int:
    now = datetime.utcnow()
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            if DB_BACKEND == "sqlite":
                cur.execute("""
                    INSERT INTO rg_documents
                    (original_filename, image_path, status, ocr_method, nome, rg, cpf,
                     data_nascimento, municipio, nome_mae, nome_pai, raw_text, error_message,
                     created_at, updated_at, image_path_verso, lado_detectado, folder_id)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (original_filename, image_path, "processing", "", "", "", "", "", "", "", "", "", "", now, now, image_path_verso, "", folder_id or ""))
                rg_id = cur.lastrowid
            else:
                cur.execute("""
                    INSERT INTO rg_documents
                    (original_filename, image_path, status, ocr_method, nome, rg, cpf,
                     data_nascimento, municipio, nome_mae, nome_pai, raw_text, error_message,
                     created_at, updated_at, image_path_verso, lado_detectado, folder_id)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id
                """, (original_filename, image_path, "processing", "", "", "", "", "", "", "", "", "", "", now, now, image_path_verso, "", folder_id or ""))
                rg_id = cur.fetchone()[0]
            conn.commit()
            return rg_id


def get_rg(rg_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            ph = "?" if DB_BACKEND == "sqlite" else "%s"
            cur.execute(f"""
                SELECT id, original_filename, image_path, status, ocr_method,
                       nome, rg, cpf, data_nascimento, municipio, nome_mae, nome_pai,
                       error_message, created_at, updated_at,
                       image_path_verso, lado_detectado, folder_id
                FROM rg_documents WHERE id = {ph}
            """, (rg_id,))
            row = cur.fetchone()
            return _rg_row_to_dict(row) if row else None


def list_rgs(folder_id: str | None = None) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            ph = "?" if DB_BACKEND == "sqlite" else "%s"
            params: list[Any] = []
            where = ""
            if folder_id is not None:
                where = f" WHERE folder_id = {ph}"
                params.append(folder_id)
            cur.execute(f"""
                SELECT id, original_filename, image_path, status, ocr_method,
                       nome, rg, cpf, data_nascimento, municipio, nome_mae, nome_pai,
                       error_message, created_at, updated_at,
                       image_path_verso, lado_detectado, folder_id
                FROM rg_documents
                {where}
                ORDER BY created_at DESC
            """, params)
            return [_rg_row_to_dict(row) for row in cur.fetchall()]


def update_rg(rg_id: int, status: str, **kwargs) -> bool:
    now = datetime.utcnow()
    allowed = set(_RG_FIELDS)
    sets, vals = ["status = %s", "updated_at = %s"], [status, now if DB_BACKEND != "sqlite" else now.isoformat()]
    for k, v in kwargs.items():
        if k in allowed:
            sets.append(f"{k} = %s")
            vals.append(v or "")
    vals.append(rg_id)
    if DB_BACKEND == "sqlite":
        query = "UPDATE rg_documents SET " + ", ".join(s.replace("%s", "?") for s in sets) + " WHERE id = ?"
    else:
        query = "UPDATE rg_documents SET " + ", ".join(sets) + " WHERE id = %s"
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            cur.execute(query, vals)
            conn.commit()
            return cur.rowcount > 0


def delete_rg(rg_id: int) -> bool:
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            ph = "?" if DB_BACKEND == "sqlite" else "%s"
            cur.execute(f"SELECT image_path, image_path_verso FROM rg_documents WHERE id = {ph}", (rg_id,))
            row = cur.fetchone()
            if not row:
                return False
            try:
                from pathlib import Path as _Path
                for img_path in [row[0], row[1] if len(row) > 1 else ""]:
                    if img_path:
                        p = _Path(img_path)
                        if p.exists():
                            p.unlink()
            except Exception:
                pass
            cur.execute(f"DELETE FROM rg_documents WHERE id = {ph}", (rg_id,))
            conn.commit()
            return cur.rowcount > 0


def delete_document(doc_id: int) -> bool:
    """Delete document row and remove file from filesystem if present"""
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            # fetch stored file path
            placeholder = "?" if DB_BACKEND == 'sqlite' else "%s"
            cur.execute(f"SELECT file FROM documents_document WHERE id = {placeholder}", (doc_id,))
            row = cur.fetchone()
            if not row:
                return False
            file_path = row[0]

            # attempt to remove file from disk — try multiple candidate paths to be robust
            tried = []
            try:
                candidates = []
                # raw value
                candidates.append(Path(file_path))
                # strip leading slashes
                candidates.append(Path(file_path.lstrip('/\\')))
                # relative to cwd
                candidates.append(Path.cwd() / file_path)
                # common media folders
                candidates.append(Path.cwd() / 'media' / 'documents' / Path(file_path).name)
                candidates.append(Path(__file__).resolve().parents[1] / 'media' / 'documents' / Path(file_path).name)

                removed = False
                for c in candidates:
                    tried.append(str(c))
                    try:
                        if c.exists():
                            c.unlink()
                            removed = True
                            break
                    except Exception as e:
                        # continue trying other candidates
                        print(f"Warning: failed unlink candidate {c}: {e}")

                if not removed:
                    print(f"Warning: file for document {doc_id} not found among candidates: {tried}")
            except Exception as e:
                print(f"Warning: could not remove file {file_path}: {e}")

            # delete DB row
            cur.execute(f"DELETE FROM documents_document WHERE id = {placeholder}", (doc_id,))
            conn.commit()
            return cur.rowcount > 0


# ─── PROCESS DOCUMENT CRUD ────────────────────────────────────────────────────

def _process_document_row_to_dict(row) -> Dict[str, Any]:
    return {
        "id": row[0],
        "folder_id": row[1] or "",
        "process_number": row[2] or "",
        "source_document_id": row[3],
        "original_filename": row[4] or "",
        "file_path": row[5] or "",
        "status": row[6] or "processing",
        "extraction_method": row[7] or "",
        "extracted_text": row[8] or "",
        "analysis_data": _json_value(row[9], {}),
        "summary": row[10] or "",
        "error_message": row[11] or "",
        "created_at": row[12].isoformat() if hasattr(row[12], "isoformat") else row[12],
        "updated_at": row[13].isoformat() if hasattr(row[13], "isoformat") else row[13],
    }


def create_process_document(
    *,
    folder_id: str,
    process_number: str,
    original_filename: str,
    file_path: str,
    source_document_id: int | None = None,
) -> int:
    now = datetime.utcnow()
    values = (
        folder_id or "",
        process_number,
        source_document_id,
        original_filename,
        file_path,
        "processing",
        "",
        "",
        json.dumps({}),
        "",
        "",
        now.isoformat() if DB_BACKEND == "sqlite" else now,
        now.isoformat() if DB_BACKEND == "sqlite" else now,
    )
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            if DB_BACKEND == "sqlite":
                cur.execute("""
                    INSERT INTO process_documents
                    (folder_id, process_number, source_document_id, original_filename, file_path,
                     status, extraction_method, extracted_text, analysis_data, summary,
                     error_message, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, values)
                process_doc_id = cur.lastrowid
            else:
                cur.execute("""
                    INSERT INTO process_documents
                    (folder_id, process_number, source_document_id, original_filename, file_path,
                     status, extraction_method, extracted_text, analysis_data, summary,
                     error_message, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, values)
                process_doc_id = cur.fetchone()[0]
            conn.commit()
            return process_doc_id


def update_process_document(process_doc_id: int, status: str, **kwargs) -> bool:
    allowed = {"extraction_method", "extracted_text", "analysis_data", "summary", "error_message"}
    now = datetime.utcnow()
    sets = ["status = %s", "updated_at = %s"]
    vals: list[Any] = [status, now.isoformat() if DB_BACKEND == "sqlite" else now]
    for key, value in kwargs.items():
        if key not in allowed:
            continue
        sets.append(f"{key} = %s")
        vals.append(json.dumps(value) if key == "analysis_data" else (value or ""))
    vals.append(process_doc_id)
    query = "UPDATE process_documents SET " + ", ".join(sets) + " WHERE id = %s"
    if DB_BACKEND == "sqlite":
        query = query.replace("%s", "?")
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            cur.execute(query, vals)
            conn.commit()
            return cur.rowcount > 0


def get_process_document(process_doc_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            ph = "?" if DB_BACKEND == "sqlite" else "%s"
            cur.execute(f"""
                SELECT id, folder_id, process_number, source_document_id, original_filename,
                       file_path, status, extraction_method, extracted_text, analysis_data,
                       summary, error_message, created_at, updated_at
                FROM process_documents
                WHERE id = {ph}
            """, (process_doc_id,))
            row = cur.fetchone()
            return _process_document_row_to_dict(row) if row else None


def list_process_documents(folder_id: str | None = None, process_number: str | None = None) -> List[Dict[str, Any]]:
    filters: list[str] = []
    params: list[Any] = []
    ph = "?" if DB_BACKEND == "sqlite" else "%s"
    if folder_id is not None:
        filters.append(f"folder_id = {ph}")
        params.append(folder_id)
    if process_number is not None:
        filters.append(f"process_number = {ph}")
        params.append(process_number)
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            cur.execute(f"""
                SELECT id, folder_id, process_number, source_document_id, original_filename,
                       file_path, status, extraction_method, extracted_text, analysis_data,
                       summary, error_message, created_at, updated_at
                FROM process_documents
                {where}
                ORDER BY created_at DESC
            """, params)
            return [_process_document_row_to_dict(row) for row in cur.fetchall()]


def delete_process_document(process_doc_id: int) -> bool:
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            ph = "?" if DB_BACKEND == "sqlite" else "%s"
            cur.execute(f"SELECT file_path FROM process_documents WHERE id = {ph}", (process_doc_id,))
            row = cur.fetchone()
            if not row:
                return False
            try:
                path = Path(row[0])
                if path.exists():
                    path.unlink()
            except Exception as exc:
                print(f"Warning: could not remove process PDF {row[0]}: {exc}")
            cur.execute(f"DELETE FROM process_documents WHERE id = {ph}", (process_doc_id,))
            conn.commit()
            return cur.rowcount > 0
