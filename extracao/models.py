from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _serialize_table(cells: list[list[str | None]]) -> str:
    import json

    return json.dumps(cells, ensure_ascii=False)


@dataclass
class DocumentRecord:
    source_file: str
    page_number: int
    document_type: str = "desconhecido"
    nivel_risco: str = "informativo"  # maximo | medio | informativo
    name: str | None = None
    cpf: str | None = None
    process_number: str | None = None
    date: str | None = None
    value: str | None = None
    # Campos obrigatórios para análise de precatórios
    tipo_acao: str | None = None          # Ex: Execução de Título, Cobrança
    situacao_processual: str | None = None  # Ex: Suspenso, Em andamento
    vara: str | None = None
    foro: str | None = None
    # Status da certidão
    status: str | None = None             # "NADA CONSTAR" | "POSITIVA"
    raw_text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_file": self.source_file,
            "page_number": self.page_number,
            "document_type": self.document_type,
            "nivel_risco": self.nivel_risco,
            "name": self.name,
            "cpf": self.cpf,
            "process_number": self.process_number,
            "date": self.date,
            "value": self.value,
            "tipo_acao": self.tipo_acao,
            "situacao_processual": self.situacao_processual,
            "vara": self.vara,
            "foro": self.foro,
            "status": self.status,
            "raw_text": self.raw_text,
            **self.metadata,
        }


@dataclass
class TableRecord:
    source_file: str
    page_number: int
    table_index: int
    document_type: str = "desconhecido"
    cells: list[list[str | None]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_file": str(self.source_file),
            "page_number": self.page_number,
            "table_index": self.table_index,
            "document_type": self.document_type,
            "cells_json": _serialize_table(self.cells),
            **self.metadata,
        }


@dataclass
class PipelineResult:
    records: list[DocumentRecord]
    tables: list[TableRecord]
    source_files: list[Path]
