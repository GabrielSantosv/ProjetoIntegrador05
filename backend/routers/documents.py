from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Response, Query, Depends
from fastapi.responses import JSONResponse
import os
from pathlib import Path
import asyncio
import io
import csv
import re
import uuid
from urllib.parse import quote

from backend import database
from backend.services import (
    extract_pdf_text,
    extract_pdf_text_quick,
    classify_document,
    parse_legal_fields,
    extract_processes_detailed,
    extract_raw_entities,
    organize_extracted_entities,
    analyze_risk,
    generate_legal_opinion,
)
from backend.document_profiles import DOCUMENT_TYPE_LABELS
from backend.auth_security import get_current_user
from fastapi.responses import FileResponse
import unicodedata

router = APIRouter(prefix='/api/documents', tags=['documents'], dependencies=[Depends(get_current_user)])

MEDIA_ROOT = Path(os.getenv('MEDIA_ROOT', './media'))
UPLOAD_DIR = Path(os.getenv('UPLOAD_DIR', str(MEDIA_ROOT / 'documents')))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _file_url(file_path: str) -> str:
    return f'/media/documents/{quote(Path(file_path).name)}'


def _preview_url(doc_id: int) -> str:
    return f'/api/documents/{doc_id}/file'


def _safe_storage_filename(filename: str) -> str:
    original = Path(filename).name
    suffix = Path(original).suffix.lower() or '.pdf'
    stem = Path(original).stem.strip() or 'documento'
    normalized = unicodedata.normalize('NFKD', stem).encode('ascii', 'ignore').decode('ascii')
    slug = re.sub(r'[^A-Za-z0-9._-]+', '_', normalized).strip('._-') or 'documento'
    return f'{uuid.uuid4().hex}_{slug[:80]}{suffix}'


def _http_500(message: str, error: Exception) -> HTTPException:
    return HTTPException(status_code=500, detail=f'{message}: {error}')


def _build_upload_metadata(
    *,
    original_filename: str,
    final_document_name: str,
    detected_document_type: str,
    final_document_type: str,
    document_type_was_edited: bool,
    document_name_was_edited: bool,
) -> dict:
    return {
        'original_filename': original_filename,
        'final_document_name': final_document_name,
        'detected_document_type': detected_document_type,
        'final_document_type': final_document_type,
        'document_type_was_edited': document_type_was_edited,
        'document_name_was_edited': document_name_was_edited,
    }


