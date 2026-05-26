"""RG (Brazilian ID card) extraction via OpenAI Vision API with OCR fallback."""
import os
import re
import base64
import json as _json
import asyncio
import shutil
import unicodedata
from pathlib import Path
from typing import Optional

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    from winsdk.windows.globalization import Language
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.storage.streams import DataWriter, InMemoryRandomAccessStream
    _WINSDK = True
except ImportError:
    _WINSDK = False


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def _norm(s: str) -> str:
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("ascii").lower()


def _fix_common_ocr_name_errors(value: str) -> str:
    value = _clean(value or "")
    replacements = {
        r"\bOOS\b": "DOS",
        r"\bD0S\b": "DOS",
        r"\bO0S\b": "DOS",
        r"\bOA\b": "DA",
        r"\bDANIEC\b": "DANIEL",
        r"\bDANIEI\b": "DANIEL",
        r"\bPUBUCA\b": "PUBLICA",
        r"\bINsrtruro\b": "INSTITUTO",
    }
    for pattern, replacement in replacements.items():
        value = re.sub(pattern, replacement, value, flags=re.IGNORECASE)
    return _clean(value)


# ─── Vision extraction (primary) ──────────────────────────────────────────────

_VISION_PROMPT = (
    "Você está analisando uma Carteira de Identidade brasileira. Pode ser:\n"
    "- RG antigo (Registro Geral) — modelo físico ou digital\n"
    "- CIN (Carteira de Identidade Nacional) — novo modelo — físico ou digital\n"
    "Pode haver 1 ou 2 imagens (frente e/ou verso do documento).\n\n"
    "Extraia os campos abaixo e retorne EXATAMENTE este JSON (sem texto adicional):\n"
    "{\n"
    "  \"nome\": \"nome completo do titular em MAIÚSCULAS\",\n"
    "  \"rg\": \"número do RG ex: 12.345.678-9 (somente números e pontuação)\",\n"
    "  \"cpf\": \"CPF no formato XXX.XXX.XXX-XX\",\n"
    "  \"data_nascimento\": \"data de nascimento no formato DD/MM/AAAA\",\n"
    "  \"municipio\": \"cidade/município de nascimento do titular, ou seja, o valor do campo 'Naturalidade' impresso no documento\",\n"
    "  \"nome_mae\": \"nome completo da mãe em MAIÚSCULAS\",\n"
    "  \"nome_pai\": \"nome completo do pai em MAIÚSCULAS (string vazia se não constar)\"\n"
    "}\n\n"
    "Regras importantes:\n"
    "- Use string vazia \"\" para campos não encontrados\n"
    "- 'municipio' deve ser o valor do campo rotulado 'Naturalidade' ou 'Naturalidade/Place of Birth' "
    "no documento — é a cidade onde a pessoa nasceu, NÃO o estado emissor do RG (ex: ignore 'Estado de São Paulo' "
    "ou 'Secretaria da Segurança Pública' que aparecem no cabeçalho)\n"
    "- No RG antigo: nome, data de nascimento e naturalidade ficam na frente; "
    "CPF e filiação (mãe/pai) ficam no verso\n"
    "- No CIN: dados principais ficam na frente, filiação fica no verso\n"
    "- No CIN o campo 'Registro Geral - CPF' é o mesmo número do CPF — "
    "use-o para preencher tanto 'rg' quanto 'cpf'\n"
    "- Retorne apenas JSON válido, sem nenhum texto adicional"
)


def _mime_type(path: str) -> str:
    suffix = Path(path).suffix.lower().lstrip(".")
    return {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
            "bmp": "image/bmp", "webp": "image/webp"}.get(suffix, "image/png")


def _crop_pdf_cards(pdf_path: str) -> str:
    """
    Renders only the card region of an RG Digital PDF at high zoom.
    The cards occupy roughly the vertical middle of the page; cropping
    eliminates the institutional header and authentication footer that
    can confuse Vision into reading city names from surrounding text.
    Falls back to a full-page render if fitz is unavailable or fails.
    """
    try:
        import fitz
        doc = fitz.open(pdf_path)
        if doc.page_count == 0:
            doc.close()
            return _pdf_to_image(pdf_path, zoom=3.0)
        page = doc[0]
        r = page.rect
        # Cards sit roughly between 30% and 57% of page height, full width with margins
        clip = fitz.Rect(r.width * 0.10, r.height * 0.30, r.width * 0.90, r.height * 0.58)
        pix = page.get_pixmap(matrix=fitz.Matrix(5.0, 5.0), clip=clip, alpha=False)
        out = str(Path(pdf_path).with_suffix("")) + "_vision_cards.png"
        pix.save(out)
        doc.close()
        print(f"[RG_VISION] pdf card crop {pix.width}x{pix.height} -> {out}")
        return out
    except Exception as e:
        print(f"[RG_VISION] pdf card crop failed: {e}")
        return _pdf_to_image(pdf_path, zoom=3.0)


