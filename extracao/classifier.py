from __future__ import annotations

from pathlib import Path

try:
    from joblib import load
except Exception:  # pragma: no cover - fallback for environments without joblib
    load = None


class DocumentClassifier:
    def __init__(self, model_path: Path | None = None) -> None:
        self.model_path = model_path
        self.model = None
        if model_path and load and model_path.exists():
            self.model = load(model_path)

    def classify(self, text: str) -> str:
        if self.model is not None:
            try:
                return str(self.model.predict([text])[0])
            except Exception:
                pass

        normalized = text.lower()
        if any(keyword in normalized for keyword in ["certidão", "certidao", "tribunal de justiça", "tj"]):
            return "certidao_tj"
        if any(keyword in normalized for keyword in ["trt", "tribunal regional do trabalho"]):
            return "certidao_trt"
        if any(keyword in normalized for keyword in ["alvará", "alvara"]):
            return "alvara"
        return "desconhecido"
