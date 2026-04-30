"""Certificate type classification service."""
import requests
from django.conf import settings


LABELS = [
    "certidao civel",
    "certidao criminal",
    "cndt",
    "certidao de distribuicao",
    "certidao negativa",
    "certidao positiva",
    "outro documento juridico",
]


def classify_certificate_type(text: str) -> str:
    """Classify certificate type using HuggingFace zero-shot API with keyword fallback."""
    return _keyword_fallback(text) if not settings.HUGGINGFACE_API_TOKEN else _classify_with_hf(text)


def _classify_with_hf(text: str) -> str:
    try:
        response = requests.post(
            f"https://api-inference.huggingface.co/models/{settings.HF_CLASSIFIER_MODEL}",
            headers={"Authorization": f"Bearer {settings.HUGGINGFACE_API_TOKEN}"},
            json={"inputs": text[:4000], "parameters": {"candidate_labels": LABELS}},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        labels = payload.get("labels") or []
        return labels[0] if labels else _keyword_fallback(text)
    except requests.RequestException:
        return _keyword_fallback(text)


def _keyword_fallback(text: str) -> str:
    lowered = text.lower()
    if "certidao negativa de debitos trabalhistas" in lowered or "cndt" in lowered:
        return "cndt"
    if "criminal" in lowered or "antecedentes criminais" in lowered:
        return "certidao criminal"
    if "civel" in lowered or "civil" in lowered or "vara civel" in lowered:
        return "certidao civel"
    if "distribuicao" in lowered or "distribuidor" in lowered:
        return "certidao de distribuicao"
    if "nada consta" in lowered or "negativa" in lowered:
        return "certidao negativa"
    if "positiva" in lowered or "consta" in lowered:
        return "certidao positiva"
    return "outro documento juridico"
