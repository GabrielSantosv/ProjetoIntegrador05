from __future__ import annotations

from pathlib import Path

from .classifier import DocumentClassifier
from .exporter import Exporter
from .models import DocumentRecord, PipelineResult, TableRecord
from .parser import RegexParser
from .readers import HybridReader


class DocumentPipeline:
    def __init__(self, prefer_reader: str = "plumber", model_path: Path | None = None, profile: str = "generic", enable_ocr: bool = False, extract_tables: bool = True) -> None:
        self.reader = HybridReader(prefer=prefer_reader, enable_ocr=enable_ocr, extract_tables=extract_tables)
        self.parser = RegexParser(profile=profile)
        self.classifier = DocumentClassifier(model_path=model_path)
        self.exporter = Exporter()

    def process_file(self, pdf_path: Path) -> tuple[list[DocumentRecord], list[TableRecord]]:
        records: list[DocumentRecord] = []
        pages = self.reader.read_pages(pdf_path)
        tables: list[TableRecord] = []

        for page in pages:
            parsed = self.parser.parse(page.text)
            document_type = self.classifier.classify(page.text)
            extra_fields = parsed.extra_fields or {}
            records.append(
                DocumentRecord(
                    source_file=str(pdf_path),
                    page_number=page.page_number,
                    document_type=document_type,
                    name=parsed.name,
                    cpf=parsed.cpf,
                    process_number=parsed.process_number,
                    date=parsed.date,
                    value=parsed.value,
                    raw_text=page.text,
                    metadata={
                        "text_source": page.source,
                        "table_count": len(page.tables or []),
                        **extra_fields,
                    },
                )
            )

            for table_index, cells in enumerate(page.tables or [], start=1):
                tables.append(
                    TableRecord(
                        source_file=str(pdf_path),
                        page_number=page.page_number,
                        table_index=table_index,
                        document_type=document_type,
                        cells=cells,
                        metadata={"text_source": page.source},
                    )
                )

        return records, tables

    def process_path(self, input_path: Path) -> PipelineResult:
        files = self._collect_pdfs(input_path)
        records: list[DocumentRecord] = []
        tables: list[TableRecord] = []
        for pdf_path in files:
            page_records, page_tables = self.process_file(pdf_path)
            records.extend(page_records)
            tables.extend(page_tables)
        return PipelineResult(records=records, tables=tables, source_files=files)

    def export(self, result: PipelineResult, output_path: Path) -> Path:
        return self.exporter.export(result, output_path)

    @staticmethod
    def _collect_pdfs(input_path: Path) -> list[Path]:
        if input_path.is_file():
            return [input_path]
        return sorted(path for path in input_path.rglob("*.pdf") if path.is_file())
