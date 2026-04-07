from __future__ import annotations

from pathlib import Path

import pdfplumber

from .classifier import DocumentClassifier
from .exporter import Exporter
from .models import DocumentRecord, PipelineResult, TableRecord
from .parser import RegexParser
from .readers import HybridReader

# Mapeamento de pasta de entrada para tipo de documento
# Permite que a estrutura de diretórios reforce a classificação
FOLDER_TYPE_MAP: dict[str, str] = {
    "01_TJSP": "",            # classificação dinâmica (civel vs criminal)
    "02_TRT15": "cndt",
    "03_CNDT": "cndt",
    "04a_CND_Federal": "cnd_federal",
    "04b_TRF3": "trf3",
    "05_DOCUMENTOS": "",
}


class DocumentPipeline:
    def __init__(
        self,
        prefer_reader: str = "plumber",
        model_path: Path | None = None,
        profile: str = "generic",
        enable_ocr: bool = False,
        extract_tables: bool = True,
        cpf_alvo: str | None = None,
    ) -> None:
        self.reader = HybridReader(prefer=prefer_reader, enable_ocr=enable_ocr, extract_tables=extract_tables)
        self.parser = RegexParser(profile=profile)
        self.classifier = DocumentClassifier(model_path=model_path)
        self.exporter = Exporter()
        # CPF do titular do precatório — usado para detectar homônimos
        self.cpf_alvo = cpf_alvo

    # ------------------------------------------------------------------
    # Processamento de arquivo com lógica de interrupção
    # ------------------------------------------------------------------
    def process_file(self, pdf_path: Path) -> tuple[list[DocumentRecord], list[TableRecord]]:
        records: list[DocumentRecord] = []
        tables: list[TableRecord] = []

        # Hint de tipo pela pasta-pai
        folder_hint = self._folder_hint(pdf_path)

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for index, plumber_page in enumerate(pdf.pages, start=1):
                    # Classificar usando texto da página
                    raw_text = plumber_page.extract_text(x_tolerance=2, y_tolerance=2) or ""
                    document_type = folder_hint or self.classifier.classify(raw_text)
                    nivel_risco = self.classifier.nivel_risco(document_type)

                    # Ajustar perfil do parser ao tipo identificado
                    if document_type and document_type != "desconhecido":
                        from .profiles import get_profile as _get_profile
                        self.parser.profile = _get_profile(document_type)

                    # Extração com lógica de homônimos (parse_page)
                    parsed = self.parser.parse_page(plumber_page, cpf_alvo=self.cpf_alvo)

                    # Determinar o número de processo primário
                    process_number = (
                        parsed.processes_from_geometry[0]
                        if parsed.processes_from_geometry
                        else parsed.process_number
                    )

                    extra_fields = parsed.extra_fields or {}
                    records.append(
                        DocumentRecord(
                            source_file=str(pdf_path),
                            page_number=index,
                            document_type=document_type,
                            nivel_risco=nivel_risco,
                            name=parsed.name,
                            cpf=parsed.cpf,
                            process_number=process_number,
                            date=parsed.date,
                            value=parsed.value,
                            tipo_acao=parsed.tipo_acao,
                            situacao_processual=parsed.situacao_processual,
                            vara=parsed.vara,
                            foro=parsed.foro,
                            status=parsed.status,
                            raw_text=raw_text,
                            metadata={
                                "text_source": "plumber",
                                "table_count": len(plumber_page.extract_tables() or []),
                                "processes_geometric": parsed.processes_from_geometry,
                                **extra_fields,
                            },
                        )
                    )

                    # Extrair tabelas
                    for table_index, cells in enumerate(plumber_page.extract_tables() or [], start=1):
                        tables.append(
                            TableRecord(
                                source_file=str(pdf_path),
                                page_number=index,
                                table_index=table_index,
                                document_type=document_type,
                                cells=cells,
                                metadata={"text_source": "plumber"},
                            )
                        )

                    # -------------------------------------------------------
                    # Lógica de Interrupção: se NADA CONSTAR para o CPF-alvo,
                    # encerrar o processamento deste arquivo imediatamente.
                    # Evita processar 60+ páginas de homônimos.
                    # -------------------------------------------------------
                    if parsed.status == "NADA CONSTAR":
                        break

        except Exception:
            # Fallback para HybridReader (leitura sem geometria)
            pages = self.reader.read_pages(pdf_path)
            for page in pages:
                document_type = folder_hint or self.classifier.classify(page.text)
                nivel_risco = self.classifier.nivel_risco(document_type)
                parsed = self.parser.parse(page.text)
                extra_fields = parsed.extra_fields or {}
                records.append(
                    DocumentRecord(
                        source_file=str(pdf_path),
                        page_number=page.page_number,
                        document_type=document_type,
                        nivel_risco=nivel_risco,
                        name=parsed.name,
                        cpf=parsed.cpf,
                        process_number=parsed.process_number,
                        date=parsed.date,
                        value=parsed.value,
                        tipo_acao=parsed.tipo_acao,
                        situacao_processual=parsed.situacao_processual,
                        vara=parsed.vara,
                        foro=parsed.foro,
                        status=parsed.status,
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

    @staticmethod
    def _folder_hint(pdf_path: Path) -> str:
        """Infere o tipo do documento pela pasta-pai, sem depender de ML."""
        for part in pdf_path.parts:
            mapped = FOLDER_TYPE_MAP.get(part)
            if mapped is not None:
                return mapped
        return ""