async def process_document_async(doc_id: int, file_path: str, upload_metadata: dict | None = None):
    """Background processing of document"""
    try:
        upload_metadata = upload_metadata or {}
        print(f"[PROCESSING] started document_id={doc_id} file={file_path}")
        
        if not os.path.exists(file_path):
            error_msg = f"Arquivo nao encontrado em disco: {file_path}"
            print(f"[FILE] saved_path={file_path} exists=False")
            database.update_document_status(doc_id, status='failed', error_message=error_msg)
            return

        # 1. Extract text (Blocking call, run in thread)
        print(f"[EXTRACT] Step 1: Extracting text from {file_path}...")
        extracted_text, extraction_method = await asyncio.to_thread(extract_pdf_text, file_path)
        
        if extraction_method == "failed" or not extracted_text.strip() or extracted_text == "Failed to extract text":
            print(
                "[EXTRACT] no selectable text extracted; marking as needs_ocr "
                f"document_id={doc_id}",
                flush=True,
            )
            detected_label = upload_metadata.get('detected_document_type') or 'Tipo desconhecido'
            final_document_type = (
                upload_metadata.get('final_document_type')
                if upload_metadata.get('document_type_was_edited')
                else detected_label
            )
            document_type = final_document_type or detected_label
            fallback_text = (
                "Nao foi possivel extrair texto selecionavel deste PDF. "
                "O documento aparenta ser uma imagem digitalizada. Instale/configure "
                "o Tesseract OCR para que a analise juridica automatica seja concluida."
            )
            database.update_document_status(
                doc_id,
                status='needs_ocr',
                document_type=document_type,
                extracted_text=fallback_text,
                extracted_data={
                    'fields': [
                        {'field_name': 'tipo_documental', 'field_value': document_type},
                        {'field_name': 'metodo_extracao', 'field_value': 'preview_metadata_fallback'},
                    ],
                    'process_numbers': [],
                    'process_count': 0,
                    'extraction_method': 'preview_metadata_fallback',
                    'raw_entities': [],
                    'organized_entities': [],
                    'risk_analysis': {
                        'score': 0,
                        'base_score': 0,
                        'classification': 'OCR NECESSARIO',
                        'classification_color': 'gray',
                        'description': 'PDF sem texto selecionavel; a analise juridica ainda nao foi executada.',
                        'risk_factors': [],
                        'positive_factors': [],
                        'negative_factors': [],
                        'calculation': {
                            'base_score': 0,
                            'total_positive_impact': 0,
                            'total_negative_impact': 0,
                            'raw_score': 0,
                            'final_score': 0,
                        },
                        'summary': fallback_text,
                        'document_type': document_type,
                    },
                    'upload_metadata': upload_metadata,
                    'extraction_warning': fallback_text,
                },
                entities=[],
                legal_opinion=fallback_text,
                risk_score=0.0,
                error_message=fallback_text,
            )
            print(f"[STATUS] final_status=needs_ocr document_id={doc_id} reason=no_text_extracted", flush=True)
            return

        print(f"[EXTRACT] Step 1 OK: Extracted {len(extracted_text)} chars using {extraction_method}")
        
        # 2. Classify document type
        print(f"[EXTRACT] Step 2: Classifying document type...")
        classification = await asyncio.to_thread(classify_document, extracted_text, Path(file_path).name)
        detected_by_backend = classification.document_type
        
        # Use label for consistency with frontend
        detected_label = DOCUMENT_TYPE_LABELS.get(detected_by_backend, detected_by_backend)
        
        final_document_type = (
            upload_metadata.get('final_document_type')
            if upload_metadata.get('document_type_was_edited')
            else detected_label
        )
        document_type = final_document_type or detected_label
        print(f"[EXTRACT] Step 2 OK: Type = {detected_by_backend} ({detected_label})")
        
        # 3. Parse fields
        print(f"[EXTRACT] Step 3: Parsing legal fields...")
        parsed_fields = await asyncio.to_thread(parse_legal_fields, extracted_text, document_type)

        # 3.5. Extract all CNJ process numbers with detailed metadata
        processes_detail = await asyncio.to_thread(extract_processes_detailed, extracted_text)
        process_numbers = [p["number"] for p in processes_detail]  # backward compat
        main_process_count = sum(1 for p in processes_detail if not p["is_homonimo"])
        homonimo_count = sum(1 for p in processes_detail if p["is_homonimo"])
        process_count = len(processes_detail)
        has_homonimos = homonimo_count > 0
        print(
            f"[EXTRACT] Step 3.5: Found {main_process_count} main + {homonimo_count} homonimo "
            f"process(es): {process_numbers}"
        )

        # 4. Extract entities
        print(f"[EXTRACT] Step 4: Extracting named entities...")
        raw_entities = await asyncio.to_thread(extract_raw_entities, extracted_text, parsed_fields)
        entities = await asyncio.to_thread(organize_extracted_entities, raw_entities)

        # 5. Score risk
        print(f"[EXTRACT] Step 5: Scoring risk...")
        try:
            risk_analysis = await asyncio.to_thread(
                analyze_risk, extracted_text, parsed_fields, entities, document_type,
                main_process_count, homonimo_count
            )
            risk_score = risk_analysis['score']
        except Exception as risk_err:
            print(f"[EXTRACT] Step 5 FAILED: {risk_err}")
            risk_analysis = {}
            risk_score = 0.0

        # 6. Generate legal opinion
        print(f"[EXTRACT] Step 6: Generating legal opinion...")
        try:
            legal_opinion = await asyncio.to_thread(
                generate_legal_opinion, extracted_text, document_type, entities,
                process_count, homonimo_count
            )
        except Exception as opinion_err:
            print(f"[EXTRACT] Step 6 FAILED: {opinion_err}")
            legal_opinion = "Erro ao gerar parecer automatico."

        # 7. Update database
        print(f"[EXTRACT] Step 7: Updating database...")
        database.update_document_status(
            doc_id,
            status='done',
            document_type=document_type,
            extracted_text=extracted_text,
            extracted_data={
                'fields': parsed_fields,
                'process_numbers': process_numbers,
                'processes_detail': processes_detail,
                'process_count': process_count,
                'main_process_count': main_process_count,
                'homonimo_count': homonimo_count,
                'has_homonimos': has_homonimos,
                'extraction_method': extraction_method,
                'raw_entities': raw_entities,
                'organized_entities': entities,
                'risk_analysis': risk_analysis,
                'classification': classification.as_dict(),
                'upload_metadata': {
                    **upload_metadata,
                    'backend_detected_document_type': detected_by_backend,
                    'backend_detected_label': detected_label,
                    'final_document_type_used': document_type,
                },
            },
            entities=entities,
            legal_opinion=legal_opinion,
            risk_score=risk_score
        )
        print(f"[STATUS] final_status=done document_id={doc_id}")
        
    except Exception as e:
        import traceback
        error_msg = f"Erro inesperado no processamento: {str(e)}"
        print(f"[EXTRACT] ✗ Fatal Error for doc {doc_id}: {error_msg}")
        print(f"Traceback: {traceback.format_exc()}")
        database.update_document_status(doc_id, status='failed', error_message=error_msg)


