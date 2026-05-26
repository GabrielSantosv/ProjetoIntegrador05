"""Standalone extraction services without Django dependencies"""
import os
import sys
import io
import shutil
import asyncio
from pathlib import Path
from dataclasses import dataclass
import logging
import re
import unicodedata

from backend.document_profiles import (
    DOCUMENT_PROFILES,
    UNKNOWN_DOCUMENT_TYPE,
    DocumentProfile,
    DOCUMENT_TYPE_LABELS
)

# Import pdfplumber directly (no Django needed)
try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

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
except ImportError:
    Language = None
    BitmapDecoder = None
    OcrEngine = None
    DataWriter = None
    InMemoryRandomAccessStream = None


logger = logging.getLogger("api.document_classifier")


def _configure_tesseract() -> bool:
    """Configure pytesseract and return whether the executable is available."""
    if not pytesseract:
        return False

    configured = os.getenv("TESSERACT_CMD")
    candidates = [
        configured,
        shutil.which("tesseract"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            pytesseract.pytesseract.tesseract_cmd = candidate
            return True

    return False


def _preferred_windows_ocr_languages() -> list[str]:
    configured = os.getenv("OCR_LANGUAGE", "por+eng")
    aliases = {
        "por": "pt-BR",
        "pt": "pt-BR",
        "pt-br": "pt-BR",
        "eng": "en-US",
        "en": "en-US",
        "en-us": "en-US",
    }
    tags = []
    for item in re.split(r"[+,; ]+", configured):
        if not item:
            continue
        tags.append(aliases.get(item.lower(), item))
    tags.extend(["pt-BR", "en-US"])
    return list(dict.fromkeys(tags))


def _create_windows_ocr_engine():
    if not OcrEngine or not Language:
        return None

    try:
        available = {
            language.language_tag.lower(): language.language_tag
            for language in OcrEngine.available_recognizer_languages
        }
        for tag in _preferred_windows_ocr_languages():
            available_tag = available.get(tag.lower())
            if available_tag:
                engine = OcrEngine.try_create_from_language(Language(available_tag))
                if engine:
                    print(f"[WINDOWS_OCR] using language={available_tag}")
                    return engine
        engine = OcrEngine.try_create_from_user_profile_languages()
        if engine:
            print("[WINDOWS_OCR] using user profile language")
        return engine
    except Exception as e:
        print(f"[WINDOWS_OCR] unavailable: {e}")
        return None


async def _windows_ocr_png(png_bytes: bytes, engine) -> str:
    stream = InMemoryRandomAccessStream()
    writer = DataWriter(stream)
    writer.write_bytes(png_bytes)
    await writer.store_async()
    await writer.flush_async()
    writer.detach_stream()
    stream.seek(0)

    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    result = await engine.recognize_async(bitmap)
    return result.text or ""


async def _extract_with_windows_ocr_async(file_path: str) -> str:
    if not fitz or not OcrEngine or not BitmapDecoder or not DataWriter or not InMemoryRandomAccessStream:
        return ""

    engine = _create_windows_ocr_engine()
    if not engine:
        return ""

    text_parts: list[str] = []
    max_pages = int(os.getenv("OCR_MAX_PAGES", "5"))
    zoom = float(os.getenv("WINDOWS_OCR_ZOOM", "2.5"))
    doc = fitz.open(file_path)
    try:
        for page_index in range(min(max_pages, len(doc))):
            page = doc[page_index]
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            page_text = await _windows_ocr_png(pix.tobytes("png"), engine)
            if page_text.strip():
                text_parts.append(page_text.strip())
    finally:
        doc.close()

    return "\n".join(text_parts)


def extract_with_windows_ocr(file_path: str) -> tuple[str, str]:
    try:
        print(f"[WINDOWS_OCR] starting native Windows OCR for {file_path}")
        text = asyncio.run(_extract_with_windows_ocr_async(file_path))
        if text.strip():
            print(f"[WINDOWS_OCR] success extraction from {file_path}")
            return text, "windows_ocr"
        print(f"[WINDOWS_OCR] no text extracted from {file_path}")
    except Exception as e:
        print(f"[WINDOWS_OCR] failed: {e}")
        logger.error(f"[WINDOWS_OCR] failed for {file_path}: {e}")

    return "", "failed"


@dataclass
class ProfileScore:
    profile_name: str
    score: int
    min_score: int
    priority: int
    valid: bool
    required_found: list[str]
    required_missing: list[list[str]]
    optional_found: list[str]
    reasons: list[str]


@dataclass
class ClassificationResult:
    document_type: str
    score: int
    matched_keywords: list[str]
    required_keywords: list[str]
    optional_keywords: list[str]
    reasons: list[str]
    candidates: list[ProfileScore]
    text_length: int
    matched_by: str = "unknown"

    def as_dict(self) -> dict:
        return {
            "document_type": self.document_type,
            "document_label": DOCUMENT_TYPE_LABELS.get(self.document_type, self.document_type),
            "score": self.score,
            "matched_keywords": self.matched_keywords,
            "required_keywords": self.required_keywords,
            "optional_keywords": self.optional_keywords,
            "reasons": self.reasons,
            "text_length": self.text_length,
            "matched_by": self.matched_by,
            "candidates": [
                {
                    "profile_name": candidate.profile_name,
                    "score": candidate.score,
                    "min_score": candidate.min_score,
                    "priority": candidate.priority,
                    "valid": candidate.valid,
                    "required_found": candidate.required_found,
                    "required_missing": candidate.required_missing,
                    "optional_found": candidate.optional_found,
                    "reasons": candidate.reasons,
                }
                for candidate in self.candidates
            ],
        }

def extract_pdf_text(file_path: str) -> tuple[str, str]:
    """
    Extract text from PDF with fallback chain:
    1. pdfplumber (fastest)
    2. PyMuPDF (fitz)
    3. OCR (Tesseract)
    
    Returns: (extracted_text, extraction_method)
    """
    text = ""
    method = "failed"
    
    if not os.path.exists(file_path):
        logger.error(f"[FILE] path does not exist: {file_path}")
        return "File not found", "error"

    # Try pdfplumber
    if pdfplumber:
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            if text.strip():
                print(f"[PDFPLUMBER] success extraction from {file_path}")
                return text, "pdfplumber"
            print(f"[PDFPLUMBER] no text extracted from {file_path}")
        except Exception as e:
            print(f"[PDFPLUMBER] failed: {e}")
            logger.warning(f"[PDFPLUMBER] failed for {file_path}: {e}")
    
    # Try PyMuPDF
    if fitz:
        try:
            doc = fitz.open(file_path)
            for page in doc:
                text += page.get_text()
            doc.close()
            if text.strip():
                print(f"[PYMUPDF] success extraction from {file_path}")
                return text, "fitz"
            print(f"[PYMUPDF] no text extracted from {file_path}")
        except Exception as e:
            print(f"[PYMUPDF] failed: {e}")
            logger.warning(f"[PYMUPDF] failed for {file_path}: {e}")
    
    # Try OCR using PyMuPDF rendering. This avoids the external Poppler/pdftoppm
    # dependency that pdf2image requires on Windows.
    if pytesseract and fitz and Image and _configure_tesseract():
        try:
            print(f"[OCR] starting Tesseract OCR for {file_path}")
            max_pages = int(os.getenv("OCR_MAX_PAGES", "5"))
            lang = os.getenv("OCR_LANGUAGE", "por+eng")
            doc = fitz.open(file_path)
            try:
                for page_index in range(min(max_pages, len(doc))):
                    page = doc[page_index]
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                    image = Image.open(io.BytesIO(pix.tobytes("png")))
                    text += pytesseract.image_to_string(image, lang=lang) + "\n"
            finally:
                doc.close()
            if text.strip():
                print(f"[OCR] success extraction from {file_path}")
                return text, "ocr"
            print(f"[OCR] no text extracted from {file_path}")
        except Exception as e:
            print(f"[OCR] failed: {e}")
            logger.error(f"[OCR] failed for {file_path}: {e}")
    else:
        print("[OCR] Tesseract executable not available or OCR dependencies missing")

    # Try native Windows OCR as a no-admin fallback. This is especially useful
    # on copied/zipped projects where Tesseract is not installed on the machine.
    windows_text, windows_method = extract_with_windows_ocr(file_path)
    if windows_text.strip():
        return windows_text, windows_method
    
    return text if text else "Failed to extract text", method


def extract_pdf_text_quick(file_path: str, max_pages: int = 2) -> tuple[str, str]:
    """Fast text extraction used by upload preview/type detection.

    This intentionally avoids OCR. OCR can take long enough that the browser
    reports a network failure while waiting for the preview classification.
    """
    text = ""

    if not os.path.exists(file_path):
        logger.error(f"[FILE] path does not exist: {file_path}")
        return "File not found", "error"

    if fitz:
        try:
            doc = fitz.open(file_path)
            try:
                for page_index in range(min(max_pages, len(doc))):
                    text += doc[page_index].get_text() + "\n"
            finally:
                doc.close()
            if text.strip():
                print(f"[QUICK_EXTRACT] success via fitz file={file_path} chars={len(text)}", flush=True)
                return text, "fitz_quick"
            print(f"[QUICK_EXTRACT] no text via fitz file={file_path}", flush=True)
        except Exception as e:
            print(f"[QUICK_EXTRACT] fitz failed file={file_path}: {e}", flush=True)

    if pdfplumber:
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages[:max_pages]:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            if text.strip():
                print(f"[QUICK_EXTRACT] success via pdfplumber file={file_path} chars={len(text)}", flush=True)
                return text, "pdfplumber_quick"
            print(f"[QUICK_EXTRACT] no text via pdfplumber file={file_path}", flush=True)
        except Exception as e:
            print(f"[QUICK_EXTRACT] pdfplumber failed file={file_path}: {e}", flush=True)

    return "", "quick_empty"


def _normalize_text(text: str) -> str:
    """Normalize text so accent/case/spacing issues do not break rules."""
    if not text:
        return ""
    # Normalize unicode to NFKD to separate accents
    text = unicodedata.normalize("NFKD", text)
    # Remove accents/combining characters
    text = "".join(char for char in text if not unicodedata.combining(char))
    # Lowercase
    text = text.lower()
    # Replace non-alphanumeric with spaces
    text = re.sub(r"[^a-z0-9]+", " ", text)
    # Collapse multiple spaces
    return re.sub(r"\s+", " ", text).strip()


def _contains(normalized_text: str, keyword: str) -> bool:
    normalized_keyword = _normalize_text(keyword)
    return bool(normalized_keyword) and normalized_keyword in normalized_text


def _score_profile(normalized_text: str, profile: DocumentProfile) -> ProfileScore:
    required_found: list[str] = []
    required_missing: list[list[str]] = []

    for keyword_group in profile.required_keywords:
        found = next((keyword for keyword in keyword_group if _contains(normalized_text, keyword)), None)
        if found:
            required_found.append(found)
        else:
            required_missing.append(list(keyword_group))

    optional_found = [
        keyword for keyword in profile.optional_keywords
        if _contains(normalized_text, keyword)
    ]

    required_total = len(profile.required_keywords)
    required_score = int((len(required_found) / required_total) * 65) if required_total else 0
    optional_total = max(len(profile.optional_keywords), 1)
    optional_score = min(35, int((len(optional_found) / optional_total) * 35))
    score = required_score + optional_score

    valid = not required_missing and score >= profile.min_score
    reasons = []
    if required_found:
        reasons.append(f"obrigatorias encontradas: {', '.join(required_found)}")
    if optional_found:
        reasons.append(f"opcionais encontradas: {', '.join(optional_found)}")
    if required_missing:
        missing = [" ou ".join(group) for group in required_missing]
        reasons.append(f"obrigatorias ausentes: {'; '.join(missing)}")
    if score < profile.min_score:
        reasons.append(f"score {score} abaixo do minimo {profile.min_score}")

    return ProfileScore(
        profile_name=profile.name,
        score=score,
        min_score=profile.min_score,
        priority=profile.priority,
        valid=valid,
        required_found=required_found,
        required_missing=required_missing,
        optional_found=optional_found,
        reasons=reasons,
    )

def classify_by_filename(filename: str) -> str | None:
    """Classify based on filename patterns."""
    if not filename:
        return None
    
    norm_fn = _normalize_text(filename)
    
    rules = [
        ("tj_falencia", ["falencia", "recuperacao judicial"]),
        ("criminal_estadual", ["acoes criminais"]),
        ("execucao_criminal_estadual", ["execucoes criminais"]),
        ("civel_estadual", ["estadual civil", "estadual civel", "distribuicoes civeis"]),
        ("tj_segundo_grau", ["2 grau", "segunda instancia"]),
        ("cnd_federal", ["cnd federal", "receita federal", "pgfn", "tributos federais"]),
        ("cnd_estadual", ["cnd estadual", "sefaz", "procuradoria geral do estado"]),
        ("cndt", ["cndt", "debitos trabalhistas"]),
        ("ceat", ["ceat", "trt15", "acoes trabalhistas"]),
        ("civel_federal", ["trf civel", "judicial civel"]),
        ("criminal_federal", ["trf criminal", "judicial criminal"]),
        ("eleitoral", ["fins eleitorais", "eleitoral"]),
    ]
    
    for doc_type, patterns in rules:
        if any(_normalize_text(p) in norm_fn for p in patterns):
            return doc_type
    
    return None

def classify_by_folder(folder_name: str) -> str | None:
    """Secondary classification based on folder name."""
    if not folder_name:
        return None
    
    norm_folder = _normalize_text(folder_name)
    
    if "tjsp" in norm_folder:
        return "civel_estadual" # Default fallback for TJSP folder
    if "cndt" in norm_folder:
        return "cndt"
    if "federal" in norm_folder:
        return "cnd_federal"
    
    return None


def classify_document(text: str, filename: str | None = None) -> ClassificationResult:
    """
    Classify a document using profile scores and explainable heuristics.
    Priority: 1. Text content, 2. Filename, 3. Folder, 4. Unknown
    """
    normalized_text = _normalize_text(text)
    candidates = [_score_profile(normalized_text, profile) for profile in DOCUMENT_PROFILES]
    candidates.sort(key=lambda item: (item.valid, item.score, item.priority), reverse=True)

    valid_candidates = [candidate for candidate in candidates if candidate.valid]
    winner = valid_candidates[0] if valid_candidates else None

    # Priority 1: Text Content
    if winner:
        result = ClassificationResult(
            document_type=winner.profile_name,
            score=winner.score,
            matched_keywords=list(dict.fromkeys(winner.required_found + winner.optional_found)),
            required_keywords=winner.required_found,
            optional_keywords=winner.optional_found,
            reasons=winner.reasons,
            candidates=candidates[:5],
            text_length=len(text or ""),
            matched_by="text"
        )
    else:
        # Priority 2: Filename
        type_by_filename = classify_by_filename(filename)
        if type_by_filename:
            result = ClassificationResult(
                document_type=type_by_filename,
                score=100,
                matched_keywords=[filename],
                required_keywords=[],
                optional_keywords=[],
                reasons=[f"Identificado pelo nome do arquivo: {filename}"],
                candidates=candidates[:5],
                text_length=len(text or ""),
                matched_by="filename"
            )
        else:
            # Priority 3: Folder
            folder_name = None
            if filename and (os.sep in filename or "/" in filename):
                folder_name = os.path.dirname(filename)
                
            type_by_folder = classify_by_folder(folder_name)
            if type_by_folder:
                result = ClassificationResult(
                    document_type=type_by_folder,
                    score=80,
                    matched_keywords=[folder_name],
                    required_keywords=[],
                    optional_keywords=[],
                    reasons=[f"Identificado pela pasta: {folder_name}"],
                    candidates=candidates[:5],
                    text_length=len(text or ""),
                    matched_by="folder"
                )
            else:
                # Priority 4: Unknown
                best = candidates[0] if candidates else None
                result = ClassificationResult(
                    document_type=UNKNOWN_DOCUMENT_TYPE,
                    score=best.score if best else 0,
                    matched_keywords=list(dict.fromkeys((best.required_found if best else []) + (best.optional_found if best else []))),
                    required_keywords=best.required_found if best else [],
                    optional_keywords=best.optional_found if best else [],
                    reasons=["Nenhum padrao textual, de nome ou de pasta identificado."],
                    candidates=candidates[:5],
                    text_length=len(text or ""),
                    matched_by="fallback"
                )

    log_classification_result(result, filename)
    return result


def log_classification_result(result: ClassificationResult, filename: str | None = None) -> None:
    """Emit human-readable logs for why the classifier chose a document type."""
    document = filename or "<sem nome>"
    label = DOCUMENT_TYPE_LABELS.get(result.document_type, result.document_type)
    lines = [
        "[CLASSIFIER]",
        f"filename={document}",
        f"matched_by={result.matched_by}",
        f"final_type={result.document_type} ({label})",
        f"score={result.score}",
        f"text_length={result.text_length}",
    ]
    if result.reasons:
        lines.append("rules:")
        lines.extend(f"- {reason}" for reason in result.reasons)

    message = "\n".join(lines)
    logger.info(message)
    print(message)


def classify_certificate_type(text: str) -> str:
    """Backward-compatible wrapper for older code paths."""
    return classify_document(text).document_type

def parse_legal_fields(text: str, document_type: str = None) -> list[dict]:
    """Parse common legal fields from text"""
    import re

    text = text or ""
    fields = {}

    def clean_person_name(value: str) -> str:
        value = re.sub(r"[*•]+", " ", value or "")
        value = re.sub(r"\([^)]*\)", " ", value)
        value = re.sub(r"\b(?:em\s+nome\s+de|nome\s+de)\b\s*:?", " ", value, flags=re.IGNORECASE)
        value = re.split(
            r"\b(?:filh[oa]\s+de|portador\(a\)|portador|CPF(?:/MF)?|CNPJ|RG|OU)\b",
            value,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        lines = [line.strip(" ,.;:-") for line in value.splitlines() if line.strip(" ,.;:-")]
        if lines:
            value = lines[0]
        value = re.sub(r"\s+", " ", value).strip(" ,.;:-")
        return value

    def looks_like_person_name(value: str) -> bool:
        normalized = _normalize_text(value)
        blocked_terms = (
            "site", "conselho", "tribunal", "justica federal", "diretoria",
            "certidao", "processos", "sao apontados", "situacao", "tramitacao",
            "secretaria", "fazenda", "planejamento", "estado de sao paulo",
            "poder judiciario", "nao constam", "nada consta", "certificamos",
            "observacoes", "ministerio", "procuradoria", "receita federal",
            "codigo de validacao", "codigo de controle", "validade",
            "pessoa juridica", "interessado nao possuir", "numero de cpf",
        )
        if any(term in normalized for term in blocked_terms):
            return False
        if re.search(r"\d", value):
            return False
        words = [word for word in re.split(r"\s+", value.strip()) if word]
        if len(words) < 2 or len(words) > 7:
            return False
        connectors = {"DA", "DE", "DO", "DAS", "DOS", "E"}
        name_words = [word for word in words if word.upper() not in connectors]
        if len(name_words) < 2:
            return False
        if value != value.upper() and any(not word[0].isupper() for word in name_words):
            return False
        return all(re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ'’-]+", word) for word in words)

    name_patterns = [
        r"([A-ZÀ-Ú][A-ZÀ-Ú\s'’-]{4,})\s*\(\s*nome\s+civil\s*\)",
        r"([A-ZÀ-Ú][A-ZÀ-Ú\s'’-]{4,})\s*\(\s*nome\s+social\s*\)",
        r"\bem\s+nome\s+de\s*[:.]?\s*[*\s]*([A-ZÀ-Ú][A-ZÀ-Ú\s'’-]{4,}?)(?=\s*,?\s*(?:RG|CPF|CNPJ|filh[oa]|portador|$))",
        r"\bcontra\s*:?\s*(?:NÃO\s+CONSTAM|NAO\s+CONSTAM|NADA\s+CONSTA|OU)?\s*([A-ZÀ-Ú][A-Za-zÀ-ú\s'’-]{4,}?)(?=\s*(?:\(|OU|CPF|CNPJ|RG|nascid[oa]|natural|,|\n))",
        r"([A-ZÀ-Ú][A-ZÀ-Ú\s'’-]{4,})\s*,?\s*RG\s*[:nº]",
        r"\bNome\s*:\s*([A-ZÀ-Ú][A-Za-zÀ-ú\s'’-]{4,})(?=\s*(?:CPF|CNPJ|RG|Ressalvado|$))",
        r"\binteressad[oa]\s*:?\s*([A-ZÀ-Ú][A-Za-zÀ-ú\s'’-]{4,})(?=\s*(?:CPF|RG|,|$))",
        r"([A-ZÀ-Ú][A-Za-zÀ-ú\s'’-]{4,})\s*,?\s*(?:RG|CPF|CNPJ)\s*[:nº]",
        r"\brequerente\s*:?\s*([^\n,]+)",
        r"\bautor(?:a)?\s*:?\s*([^\n,]+)",
        r"(?m)^\s*([A-ZÀ-Ú][A-ZÀ-Ú\s'’-]{4,})\s*$",
    ]
    for pattern in name_patterns:
        for name_match in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
            name = clean_person_name(name_match.group(1))
            if looks_like_person_name(name):
                fields["nome"] = name
                break
        if "nome" in fields:
            break
    
    # CPF pattern (11 digits with or without formatting)
    cpf_match = re.search(
        r"(?:CPF(?:/MF)?|CPF/CNPJ)?\s*(?:n[ºo.]*)?\s*(\d{3}\.?\d{3}\.?\d{3}-?\d{2})",
        text,
        re.IGNORECASE,
    )
    if cpf_match:
        fields["cpf"] = cpf_match.group(1)
    
    # CNPJ pattern
    cnpj_match = re.search(r"(\d{2}\.?\d{3}\.?\d{3}/?0001-?\d{2})", text)
    if cnpj_match:
        fields["cnpj"] = cnpj_match.group(1)
    
    # Process number (CNJ format) — keep first match for backward compatibility
    process_match = re.search(r"(\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4})", text)
    if process_match:
        fields["processo"] = process_match.group(1)

    rg_match = re.search(r"\bRG\s*(?:n[ºo.]*)?\s*([0-9A-Za-z.-]{5,})", text, re.IGNORECASE)
    if rg_match:
        fields["rg"] = rg_match.group(1).strip(" ,.;:-")

    certificate_number = re.search(
        r"CERTID[AÃ]O\s*(?:N[ºo.]|NO|NUMERO)\s*:?\s*([A-Z0-9][A-Z0-9./-]{3,})",
        text,
        re.IGNORECASE,
    )
    if not certificate_number:
        certificate_number = re.search(
            r"(?m)^\s*N[ºo.]\s*:?\s*([A-Z0-9][A-Z0-9./-]{3,})\s*$",
            text,
            re.IGNORECASE,
        )
    if certificate_number:
        fields["numero_certidao"] = certificate_number.group(1).strip(" ,.;:-")
    
    # Dates (DD/MM/YYYY or DD-MM-YYYY)
    preferred_date = re.search(
        r"(?:Certid[aã]o\s+emitida\s+em|Emitida\b.*?\bdia)\s*:?\s*(\d{2}[/-]\d{2}[/-]\d{4})",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if preferred_date:
        fields["data"] = preferred_date.group(1)
    else:
        months = {
            "janeiro": "01", "fevereiro": "02", "marco": "03", "marco": "03",
            "abril": "04", "maio": "05", "junho": "06", "julho": "07",
            "agosto": "08", "setembro": "09", "outubro": "10",
            "novembro": "11", "dezembro": "12",
        }
        long_date = re.search(
            r"\b(\d{1,2})\s+de\s+([A-Za-zÀ-úçÇ]+)\s+de\s+(\d{4})\b",
            text,
            re.IGNORECASE,
        )
        if long_date:
            month = months.get(_normalize_text(long_date.group(2)))
            if month:
                fields["data"] = f"{int(long_date.group(1)):02d}/{month}/{long_date.group(3)}"
        if "data" not in fields:
            date_matches = re.findall(r"(\d{2}[/-]\d{2}[/-]\d{4})", text)
            if date_matches:
                fields["data"] = date_matches[0]

    validity_match = re.search(
        r"(?:validade|v[aá]lida\s+at[eé])[^\d]{0,40}(\d{2}[/-]\d{2}[/-]\d{4})",
        text,
        re.IGNORECASE,
    )
    if validity_match:
        fields["validade"] = validity_match.group(1)

    code_match = re.search(
        r"(?:c[oó]digo\s+de\s+valida[cç][aã]o|c[oó]digo\s+de\s+controle(?:\s+da\s+certid[aã]o)?)\s*:\s*([A-Z0-9][A-Z0-9./-]{5,})",
        text,
        re.IGNORECASE,
    )
    if code_match:
        fields["codigo_validacao"] = code_match.group(1).strip(" ,.;:-")
    
    # Currency amounts (R$ format)
    currency_match = re.search(r"R\$\s*[\d.,]+", text)
    if currency_match:
        fields["valor"] = currency_match.group(0)
    
    # Common legal field names
    defendant_match = re.search(r"\b(?:réu|ré)\b\s*:\s*([^\n,]+)", text, re.IGNORECASE)
    if defendant_match:
        fields["réu"] = defendant_match.group(1).strip()
    
    author_match = re.search(r"\b(?:autor|autora)\b\s*:\s*([^\n,]+)", text, re.IGNORECASE)
    if author_match:
        fields["autor"] = author_match.group(1).strip()
    
    return [{"field_name": k, "field_value": v} for k, v in fields.items()]


def extract_all_process_numbers(text: str) -> list[str]:
    """Extract all unique CNJ process numbers from text, preserving order of appearance.

    Returns a deduplicated list. The first element matches what parse_legal_fields
    stores in the 'processo' field, so callers can rely on index 0 for compatibility.
    """
    matches = re.findall(r"\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}", text or "")
    seen: set[str] = set()
    result: list[str] = []
    for m in matches:
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result


def _extract_action_type_near(text: str, match_end: int) -> str:
    """Extract action/class type from text window immediately after a process number."""
    window = text[match_end:match_end + 600]

    # Priority 1: labeled field "Ação:", "Classe:", "Tipo:", "Assunto:"
    label_re = re.compile(
        r'(?:A[cç][aã]o|Classe(?:\s+Processual)?|Tipo(?:\s+da\s+A[cç][aã]o)?|Assunto)\s*:\s*'
        r'(.+?)(?=\n[ \t]*\n|\d{7}-\d{2}|\Z)',
        re.IGNORECASE | re.DOTALL,
    )
    m = label_re.search(window)
    if m:
        raw = re.sub(r'\s+', ' ', m.group(1)).strip()
        if 3 <= len(raw) <= 250:
            return raw

    # Priority 2: inline action type after "- " or ": " on the same line as the number
    first_newline = window.find('\n')
    same_line = (window[:first_newline] if first_newline > 0 else window[:150]).strip()
    m2 = re.match(r'[-–—\s]+([A-ZÀ-Ú][A-Za-zÀ-ú].{4,})', same_line)
    if m2:
        candidate = re.sub(r'\s+', ' ', m2.group(1)).strip()
        if 4 <= len(candidate) <= 150:
            return candidate

    return ""


def extract_processes_detailed(text: str) -> list[dict]:
    """Extract all CNJ process numbers with rich metadata.

    Each item contains:
      - number:       the CNJ number string
      - is_homonimo:  True when the number falls in the homonymous section
      - action_type:  action/class label found near the number (may be empty string)

    The list is deduplicated and order-preserved. Backward-compatible: calling
    ``[p["number"] for p in extract_processes_detailed(t)]`` equals
    ``extract_all_process_numbers(t)``.
    """
    text = text or ""

    # Locate where the homonymous section begins (if present)
    hom_re = re.compile(
        r'\b(?:hom[oô]nimo[s]?'
        r'|distribui[cç][oõ]es?\s+hom[oô]nima[s]?'
        r'|processos?\s+hom[oô]nimos?'
        r'|poss[ií]vel\s+hom[oô]nimo[s]?)\b',
        re.IGNORECASE,
    )
    hom_match = hom_re.search(text)
    homonimo_start = hom_match.start() if hom_match else len(text)

    process_re = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}')
    seen: set[str] = set()
    result: list[dict] = []

    for match in process_re.finditer(text):
        number = match.group(0)
        if number in seen:
            continue
        seen.add(number)
        result.append({
            "number": number,
            "is_homonimo": match.start() >= homonimo_start,
            "action_type": _extract_action_type_near(text, match.end()),
        })

    return result


def normalize_entity_text(value: str) -> str:
    """Clean whitespace, OCR artifacts and glued labels before display."""
    value = clean_entity_label_prefix(value or "")
    value = re.sub(r"[*•]+", " ", value)
    value = re.sub(r"\([^)]*\)", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" ,.;:-")


def clean_entity_label_prefix(value: str) -> str:
    """Remove labels accidentally glued to entity text, e.g. PESSOAISMAEL."""
    return re.sub(
        r"^\s*(PESSOA|LOCAL|TEMPO|DATA|CPF|CNPJ|PROCESSO|ORGAO)\s*[:\-]?\s*",
        "",
        value or "",
        flags=re.IGNORECASE,
    )


def is_valid_person_name(value: str) -> bool:
    value = normalize_entity_text(value)
    normalized = _normalize_text(value)
    blocked_terms = (
        "da fe", "dar fe", "pe dos feitos", "poder judiciario", "tribunal",
        "certidao", "acoes criminais", "distribuicoes", "servico tecnico",
        "informacoes criminais", "informacoes civeis", "acao penal",
        "procedimento ordinario", "inquerito policial", "objeto e pe",
        "secretaria", "fazenda", "receita federal", "procuradoria",
        "conselho da justica", "justica federal", "nada constar",
        "nada consta", "nao constam", "file not found", "podera ser completada",
    )
    if any(term in normalized for term in blocked_terms):
        return False
    if re.search(r"\d", value):
        return False
    words = [word for word in value.split() if word]
    if len(words) < 2 or len(words) > 7:
        return False
    small_connectors = {"DA", "DE", "DO", "DAS", "DOS", "E"}
    name_words = [word for word in words if word.upper() not in small_connectors]
    if len(name_words) < 2:
        return False
    return all(re.fullmatch(r"[A-Za-zÀ-ú'’-]+", word) for word in words)


def _add_raw_entity(entities: list[dict], label: str, text: str, confidence: float = 0.8, source: str = "regex") -> None:
    text = normalize_entity_text(text)
    if text:
        entities.append({"label": label, "text": text, "confidence": confidence, "source": source})


def extract_raw_entities(text: str, parsed_fields: list[dict] | None = None) -> list[dict]:
    """Extract broad raw candidates from reusable legal/document patterns."""
    parsed_fields = parsed_fields or parse_legal_fields(text)
    entities: list[dict] = []

    for field in parsed_fields:
        name = field.get("field_name")
        value = str(field.get("field_value") or "")
        if name == "nome":
            _add_raw_entity(entities, "PESSOA", value, 0.95, "parsed_field")
        elif name in {"cpf", "cnpj", "processo", "data"}:
            _add_raw_entity(entities, name.upper(), value, 0.95, "parsed_field")

    person_patterns = [
        r"\bNome\s*:\s*([A-ZÀ-Ú][A-ZÀ-Ú\s\'-]{4,})(?=\s*(?:CPF|CNPJ|RG|Ressalvado|$))",
        r"\bcontra\s*:?\s*[*\s]*([A-ZÀ-Ú][A-ZÀ-Ú\s\'-]{4,}?)(?=\s*(?:\(|OU|CPF|CNPJ|RG|nascid[oa]|natural|,))",
        r"\bem nome de\s*:?\s*[*\s]*([A-ZÀ-Ú][A-ZÀ-Ú\s\'-]{4,}?)(?=\s*,?\s*(?:RG|CPF|CNPJ|,))",
        r"([A-ZÀ-Ú][A-ZÀ-Ú\s\'-]{4,})\s*,?\s*(?:RG|CPF|CNPJ)\s*[:nº]",
    ]
    for pattern in person_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
            candidate = normalize_entity_text(match.group(1).splitlines()[0])
            if is_valid_person_name(candidate):
                _add_raw_entity(entities, "PESSOA", candidate, 0.9, "person_context")

    for match in re.finditer(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", text):
        _add_raw_entity(entities, "CPF_CNPJ", match.group(0), 0.98, "cpf_regex")
    for match in re.finditer(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b", text):
        _add_raw_entity(entities, "CPF_CNPJ", match.group(0), 0.98, "cnpj_regex")
    for match in re.finditer(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b", text):
        _add_raw_entity(entities, "PROCESSO", match.group(0), 0.98, "process_regex")
    for match in re.finditer(r"\b\d{2}[/-]\d{2}[/-]\d{4}\b", text):
        _add_raw_entity(entities, "DATA", match.group(0), 0.9, "date_regex")

    organ_patterns = (
        "Tribunal de Justiça do Estado de São Paulo",
        "Tribunal Regional Federal",
        "Justiça Federal",
        "Conselho da Justiça Federal",
        "Receita Federal",
        "Procuradoria-Geral da Fazenda Nacional",
        "Secretaria da Fazenda e Planejamento do Estado de São Paulo",
        "Ministério da Fazenda",
        "Poder Judiciário",
    )
    normalized_text = _normalize_text(text)
    for organ in organ_patterns:
        if _contains(normalized_text, organ):
            _add_raw_entity(entities, "ORGAO_TRIBUNAL", organ, 0.85, "organ_keyword")

    location_patterns = [
        r"\bComarca de\s+([A-ZÀ-Ú][A-Za-zÀ-ú\s]+?)(?=,|\n|\.|-)",
        r"\bForo de\s+([A-ZÀ-Ú][A-Za-zÀ-ú\s]+?)(?=,|\n|\.|-)",
        r"\bnatural\s+de\s+([A-ZÀ-Ú][A-Za-zÀ-ú\s]+?)(?=,|\n|\.|-)",
    ]
    for pattern in location_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            _add_raw_entity(entities, "LOCAL", match.group(1), 0.75, "location_context")
    for location in ("São Paulo", "Campinas", "Campos do Jordão", "São Manuel", "Brasília", "Nova Esperanca", "Rio de Janeiro"):
        if _contains(normalized_text, location):
            _add_raw_entity(entities, "LOCAL", location, 0.7, "location_keyword")

    class_terms = (
        "Ação Penal", "Procedimento Ordinário", "Lesão Corporal Dolosa",
        "Inquérito Policial", "Execução Criminal", "Falência",
        "Recuperação Judicial", "Recuperações Judiciais", "Execução Fiscal",
        "Ação Monitória",
    )
    for term in class_terms:
        if _contains(normalized_text, term):
            _add_raw_entity(entities, "CLASSE_PROCESSUAL", term, 0.8, "class_keyword")

    status_terms = (
        "Nada consta", "Nada constar", "Não constam", "Certidão negativa",
        "Verificou constar", "Homônimo", "Não qualificado",
    )
    for term in status_terms:
        if _contains(normalized_text, term):
            _add_raw_entity(entities, "SITUACAO_RESULTADO", term, 0.8, "status_keyword")
    if re.search(r"\bverificou\s+c?\s*onstar\b|\bverificou\s+constar\b", text, re.IGNORECASE):
        _add_raw_entity(entities, "SITUACAO_RESULTADO", "Consta", 0.85, "status_context")
    if re.search(r"\bn\s*ada\s+consta(?:r)?\b|\bnada\s+consta(?:r)?\b", text, re.IGNORECASE):
        _add_raw_entity(entities, "SITUACAO_RESULTADO", "Nada consta", 0.85, "status_context")

    legal_terms = (
        "Certidão de objeto e pé", "Dívida Ativa", "Débitos tributários",
        "Fins eleitorais", "Distribuições criminais", "Distribuições cíveis",
        "Débitos trabalhistas", "Pedido de falência",
    )
    for term in legal_terms:
        if _contains(normalized_text, term):
            _add_raw_entity(entities, "TERMO_JURIDICO", term, 0.75, "legal_keyword")

    return entities


def reclassify_entity(entity: dict) -> dict | None:
    text = normalize_entity_text(str(entity.get("text") or entity.get("value") or ""))
    if not text:
        return None
    label = str(entity.get("label") or entity.get("entity") or entity.get("type") or "OUTROS").upper()
    normalized = _normalize_text(text)

    if re.fullmatch(r"\d{3}\.\d{3}\.\d{3}-\d{2}", text) or re.fullmatch(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}", text):
        category = "CPF/CNPJ"
    elif re.fullmatch(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}", text):
        category = "Processos"
    elif re.fullmatch(r"\d{2}[/-]\d{2}[/-]\d{4}", text):
        category = "Datas"
    elif label == "PESSOA":
        if not is_valid_person_name(text):
            return None
        category = "Pessoas"
    elif label in {"CPF", "CNPJ", "CPF_CNPJ"}:
        category = "CPF/CNPJ"
    elif label == "PROCESSO":
        category = "Processos"
    elif label == "DATA":
        category = "Datas"
    elif label == "LOCAL":
        category = "Locais"
    elif label == "ORGAO_TRIBUNAL":
        category = "Órgãos/Tribunais"
    elif label == "CLASSE_PROCESSUAL":
        category = "Classes processuais"
    elif label == "SITUACAO_RESULTADO":
        category = "Situação/Resultado"
    elif label == "TERMO_JURIDICO":
        category = "Termos jurídicos relevantes"
    elif any(term in normalized for term in ("tribunal", "justica federal", "receita federal", "secretaria da fazenda", "procuradoria")):
        category = "Órgãos/Tribunais"
    else:
        category = "Outros"

    return {
        "category": category,
        "label": category,
        "text": text,
        "value": text,
        "confidence": entity.get("confidence"),
        "source": entity.get("source", "post_process"),
    }


def deduplicate_entities(entities: list[dict]) -> list[dict]:
    category_order = {
        "Pessoas": 0,
        "CPF/CNPJ": 1,
        "Processos": 2,
        "Locais": 3,
        "Órgãos/Tribunais": 4,
        "Datas": 5,
        "Classes processuais": 6,
        "Situação/Resultado": 7,
        "Termos jurídicos relevantes": 8,
        "Outros": 9,
    }
    seen = set()
    unique = []
    for entity in entities:
        key = (entity["category"], _normalize_text(entity["text"]))
        if key in seen:
            continue
        seen.add(key)
        unique.append(entity)
    return sorted(unique, key=lambda item: (category_order.get(item["category"], 99), item["text"]))


def organize_extracted_entities(raw_entities: list[dict]) -> list[dict]:
    organized = []
    for entity in raw_entities:
        cleaned = reclassify_entity(entity)
        if cleaned:
            organized.append(cleaned)
    return deduplicate_entities(organized)


def extract_named_entities(text: str, parsed_fields: list[dict] | None = None) -> list[dict]:
    """Extract, clean, reclassify and group legal entities for display."""
    return organize_extracted_entities(extract_raw_entities(text, parsed_fields))


def _risk_classification(score: int) -> dict:
    if score <= 20:
        return {
            "label": "BAIXO RISCO",
            "color": "green",
            "description": "Poucos indicios de impedimentos juridicos relevantes.",
        }
    if score <= 40:
        return {
            "label": "RISCO LEVE",
            "color": "teal",
            "description": "Ha pontos de atencao, mas sem sinais fortes de impedimento.",
        }
    if score <= 60:
        return {
            "label": "RISCO MODERADO",
            "color": "amber",
            "description": "Foram encontrados elementos que exigem revisao juridica cuidadosa.",
        }
    if score <= 80:
        return {
            "label": "ALTO RISCO",
            "color": "orange",
            "description": "Foram encontrados elementos juridicos relevantes que podem impactar a operacao.",
        }
    return {
        "label": "RISCO CRITICO",
        "color": "red",
        "description": "Ha indicios graves ou acumulados que podem impedir ou comprometer a operacao.",
    }


def analyze_risk(text: str, parsed_fields: list[dict], entities: list[dict], document_type: str = None, process_count: int = 0, homonimo_count: int = 0) -> dict:
    """Calculate risk score and return an explainable analysis."""
    normalized_text = _normalize_text(text)
    field_names = {field.get("field_name") for field in parsed_fields}
    entity_types = {entity.get("entity") or entity.get("type") or entity.get("category") for entity in entities}
    base_score = 20
    risk_factors: list[dict] = []

    def has_any(*keywords: str) -> bool:
        return any(_contains(normalized_text, keyword) for keyword in keywords)

    def add_factor(rule: str, description: str, impact: int, factor_type: str) -> None:
        risk_factors.append({
            "rule": rule,
            "description": description,
            "impact": impact,
            "type": factor_type,
        })

    positive_rules = [
        ("certidao_negativa", "Certidao negativa encontrada", -20, ("certidao negativa", "e certificado que nao constam", "nao constam pendencias", "nada consta")),
        ("sem_acoes_relevantes", "Texto indica ausencia de acoes ou impedimentos relevantes", -15, ("nao constam acoes", "nada consta", "nao constam debitos")),
        ("documento_valido", "Documento contem indicacao de validade ou autenticidade", -10, ("valida ate", "validade", "autenticidade", "codigo de controle")),
    ]
    negative_rules = [
        ("processo_criminal", "Processo ou inquerito criminal localizado", 55, ("processo criminal localizado", "verificou constar", "acao penal", "inquerito policial", "vara criminal")),
        ("certidao_positiva", "Certidao positiva ou apontamento localizado", 35, ("verificou constar", "certidao positiva", "constar contra", "constam apontamentos")),
        ("pendencia_fiscal", "Pendencia fiscal ou tributaria localizada", 35, ("pendencia fiscal", "pendencias fiscais", "debitos tributarios", "inscricao em divida ativa")),
        ("execucao_fiscal", "Execucao fiscal localizada", 35, ("execucao fiscal localizada", "execucoes fiscais localizadas", "verificou constar execucao fiscal", "consta execucao fiscal")),
        ("acao_monitoria", "Acao monitoria localizada", 25, ("acao monitoria", "acao monitoria", "monitoria")),
        ("fraude", "Indicador textual de fraude ou ilegalidade", 45, ("fraude", "ilegal", "falsidade", "documento falso")),
        ("inconsistencia_documental", "Indicador de inconsistencia documental", 25, ("inconsistencia cadastral", "divergencia cadastral", "dados inconsistentes")),
        ("litigio", "Termos de litigio ou disputa encontrados", 15, ("litigio", "disputa", "controversia", "reclamacao")),
    ]

    for rule, description, impact, keywords in positive_rules:
        if has_any(*keywords):
            add_factor(rule, description, impact, "positive")

    if "cpf" in field_names:
        add_factor("cpf_encontrado", "CPF encontrado e extraido do documento", -5, "positive")
    if "nome" in field_names or "PESSOA" in entity_types or "Pessoas" in entity_types:
        add_factor("nome_identificado", "Nome da pessoa identificado no documento", -5, "positive")
    if "data" in field_names:
        add_factor("data_encontrada", "Data relevante encontrada no documento", -5, "positive")

    for rule, description, impact, keywords in negative_rules:
        if has_any(*keywords):
            add_factor(rule, description, impact, "negative")

    # Process count factor: more processes in a certificate → higher risk
    if process_count == 1:
        add_factor(
            "processo_identificado",
            "Um numero de processo identificado no documento",
            5,
            "negative",
        )
    elif 2 <= process_count <= 3:
        add_factor(
            "multiplos_processos_moderado",
            f"{process_count} numeros de processo identificados — volume processual moderado",
            15,
            "negative",
        )
    elif process_count >= 4:
        add_factor(
            "multiplos_processos_alto",
            f"{process_count} numeros de processo identificados — volume processual elevado, requer analise manual",
            30,
            "negative",
        )

    # Homônimos: informacional, impacto leve (não são processos diretos da pessoa)
    if homonimo_count == 1:
        add_factor(
            "homonimo_encontrado",
            "1 processo homonimo identificado — exige declaracao de ciencia assinada pelo requerente",
            5,
            "negative",
        )
    elif homonimo_count > 1:
        add_factor(
            "homonimos_encontrados",
            f"{homonimo_count} processos homonimos identificados — exigem declaracao de ciencia assinada pelo requerente",
            8,
            "negative",
        )

    raw_score = base_score + sum(factor["impact"] for factor in risk_factors)
    final_score = max(0, min(100, int(raw_score)))
    classification = _risk_classification(final_score)
    positive_factors = [factor for factor in risk_factors if factor["type"] == "positive"]
    negative_factors = [factor for factor in risk_factors if factor["type"] == "negative"]

    if process_count > 1:
        process_note = (
            f" Foram identificados {process_count} numero(s) de processo no documento,"
            " o que aumenta a necessidade de analise manual."
        )
    elif process_count == 1:
        process_note = " Foi identificado 1 numero de processo no documento."
    else:
        process_note = ""

    homonimo_note = ""
    if homonimo_count == 1:
        homonimo_note = " Ha 1 processo homonimo que exige declaracao de ciencia."
    elif homonimo_count > 1:
        homonimo_note = f" Ha {homonimo_count} processos homonimos que exigem declaracao de ciencia."

    if negative_factors and final_score > 60:
        summary = "O documento apresenta risco elevado porque foram encontrados apontamentos juridicos relevantes que podem impactar a analise." + process_note + homonimo_note
    elif negative_factors:
        summary = "O documento possui pontos de atencao juridica, mas tambem apresenta elementos positivos que reduzem o risco final." + process_note + homonimo_note
    elif positive_factors:
        summary = "O documento apresenta baixo risco juridico porque foram encontrados elementos favoraveis e dados consistentes." + process_note + homonimo_note
    else:
        summary = "O documento nao trouxe indicadores suficientes de risco; recomenda-se revisao manual se o PDF estiver incompleto ou ilegivel." + process_note + homonimo_note

    return {
        "score": final_score,
        "base_score": base_score,
        "classification": classification["label"],
        "classification_color": classification["color"],
        "description": classification["description"],
        "risk_factors": risk_factors,
        "positive_factors": positive_factors,
        "negative_factors": negative_factors,
        "calculation": {
            "base_score": base_score,
            "total_positive_impact": sum(factor["impact"] for factor in positive_factors),
            "total_negative_impact": sum(factor["impact"] for factor in negative_factors),
            "raw_score": raw_score,
            "final_score": final_score,
        },
        "summary": summary,
        "document_type": document_type,
        "process_count": process_count,
        "homonimo_count": homonimo_count,
    }


def score_risk(text: str, parsed_fields: list[dict], entities: list[dict]) -> float:
    """Backward-compatible numeric score from 0.0 to 1.0."""
    return round(analyze_risk(text, parsed_fields, entities)["score"] / 100, 2)


def generate_legal_opinion(text: str, document_type: str = None, entities: list[dict] = None, process_count: int = 0, homonimo_count: int = 0) -> str:
    """Generate a basic legal opinion"""
    if not entities:
        entities = []

    label = DOCUMENT_TYPE_LABELS.get(document_type, document_type or "não identificado")
    opinion = f"Parecer técnico - Documento classificado como '{label}'.\n"

    if entities:
        opinion += f"Foram identificadas {len(entities)} entidades no documento.\n"

    main_count = process_count - homonimo_count
    if main_count == 1:
        opinion += "Foi identificado 1 número de processo principal no documento.\n"
    elif main_count > 1:
        opinion += (
            f"Foram identificados {main_count} números de processo no documento. "
            "O documento contém múltiplas referências processuais que devem ser "
            "conferidas individualmente pelo analista responsável.\n"
        )

    if homonimo_count == 1:
        opinion += (
            "Foi identificado 1 processo homônimo. "
            "É necessária a assinatura de declaração de ciência pelo requerente.\n"
        )
    elif homonimo_count > 1:
        opinion += (
            f"Foram identificados {homonimo_count} processos homônimos. "
            "Para todos eles, é necessária a assinatura de declaração de ciência pelo requerente, "
            "confirmando estar ciente da existência desses processos.\n"
        )

    opinion += "Para análise jurídica completa, recomenda-se avaliação por profissional especializado."

    return opinion
