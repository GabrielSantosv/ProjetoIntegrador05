"""Extract a PDF with the current pipeline and persist the result into PostgreSQL."""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import django
from dotenv import load_dotenv
from psycopg.types.json import Json

from database import get_cursor


BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR / "backend"

load_dotenv(BASE_DIR / "backend" / ".env")
load_dotenv(BASE_DIR / ".env", override=False)

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "legal_docs.settings")
django.setup()

from documents.services.ai import HuggingFaceClient
from documents.services.classifier import classify_certificate_type
from documents.services.ner import extract_named_entities
from documents.services.parser import parse_legal_fields, score_risk
from documents.services.pdf import extract_pdf_text


def ensure_user(cursor, username: str, email: str | None = None, password_hash: str | None = None) -> int:
    """Create the user if needed and return its id."""
    cursor.execute(
        "SELECT id FROM app_user WHERE username = %s",
        (username,),
    )
    row = cursor.fetchone()
    if row:
        return row[0]

    cursor.execute(
        """
        INSERT INTO app_user (username, email, password_hash, is_active, is_staff, created_at, updated_at)
        VALUES (%s, %s, %s, TRUE, FALSE, NOW(), NOW())
        RETURNING id
        """,
        (username, email, password_hash),
    )
    return cursor.fetchone()[0]


def insert_document(
    cursor,
    owner_id: int,
    title: str,
    file_path: str,
    status: str = "pending",
    document_type: str | None = None,
    extracted_data: dict[str, Any] | None = None,
    legal_opinion: str | None = None,
    risk_score: int = 0,
    error_message: str | None = None,
) -> int:
    """Insert a document row and return its id."""
    cursor.execute(
        """
        INSERT INTO documents_document (
            owner_id, title, file_path, status, document_type,
            extracted_data, legal_opinion, risk_score, error_message,
            created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        RETURNING id
        """,
        (
            owner_id,
            title,
            file_path,
            status,
            document_type,
            Json(extracted_data or {}),
            legal_opinion,
            risk_score,
            error_message,
        ),
    )
    return cursor.fetchone()[0]


def insert_document_text(
    cursor,
    document_id: int,
    raw_text: str = "",
    raw_ocr_text: str = "",
    pages: list[Any] | None = None,
    extraction_method: str | None = None,
) -> int:
    cursor.execute(
        """
        INSERT INTO documents_documenttext (
            document_id, raw_text, raw_ocr_text, pages, extraction_method, created_at
        )
        VALUES (%s, %s, %s, %s, %s, NOW())
        RETURNING id
        """,
        (document_id, raw_text, raw_ocr_text, Json(pages or []), extraction_method),
    )
    return cursor.fetchone()[0]


def insert_document_entities(cursor, document_id: int, entities: list[dict[str, Any]]) -> None:
    """Insert named entities associated with a document."""
    for entity in entities:
        cursor.execute(
            """
            INSERT INTO documents_documententity (
                document_id, entity_type, value, start_char, end_char, page, confidence, meta, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """,
            (
                document_id,
                entity.get("entity_type", "UNKNOWN"),
                entity.get("value", ""),
                entity.get("start_char"),
                entity.get("end_char"),
                entity.get("page"),
                entity.get("confidence"),
                Json(entity.get("meta", {})),
            ),
        )


def insert_parsed_fields(cursor, document_id: int, parsed_fields: list[dict[str, Any]]) -> None:
    """Insert structured fields extracted from the PDF."""
    for field in parsed_fields:
        cursor.execute(
            """
            INSERT INTO documents_parsedfield (
                document_id, field_name, field_value, page, confidence,
                source_text, bbox, extraction_method, validated, validated_at, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """,
            (
                document_id,
                field.get("field_name", "unnamed_field"),
                Json(field.get("field_value", {})),
                field.get("page"),
                field.get("confidence"),
                field.get("source_text"),
                Json(field.get("bbox", {})),
                field.get("extraction_method"),
                field.get("validated", False),
                field.get("validated_at"),
            ),
        )


def insert_processing_log(
    cursor,
    document_id: int,
    status: str,
    message: str | None = None,
    worker: str | None = None,
    attempt: int = 1,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
) -> int:
    cursor.execute(
        """
        INSERT INTO documents_processinglog (
            document_id, status, message, worker, attempt, started_at, ended_at, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        RETURNING id
        """,
        (document_id, status, message, worker, attempt, started_at, ended_at),
    )
    return cursor.fetchone()[0]


def insert_export(
    cursor,
    document_id: int,
    export_type: str,
    file_path: str | None = None,
    created_by_id: int | None = None,
) -> int:
    cursor.execute(
        """
        INSERT INTO documents_export (
            document_id, created_by_id, export_type, file_path, created_at
        )
        VALUES (%s, %s, %s, %s, NOW())
        RETURNING id
        """,
        (document_id, created_by_id, export_type, file_path),
    )
    return cursor.fetchone()[0]