@router.post('/detect')
async def detect_document_type(file: UploadFile = File(...)) -> JSONResponse:
    """Detect document type from a PDF without saving it."""
    try:
        print(f"[DETECT] request received filename={file.filename}", flush=True)
        if not file.filename:
            raise HTTPException(status_code=400, detail='Nome do arquivo ausente')
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail='Envie um arquivo PDF')

        # Read content to memory
        content = await file.read()
        print(f"[DETECT] file read filename={file.filename} bytes={len(content)}", flush=True)
        
        # Save temporary file for text extraction
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # Fast preview detection: no OCR and only first pages.
            extracted_text, method = await asyncio.wait_for(
                asyncio.to_thread(extract_pdf_text_quick, tmp_path),
                timeout=8,
            )
            
            # Classify
            classification = await asyncio.to_thread(classify_document, extracted_text, file.filename)
            result = classification.as_dict()
            result['extraction_method'] = method
            print(
                f"[DETECT] response filename={file.filename} type={result['document_type']} "
                f"matched_by={result['matched_by']} method={method}",
                flush=True,
            )
            
            return JSONResponse(result)
        except asyncio.TimeoutError:
            print(f"[DETECT] quick detection timeout filename={file.filename}; using filename fallback", flush=True)
            classification = await asyncio.to_thread(classify_document, "", file.filename)
            result = classification.as_dict()
            result['extraction_method'] = 'filename_timeout_fallback'
            return JSONResponse(result)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
    except HTTPException:
        raise
    except Exception as e:
        raise _http_500('Falha ao detectar tipo documental', e)


@router.post('/')
async def upload_document(
    title: str = Form(''),
    original_filename: str = Form(''),
    final_document_name: str = Form(''),
    detected_document_type: str = Form('Tipo desconhecido'),
    final_document_type: str = Form('Tipo desconhecido'),
    document_type_was_edited: bool = Form(False),
    document_name_was_edited: bool = Form(False),
    folder_id: str = Form(''),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    """Upload and start processing a PDF document"""
    try:
        print(f"[UPLOAD] request received filename={file.filename}", flush=True)
        if not file.filename:
            raise HTTPException(status_code=400, detail='Nome do arquivo ausente')
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail='Envie um arquivo PDF')

        print(f"[UPLOAD] checking database schema", flush=True)
        try:
            database.ensure_schema()
            print(f"[UPLOAD] database schema OK", flush=True)
        except Exception as db_err:
            print(f"[UPLOAD] database schema error: {db_err}", flush=True)
            raise HTTPException(status_code=500, detail=f"Erro de Banco de Dados: {str(db_err)}")

        if folder_id and not database.get_folder(folder_id, owner_id=current_user["id"]):
            raise HTTPException(status_code=404, detail="Pasta nao encontrada")

        original_filename = original_filename or file.filename
        final_document_name = (final_document_name or title or file.filename).strip()
        final_document_type = final_document_type or detected_document_type or 'Tipo desconhecido'
        upload_metadata = _build_upload_metadata(
            original_filename=original_filename,
            final_document_name=final_document_name,
            detected_document_type=detected_document_type,
            final_document_type=final_document_type,
            document_type_was_edited=document_type_was_edited,
            document_name_was_edited=document_name_was_edited,
        )

        print(f"[UPLOAD] payload title={final_document_name} type={final_document_type}", flush=True)

        # Save file
        safe_filename = _safe_storage_filename(file.filename)
        file_path = UPLOAD_DIR / safe_filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"[UPLOAD] reading upload content", flush=True)
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)
        
        print(f"[UPLOAD] file saved path={file_path} bytes={len(content)} exists={file_path.exists()}", flush=True)

        # Create document record
        print(f"[UPLOAD] creating database record", flush=True)
        doc_id = database.create_document(
            filename=final_document_name,
            file_path=str(file_path),
            extraction_method='hybrid',
            folder_id=folder_id,
            owner_id=current_user["id"],
        )

        database.update_document_status(
            doc_id,
            status='processing',
            document_type=final_document_type,
            extracted_data={'upload_metadata': upload_metadata},
        )
        
        print(f"[UPLOAD] database record created id={doc_id}; starting background processing", flush=True)
        # Start async processing (don't await)
        asyncio.create_task(process_document_async(doc_id, str(file_path), upload_metadata))
        
        # Return React-compatible response
        return JSONResponse({
            'id': doc_id,
            'title': final_document_name,
            'file_url': _file_url(str(file_path)),
            'preview_url': _preview_url(doc_id),
            'pdf_url': _preview_url(doc_id),
            'filename': safe_filename,
            'status': 'processing',
            'document_type': final_document_type,
            'extracted_data': {'upload_metadata': upload_metadata},
            'entities': [],
            'legal_opinion': '',
            'risk_score': 0.0,
            'error_message': '',
            'created_at': str(__import__('datetime').datetime.now().isoformat()),
            'updated_at': str(__import__('datetime').datetime.now().isoformat()),
            'folder_id': folder_id,
        }, status_code=201)
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"[UPLOAD] Erro fatal: {str(e)}")
        print(traceback.format_exc())
        raise _http_500('Falha ao enviar PDF', e)


