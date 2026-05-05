"""Celery tasks for long-running document processing."""
from celery import shared_task
from django.db import transaction
from django.utils import timezone

from documents.models import Document, DocumentEntity, DocumentText, ParsedField, ProcessingLog
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

    worker_name = getattr(self.request, "hostname", None) or "local"
    attempt_number = (getattr(self.request, "retries", 0) or 0) + 1

    ProcessingLog.objects.create(
        document=document,
        status=Document.Status.PROCESSING,
        message="Processamento iniciado",
        worker=worker_name,
        attempt=attempt_number,
        started_at=timezone.now(),
    )

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

        parsed_fields = []
        for field_name, field_value in parsed_data.items():
            if field_name in {"validacao", "geometria", "revisao_manual"}:
                continue
            if field_value in (None, "", [], {}):
                continue
            parsed_fields.append(
                ParsedField(
                    document=document,
                    field_name=field_name,
                    field_value=field_value,
                    page=1,
                    confidence=1.0,
                )
            )

        entities_payload = extract_named_entities(extracted.text)
        entities = []
        for entity in entities_payload:
            entities.append(
                DocumentEntity(
                    document=document,
                    entity_type=entity.get("label", "UNKNOWN"),
                    value=entity.get("text", ""),
                    confidence=entity.get("score"),
                    meta=entity,
                )
            )

        with transaction.atomic():
            document.extracted_text = extracted.text
            document.extracted_data = {
                **parsed_data,
                "pages": extracted.pages,
                "texto_bruto_ocr": extracted.raw_ocr_text,
                "metodo_extracao": extracted.extraction_method,
            }
            document.entities = entities_payload
            document.document_type = document_type
            document.risk_score = risk_score
            document.legal_opinion = legal_opinion
            document.status = Document.Status.DONE
            document.error_message = ""
            document.save()

            DocumentText.objects.update_or_create(
                document=document,
                defaults={
                    "raw_text": extracted.text,
                    "raw_ocr_text": extracted.raw_ocr_text,
                    "pages": extracted.pages,
                    "extraction_method": extracted.extraction_method,
                },
            )

            DocumentEntity.objects.filter(document=document).delete()
            DocumentEntity.objects.bulk_create(entities)

            ParsedField.objects.filter(document=document).delete()
            ParsedField.objects.bulk_create(parsed_fields)

            ProcessingLog.objects.create(
                document=document,
                status=Document.Status.DONE,
                message="Processamento concluido com sucesso",
                worker=worker_name,
                attempt=attempt_number,
                started_at=timezone.now(),
                ended_at=timezone.now(),
            )
    except Exception as exc:  # noqa: BLE001 - surfaced to API for MVP observability.
        document.status = Document.Status.FAILED
        document.error_message = str(exc)
        document.save(update_fields=["status", "error_message", "updated_at"])
        ProcessingLog.objects.create(
            document=document,
            status=Document.Status.FAILED,
            message=str(exc),
            worker=worker_name,
            attempt=attempt_number,
            started_at=timezone.now(),
            ended_at=timezone.now(),
        )
        raise