def _prepare_image_for_vision(path: str) -> tuple[str, str]:
    """
    Returns (base64_data, mime_type).
    For PDFs: crops to the RG card region to eliminate surrounding
    institutional text that can confuse Vision field extraction.
    """
    if Path(path).suffix.lower() == ".pdf":
        rendered = _crop_pdf_cards(path)
        with open(rendered, "rb") as f:
            return base64.b64encode(f.read()).decode(), "image/png"
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode(), _mime_type(path)


def extract_rg_with_vision(path1: str, path2: Optional[str] = None) -> dict:
    """
    Primary extraction: sends images directly to OpenAI GPT-4o-mini Vision.
    Handles all formats: old RG, CIN, physical photo, digital PDF.
    Returns dict with 7 fields (empty strings for missing), or {} on failure.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return {}
    try:
        from openai import OpenAI

        content: list = [{"type": "text", "text": _VISION_PROMPT}]
        for path in [p for p in [path1, path2] if p]:
            b64, mime = _prepare_image_for_vision(path)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "high"},
            })

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=500,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": content}],
        )

        data = _json.loads(response.choices[0].message.content)
        fields = {
            "nome":            _clean(str(data.get("nome", "") or "")),
            "rg":              _clean(str(data.get("rg", "") or "")),
            "cpf":             _clean(str(data.get("cpf", "") or "")),
            "data_nascimento": _clean(str(data.get("data_nascimento", "") or "")),
            "municipio":       _clean(str(data.get("municipio", "") or "")),
            "nome_mae":        _clean(str(data.get("nome_mae", "") or "")),
            "nome_pai":        _clean(str(data.get("nome_pai", "") or "")),
        }
        n = sum(1 for v in fields.values() if v)
        print(f"[RG_VISION] {n}/7 campos: nome={fields['nome']!r} cpf={fields['cpf']!r}")
        return fields
    except Exception as e:
        print(f"[RG_VISION] falhou: {e}")
        return {}


def _score_rg_fields(fields: dict) -> int:
    weights = {"nome": 2, "rg": 2, "cpf": 2, "data_nascimento": 2,
               "municipio": 1, "nome_mae": 2, "nome_pai": 1}
    return sum(w for k, w in weights.items() if fields.get(k))


def process_rg_document(path1: str, path2: Optional[str] = None) -> tuple[dict, str, str, str]:
    """
    Main extraction entry point.

    1. Tenta OpenAI Vision (extrai todos os campos de uma vez, qualquer formato)
    2. Se Vision falhar ou retornar menos de 2 campos essenciais, cai no OCR + regex
    3. Se ambos retornarem algo, mescla preferindo Vision onde ela tem dados

    Retorna (fields, method, raw_text, lado_detectado).
    """
    _ESSENTIAL = {"nome", "rg", "cpf", "data_nascimento"}
    empty = {k: "" for k in ["nome", "rg", "cpf", "data_nascimento", "municipio", "nome_mae", "nome_pai"]}

    # ── Primário: Vision API ──────────────────────────────────────────────────
    vision_fields = extract_rg_with_vision(path1, path2)
    vision_score = _score_rg_fields(vision_fields)
    essential_found = sum(1 for k in _ESSENTIAL if vision_fields.get(k))

    if vision_fields and essential_found >= 2:
        lado = "frente/verso" if path2 else detect_side("")
        print(f"[RG] vision aceito score={vision_score} essenciais={essential_found}/4")
        return vision_fields, "openai_vision", _json.dumps(vision_fields, ensure_ascii=False), "frente/verso" if path2 else "frente"

    if vision_fields:
        print(f"[RG] vision parcial ({essential_found}/4 essenciais) — tentando OCR fallback")
    else:
        print("[RG] vision falhou — tentando OCR fallback")

    # ── Fallback: OCR + regex ─────────────────────────────────────────────────
    text1, method1 = ocr_image(path1)
    text2, method2 = ("", "") if not path2 else ocr_image(path2)

    if not text1.strip() and not text2.strip():
        if vision_fields:
            lado = "frente/verso" if path2 else "frente"
            return vision_fields, "openai_vision_partial", "", lado
        return empty, "failed", "", "desconhecido"

    if path2 and (text1.strip() or text2.strip()):
        ocr_fields = extract_rg_fields_combined(text1, text2)
        side1, side2 = detect_side(text1), detect_side(text2)
        lado = f"{side1}/{side2}"
        if not ocr_fields.get("nome_mae") and not ocr_fields.get("nome_pai"):
            filiacao_path = _pick_filiacao_path(path1, path2, text1, text2, side1, side2)
            mae, pai = extract_filiacao_with_vision(filiacao_path)
            if mae:
                ocr_fields["nome_mae"] = mae
            if pai:
                ocr_fields["nome_pai"] = pai
    else:
        text = text1 or text2
        ocr_fields = extract_rg_fields(text)
        lado = detect_side(text)

    method = method1 or method2

    # Mescla Vision + OCR: Vision vence onde tem dado, OCR complementa o resto
    if vision_score > 0:
        merged = {k: vision_fields.get(k) or ocr_fields.get(k, "") for k in empty}
        merged_score = _score_rg_fields(merged)
        ocr_score = _score_rg_fields(ocr_fields)
        if merged_score >= ocr_score:
            print(f"[RG] mesclado vision+ocr score={merged_score}")
            return merged, f"openai_vision+{method}", text1, lado

    return ocr_fields, method, text1, lado


def _pick_filiacao_path(path1: str, path2: str, text1: str, text2: str,
                        side1: str, side2: str) -> str:
    if "filia" in text1.lower() and "filia" not in text2.lower():
        return path1
    if "filia" in text2.lower():
        return path2
    return path2 if side2 == "verso" else (path1 if side1 == "verso" else path2)


# ─── OCR (fallback) ───────────────────────────────────────────────────────────

def _setup_tesseract() -> bool:
    if not pytesseract:
        return False
    for candidate in [
        shutil.which("tesseract"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]:
        if candidate and Path(candidate).exists():
            pytesseract.pytesseract.tesseract_cmd = candidate
            return True
    return False


def _ocr_tesseract(image_path: str) -> str:
    if not _setup_tesseract() or not Image:
        return ""
    try:
        img = Image.open(image_path).convert("RGB")
        for lang in ["por", None]:
            try:
                cfg = "--psm 6 --oem 3"
                text = (pytesseract.image_to_string(img, lang=lang, config=cfg)
                        if lang else pytesseract.image_to_string(img, config=cfg))
                if text.strip():
                    return text.strip()
            except Exception:
                continue
        return ""
    except Exception as e:
        print(f"[RG_OCR] tesseract failed: {e}")
        return ""


async def _windows_ocr_async(image_path: str) -> str:
    if not _WINSDK:
        return ""
    try:
        for tag in ["pt-BR", "en-US"]:
            try:
                engine = OcrEngine.try_create_from_language(Language(tag))
                if engine:
                    break
            except Exception:
                continue
        else:
            engine = OcrEngine.try_create_from_user_profile_languages()
        if not engine:
            return ""
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        stream = InMemoryRandomAccessStream()
        writer = DataWriter(stream)
        writer.write_bytes(image_bytes)
        await writer.store_async()
        await writer.flush_async()
        writer.detach_stream()
        stream.seek(0)
        decoder = await BitmapDecoder.create_async(stream)
        bitmap = await decoder.get_software_bitmap_async()
        result = await engine.recognize_async(bitmap)
        return result.text or ""
    except Exception as e:
        print(f"[RG_OCR] windows_ocr failed: {e}")
        return ""


def _ocr_windows(image_path: str) -> str:
    try:
        return asyncio.run(_windows_ocr_async(image_path))
    except Exception as e:
        print(f"[RG_OCR] windows wrapper failed: {e}")
        return ""


def _extract_text_from_pdf(pdf_path: str) -> str:
    try:
        import fitz
        doc = fitz.open(pdf_path)
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text.strip()
    except Exception as e:
        print(f"[RG_OCR] pdf_text_extract failed: {e}")
        return ""


def _pdf_to_image(pdf_path: str, zoom: float = 2.0) -> str:
    try:
        import fitz
        doc = fitz.open(pdf_path)
        if doc.page_count == 0:
            return pdf_path
        page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        img_path = str(Path(pdf_path).with_suffix("")) + "_page.png"
        pix.save(img_path)
        doc.close()
        print(f"[RG_OCR] pdf rendered zoom={zoom} -> {img_path}")
        return img_path
    except Exception as e:
        print(f"[RG_OCR] pdf_to_image failed: {e}")
        return pdf_path


def _ocr_pdf_rendered_regions(pdf_path: str) -> tuple[str, str]:
    try:
        import fitz
        doc = fitz.open(pdf_path)
        if doc.page_count == 0:
            return "", "failed"
        page = doc[0]
        rect = page.rect
        regions = [
            ("cards", fitz.Rect(rect.width * 0.14, rect.height * 0.335, rect.width * 0.85, rect.height * 0.52), 5.0),
            ("front", fitz.Rect(rect.width * 0.145, rect.height * 0.34, rect.width * 0.49, rect.height * 0.515), 6.0),
            ("back",  fitz.Rect(rect.width * 0.49, rect.height * 0.34, rect.width * 0.84, rect.height * 0.515), 6.0),
            ("page",  rect, 3.0),
        ]
        texts: list[str] = []
        base = Path(pdf_path).with_suffix("")
        for name, clip, z in regions:
            out = f"{base}_{name}.png"
            pix = page.get_pixmap(matrix=fitz.Matrix(z, z), clip=clip, alpha=False)
            pix.save(out)
            text = _ocr_tesseract(out) or _ocr_windows(out)
            if text.strip():
                texts.append(text.strip())
            if name != "page":
                try:
                    Path(out).unlink()
                except Exception:
                    pass
        doc.close()
        combined = "\n".join(texts)
        if combined.strip():
            return combined, "pdf_regions"
    except Exception as e:
        print(f"[RG_OCR] pdf_rendered_regions failed: {e}")
    return "", "failed"


def _has_useful_rg_fields(text: str) -> bool:
    fields = extract_rg_fields(text)
    return sum(1 for k in ("nome", "rg", "cpf", "data_nascimento", "municipio") if fields.get(k)) >= 2


def _rg_field_score(text: str) -> int:
    return _score_rg_fields(extract_rg_fields(text))


def _ocr_pdf(pdf_path: str) -> tuple[str, str]:
    candidates: list[tuple[int, str, str]] = []

    text = _extract_text_from_pdf(pdf_path)
    if len(text.strip()) > 100 and _has_useful_rg_fields(text):
        candidates.append((_rg_field_score(text), text, "pdf_text"))

    try:
        import fitz
        doc = fitz.open(pdf_path)
        all_texts: list[str] = []
        for page in doc:
            for img in page.get_images(full=True):
                xref = img[0]
                base = doc.extract_image(xref)
                w, h = base.get("width", 0), base.get("height", 0)
                if w < 300 or h < 150:
                    continue
                img_bytes = base["image"]
                img_ext = base.get("ext", "png")
                tmp_path = f"{pdf_path}_emb{xref}.{img_ext}"
                with open(tmp_path, "wb") as f:
                    f.write(img_bytes)
                t = _ocr_tesseract(tmp_path) or _ocr_windows(tmp_path)
                if t.strip():
                    all_texts.append(t)
                try:
                    Path(tmp_path).unlink()
                except Exception:
                    pass
        doc.close()
        if all_texts:
            combined = "\n".join(all_texts)
            candidates.append((_rg_field_score(combined), combined, "pdf_images"))
    except Exception as e:
        print(f"[RG_OCR] pdf_images failed: {e}")

    rendered_text, rendered_method = _ocr_pdf_rendered_regions(pdf_path)
    if rendered_text.strip():
        candidates.append((_rg_field_score(rendered_text), rendered_text, rendered_method))

    img_path = _pdf_to_image(pdf_path, zoom=4.0)
    t = _ocr_tesseract(img_path)
    if t.strip():
        candidates.append((_rg_field_score(t), t, "pytesseract"))
    t = _ocr_windows(img_path)
    if t.strip():
        candidates.append((_rg_field_score(t), t, "windows_ocr"))

    if candidates:
        score, best_text, best_method = max(candidates, key=lambda c: c[0])
        print(f"[RG_OCR] pdf selected method={best_method} score={score}")
        return best_text, best_method

    return "", "failed"


def ocr_image(image_path: str) -> tuple[str, str]:
    if Path(image_path).suffix.lower() == ".pdf":
        return _ocr_pdf(image_path)

    candidates: list[tuple[int, str, str]] = []
    text = _ocr_tesseract(image_path)
    if text.strip():
        candidates.append((_rg_field_score(text), text, "pytesseract"))
    text = _ocr_windows(image_path)
    if text.strip():
        candidates.append((_rg_field_score(text), text, "windows_ocr"))

    if candidates:
        score, best_text, best_method = max(candidates, key=lambda c: c[0])
        print(f"[RG_OCR] image selected method={best_method} score={score}")
        return best_text, best_method

    print("[RG_OCR] all methods failed")
    return "", "failed"


# ─── Side detection ───────────────────────────────────────────────────────────

_FRENTE_KW = [
    "república federativa", "carteira de identidade", "registro geral",
    "naturalidade", "data de nascimento", "date of birth",
    "secretaria", "ssp", "detran", "instituto", "delegacia",
    "governo federal", "place of birth", "personal number",
]
_VERSO_KW = [
    "cpf", "validade", "assinatura do titular", "digital", "identificação civil",
    "número do cpf", "numero do cpf", "cnh", "habilitação", "categoria",
    "data de expedição", "data de emissão", "orgao expedidor", "órgão expedidor",
    "card issuer", "place of issue", "emissão", "emissao",
    "filiação", "nome do pai", "nome da mae", "nome da mãe",
    "assinatura do diretor", "t. eleitor", "nis/pis/pasep", "cert. militar",
    "polegar", "valida em todo", "identidade profissional",
]


def detect_side(text: str) -> str:
    t = text.lower()
    frente_score = sum(1 for kw in _FRENTE_KW if kw in t)
    verso_score  = sum(1 for kw in _VERSO_KW  if kw in t)
    if frente_score > verso_score:
        return "frente"
    if verso_score > frente_score:
        return "verso"
    return "desconhecido"


# ─── Field extractors (OCR fallback) ──────────────────────────────────────────

_NAME_STOPWORDS = {
    "NAME", "NOME", "SOCIAL", "REGISTRO", "GERAL", "CPF", "PERSONAL",
    "NUMBER", "SEXO", "SEX", "DATA", "NASCIMENTO", "BIRTH", "DATE",
    "NATURALIDADE", "NATIONALITY", "NACIONALIDADE", "VALIDADE", "EXPIRY",
    "SIGNATURE", "ASSINATURA", "TITULAR", "CARTEIRA", "IDENTIDADE",
    "FEDERAL", "BRASIL", "BRAZIL", "ESTADO", "SECRETARIA", "SEGURANCA",
    "PUBLICA", "GOVERNO", "REPUBLICA", "FILIACAO", "FILIAÇÃO", "FILIATION",
    "ORGAO", "ORGÃO", "LOCAL", "EMISSAO", "EMISSÃO", "EXPEDIDOR", "ISSUER",
    "PLACE", "ISSUE", "CARD", "SOROCABA", "BRA",
    "INSTITUTO", "IDENTIFICACAO", "IDENTIFICAÇÃO", "DIVISIONAL", "DELEGADO",
    "DELEGACIA", "IIRGD", "PCSP", "SESP", "DENATRAN",
}


def _extract_nome(text: str) -> str:
    patterns = [
        r'Nome\s*/\s*Name',
        r'\bName\b',
        r'\bNome\b',
        r'1\s+nome',
        r'nome\s*completo',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if not m:
            continue
        after = text[m.end():m.end() + 200]
        stop = re.search(
            r'/|Nome\s+Social|Registro\s+Geral|Social\s+Name|Sexo|Sex\b|FILIA',
            after, re.IGNORECASE
        )
        chunk = after[:stop.start()] if stop else after
        for line in chunk.split("\n"):
            words = re.findall(r'[A-ZÁÉÍÓÚÂÊÔÃÕÇÀ-Ü]{2,}', line)
            words = [w for w in words if w not in _NAME_STOPWORDS]
            if len(words) >= 2:
                return _fix_common_ocr_name_errors(" ".join(words))

    before_label = re.search(
        r'([A-ZÁÉÍÓÚÂÊÔÃÕÇÀ-Ü]{2,}(?:[ \t]+(?:D[AEIO]S?|[A-ZÁÉÍÓÚÂÊÔÃÕÇÀ-Ü]{2,})){1,5})[ \t]+NOME[ \t]+FILIA',
        text, re.IGNORECASE,
    )
    if before_label:
        candidate = _fix_common_ocr_name_errors(before_label.group(1).upper())
        words = [w for w in candidate.split() if w not in _NAME_STOPWORDS]
        if len(words) >= 2:
            return _clean(" ".join(words))

    rg_digital = re.search(
        r'IDENTIFICA[A-ZÇÀ-Üa-zçà-ü\s]{0,40}?\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇÀ-Ü]{2,}(?:\s+(?:D[AEIO]S?|[A-ZÁÉÍÓÚÂÊÔÃÕÇÀ-Ü]{2,})){1,5})\s+FILIA',
        text, re.IGNORECASE,
    )
    if rg_digital:
        candidate = _fix_common_ocr_name_errors(rg_digital.group(1).upper())
        words = [w for w in candidate.split() if w not in _NAME_STOPWORDS]
        if len(words) >= 2:
            return _clean(" ".join(words))

    return ""


def _extract_data_nascimento(text: str) -> str:
    m = re.search(
        r'(?:data\s*(?:de\s*)?nasc(?:imento)?|date\s*of\s*birth|nasc\.?)\s*[^0-9\n]{0,40}?'
        r'(\d{2})[/\-\.](\d{2})[/\-\.](\d{4})',
        text, re.IGNORECASE
    )
    if m:
        d, mo, y = m.group(1), m.group(2), m.group(3)
        if 1900 <= int(y) <= 2015:
            return f"{d}/{mo}/{y}"

    masked = text
    for kw_pat in [
        r'(?:valid(?:ade|ity)|expir[ay])[^\n]{0,60}(\d{2}[/\-\.]\d{2}[/\-\.]\d{4})',
        r'(?:emiss[aã]o|issue|expedi[cç])[^\n]{0,60}(\d{2}[/\-\.]\d{2}[/\-\.]\d{4})',
    ]:
        for km in re.finditer(kw_pat, masked, re.IGNORECASE):
            start, end = km.span(1)
            masked = masked[:start] + "XX/XX/XXXX" + masked[end:]

    for dm in re.finditer(r'\b(\d{2})[/\-\.](\d{2})[/\-\.](\d{4})\b', masked):
        y = int(dm.group(3))
        if 1900 <= y <= 2015:
            return f"{dm.group(1)}/{dm.group(2)}/{dm.group(3)}"

    return ""


def _extract_municipio(text: str) -> str:
    labels = [
        r'Naturalidade\s*/\s*Place\s*of\s*Birth',
        r'Place\s*of\s*Birth',
        r'Naturalidade',
        r'Mun\.?\s*Nasc',
        r'Local\s*de\s*Nascimento',
    ]
    for pat in labels:
        m = re.search(pat, text, re.IGNORECASE)
        if not m:
            continue
        after = text[m.end():m.end() + 100]
        stop = re.search(r'/|Validade|Expiry|Nationality|Nacionalidade|Assinatura', after, re.IGNORECASE)
        chunk = after[:stop.start()] if stop else after
        city_m = re.search(r'[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{2,}(?:[ \t/\-]+[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{2,})*', chunk)
        if city_m:
            return _clean(city_m.group(0))
    return ""


_FILIACAO_STOP = re.compile(
    r'Órgão|Orgao|Expedidor|Card\s+Issuer|Local|Place\s+of\s+Issue|Emiss|Issue\b|IIRGD|SESP|SSP|DETRAN|\d{2}/\d{2}',
    re.IGNORECASE,
)
_NAME_RUN = re.compile(
    r'[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{2,}(?:\s+(?:D[AEIO]S?|[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{2,})){1,5}',
)


def _clean_parent_name(value: str) -> str:
    value = _fix_common_ocr_name_errors(value)
    value = re.split(
        r'\b(?:DATA|NASCIMENTO|NASC|FATOR|NATURALIDADE|ORGAO|ÓRGÃO|EXPEDIDOR)\b',
        value, maxsplit=1, flags=re.IGNORECASE,
    )[0]
    return _clean(value.strip(" ,.;:-"))


def _split_two_names(text: str) -> tuple[str, str]:
    text = _fix_common_ocr_name_errors(text)
    _FEMALE = r'(?:BERENICE|MARIA|ANA|ANTONIA|JOSEFA|APARECIDA|CLAUDIA|LUCIANA|FERNANDA|PATRICIA|ROSANA|REGINA|SANDRA|FATIMA|FRANCISCA|ELIZABETE|ELISABETE|DEBORA|ANDREIA|ANDREA|CRISTINA|SILVIA|JULIANA|VANESSA|SIMONE|RENATA)'
    _MALE   = r'(?:DANIEL|ANTONIO|JOS[ÉE]|JOSE|CARLOS|MARCOS|PAULO|LUIZ|LUIS|PEDRO|RAFAEL|ROBERTO|FRANCISCO|GABRIEL|JOAO|JOÃO|RODRIGO|FERNANDO|SERGIO|MARCELO|DIEGO|ANDRE|ANDRÉS|EDUARDO|ALEXANDRE|THIAGO|LUCAS)'

    female_first = re.search(
        rf'\b({_FEMALE}[A-ZÁÉÍÓÚÂÊÔÃÕÇÀ-Ü\s]{{5,100}}?)\s+({_MALE}[A-ZÁÉÍÓÚÂÊÔÃÕÇÀ-Ü\s]{{5,80}})',
        text, re.IGNORECASE,
    )
    if female_first:
        return _clean_parent_name(female_first.group(1).upper()), _clean_parent_name(female_first.group(2).upper())

    male_first = re.search(
        rf'\b({_MALE}[A-ZÁÉÍÓÚÂÊÔÃÕÇÀ-Ü\s]{{5,80}}?)\s+({_FEMALE}[A-ZÁÉÍÓÚÂÊÔÃÕÇÀ-Ü\s]{{5,100}})',
        text, re.IGNORECASE,
    )
    if male_first:
        return _clean_parent_name(male_first.group(2).upper()), _clean_parent_name(male_first.group(1).upper())

    runs = [_clean_parent_name(n) for n in _NAME_RUN.findall(text)
            if _clean(n) not in _NAME_STOPWORDS and len(_clean(n).split()) >= 2]
    return (runs[0] if runs else ""), (runs[1] if len(runs) > 1 else "")


def _extract_filiacao(text: str) -> tuple[str, str]:
    fil_m = re.search(r'FILIA[CÇ][AÃ]O|Filia[cç][aã]o|Filiation', text, re.IGNORECASE)
    if not fil_m:
        return "", ""

    chunk = text[fil_m.end():fil_m.end() + 500]
    stop_m = _FILIACAO_STOP.search(chunk)
    if stop_m:
        chunk = chunk[:stop_m.start()]

    _PARTICLES = {"DOS", "DAS", "DE", "DA", "DO"}
    names_from_lines = []
    for line in chunk.split("\n"):
        line = _clean(line)
        if not line or len(line) < 2:
            continue
        name_words = re.findall(r'[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{2,}', line)
        if not name_words:
            continue
        alpha = sum(1 for c in line if c.isalpha())
        upper = sum(1 for c in line if c.isupper())
        if alpha == 0 or upper / alpha < 0.6:
            continue
        if len(name_words) == 1 and names_from_lines:
            last_word = names_from_lines[-1].split()[-1].upper()
            if last_word in _PARTICLES:
                names_from_lines[-1] = names_from_lines[-1] + " " + name_words[0]
                continue
        if len(name_words) >= 2:
            names_from_lines.append(" ".join(name_words))
            if len(names_from_lines) == 2:
                break

    if len(names_from_lines) >= 2:
        first  = _fix_common_ocr_name_errors(names_from_lines[0].upper())
        second = _fix_common_ocr_name_errors(names_from_lines[1].upper())
        male_starters = ("DANIEL", "ANTONIO", "JOSÉ", "JOSE", "CARLOS", "MARCOS", "PAULO", "LUIZ", "LUIS", "PEDRO", "RAFAEL", "ROBERTO", "FRANCISCO")
        if first.startswith(male_starters):
            return second, first
        return first, second

    if len(names_from_lines) == 1:
        mae, pai = _split_two_names(names_from_lines[0])
        if mae:
            return mae, pai

    return _split_two_names(chunk)


def _extract_cpf(text: str) -> str:
    m = re.search(r'\b(\d{3})[\.\s\-/]?(\d{3})[\.\s\-/]?(\d{3})[\.\s\-/]?(\d{2})\b', text)
    if m:
        d = "".join(m.groups())
        if len(d) == 11:
            return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    return ""


def _extract_rg(text: str, cpf: str) -> str:
    masked = text
    if cpf:
        cpf_m = re.search(r'\b(\d{3})[\.\s\-/]?(\d{3})[\.\s\-/]?(\d{3})[\.\s\-/]?(\d{2})\b', masked)
        if cpf_m:
            masked = masked[:cpf_m.start()] + " " * (cpf_m.end() - cpf_m.start()) + masked[cpf_m.end():]

    rg_m = re.search(r'\b\d{1,2}[\.\s]?\d{3}[\.\s]?\d{3}[\-\s]?\d\b', masked)
    if not rg_m:
        rg_m = re.search(r'\b\d{7,9}\b', masked)
    if rg_m:
        return _clean(rg_m.group(0))

    if cpf:
        return cpf
    return ""


def _label_fallback(text: str, labels: list[str]) -> str:
    for label in labels:
        m = re.search(re.escape(label), text, re.IGNORECASE)
        if not m:
            m = re.search(re.escape(_norm(label)), _norm(text), re.IGNORECASE)
        if not m:
            continue
        after = text[m.end():m.end() + 150]
        for line in after.split("\n"):
            candidate = _clean(re.sub(r"[^\w\sÀ-ÿ./\-]", "", line))
            if len(candidate) > 4:
                return candidate
    return ""


def extract_rg_fields(text: str) -> dict[str, str]:
    cpf             = _extract_cpf(text)
    rg              = _extract_rg(text, cpf)
    data_nascimento = _extract_data_nascimento(text)
    nome            = _extract_nome(text)
    municipio       = _extract_municipio(text)
    nome_mae, nome_pai = _extract_filiacao(text)

    if not nome_mae:
        nome_mae = _label_fallback(text, ["nome da mãe", "nome da mae", "mãe:", "mae:"])
    if not nome_pai:
        nome_pai = _label_fallback(text, ["nome do pai", "pai:"])

    return {
        "nome":            nome,
        "rg":              rg,
        "cpf":             cpf,
        "data_nascimento": data_nascimento,
        "municipio":       municipio,
        "nome_mae":        nome_mae,
        "nome_pai":        nome_pai,
    }


def extract_rg_fields_combined(text1: str, text2: str) -> dict[str, str]:
    side1 = detect_side(text1)
    side2 = detect_side(text2)
    if side1 == "verso" or side2 == "frente":
        frente_text, verso_text = text2, text1
    else:
        frente_text, verso_text = text1, text2

    fields_f = extract_rg_fields(frente_text)
    fields_v = extract_rg_fields(verso_text)

    merged: dict[str, str] = {}
    for key in ["nome", "rg", "data_nascimento", "municipio", "nome_mae", "nome_pai"]:
        merged[key] = fields_f.get(key) or fields_v.get(key) or ""
    merged["cpf"] = fields_v.get("cpf") or fields_f.get("cpf") or ""
    return merged


def extract_filiacao_with_vision(image_path: str) -> tuple[str, str]:
    """Narrow Vision fallback: extract only parent names from a specific image."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return "", ""
    try:
        from openai import OpenAI

        suffix = Path(image_path).suffix.lower().lstrip(".")
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                "bmp": "image/bmp", "webp": "image/webp"}.get(suffix, "image/jpeg")
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=150,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": [
                {"type": "text", "text": (
                    "Carteira de Identidade brasileira (RG ou CIN, qualquer modelo). "
                    "Encontre a seção 'Filiação' ou 'Filiation' e extraia os nomes completos dos pais. "
                    "Retorne JSON: {\"nome_mae\": \"NOME DA MÃE\", \"nome_pai\": \"NOME DO PAI\"}. "
                    "Nomes em MAIÚSCULAS. Use string vazia se não encontrar."
                )},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ]}],
        )
        result = _json.loads(response.choices[0].message.content)
        mae = _clean(result.get("nome_mae", "") or "")
        pai = _clean(result.get("nome_pai", "") or "")
        print(f"[RG_OCR] filiacao vision: mae={mae!r} pai={pai!r}")
        return mae, pai
    except Exception as e:
        print(f"[RG_OCR] filiacao vision failed: {e}")
        return "", ""
