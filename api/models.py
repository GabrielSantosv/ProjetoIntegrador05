from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class DocumentEntity(BaseModel):
    entity_type: str
    value: str
    confidence: Optional[float] = None


class ParsedField(BaseModel):
    field_name: str
    field_value: str


class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_path: str
    status: str
    extraction_method: str
    document_type: Optional[str] = None
    extracted_text: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    entities: Optional[List[Dict[str, Any]]] = None
    legal_opinion: Optional[str] = None
    risk_score: Optional[float] = None
    created_at: str
    updated_at: str


class DocumentListResponse(BaseModel):
    id: int
    filename: str
    document_type: Optional[str] = None
    risk_score: Optional[float] = None
    status: str
    created_at: str
