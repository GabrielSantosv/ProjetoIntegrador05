"""Celery application bootstrap."""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "legal_docs.settings")

app = Celery("legal_docs")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
