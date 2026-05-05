import psycopg
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from contextlib import contextmanager
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / 'backend' / '.env')

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', 5432))
DB_NAME = os.getenv('DB_NAME', 'Projeto_integrador')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'admin')


@contextmanager
def get_connection():
    conn = psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
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


def create_document(filename: str, file_path: str, extraction_method: str = 'hybrid') -> int:
    """Create document record and return ID"""
    from datetime import datetime
    
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            now = datetime.utcnow()
            cur.execute("""
                INSERT INTO documents_document 
                (title, file, status, document_type, extracted_text, extracted_data, entities, legal_opinion, risk_score, error_message, created_at, updated_at, owner_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                filename, 
                file_path, 
                'processing', 
                'documentojuridico',
                '',  # extracted_text
                '{}',  # extracted_data as JSON
                '[]',  # entities as JSON array
                '',  # legal_opinion
                0,  # risk_score
                '',  # error_message
                now,  # created_at
                now,  # updated_at
                1  # owner_id=1 (demo user)
            ))
            doc_id = cur.fetchone()[0]
            conn.commit()
            return doc_id


def get_document(doc_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve document with all related data"""
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            cur.execute("""
                SELECT id, title, file, status, document_type,
                       extracted_text, extracted_data, entities, legal_opinion, risk_score,
                       created_at, updated_at
                FROM documents_document
                WHERE id = %s
            """, (doc_id,))
            
            row = cur.fetchone()
            if not row:
                return None
            
            return {
                'id': row[0],
                'filename': row[1],  # title
                'file_path': row[2],  # file field contains path
                'status': row[3],
                'extraction_method': 'hybrid',  # Default method since not stored in Django
                'document_type': row[4],
                'extracted_text': row[5],
                'extracted_data': row[6],
                'entities': row[7],
                'legal_opinion': row[8],
                'risk_score': row[9],
                'created_at': row[10].isoformat() if row[10] else None,
                'updated_at': row[11].isoformat() if row[11] else None,
            }


def list_documents(limit: int = 50, offset: int = 0) -> tuple[List[Dict[str, Any]], int]:
    """List documents with pagination"""
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            # Get total count
            cur.execute("SELECT COUNT(*) FROM documents_document")
            total = cur.fetchone()[0]
            
            # Get paginated results
            cur.execute("""
                SELECT id, title, document_type, risk_score, status, created_at
                FROM documents_document
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, (limit, offset))
            
            rows = cur.fetchall()
            documents = []
            for row in rows:
                documents.append({
                    'id': row[0],
                    'filename': row[1],
                    'document_type': row[2],
                    'risk_score': row[3],
                    'status': row[4],
                    'created_at': row[5].isoformat() if row[5] else None,
                })
            
            return documents, total


def update_document_status(doc_id: int, status: str, **kwargs) -> bool:
    """Update document status and optional fields"""
    with get_connection() as conn:
        with get_cursor(conn) as cur:
            # Build dynamic update
            fields = ['status = %s', 'updated_at = %s']
            values = [status, datetime.now()]
            
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
            
            values.append(doc_id)
            
            query = f"UPDATE documents_document SET {', '.join(fields)} WHERE id = %s"
            cur.execute(query, values)
            conn.commit()
            return cur.rowcount > 0
