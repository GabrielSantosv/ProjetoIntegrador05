"""HuggingFace Inference API client."""
import requests
from django.conf import settings


class HuggingFaceClient:
    def __init__(self) -> None:
        self.token = settings.HUGGINGFACE_API_TOKEN
        self.model = settings.HUGGINGFACE_MISTRAL_MODEL

    def generate_legal_opinion(self, text: str, extracted_data: dict, document_type: str) -> str:
        """Ask Mistral for a short legal opinion; return a useful fallback without a token."""
        if not self.token:
            return "Parecer IA indisponivel: configure HUGGINGFACE_API_TOKEN para habilitar a analise."

        prompt = (
            "Voce e um assistente juridico brasileiro. Gere um parecer objetivo em ate 8 linhas, "
            "apontando riscos, campos encontrados e proximas providencias.\n\n"
            f"Tipo: {document_type}\nDados: {extracted_data}\nTexto:\n{text[:6000]}"
        )
        try:
            response = requests.post(
                f"https://api-inference.huggingface.co/models/{self.model}",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"inputs": prompt, "parameters": {"max_new_tokens": 350, "temperature": 0.2}},
                timeout=90,
            )
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, list) and payload:
                return payload[0].get("generated_text", "").replace(prompt, "").strip()
            return str(payload)
        except requests.RequestException as exc:
            return f"Parecer IA indisponivel no momento: {exc}"
