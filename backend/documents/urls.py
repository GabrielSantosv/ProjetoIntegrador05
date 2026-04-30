from django.urls import include, path
from rest_framework.routers import DefaultRouter

from documents.views import DocumentViewSet

router = DefaultRouter()
router.register("documents", DocumentViewSet, basename="documents")

urlpatterns = [path("", include(router.urls))]