@router.post('/{doc_id}/reprocess')
async def reprocess_document(doc_id: int, current_user: dict = Depends(get_current_user)):
    """Put an existing document back into the processing queue."""
    try:
        database.ensure_schema()
        doc = database.get_document(doc_id, owner_id=current_user["id"])
        if not doc:
            raise HTTPException(status_code=404, detail='Document not found')

        file_path = doc.get('file_path')
        if not file_path or not Path(file_path).exists():
            raise HTTPException(status_code=404, detail='Arquivo fisico nao encontrado no servidor')

        extracted_data = doc.get('extracted_data') or {}
        upload_metadata = extracted_data.get('upload_metadata') or {}
        database.update_document_status(
            doc_id,
            status='processing',
            extracted_text='',
            extracted_data={'upload_metadata': upload_metadata},
            entities=[],
            legal_opinion='',
            risk_score=0.0,
            error_message='',
        )
        print(f"[REPROCESS] queued document_id={doc_id} file={file_path}", flush=True)
        asyncio.create_task(process_document_async(doc_id, file_path, upload_metadata))
        return {'id': doc_id, 'status': 'processing'}
    except HTTPException:
        raise
    except Exception as e:
        raise _http_500('Falha ao reprocessar documento', e)


@router.get('/summary/')
async def get_summary(folder_id: str | None = Query(None), current_user: dict = Depends(get_current_user)):
    """Dashboard summary counters."""
    try:
        database.ensure_schema()
        return database.get_summary(folder_id=folder_id, owner_id=current_user["id"])
    except Exception as e:
        raise _http_500('Falha ao carregar resumo', e)


@router.get('/')
async def list_documents(limit: int = 50, offset: int = 0, folder_id: str | None = Query(None), current_user: dict = Depends(get_current_user)):
    """List all documents with pagination"""
    try:
        database.ensure_schema()
        documents, total = database.list_documents(limit, offset, folder_id=folder_id, owner_id=current_user["id"])
        # Convert to React-compatible format
        result = []
        for doc in documents:
            extracted = doc.get('extracted_data') or {}
            result.append({
                'id': doc['id'],
                'title': doc['filename'],
                'file_url': _file_url(doc.get('file_path') or doc['filename']),
                'preview_url': _preview_url(doc['id']),
                'pdf_url': _preview_url(doc['id']),
                'status': doc['status'],
                'document_type': doc['document_type'],
                'extracted_data': {
                    'processes_detail': extracted.get('processes_detail', []),
                    'process_numbers': extracted.get('process_numbers', []),
                },
                'entities': [
                    e for e in (doc.get('entities') or [])
                    if e.get('category') == 'Processos' or e.get('label') == 'PROCESSO'
                ],
                'legal_opinion': '',
                'risk_score': doc['risk_score'] or 0.0,
                'error_message': doc.get('error_message', ''),
                'created_at': doc['created_at'],
                'updated_at': doc.get('updated_at') or doc['created_at'],
                'folder_id': doc.get('folder_id', ''),
            })
        return result
    except Exception as e:
        raise _http_500('Falha ao listar documentos', e)


