"""Celery tasks for long-running document processing."""
from celery import shared_task
from django.db import transaction

from documents.models import Document
from documents.services.ai import HuggingFaceClient
from documents.services.classifier import classify_certificate_type
from documents.services.ner import extract_named_entities
from documents.services.parser import parse_legal_fields, score_risk
from documents.services.pdf import extract_pdf_text


@shared_task(bind=True, autoretry_for=(TimeoutError,), retry_backoff=True, max_retries=2)
def process_document(self, document_id: int) -> None:
    document = Document.objects.get(pk=document_id)
    document.status = Document.Status.PROCESSING
    document.save(update_fields=["status", "updated_at"])

    try:
        extracted = extract_pdf_text(document.file.path)
        document_type = classify_certificate_type(extracted.text)
        parsed_data = parse_legal_fields(
            text=extracted.text,
            document_type=document_type,
            pages=extracted.pages,
        )
        entities = extract_named_entities(extracted.text)
        risk_score = parsed_data.get("risco") or score_risk(parsed_data, extracted.text, document_type)
        legal_opinion = HuggingFaceClient().generate_legal_opinion(
            text=extracted.text,
            extracted_data=parsed_data,
            document_type=document_type,
        )

        with transaction.atomic():
            document.extracted_text = extracted.text
            document.extracted_data = {
                **parsed_data,
                "pages": extracted.pages,
                "texto_bruto_ocr": extracted.raw_ocr_text,
                "metodo_extracao": extracted.extraction_method,
            }
            document.entities = entities
            document.document_type = document_type
            document.risk_score = risk_score
            document.legal_opinion = legal_opinion
            document.status = Document.Status.DONE
            document.error_message = ""
            document.save()
    except Exception as exc:  # noqa: BLE001 - surfaced to API for MVP observability.
        document.status = Document.Status.FAILED
        document.error_message = str(exc)
        document.save(update_fields=["status", "error_message", "updated_at"])
        raise
