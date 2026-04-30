"""API endpoints for upload, listing and exports."""
import threading

from django.db.models import Avg, Count, Q
from django.http import FileResponse
from rest_framework import decorators, permissions, response, viewsets

from documents.models import Document
from documents.serializers import DocumentSerializer, DocumentSummarySerializer
from documents.services.exporters import build_excel, build_word
from documents.tasks import process_document


class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Document.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        title = serializer.validated_data.get("title") or serializer.validated_data["file"].name
        document = serializer.save(owner=self.request.user, title=title)
        thread = threading.Thread(target=process_document.apply, kwargs={"args": [document.id]})
        thread.daemon = True
        thread.start()

    def perform_destroy(self, instance):
        """Delete the database row and the uploaded PDF from MEDIA_ROOT."""
        if instance.file:
            instance.file.delete(save=False)
        instance.delete()

    @decorators.action(detail=False, methods=["get"])
    def summary(self, request):
        queryset = self.get_queryset()
        counts = queryset.aggregate(
            total=Count("id"),
            done=Count("id", filter=Q(status=Document.Status.DONE)),
            failed=Count("id", filter=Q(status=Document.Status.FAILED)),
            processing=Count("id", filter=Q(status__in=[Document.Status.PENDING, Document.Status.PROCESSING])),
            avg_risk=Avg("risk_score"),
        )
        serializer = DocumentSummarySerializer({**counts, "avg_risk": counts["avg_risk"] or 0})
        return response.Response(serializer.data)

    @decorators.action(detail=True, methods=["get"])
    def export_excel(self, request, pk=None):
        workbook_stream = build_excel(self.get_object())
        return FileResponse(
            workbook_stream,
            as_attachment=True,
            filename=f"documento-{pk}.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    @decorators.action(detail=True, methods=["get"])
    def export_word(self, request, pk=None):
        document_stream = build_word(self.get_object())
        return FileResponse(
            document_stream,
            as_attachment=True,
            filename=f"documento-{pk}.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
