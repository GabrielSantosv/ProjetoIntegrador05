from fastapi import APIRouter, UploadFile, File, HTTPException, Header, Response
from fastapi.responses import JSONResponse
import os
from pathlib import Path
from typing import Optional
import asyncio

from api import database
from api.models import DocumentResponse, DocumentListResponse
from api.services import (
    extract_pdf_text,
    classify_certificate_type,
    parse_legal_fields,
    extract_named_entities,
    score_risk,
    generate_legal_opinion
)
from fastapi.responses import FileResponse
import unicodedata

router = APIRouter(prefix='/api/documents', tags=['documents'])

UPLOAD_DIR = Path(os.getenv('MEDIA_ROOT', './media/documents'))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def process_document_async(doc_id: int, file_path: str):
    """Background processing of document"""
    try:
        print(f"[EXTRACT] Starting extraction for doc {doc_id}, file: {file_path}")
        
        # 1. Extract text
        print(f"[EXTRACT] Step 1: Extracting text...")
        extracted_text, extraction_method = extract_pdf_text(file_path)
        print(f"[EXTRACT] Step 1 OK: Extracted {len(extracted_text)} chars")
        
        # 2. Classify document type
        print(f"[EXTRACT] Step 2: Classifying document type...")
        document_type = classify_certificate_type(extracted_text)
        print(f"[EXTRACT] Step 2 OK: Type = {document_type}")
        
        # 3. Parse fields
        print(f"[EXTRACT] Step 3: Parsing legal fields...")
        parsed_fields = parse_legal_fields(extracted_text, document_type)
        print(f"[EXTRACT] Step 3 OK: Fields = {parsed_fields}")
        
        # 4. Extract entities
        print(f"[EXTRACT] Step 4: Extracting named entities...")
        entities = extract_named_entities(extracted_text)
        print(f"[EXTRACT] Step 4 OK: Entities = {len(entities)} found")
        
        # 5. Score risk
        print(f"[EXTRACT] Step 5: Scoring risk...")
        risk_score = score_risk(extracted_text, parsed_fields, entities)
        print(f"[EXTRACT] Step 5 OK: Risk = {risk_score}")
        
        # 6. Generate legal opinion
        print(f"[EXTRACT] Step 6: Generating legal opinion...")
        legal_opinion = generate_legal_opinion(extracted_text, document_type, entities)
        print(f"[EXTRACT] Step 6 OK: Opinion length = {len(legal_opinion)}")
        
        # 7. Update database
        print(f"[EXTRACT] Step 7: Updating database...")
        database.update_document_status(
            doc_id,
            status='completed',
            document_type=document_type,
            extracted_text=extracted_text,
            extracted_data={'fields': parsed_fields},
            entities=[{'type': e.get('entity'), 'value': e.get('value')} for e in entities],
            legal_opinion=legal_opinion,
            risk_score=risk_score
        )
        print(f"[EXTRACT] ✓ Document {doc_id} extraction completed successfully")
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"[EXTRACT] ✗ Error processing document {doc_id}: {error_msg}")
        print(f"[EXTRACT] Traceback: {traceback.format_exc()}")
        database.update_document_status(doc_id, status='failed', error_message=error_msg)


@router.post('/')
async def upload_document(title: str = '', file: UploadFile = File(...)) -> JSONResponse:
    """Upload and start processing a PDF document"""
    try:
        # Save file
        file_path = UPLOAD_DIR / file.filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # Create document record
        doc_id = database.create_document(
            filename=title or file.filename,
            file_path=str(file_path),
            extraction_method='hybrid'
        )
        
        # Start async processing (don't await)
        asyncio.create_task(process_document_async(doc_id, str(file_path)))
        
        # Return React-compatible response
        return JSONResponse({
            'id': doc_id,
            'title': title or file.filename,
            'file_url': f'/media/documents/{file.filename}',
            'filename': file.filename,
            'status': 'processing',
            'document_type': None,
            'extracted_data': {},
            'entities': [],
            'legal_opinion': '',
            'risk_score': 0.0,
            'error_message': '',
            'created_at': str(__import__('datetime').datetime.now().isoformat()),
            'updated_at': str(__import__('datetime').datetime.now().isoformat()),
        }, status_code=201)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/')
async def list_documents(limit: int = 50, offset: int = 0):
    """List all documents with pagination"""
    try:
        documents, total = database.list_documents(limit, offset)
        # Convert to React-compatible format
        result = []
        for doc in documents:
            result.append({
                'id': doc['id'],
                'title': doc['filename'],
                'file_url': f'/media/documents/{doc["filename"]}',
                'status': doc['status'],
                'document_type': doc['document_type'],
                'extracted_data': {},
                'entities': [],
                'legal_opinion': '',
                'risk_score': doc['risk_score'] or 0.0,
                'error_message': '',
                'created_at': doc['created_at'],
                'updated_at': doc['created_at'],
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/{doc_id}')
async def get_document(doc_id: int):
    """Get document details"""
    try:
        doc = database.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail='Document not found')
        
        # Convert to React-compatible LegalDocument format
        return {
            'id': doc['id'],
            'title': doc['filename'],
            'file_url': f'/media/documents/{doc["filename"]}',
            'status': doc['status'],
            'document_type': doc['document_type'] or '',
            'extracted_data': doc['extracted_data'] or {},
            'entities': doc['entities'] or [],
            'legal_opinion': doc['legal_opinion'] or '',
            'risk_score': doc['risk_score'] or 0.0,
            'error_message': '',
            'created_at': doc['created_at'],
            'updated_at': doc['updated_at'],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/{doc_id}/file')
async def get_document_file(doc_id: int):
    """Return the actual file stored for a given document id using the DB-stored path."""
    try:
        doc = database.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail='Document not found')

        file_path = doc.get('file_path')
        if not file_path:
            raise HTTPException(status_code=404, detail='File path not available')

        # Try direct path and some common candidates
        candidates = [
            Path(file_path),
            Path(file_path.lstrip('/\\')),
            Path.cwd() / file_path,
            Path.cwd() / 'media' / 'documents' / Path(file_path).name,
            Path(__file__).resolve().parents[1] / 'media' / 'documents' / Path(file_path).name,
        ]

        for c in candidates:
            if c.exists() and c.is_file():
                return FileResponse(str(c))

        # Fallback: try to find a file in MEDIA_ROOT/documents that matches the
        # stored basename after unicode normalization (handles encoding loss)
        media_root = os.getenv('MEDIA_ROOT', './media')
        media_dir = Path(media_root).resolve() / 'documents'
        try:
            target = Path(file_path).name
            def norm(s: str) -> str:
                return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii').lower()

            def simplify(s: str) -> str:
                n = norm(s)
                return ''.join(ch for ch in n if ch.isalnum())

            target_norm = norm(target)
            target_simple = simplify(target)
            for f in media_dir.iterdir() if media_dir.exists() else []:
                try:
                    if not f.is_file():
                        continue
                    fn = f.name
                    if norm(fn) == target_norm:
                        return FileResponse(str(f))
                    if target_norm in norm(fn):
                        return FileResponse(str(f))
                    if simplify(fn) == target_simple or target_simple in simplify(fn):
                        return FileResponse(str(f))
                except Exception:
                    continue
        except Exception:
            pass

        raise HTTPException(status_code=404, detail='File not found on disk')
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.delete('/{doc_id}/')
async def delete_document(doc_id: int):
    """Delete document record and associated file"""
    try:
        doc = database.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail='Document not found')

        ok = database.delete_document(doc_id)
        if not ok:
            raise HTTPException(status_code=500, detail='Failed to delete document')

        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
