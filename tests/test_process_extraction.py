"""
Tests for multi-process CNJ number extraction and related risk scoring.

Run with:
    python -m pytest tests/test_process_extraction.py -v
"""
import pytest
import sys
import os

# Allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.services import (
    extract_all_process_numbers,
    parse_legal_fields,
    analyze_risk,
)

# ────────────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────────────

SINGLE_PROCESS_TEXT = """
CERTIDÃO DE DISTRIBUIÇÃO
Processo: 0034647-39.1968.8.26.0100
Nada consta no nome do requerente.
"""

MULTI_PROCESS_TEXT = """
CERTIDÃO ESTADUAL DE DISTRIBUIÇÕES CÍVEIS
Os seguintes processos foram localizados:
1) 0034647-39.1968.8.26.0100
2) 0001234-56.2020.8.26.0100
3) 0009876-54.2021.8.26.0100
Certidão emitida em 01/01/2025.
"""

DUPLICATE_PROCESS_TEXT = """
O processo 0034647-39.1968.8.26.0100 foi distribuído em 2020.
Consulte o processo 0034647-39.1968.8.26.0100 para mais detalhes.
Outro processo: 0001111-22.2022.8.26.0100.
"""

MANY_PROCESSES_TEXT = "\n".join(
    f"Processo {i+1}: {str(i+1).zfill(7)}-{str(i+1).zfill(2)}.2020.8.26.0100"
    for i in range(5)
)

NO_PROCESS_TEXT = """
CERTIDÃO NEGATIVA
Nada consta no nome do requerente para o período consultado.
Data: 01/01/2025
"""


# ────────────────────────────────────────────────────────────────────────────
# extract_all_process_numbers
# ────────────────────────────────────────────────────────────────────────────

class TestExtractAllProcessNumbers:
    def test_single_process(self):
        result = extract_all_process_numbers(SINGLE_PROCESS_TEXT)
        assert result == ["0034647-39.1968.8.26.0100"]

    def test_multiple_processes_order_preserved(self):
        result = extract_all_process_numbers(MULTI_PROCESS_TEXT)
        assert result == [
            "0034647-39.1968.8.26.0100",
            "0001234-56.2020.8.26.0100",
            "0009876-54.2021.8.26.0100",
        ]

    def test_duplicates_removed(self):
        result = extract_all_process_numbers(DUPLICATE_PROCESS_TEXT)
        # 0034647 appears twice but must be returned once, 0001111 once
        assert result == [
            "0034647-39.1968.8.26.0100",
            "0001111-22.2022.8.26.0100",
        ]
        assert len(result) == 2

    def test_no_process(self):
        result = extract_all_process_numbers(NO_PROCESS_TEXT)
        assert result == []

    def test_empty_string(self):
        assert extract_all_process_numbers("") == []

    def test_none_safe(self):
        # Should not raise
        result = extract_all_process_numbers(None)  # type: ignore[arg-type]
        assert result == []

    def test_count_reflects_list(self):
        result = extract_all_process_numbers(MANY_PROCESSES_TEXT)
        assert len(result) == 5

    def test_first_matches_parse_legal_fields(self):
        """First element of extract_all_process_numbers must equal parse_legal_fields 'processo' field."""
        result = extract_all_process_numbers(MULTI_PROCESS_TEXT)
        fields = parse_legal_fields(MULTI_PROCESS_TEXT)
        processo_field = next(
            (f["field_value"] for f in fields if f["field_name"] == "processo"), None
        )
        assert result[0] == processo_field


# ────────────────────────────────────────────────────────────────────────────
# parse_legal_fields — backward compatibility
# ────────────────────────────────────────────────────────────────────────────

class TestParseFieldsBackwardCompat:
    def test_single_processo_field_still_returned(self):
        fields = parse_legal_fields(SINGLE_PROCESS_TEXT)
        processo = next((f for f in fields if f["field_name"] == "processo"), None)
        assert processo is not None
        assert processo["field_value"] == "0034647-39.1968.8.26.0100"

    def test_multi_text_returns_first_processo(self):
        fields = parse_legal_fields(MULTI_PROCESS_TEXT)
        processo = next((f for f in fields if f["field_name"] == "processo"), None)
        assert processo is not None
        assert processo["field_value"] == "0034647-39.1968.8.26.0100"

    def test_no_processo_when_absent(self):
        fields = parse_legal_fields(NO_PROCESS_TEXT)
        processo = next((f for f in fields if f["field_name"] == "processo"), None)
        assert processo is None


# ────────────────────────────────────────────────────────────────────────────
# analyze_risk — process_count factor
# ────────────────────────────────────────────────────────────────────────────

class TestAnalyzeRiskProcessCount:
    def _run(self, text: str, process_count: int) -> dict:
        fields = parse_legal_fields(text)
        return analyze_risk(text, fields, [], process_count=process_count)

    def test_zero_processes_no_factor_added(self):
        result = self._run(NO_PROCESS_TEXT, process_count=0)
        rules = {f["rule"] for f in result["risk_factors"]}
        assert "processo_identificado" not in rules
        assert "multiplos_processos_moderado" not in rules
        assert "multiplos_processos_alto" not in rules

    def test_one_process_adds_leve_factor(self):
        result = self._run(SINGLE_PROCESS_TEXT, process_count=1)
        rules = {f["rule"] for f in result["risk_factors"]}
        assert "processo_identificado" in rules

    def test_two_processes_adds_moderado_factor(self):
        result = self._run(MULTI_PROCESS_TEXT, process_count=2)
        rules = {f["rule"] for f in result["risk_factors"]}
        assert "multiplos_processos_moderado" in rules

    def test_three_processes_adds_moderado_factor(self):
        result = self._run(MULTI_PROCESS_TEXT, process_count=3)
        rules = {f["rule"] for f in result["risk_factors"]}
        assert "multiplos_processos_moderado" in rules

    def test_four_plus_processes_adds_alto_factor(self):
        result = self._run(MANY_PROCESSES_TEXT, process_count=5)
        rules = {f["rule"] for f in result["risk_factors"]}
        assert "multiplos_processos_alto" in rules

    def test_risk_increases_with_more_processes(self):
        score_zero = self._run(NO_PROCESS_TEXT, process_count=0)["score"]
        score_one = self._run(NO_PROCESS_TEXT, process_count=1)["score"]
        score_many = self._run(NO_PROCESS_TEXT, process_count=5)["score"]
        assert score_zero <= score_one
        assert score_one < score_many

    def test_process_count_in_return_dict(self):
        result = self._run(SINGLE_PROCESS_TEXT, process_count=1)
        assert result["process_count"] == 1

    def test_backward_compat_no_process_count_arg(self):
        """Calling without process_count must not raise (defaults to 0)."""
        fields = parse_legal_fields(NO_PROCESS_TEXT)
        result = analyze_risk(NO_PROCESS_TEXT, fields, [])
        assert "score" in result
        assert result["process_count"] == 0

    def test_summary_mentions_multiple_processes(self):
        result = self._run(MULTI_PROCESS_TEXT, process_count=3)
        assert "3" in result["summary"]

    def test_frontend_safe_when_process_numbers_empty(self):
        """process_count=0 must return a fully-formed result without errors."""
        result = self._run("", process_count=0)
        assert isinstance(result["score"], int)
        assert isinstance(result["risk_factors"], list)
        assert result["process_count"] == 0
