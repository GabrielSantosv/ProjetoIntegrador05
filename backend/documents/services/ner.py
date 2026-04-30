"""Named Entity Recognition service for Portuguese legal text."""
import re
import requests
from django.conf import settings


def extract_named_entities(text: str) -> list[dict]:
    """Extract PESSOA, LOCAL and TEMPO entities via HuggingFace, with regex fallback for dates."""
    if not settings.HUGGINGFACE_API_TOKEN:
        return _date_fallback(text)

    try:
        response = requests.post(
            f"https://api-inference.huggingface.co/models/{settings.HF_NER_MODEL}",
            headers={"Authorization": f"Bearer {settings.HUGGINGFACE_API_TOKEN}"},
            json={"inputs": text[:4000]},
            timeout=60,
        )
        response.raise_for_status()
        return _normalize_entities(response.json())
    except requests.RequestException:
        return _date_fallback(text)


def _normalize_entities(payload: list[dict]) -> list[dict]:
    wanted = {"PESSOA", "LOCAL", "TEMPO", "PER", "LOC", "TIME", "DATE"}
    entities = []
    for item in payload:
        label = str(item.get("entity_group") or item.get("entity") or "").replace("B-", "").replace("I-", "")
        if label in wanted:
            entities.append({
                "label": _map_label(label),
                "text": item.get("word", "").replace(" ##", ""),
                "score": round(float(item.get("score", 0)), 4),
            })
    return entities


def _map_label(label: str) -> str:
    return {"PER": "PESSOA", "LOC": "LOCAL", "TIME": "TEMPO", "DATE": "TEMPO"}.get(label, label)


def _date_fallback(text: str) -> list[dict]:
    return [
        {"label": "TEMPO", "text": match.group(0), "score": 1.0}
        for match in re.finditer(r"\d{2}/\d{2}/\d{4}", text)
    ]
