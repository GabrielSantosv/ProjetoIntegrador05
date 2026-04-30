# Generated for the MVP scaffold.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="Document",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("file", models.FileField(upload_to="documents/%Y/%m/")),
                ("status", models.CharField(choices=[("pending", "Pendente"), ("processing", "Processando"), ("done", "Concluido"), ("failed", "Falhou")], default="pending", max_length=20)),
                ("document_type", models.CharField(blank=True, max_length=120)),
                ("extracted_text", models.TextField(blank=True)),
                ("extracted_data", models.JSONField(blank=True, default=dict)),
                ("entities", models.JSONField(blank=True, default=list)),
                ("legal_opinion", models.TextField(blank=True)),
                ("risk_score", models.PositiveSmallIntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="documents", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
