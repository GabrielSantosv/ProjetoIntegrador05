from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import pdfplumber

from .profiles import DocumentProfile, get_profile

# ---------------------------------------------------------------------------
# Padrões globais
# ---------------------------------------------------------------------------
CPF_REGEX = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
PROCESS_REGEX = re.compile(r"\b\d{7,8}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b")
DATE_REGEX = re.compile(r"\b\d{2}/\d{2}/\d{4}\b")
MONEY_REGEX = re.compile(r"R\$\s?\d{1,3}(?:\.\d{3})*,\d{2}")
NAME_HINT_REGEX = re.compile(
    r"(?:nome|interessado|requerente|autor)[:\-]?\s*([A-ZÀ-Ü][A-ZÀ-Ü\s]{3,})",
    re.IGNORECASE,
)

# Frase que indica que o CPF-alvo não tem processos (homônimos a ignorar)
NADA_CONSTAR_REGEX = re.compile(
    r"verificou\s+nada\s+constar|nada\s+constar|sem\s+ocorrências",
    re.IGNORECASE,
)

# Marcador geométrico de início de processo na margem esquerda (TJSP usa "»")
PROCESS_BULLET_CHAR = "»"
# Tolerância X para considerar que um word está na margem esquerda (pts)
LEFT_MARGIN_TOLERANCE = 20.0


@dataclass
class ParsedFields:
    name: str | None = None
    cpf: str | None = None
    process_number: str | None = None
    date: str | None = None
    value: str | None = None
    tipo_acao: str | None = None
    situacao_processual: str | None = None
    vara: str | None = None
    foro: str | None = None
    status: str | None = None           # "NADA CONSTAR" | "POSITIVA"
    processes_from_geometry: list[str] = field(default_factory=list)
    extra_fields: dict[str, str | None] = field(default_factory=dict)


