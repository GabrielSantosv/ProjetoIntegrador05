from fastapi import APIRouter, UploadFile, File, HTTPException, Header
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

router = APIRouter(prefix='/api/documents', tags=['documents'])

UPLOAD_DIR = Path(os.getenv('MEDIA_ROOT', './media/documents'))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def process_document_async(doc_id: int, file_path: str):
    """Background processing of document"""
    try:
        # 1. Extract text
        extracted_text, extraction_method = extract_pdf_text(file_path)
        
        # 2. Classify document type
        document_type = classify_certificate_type(extracted_text)
        
        # 3. Parse fields
        parsed_fields = parse_legal_fields(extracted_text, document_type)
        
        # 4. Extract entities
        entities = extract_named_entities(extracted_text)
        
        # 5. Score risk
        risk_score = score_risk(extracted_text, parsed_fields, entities)
        
        # 6. Generate legal opinion
        legal_opinion = generate_legal_opinion(extracted_text, document_type, entities)
        
        # 7. Update database
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
        
    except Exception as e:
        database.update_document_status(doc_id, status='failed')
        print(f"Error processing document {doc_id}: {str(e)}")


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
