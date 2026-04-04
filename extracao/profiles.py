from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentProfile:
    name: str
    field_patterns: dict[str, str]
    keywords: tuple[str, ...] = ()


PROFILES: dict[str, DocumentProfile] = {
    "generic": DocumentProfile(
        name="generic",
        keywords=(),
        field_patterns={
            "cpf": r"\b(\d{3}\.\d{3}\.\d{3}-\d{2})\b",
            "process_number": r"\b(\d{7,8}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})\b",
            "date": r"\b(\d{2}/\d{2}/\d{4})\b",
            "value": r"(R\$\s?\d{1,3}(?:\.\d{3})*,\d{2})",
            "name": r"(?:nome|interessado|requerente|autor)[:\-]?\s*([A-ZÀ-Ü][A-ZÀ-Ü\s]{3,})",
        },
    ),
    "tj": DocumentProfile(
        name="tj",
        keywords=("tribunal de justiça", "tj", "certidão"),
        field_patterns={
            "orgao": r"(?:tribunal de justiça|tj[a-z\s]*)[:\-]?\s*([A-ZÀ-Ü\s]{3,})",
            "cpf": r"\b(\d{3}\.\d{3}\.\d{3}-\d{2})\b",
            "process_number": r"\b(\d{7,8}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})\b",
            "assunto": r"(?:assunto|classe)[:\-]?\s*([A-ZÀ-Ü0-9\s]{3,})",
        },
    ),
    "trt": DocumentProfile(
        name="trt",
        keywords=("tribunal regional do trabalho", "trt", "trabalho"),
        field_patterns={
            "vara": r"(?:vara|gabinete)[:\-]?\s*([A-ZÀ-Ü0-9\s]{3,})",
            "cpf": r"\b(\d{3}\.\d{3}\.\d{3}-\d{2})\b",
            "process_number": r"\b(\d{7,8}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})\b",
            "reclamante": r"(?:reclamante)[:\-]?\s*([A-ZÀ-Ü\s]{3,})",
            "reclamado": r"(?:reclamado)[:\-]?\s*([A-ZÀ-Ü\s]{3,})",
        },
    ),
    "alvara": DocumentProfile(
        name="alvara",
        keywords=("alvará", "alvara"),
        field_patterns={
            "beneficiario": r"(?:beneficiário|beneficiario)[:\-]?\s*([A-ZÀ-Ü\s]{3,})",
            "cpf": r"\b(\d{3}\.\d{3}\.\d{3}-\d{2})\b",
            "value": r"(R\$\s?\d{1,3}(?:\.\d{3})*,\d{2})",
        },
    ),
}


def get_profile(name: str | None) -> DocumentProfile:
    if not name:
        return PROFILES["generic"]
    normalized = name.strip().lower()
    return PROFILES.get(normalized, PROFILES["generic"])