@router.get('/{doc_id}')
async def get_document(doc_id: int, current_user: dict = Depends(get_current_user)):
    """Get document details"""
    try:
        doc = database.get_document(doc_id, owner_id=current_user["id"])
        if not doc:
            raise HTTPException(status_code=404, detail='Document not found')
        
        # Convert to React-compatible LegalDocument format
        return {
            'id': doc['id'],
            'title': doc['filename'],
            'file_url': f'/media/documents/{quote(Path(doc["file_path"]).name)}',
            'preview_url': _preview_url(doc['id']),
            'pdf_url': _preview_url(doc['id']),
            'status': doc['status'],
            'document_type': doc['document_type'] or '',
            'extraction_method': (doc['extracted_data'] or {}).get('extraction_method') or doc.get('extraction_method') or '',
            'extracted_data': doc['extracted_data'] or {},
            'entities': doc['entities'] or [],
            'legal_opinion': doc['legal_opinion'] or '',
            'risk_score': doc['risk_score'] or 0.0,
            'error_message': doc.get('error_message', ''),
            'created_at': doc['created_at'],
            'updated_at': doc['updated_at'],
            'folder_id': doc.get('folder_id', ''),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise _http_500('Falha ao buscar documento', e)


@router.get('/{doc_id}/file')
async def get_document_file(doc_id: int, current_user: dict = Depends(get_current_user)):
    """Return the actual file stored for a given document id using the DB-stored path."""
    try:
        doc = database.get_document(doc_id, owner_id=current_user["id"])
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
                return FileResponse(
                    str(c),
                    media_type='application/pdf',
                    headers={'Content-Disposition': f'inline; filename="{quote(c.name)}"'},
                )

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
                        return FileResponse(str(f), media_type='application/pdf', headers={'Content-Disposition': f'inline; filename="{quote(f.name)}"'})
                    if target_norm in norm(fn):
                        return FileResponse(str(f), media_type='application/pdf', headers={'Content-Disposition': f'inline; filename="{quote(f.name)}"'})
                    if simplify(fn) == target_simple or target_simple in simplify(fn):
                        return FileResponse(str(f), media_type='application/pdf', headers={'Content-Disposition': f'inline; filename="{quote(f.name)}"'})
                except Exception:
                    continue
        except Exception:
            pass

        raise HTTPException(status_code=404, detail='Arquivo fisico nao encontrado no servidor')
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/{doc_id}/export_excel')
async def export_excel(doc_id: int, current_user: dict = Depends(get_current_user)):
    """Simple CSV export that spreadsheet apps can open."""
    doc = database.get_document(doc_id, owner_id=current_user["id"])
    if not doc:
        raise HTTPException(status_code=404, detail='Document not found')

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Campo', 'Valor'])
    writer.writerow(['Titulo', doc['filename']])
    writer.writerow(['Status', doc['status']])
    writer.writerow(['Tipo', doc['document_type'] or ''])
    writer.writerow(['Risco', doc['risk_score']])
    writer.writerow(['Parecer', doc['legal_opinion'] or ''])
    for field in (doc.get('extracted_data') or {}).get('fields', []):
        writer.writerow([field.get('field_name', ''), field.get('field_value', '')])

    return Response(
        content=output.getvalue(),
        media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename="documento-{doc_id}.csv"'},
    )


@router.get('/{doc_id}/export_word')
async def export_word(doc_id: int, current_user: dict = Depends(get_current_user)):
    """Simple text export for the legal opinion and extracted text."""
    doc = database.get_document(doc_id, owner_id=current_user["id"])
    if not doc:
        raise HTTPException(status_code=404, detail='Document not found')

    content = (
        f"Documento: {doc['filename']}\n"
        f"Status: {doc['status']}\n"
        f"Tipo: {doc['document_type'] or ''}\n"
        f"Risco: {doc['risk_score']}/100\n\n"
        f"Parecer juridico:\n{doc['legal_opinion'] or ''}\n\n"
        f"Texto extraido:\n{doc['extracted_text'] or ''}\n"
    )
    return Response(
        content=content,
        media_type='text/plain; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename="documento-{doc_id}.txt"'},
    )



@router.delete('/{doc_id}/')
async def delete_document(doc_id: int, current_user: dict = Depends(get_current_user)):
    """Delete document record and associated file"""
    try:
        doc = database.get_document(doc_id, owner_id=current_user["id"])
        if not doc:
            raise HTTPException(status_code=404, detail='Document not found')

        ok = database.delete_document(doc_id, owner_id=current_user["id"])
        if not ok:
            raise HTTPException(status_code=500, detail='Failed to delete document')

        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
