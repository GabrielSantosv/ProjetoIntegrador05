from __future__ import annotations

import re
from dataclasses import dataclass

from .profiles import DocumentProfile, get_profile

CPF_REGEX = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
PROCESS_REGEX = re.compile(r"\b\d{7,8}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b")
DATE_REGEX = re.compile(r"\b\d{2}/\d{2}/\d{4}\b")
MONEY_REGEX = re.compile(r"R\$\s?\d{1,3}(?:\.\d{3})*,\d{2}")
NAME_HINT_REGEX = re.compile(r"(?:nome|interessado|requerente|autor)[:\-]?\s*([A-ZÀ-Ü][A-ZÀ-Ü\s]{3,})", re.IGNORECASE)


@dataclass
class ParsedFields:
    name: str | None = None
    cpf: str | None = None
    process_number: str | None = None
    date: str | None = None
    value: str | None = None
    extra_fields: dict[str, str | None] | None = None


class RegexParser:
    def __init__(self, profile: str = "generic") -> None:
        self.profile = get_profile(profile)

    def parse(self, text: str) -> ParsedFields:
        normalized = " ".join(text.split())
        cpf = self._first_match(CPF_REGEX, normalized)
        process_number = self._first_match(PROCESS_REGEX, normalized)
        date = self._first_match(DATE_REGEX, normalized)
        value = self._first_match(MONEY_REGEX, normalized)
        name = self._parse_name(normalized)
        extra_fields = self._parse_profile_fields(normalized, self.profile)
        return ParsedFields(name=name, cpf=cpf, process_number=process_number, date=date, value=value, extra_fields=extra_fields)

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

    def _parse_profile_fields(self, text: str, profile: DocumentProfile) -> dict[str, str | None]:
        extracted: dict[str, str | None] = {}
        for field_name, pattern in profile.field_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            extracted[field_name] = match.group(1).strip() if match and match.groups() else (match.group(0).strip() if match else None)
        return extracted
