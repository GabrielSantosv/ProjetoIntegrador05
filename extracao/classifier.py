from __future__ import annotations

from pathlib import Path

try:
    from joblib import load
except Exception:  # pragma: no cover
    load = None

# ---------------------------------------------------------------------------
# Hierarquia de risco por tipo de documento
# ---------------------------------------------------------------------------
RISK_MAP: dict[str, str] = {
    # Risco Máximo
    "civel_estadual": "maximo",
    "cnd_federal": "maximo",
    "civel_federal": "maximo",
    "cnd_estadual": "maximo",
    # Risco Médio
    "cndt": "medio",
    "criminal_estadual": "medio",
    "criminal_federal": "medio",
    # Risco Informativo
    "trf3": "informativo",
    "ceat": "informativo",
    "eleitoral": "informativo",
    # Fallback
    "desconhecido": "informativo",
}


class DocumentClassifier:
    def __init__(self, model_path: Path | None = None) -> None:
        self.model_path = model_path
        self.model = None
        if model_path and load and model_path.exists():
            self.model = load(model_path)

    def classify(self, text: str) -> str:
        """Retorna o tipo granular do documento."""
        if self.model is not None:
            try:
                return str(self.model.predict([text])[0])
            except Exception:
                pass

        normalized = text.lower()

        # --- TJSP: separar Cível de Criminal ---
        if "distribuições criminais" in normalized:
            return "criminal_estadual"
        if "distribuições cíveis" in normalized or "distribuicoes civeis" in normalized:
            return "civel_estadual"

        # --- Federal: separar CND (fiscal) de TRF3 (judicial) ---
        if "débitos relativos a tributos federais" in normalized or "debitos relativos a tributos federais" in normalized:
            return "cnd_federal"
        if "tribunal regional federal" in normalized or "trf" in normalized:
            return "trf3"

        # --- Trabalhista ---
        if "certidão negativa de débitos trabalhistas" in normalized or "cndt" in normalized:
            return "cndt"
        if "ceat" in normalized or "certidão de ações trabalhistas" in normalized:
            return "ceat"
        if any(k in normalized for k in ["trt", "tribunal regional do trabalho"]):
            return "cndt"

        # --- Estadual não-TJSP ---
        if any(k in normalized for k in ["cnd estadual", "certidão negativa estadual", "sefaz", "ceat"]):
            return "cnd_estadual"

        # --- Federal judicial (TRF) separado de fiscal (CND) ---
        if "justiça federal" in normalized or "civel federal" in normalized:
            return "civel_federal"
        if "criminal federal" in normalized:
            return "criminal_federal"

        # --- Eleitoral ---
        if "tribunal superior eleitoral" in normalized or "tse" in normalized or "eleitoral" in normalized:
            return "eleitoral"

        return "desconhecido"

    def nivel_risco(self, document_type: str) -> str:
        """Retorna o nível de risco para o tipo identificado."""
        return RISK_MAP.get(document_type, "informativo")
