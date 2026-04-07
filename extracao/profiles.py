from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentProfile:
    name: str
    field_patterns: dict[str, str]
    keywords: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Perfis granulares por tipo de certidão
# ---------------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Certidão Cível Estadual (TJSP) — Risco MÁXIMO
    # Keyword gatilho: "Distribuições Cíveis"
    # ------------------------------------------------------------------
    "civel_estadual": DocumentProfile(
        name="civel_estadual",
        keywords=("distribuições cíveis", "tjsp", "tribunal de justiça"),
        field_patterns={
            "cpf": r"\b(\d{3}\.\d{3}\.\d{3}-\d{2})\b",
            "process_number": r"\b(\d{7,8}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})\b",
            "tipo_acao": r"(?:classe|tipo de ação)[:\-]?\s*([A-ZÀ-Üa-zà-ü\s]{3,}?)(?=\n|vara|foro|$)",
            "situacao_processual": r"(?:situação|situacao|fase)[:\-]?\s*([A-ZÀ-Üa-zà-ü\s]{3,}?)(?=\n|$)",
            "vara": r"(?:vara)[:\-]?\s*([A-ZÀ-Ü0-9ª\.ºa-zà-ü\s]{3,}?)(?=\n|foro|$)",
            "foro": r"(?:foro|comarca)[:\-]?\s*([A-ZÀ-Üa-zà-ü\s]{3,}?)(?=\n|vara|$)",
        },
    ),

    # ------------------------------------------------------------------
    # Certidão Criminal Estadual (TJSP) — Risco MÉDIO
    # Keyword gatilho: "Distribuições Criminais"
    # ------------------------------------------------------------------
    "criminal_estadual": DocumentProfile(
        name="criminal_estadual",
        keywords=("distribuições criminais", "tjsp", "criminal"),
        field_patterns={
            "cpf": r"\b(\d{3}\.\d{3}\.\d{3}-\d{2})\b",
            "process_number": r"\b(\d{7,8}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})\b",
            "tipo_acao": r"(?:classe|tipo de ação)[:\-]?\s*([A-ZÀ-Üa-zà-ü\s]{3,}?)(?=\n|vara|foro|$)",
            "situacao_processual": r"(?:situação|situacao)[:\-]?\s*([A-ZÀ-Üa-zà-ü\s]{3,}?)(?=\n|$)",
            "vara": r"(?:vara)[:\-]?\s*([A-ZÀ-Ü0-9ª\.ºa-zà-ü\s]{3,}?)(?=\n|foro|$)",
            "foro": r"(?:foro|comarca)[:\-]?\s*([A-ZÀ-Üa-zà-ü\s]{3,}?)(?=\n|$)",
        },
    ),

    # ------------------------------------------------------------------
    # CND Federal — Risco MÁXIMO (04a_CND_Federal)
    # Keyword gatilho: "Débitos Relativos a Tributos Federais"
    # ------------------------------------------------------------------
    "cnd_federal": DocumentProfile(
        name="cnd_federal",
        keywords=("débitos relativos a tributos federais", "receita federal", "pgfn"),
        field_patterns={
            "cpf": r"\b(\d{3}\.\d{3}\.\d{3}-\d{2})\b",
            "name": r"(?:nome|contribuinte)[:\-]?\s*([A-ZÀ-Ü][A-ZÀ-Ü\s]{3,})",
            "date": r"\b(\d{2}/\d{2}/\d{4})\b",
        },
    ),

    # ------------------------------------------------------------------
    # TRF3 — Risco INFORMATIVO (04b_TRF3)
    # ------------------------------------------------------------------
    "trf3": DocumentProfile(
        name="trf3",
        keywords=("tribunal regional federal", "trf3", "trf"),
        field_patterns={
            "cpf": r"\b(\d{3}\.\d{3}\.\d{3}-\d{2})\b",
            "process_number": r"\b(\d{7,8}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})\b",
            "tipo_acao": r"(?:classe|tipo de ação)[:\-]?\s*([A-ZÀ-Üa-zà-ü\s]{3,}?)(?=\n|vara|$)",
            "vara": r"(?:vara|seção)[:\-]?\s*([A-ZÀ-Ü0-9ª\.ºa-zà-ü\s]{3,}?)(?=\n|$)",
            "foro": r"(?:subseção|foro)[:\-]?\s*([A-ZÀ-Üa-zà-ü\s]{3,}?)(?=\n|$)",
        },
    ),

    # ------------------------------------------------------------------
    # CNDT — Risco MÉDIO
    # ------------------------------------------------------------------
    "cndt": DocumentProfile(
        name="cndt",
        keywords=("certidão negativa de débitos trabalhistas", "cndt", "tst"),
        field_patterns={
            "cpf": r"\b(\d{3}\.\d{3}\.\d{3}-\d{2})\b",
            "name": r"(?:nome|interessado)[:\-]?\s*([A-ZÀ-Ü][A-ZÀ-Ü\s]{3,})",
            "date": r"\b(\d{2}/\d{2}/\d{4})\b",
        },
    ),

    # ------------------------------------------------------------------
    # CEAT — Risco INFORMATIVO
    # ------------------------------------------------------------------
    "ceat": DocumentProfile(
        name="ceat",
        keywords=("ceat", "certidão de ações trabalhistas"),
        field_patterns={
            "cpf": r"\b(\d{3}\.\d{3}\.\d{3}-\d{2})\b",
            "process_number": r"\b(\d{7,8}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})\b",
            "tipo_acao": r"(?:tipo|classe)[:\-]?\s*([A-ZÀ-Üa-zà-ü\s]{3,}?)(?=\n|$)",
            "situacao_processual": r"(?:situação|situacao)[:\-]?\s*([A-ZÀ-Üa-zà-ü\s]{3,}?)(?=\n|$)",
            "vara": r"(?:vara)[:\-]?\s*([A-ZÀ-Ü0-9ª\.ºa-zà-ü\s]{3,}?)(?=\n|$)",
        },
    ),
}


def get_profile(name: str | None) -> DocumentProfile:
    if not name:
        return PROFILES["generic"]
    normalized = name.strip().lower()
    return PROFILES.get(normalized, PROFILES["generic"])