def save_document_bundle(bundle: dict[str, Any]) -> dict[str, int]:
    """Persist a complete document bundle and return inserted ids."""
    with get_cursor() as cursor:
        user = bundle["user"]
        document = bundle["document"]
        text = bundle.get("text", {})
        entities = bundle.get("entities", [])
        parsed_fields = bundle.get("parsed_fields", [])
        log = bundle.get("processing_log", {})
        exports = bundle.get("exports", [])

        user_id = ensure_user(
            cursor,
            username=user["username"],
            email=user.get("email"),
            password_hash=user.get("password_hash"),
        )

        document_id = insert_document(
            cursor,
            owner_id=user_id,
            title=document["title"],
            file_path=document["file_path"],
            status=document.get("status", "pending"),
            document_type=document.get("document_type"),
            extracted_data=document.get("extracted_data"),
            legal_opinion=document.get("legal_opinion"),
            risk_score=document.get("risk_score", 0),
            error_message=document.get("error_message"),
        )

        text_id = insert_document_text(
            cursor,
            document_id=document_id,
            raw_text=text.get("raw_text", ""),
            raw_ocr_text=text.get("raw_ocr_text", ""),
            pages=text.get("pages", []),
            extraction_method=text.get("extraction_method"),
        )

        insert_document_entities(cursor, document_id=document_id, entities=entities)
        insert_parsed_fields(cursor, document_id=document_id, parsed_fields=parsed_fields)

        log_id = insert_processing_log(
            cursor,
            document_id=document_id,
            status=log.get("status", document.get("status", "pending")),
            message=log.get("message"),
            worker=log.get("worker"),
            attempt=log.get("attempt", 1),
            started_at=log.get("started_at"),
            ended_at=log.get("ended_at"),
        )

        export_ids: list[int] = []
        for export in exports:
            export_ids.append(
                insert_export(
                    cursor,
                    document_id=document_id,
                    export_type=export["export_type"],
                    file_path=export.get("file_path"),
                    created_by_id=export.get("created_by_id"),
                )
            )

    return {
        "user_id": user_id,
        "document_id": document_id,
        "text_id": text_id,
        "log_id": log_id,
        "export_ids_count": len(export_ids),
    }


def build_bundle_from_pdf(
    pdf_path: str,
    username: str,
    email: str | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    """Run the current extraction pipeline and build a persistence bundle."""
    extracted = extract_pdf_text(pdf_path)
    document_type = classify_certificate_type(extracted.text)
    extracted_data = parse_legal_fields(
        text=extracted.text,
        document_type=document_type,
        pages=extracted.pages,
    )
    entities_raw = extract_named_entities(extracted.text)
    entities = [
        {
            "entity_type": entity.get("label", "UNKNOWN"),
            "value": entity.get("text", ""),
            "confidence": entity.get("score"),
            "meta": entity,
        }
        for entity in entities_raw
    ]

    risk_score = extracted_data.get("risco") or score_risk(extracted_data, extracted.text, document_type)
    legal_opinion = HuggingFaceClient().generate_legal_opinion(
        text=extracted.text,
        extracted_data=extracted_data,
        document_type=document_type,
    )

    parsed_fields = []
    for field_name, field_value in extracted_data.items():
        if field_name in {"validacao", "geometria"}:
            continue
        if field_name == "revisao_manual":
            continue
        if field_value in (None, "", [], {}):
            continue
        parsed_fields.append(
            {
                "field_name": field_name,
                "field_value": field_value,
                "page": 1,
                "confidence": 1.0,
                "source_text": str(field_value),
                "bbox": {},
                "extraction_method": extracted.extraction_method,
                "validated": bool(extracted_data.get("validacao", {}).get("is_valid")),
            }
        )

    pdf_name = Path(pdf_path).name
    return {
        "user": {"username": username, "email": email, "password_hash": None},
        "document": {
            "title": title or pdf_name,
            "file_path": pdf_path,
            "status": "done",
            "document_type": document_type,
            "extracted_data": extracted_data,
            "legal_opinion": legal_opinion,
            "risk_score": risk_score,
            "error_message": None,
        },
        "text": {
            "raw_text": extracted.text,
            "raw_ocr_text": extracted.raw_ocr_text,
            "pages": extracted.pages,
            "extraction_method": extracted.extraction_method,
        },
        "entities": entities,
        "parsed_fields": parsed_fields,
        "processing_log": {
            "status": "done",
            "message": "PDF processado e salvo com o pipeline atual",
            "worker": "local-script",
            "attempt": 1,
            "started_at": None,
            "ended_at": datetime.now(),
        },
        "exports": [],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Processa um PDF com o pipeline atual e salva no PostgreSQL.")
    parser.add_argument("pdf_path", nargs="?", help="Caminho do PDF para processar")
    parser.add_argument("--username", default="demo", help="Nome do usuário dono do documento")
    parser.add_argument("--email", default="demo@example.com", help="Email opcional do usuário")
    parser.add_argument("--title", default=None, help="Título opcional do documento")
    args = parser.parse_args()

    if not args.pdf_path:
        raise SystemExit("Informe o caminho do PDF: python salvar_documento.py caminho\\para\\arquivo.pdf")

    bundle = build_bundle_from_pdf(
        pdf_path=args.pdf_path,
        username=args.username,
        email=args.email,
        title=args.title,
    )
    result = save_document_bundle(bundle)
    print(result)