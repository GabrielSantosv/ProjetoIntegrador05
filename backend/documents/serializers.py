"""DRF serializers for document APIs."""
from rest_framework import serializers

from documents.models import Document


class DocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "file",
            "file_url",
            "status",
            "document_type",
            "extracted_data",
            "entities",
            "legal_opinion",
            "risk_score",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "file_url",
            "status",
            "document_type",
            "extracted_data",
            "entities",
            "legal_opinion",
            "risk_score",
            "error_message",
            "created_at",
            "updated_at",
        ]

    def get_file_url(self, obj: Document) -> str:
        request = self.context.get("request")
        if not obj.file:
            return ""
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url

    def validate_file(self, value):
        if value.content_type != "application/pdf":
            raise serializers.ValidationError("Envie um arquivo PDF valido.")
        if value.size > 25 * 1024 * 1024:
            raise serializers.ValidationError("O PDF deve ter no maximo 25 MB.")
        return value


class DocumentSummarySerializer(serializers.Serializer):
    total = serializers.IntegerField()
    done = serializers.IntegerField()
    failed = serializers.IntegerField()
    processing = serializers.IntegerField()
    avg_risk = serializers.FloatField()