class RegexParser:
    """Parser baseado em Regex + extração geométrica via pdfplumber."""

    def __init__(self, profile: str = "generic") -> None:
        self.profile = get_profile(profile)

    # ------------------------------------------------------------------
    # Ponto de entrada: texto plano (compatibilidade legada)
    # ------------------------------------------------------------------
    def parse(self, text: str) -> ParsedFields:
        return self._parse_text(text)

    # ------------------------------------------------------------------
    # Ponto de entrada aprimorado: recebe página pdfplumber diretamente
    # Permite extração geométrica + lógica de homônimos por CPF-alvo
    # ------------------------------------------------------------------
    def parse_page(
        self,
        page: "pdfplumber.page.Page",  # type: ignore[name-defined]
        cpf_alvo: str | None = None,
    ) -> ParsedFields:
        """
        Extrai campos de uma página pdfplumber.

        - Se *cpf_alvo* for fornecido, verifica se "NADA CONSTAR" aparece logo
          após o CPF. Nesse caso marca status="NADA CONSTAR" e a chamada retorna
          sem processar o restante da página (lógica de interrupção de homônimos).
        - Usa coordenadas X/Y para capturar processos que iniciam com o marcador
          "»" na margem esquerda, descartando rodapés e títulos.
        """
        text: str = page.extract_text(x_tolerance=2, y_tolerance=2) or ""

        # 1. Detectar status NADA CONSTAR referente ao CPF-alvo
        status = self._detect_status(text, cpf_alvo)
        if status == "NADA CONSTAR":
            # Interrompe: não há processos reais do titular nesta certidão
            parsed = self._parse_text(text)
            parsed.status = "NADA CONSTAR"
            parsed.processes_from_geometry = []
            return parsed

        # 2. Extração geométrica de processos via coordenadas
        geo_processes = self._extract_processes_geometric(page)

        # 3. Parse de campos textuais normais
        parsed = self._parse_text(text)
        parsed.status = status
        parsed.processes_from_geometry = geo_processes
        return parsed

    # ------------------------------------------------------------------
    # Detecção de NADA CONSTAR para o CPF-alvo
    # ------------------------------------------------------------------
    @staticmethod
    def _detect_status(text: str, cpf_alvo: str | None) -> str:
        """
        Retorna "NADA CONSTAR" se a frase aparecer próxima ao CPF-alvo,
        caso contrário retorna "POSITIVA".
        """
        if not cpf_alvo:
            # Sem CPF-alvo: verifica se o documento inteiro é negativo
            if NADA_CONSTAR_REGEX.search(text):
                return "NADA CONSTAR"
            return "POSITIVA"

        # Localiza o CPF no texto e verifica as 500 chars seguintes
        idx = text.find(cpf_alvo)
        if idx == -1:
            return "POSITIVA"

        janela = text[idx: idx + 500]
        if NADA_CONSTAR_REGEX.search(janela):
            return "NADA CONSTAR"
        return "POSITIVA"

    # ------------------------------------------------------------------
    # Extração geométrica: processa marcador "»" na margem esquerda
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_processes_geometric(page: Any) -> list[str]:
        """
        Usa coordenadas X do pdfplumber para identificar processos que começam
        com o caractere '»' na margem esquerda do documento.
        Descarta elementos de rodapé (y > 90% da altura da página).
        """
        processes: list[str] = []

        try:
            words = page.extract_words(x_tolerance=2, y_tolerance=2)
        except Exception:
            return processes

        page_height = float(page.height)
        footer_threshold = page_height * 0.90

        # Determinar a margem esquerda mínima da página
        x_values = [float(w["x0"]) for w in words if w.get("text", "").strip()]
        if not x_values:
            return processes
        left_margin = min(x_values)

        # Agrupar palavras por linha (top aproximado — pdfplumber usa "top", não "y0")
        lines: dict[int, list[dict]] = {}
        for w in words:
            y_key = round(float(w["top"]) / 3) * 3  # bucket de 3pts
            lines.setdefault(y_key, []).append(w)

        for y_key in sorted(lines.keys()):
            line_words = sorted(lines[y_key], key=lambda w: float(w["x0"]))
            if not line_words:
                continue

            first_word = line_words[0]
            y0 = float(first_word["top"])
            x0 = float(first_word["x0"])
            text_word = first_word.get("text", "").strip()

            # Ignorar rodapé
            if y0 > footer_threshold:
                continue

            # Processo deve iniciar com "»" na margem esquerda
            if text_word == PROCESS_BULLET_CHAR and (x0 - left_margin) <= LEFT_MARGIN_TOLERANCE:
                line_text = " ".join(w.get("text", "") for w in line_words)
                match = PROCESS_REGEX.search(line_text)
                if match:
                    processes.append(match.group(0))

        return processes

    # ------------------------------------------------------------------
    # Parse de campos via Regex (texto plano)
    # ------------------------------------------------------------------
    def _parse_text(self, text: str) -> ParsedFields:
        normalized = " ".join(text.split())
        cpf = self._first_match(CPF_REGEX, normalized)
        process_number = self._first_match(PROCESS_REGEX, normalized)
        date = self._first_match(DATE_REGEX, normalized)
        value = self._first_match(MONEY_REGEX, normalized)
        name = self._parse_name(normalized)
        extra = self._parse_profile_fields(normalized, self.profile)

        return ParsedFields(
            name=name,
            cpf=cpf,
            process_number=process_number,
            date=date,
            value=value,
            tipo_acao=extra.pop("tipo_acao", None),
            situacao_processual=extra.pop("situacao_processual", None),
            vara=extra.pop("vara", None),
            foro=extra.pop("foro", None),
            extra_fields=extra,
        )

    @staticmethod
    def _first_match(pattern: re.Pattern[str], text: str) -> str | None:
        match = pattern.search(text)
        return match.group(0) if match else None

    @staticmethod
    def _parse_name(text: str) -> str | None:
        match = NAME_HINT_REGEX.search(text)
        if match:
            return " ".join(match.group(1).split()).title()
        return None

    @staticmethod
    def _parse_profile_fields(text: str, profile: DocumentProfile) -> dict[str, str | None]:
        extracted: dict[str, str | None] = {}
        for field_name, pattern in profile.field_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip() if match.groups() else match.group(0).strip()
            else:
                value = None
            extracted[field_name] = value
        return extracted
