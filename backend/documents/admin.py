from django.contrib import admin

from documents.models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "status", "document_type", "risk_score", "created_at")
    list_filter = ("status", "document_type", "created_at")
    search_fields = ("title", "extracted_text")
