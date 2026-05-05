"""Persistent document processing entities."""
from django.conf import settings
from django.db import models


class Document(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        PROCESSING = "processing", "Processando"
        DONE = "done", "Concluido"
        FAILED = "failed", "Falhou"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="documents/%Y/%m/")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    document_type = models.CharField(max_length=120, blank=True)
    extracted_text = models.TextField(blank=True)
    extracted_data = models.JSONField(default=dict, blank=True)
    entities = models.JSONField(default=list, blank=True)
    legal_opinion = models.TextField(blank=True)
    risk_score = models.PositiveSmallIntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class DocumentText(models.Model):
    document = models.OneToOneField(Document, on_delete=models.CASCADE, related_name="text")
    raw_text = models.TextField(blank=True)
    raw_ocr_text = models.TextField(blank=True)
    pages = models.JSONField(default=list, blank=True)
    extraction_method = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Text for {self.document_id}"


class DocumentEntity(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="document_entities")
    entity_type = models.CharField(max_length=120)
    value = models.TextField()
    start_char = models.IntegerField(null=True, blank=True)
    end_char = models.IntegerField(null=True, blank=True)
    page = models.IntegerField(null=True, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["document", "entity_type"])]

    def __str__(self) -> str:
        return f"{self.entity_type}: {self.value}"


class ParsedField(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="parsed_fields")
    field_name = models.CharField(max_length=200)
    field_value = models.JSONField(default=dict, blank=True)
    page = models.IntegerField(null=True, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.field_name} ({self.document_id})"


class ProcessingLog(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="processing_logs")
    status = models.CharField(max_length=20)
    message = models.TextField(blank=True)
    worker = models.CharField(max_length=200, blank=True)
    attempt = models.IntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Log {self.status} for {self.document_id}"


class Export(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="exports")
    export_type = models.CharField(max_length=20)
    file = models.FileField(upload_to="exports/%Y/%m/", blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.export_type} for {self.document_id}"
