"""Standalone extraction services without Django dependencies"""
import os
import sys
from pathlib import Path

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
    from pdf2image import convert_from_path
except ImportError:
    pytesseract = None
    convert_from_path = None


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
    
    # Try pdfplumber
    if pdfplumber:
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            if text.strip():
                return text, "pdfplumber"
        except Exception as e:
            print(f"pdfplumber failed: {e}")
    
    # Try PyMuPDF
    if fitz:
        try:
            doc = fitz.open(file_path)
            for page in doc:
                text += page.get_text()
            doc.close()
            if text.strip():
                return text, "fitz"
        except Exception as e:
            print(f"PyMuPDF failed: {e}")
    
    # Try OCR
    if pytesseract and convert_from_path:
        try:
            images = convert_from_path(file_path)
            for image in images:
                text += pytesseract.image_to_string(image) + "\n"
            if text.strip():
                return text, "ocr"
        except Exception as e:
            print(f"OCR failed: {e}")
    
    return text if text else "Failed to extract text", method


def classify_certificate_type(text: str) -> str:
    """Classify document type based on keywords"""
    text_lower = text.lower()
    
    # Keyword patterns for different document types
    patterns = {
        "certidão": ["certidão", "certidao"],
        "contrato": ["contrato", "acordo", "ajuste"],
        "petição": ["petição", "peticao", "ação", "acao"],
        "sentença": ["sentença", "sentenca", "julgado"],
        "procuração": ["procuração", "procuracao", "poder"],
        "parecer": ["parecer", "opinião", "opiniao"],
        "relatório": ["relatório", "relatorio", "informe"],
    }
    
    for doc_type, keywords in patterns.items():
        if any(kw in text_lower for kw in keywords):
            return doc_type
    
    return "indeterminado"


def parse_legal_fields(text: str, document_type: str = None) -> list[dict]:
    """Parse common legal fields from text"""
    import re
    
    fields = {}
    
    # CPF pattern (11 digits with or without formatting)
    cpf_match = re.search(r'(\d{3}\.?\d{3}\.?\d{3}-?\d{2})', text)
    if cpf_match:
        fields['cpf'] = cpf_match.group(1)
    
    # CNPJ pattern
    cnpj_match = re.search(r'(\d{2}\.?\d{3}\.?\d{3}/?0001-?\d{2})', text)
    if cnpj_match:
        fields['cnpj'] = cnpj_match.group(1)
    
    # Process number (20 digits)
    process_match = re.search(r'(\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4})', text)
    if process_match:
        fields['processo'] = process_match.group(1)
    
    # Dates (DD/MM/YYYY or DD-MM-YYYY)
    date_matches = re.findall(r'(\d{2}[/-]\d{2}[/-]\d{4})', text)
    if date_matches:
        fields['data'] = date_matches[0]
    
    # Currency amounts (R$ format)
    currency_match = re.search(r'R\$\s*[\d.,]+', text)
    if currency_match:
        fields['valor'] = currency_match.group(0)
    
    # Common legal field names
    defendant_match = re.search(r'(?:réu|ré)\s*:?\s*([^\n,]+)', text, re.IGNORECASE)
    if defendant_match:
        fields['réu'] = defendant_match.group(1).strip()
    
    author_match = re.search(r'(?:autor|autora)\s*:?\s*([^\n,]+)', text, re.IGNORECASE)
    if author_match:
        fields['autor'] = author_match.group(1).strip()
    
    return [{'field_name': k, 'field_value': v} for k, v in fields.items()]


def extract_named_entities(text: str) -> list[dict]:
    """Extract named entities (people, places, times) with regex"""
    import re
    
    entities = []
    
    # Names (capitalized words that appear to be person names)
    name_pattern = r'\b([A-Z][a-záéíóú]+(?:\s+[A-Z][a-záéíóú]+)+)\b'
    for match in re.finditer(name_pattern, text):
        entities.append({
            'entity': 'PESSOA',
            'value': match.group(1),
            'confidence': 0.7
        })
    
    # Common location indicators
    location_keywords = ['Brasil', 'São Paulo', 'Rio de Janeiro', 'Minas Gerais', 'Salvador', 
                        'Brasília', 'Fortaleza', 'Recife', 'Manaus', 'Curitiba', 'Porto Alegre']
    for location in location_keywords:
        if location.lower() in text.lower():
            entities.append({
                'entity': 'LOCAL',
                'value': location,
                'confidence': 0.8
            })
    
    # Temporal expressions
    temporal_keywords = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
                        'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
    for temporal in temporal_keywords:
        if temporal.lower() in text.lower():
            entities.append({
                'entity': 'TEMPO',
                'value': temporal,
                'confidence': 0.6
            })
    
    # Remove duplicates
    seen = set()
    unique_entities = []
    for ent in entities:
        key = (ent['entity'], ent['value'])
        if key not in seen:
            seen.add(key)
            unique_entities.append(ent)
    
    return unique_entities[:20]  # Limit to 20 entities


def score_risk(text: str, parsed_fields: list[dict], entities: list[dict]) -> float:
    """Calculate risk score based on text analysis"""
    risk_score = 0.0
    
    text_lower = text.lower()
    
    # Risk indicators
    high_risk_keywords = ['fraude', 'crime', 'ilegal', 'morto', 'morte', 'falecimento']
    medium_risk_keywords = ['litígio', 'disputa', 'controvérsia', 'reclamação', 'reclamacao']
    low_risk_keywords = ['aprovado', 'julgado', 'sentenciado', 'condenado']
    
    for keyword in high_risk_keywords:
        if keyword in text_lower:
            risk_score += 0.25
    
    for keyword in medium_risk_keywords:
        if keyword in text_lower:
            risk_score += 0.10
    
    for keyword in low_risk_keywords:
        if keyword in text_lower:
            risk_score -= 0.05
    
    # Normalize to 0-1
    risk_score = max(0.0, min(1.0, risk_score))
    
    return round(risk_score, 2)


def generate_legal_opinion(text: str, document_type: str = None, entities: list[dict] = None) -> str:
    """Generate a basic legal opinion"""
    if not entities:
        entities = []
    
    opinion = f"Parecer técnico - Documento classificado como '{document_type or 'não identificado'}'.\n"
    
    if entities:
        opinion += f"Foram identificadas {len(entities)} entidades no documento.\n"
    
    opinion += "Para análise jurídica completa, recomenda-se avaliação por profissional especializado."
    
    return opinion
