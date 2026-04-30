"""Rule-based extraction for Brazilian legal PDFs."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
import re
from typing import Any


CPF_RE = re.compile(r"\b(\d{3}\.?\d{3}\.?\d{3}-?\d{2})\b")
PROCESS_RE = re.compile(r"\b(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})\b")
DATE_RE = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b")
ISO_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
MONEY_RE = re.compile(r"(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})")

LABEL_PATTERNS = {
    "nome": [
        r"contra:.*?\s+([A-ZÀ-Ú][A-ZÀ-Ú\s]{6,80}),\s*RG\s*:",
        r"([A-ZÀ-Ú][A-ZÀ-Ú\s]{6,80}),\s*RG\s*:.*?CPF\s*:",
        r"(?:nome|requerente|interessado|parte|autor|reu)\s*:?\s*([A-ZÀ-Ú][A-Za-zÀ-ú'\s]{4,80})",
    ],
    "tipo_acao": [
        r"(?:classe|tipo de acao|natureza)\s*:?\s*([A-Za-zÀ-ú\s]{5,80})",
    ],
    "situacao_processual": [
        r"(?:situacao processual|situacao|status|resultado)\s*:?\s*([A-Za-zÀ-ú\s]{5,120})",
        r"(nada\s+(?:consta|constar))",
    ],
    "vara": [
        r"((?:\d+[a-zªº]*\s*)?vara\s+(?:civel|criminal|federal|do trabalho|da familia)\.?)",
        r"((?:\d+[a-zªº]*\s*)?vara\s+(?:civel|criminal|federal|do trabalho|da familia)\s*\d*)",
        r"(vara\s+(?:civel|criminal|federal|do trabalho|da familia)\s*\d*)",
    ],
    "foro": [
        r"(foro\s+de\s+[A-Za-zÀ-ú\s]{4,80})\s*-",
        r"(?:foro|forum|comarca)\s*:?\s*([A-Za-zÀ-ú\s]{4,80})",
    ],
}

DOCUMENT_RULES = {
    "certidao criminal": {
        "tipo_acao_default": "Certidao Criminal",
        "risk_terms": ["condenacao", "prisao", "criminal", "execucao penal", "antecedente"],
    },
    "certidao civel": {
        "tipo_acao_default": "Acao Civel",
        "risk_terms": ["execucao", "penhora", "cobranca", "indenizacao", "falencia"],
    },
    "cndt": {
        "tipo_acao_default": "Certidao Negativa de Debitos Trabalhistas",
        "risk_terms": ["debito trabalhista", "inadimplente", "positiva"],
    },
    "certidao de distribuicao": {
        "tipo_acao_default": "Certidao de Distribuicao",
        "risk_terms": ["distribuido", "processo encontrado", "consta"],
    },
}


def parse_legal_fields(text: str, document_type: str = "", pages: list[dict] | None = None) -> dict:
    """Extract and validate legal fields from text and optional page coordinates."""
    normalized_text = _normalize_spaces(text)
    pages = pages or []

    fields = {
        "nome": _extract_labeled_field(normalized_text, "nome"),
        "cpf": _format_cpf(_first(CPF_RE.findall(normalized_text))),
        "numero_processo": _first(PROCESS_RE.findall(normalized_text)),
        "data": _extract_date(normalized_text),
        "valor": _extract_money(normalized_text),
        "tipo_acao": _extract_labeled_field(normalized_text, "tipo_acao"),
        "situacao_processual": _extract_labeled_field(normalized_text, "situacao_processual"),
        "vara": _extract_labeled_field(normalized_text, "vara"),
        "foro": _extract_labeled_field(normalized_text, "foro"),
    }

    geometric_process = extract_process_by_geometry(pages)
    if not fields["numero_processo"] and geometric_process:
        fields["numero_processo"] = geometric_process

    fields = _apply_document_rules(fields, normalized_text, document_type)
    validation = validate_extracted_data(fields)
    risk = score_risk(fields, normalized_text, document_type)

    return {
        **fields,
        "risco": risk,
        "nivel_risco": _risk_label(risk),
        "validacao": validation,
        "revisao_manual": validation["requires_manual_review"],
        "geometria": {"numero_processo": geometric_process},
    }


def extract_process_by_geometry(pages: list[dict]) -> str:
    """Find a process number using page coordinates in likely header/metadata regions."""
    candidates: list[tuple[float, str]] = []
    for page in pages:
        height = float(page.get("height") or 0)
        width = float(page.get("width") or 0)
        words = page.get("words") or []
        for index, word in enumerate(words):
            text = str(word.get("text", ""))
            if PROCESS_RE.fullmatch(text):
                top = float(word.get("top") or 0)
                x0 = float(word.get("x0") or 0)
                score = 0.0
                if height and top <= height * 0.35:
                    score += 2.0
                if width and x0 >= width * 0.45:
                    score += 1.0
                candidates.append((score, text))

            joined = _join_nearby_words(words[index:index + 8])
            match = PROCESS_RE.search(joined)
            if match:
                top = float(word.get("top") or 0)
                score = 1.0 + (1.0 if height and top <= height * 0.35 else 0.0)
                candidates.append((score, match.group(1)))

    if not candidates:
        return ""
    return sorted(candidates, key=lambda item: item[0], reverse=True)[0][1]


def validate_extracted_data(fields: dict) -> dict:
    """Validate required fields and return issues for manual review."""
    required = ["nome", "cpf", "data"]
    issues = []
    missing = [field for field in required if not fields.get(field)]
    if missing:
        issues.append(f"Campos obrigatorios ausentes: {', '.join(missing)}")

    cpf = fields.get("cpf") or ""
    if cpf and not _is_valid_cpf(cpf):
        issues.append("CPF invalido ou inconsistente")

    if fields.get("data") and not _is_valid_iso_date(fields["data"]):
        issues.append("Data invalida")

    if not fields.get("numero_processo") and _looks_like_positive_certificate(fields):
        issues.append("Situacao indica possivel ocorrencia, mas numero do processo nao foi encontrado")

    return {
        "is_valid": not issues,
        "requires_manual_review": bool(issues),
        "missing_fields": missing,
        "issues": issues,
    }


def score_risk(parsed_data: dict, text: str, document_type: str = "") -> int:
    """Compute risk with low risk for 'nada consta' and stronger signals for found records."""
    situation = str(parsed_data.get("situacao_processual") or "").lower()
    lowered = text.lower()
    if "nada consta" in situation or "nada constar" in situation or "nada consta" in lowered:
        return 5

    rules = DOCUMENT_RULES.get(document_type.lower(), {})
    risk_terms = [
        "penhora",
        "execucao",
        "protesto",
        "indisponibilidade",
        "debito",
        "condenacao",
        "consta",
        *rules.get("risk_terms", []),
    ]
    term_points = sum(12 for term in set(risk_terms) if term in lowered)
    process_points = 20 if parsed_data.get("numero_processo") else 0
    value_points = 15 if parsed_data.get("valor") else 0
    review_points = 10 if parsed_data.get("revisao_manual") else 0
    return min(100, max(20 if process_points else 0, term_points + process_points + value_points + review_points))


def _apply_document_rules(fields: dict, text: str, document_type: str) -> dict:
    rules = DOCUMENT_RULES.get(document_type.lower(), {})
    if not fields["tipo_acao"] and rules.get("tipo_acao_default"):
        fields["tipo_acao"] = rules["tipo_acao_default"]

    lowered = text.lower()
    if not fields["situacao_processual"]:
        if "nada consta" in lowered or "nada constar" in lowered:
            fields["situacao_processual"] = "Nada consta"
        elif fields["numero_processo"] or "consta" in lowered:
            fields["situacao_processual"] = "Ocorrencia encontrada"

    if document_type.lower() == "cndt" and not fields["foro"]:
        fields["foro"] = "Justica do Trabalho"
    return fields


def _extract_labeled_field(text: str, field: str) -> str:
    for pattern in LABEL_PATTERNS[field]:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _clean_value(match.group(1), field)
    return ""


def _extract_date(text: str) -> str:
    iso = _first(ISO_DATE_RE.findall(text))
    if iso:
        return iso
    value = _first(DATE_RE.findall(text))
    if not value:
        return ""
    for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return ""


def _extract_money(text: str) -> float | None:
    match = MONEY_RE.search(text)
    if not match:
        return None
    normalized = match.group(1).replace(".", "").replace(",", ".")
    try:
        return float(Decimal(normalized))
    except InvalidOperation:
        return None


def _format_cpf(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) != 11:
        return ""
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def _is_valid_cpf(value: str) -> bool:
    digits = [int(char) for char in re.sub(r"\D", "", value)]
    if len(digits) != 11 or len(set(digits)) == 1:
        return False

    for length in (9, 10):
        total = sum(digit * weight for digit, weight in zip(digits[:length], range(length + 1, 1, -1)))
        check = (total * 10) % 11
        if check == 10:
            check = 0
        if check != digits[length]:
            return False
    return True


def _is_valid_iso_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _looks_like_positive_certificate(fields: dict) -> bool:
    situation = str(fields.get("situacao_processual") or "").lower()
    if "nada consta" in situation or "nada constar" in situation:
        return False
    return any(term in situation for term in ["ocorrencia", "em andamento", "consta", "distribuido"])


def _clean_value(value: str, field: str = "") -> str:
    stop_pattern = r"\s{2,}| cpf\b| processo\b| data\b| valor\b| situacao\b"
    if field not in {"vara", "foro"}:
        stop_pattern += r"| vara\b| foro\b| forum\b"
    if field == "foro":
        stop_pattern += r"| vara\b"
    value = re.split(stop_pattern, value.strip(), flags=re.IGNORECASE)[0]
    return " ".join(value.strip(":-.,; ").split())


def _join_nearby_words(words: list[dict[str, Any]]) -> str:
    return "".join(str(word.get("text", "")) for word in words)


def _normalize_spaces(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text or "")


def _risk_label(score: int) -> str:
    if score <= 20:
        return "baixo"
    if score <= 60:
        return "medio"
    return "alto"


def _first(values: list[str]) -> str:
    return values[0] if values else ""
