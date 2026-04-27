from __future__ import annotations

import logging
from pathlib import Path

import pdfplumber

from .classifier import DocumentClassifier
from .exporter import Exporter
from .extraction_strategies import FallbackExtractor, ExtractionResult
from .models import DocumentRecord, PipelineResult, TableRecord
from .parser import RegexParser
from .readers import HybridReader

logger = logging.getLogger(__name__)

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
        # Sistema de fallback para extração
        self.extractor = FallbackExtractor(
            prefer_strategy="plumber" if prefer_reader == "plumber" else "fitz",
            enable_ocr=enable_ocr,
            extract_tables=extract_tables,
        )
        # Leitor legado (fallback de fallback)
        self.reader = HybridReader(prefer=prefer_reader, enable_ocr=enable_ocr, extract_tables=extract_tables)
        self.parser = RegexParser(profile=profile)
        self.classifier = DocumentClassifier(model_path=model_path)
        self.exporter = Exporter()
        # CPF do titular do precatório — usado para detectar homônimos
        self.cpf_alvo = cpf_alvo

    # ------------------------------------------------------------------
    # Processamento de arquivo com lógica de fallback robusto
    # ------------------------------------------------------------------
    def process_file(self, pdf_path: Path) -> tuple[list[DocumentRecord], list[TableRecord]]:
        records: list[DocumentRecord] = []
        tables: list[TableRecord] = []

        # Hint de tipo pela pasta-pai
        folder_hint = self._folder_hint(pdf_path)

        try:
            # ============================================================
            # ESTRATÉGIA PRINCIPAL: Usar FallbackExtractor com 3 fallbacks
            # ============================================================
            extraction_result = self.extractor.extract(pdf_path)

            logger.info(
                f"\n{'='*70}"
                f"\nArquivo: {pdf_path.name}"
                f"\nEstrutura principal: {extraction_result.strategy_used}"
                f"\nÉ escaneado: {extraction_result.is_scanned}"
                f"\nFallbacks usados: {extraction_result.fallback_count}"
                f"\n{'='*70}"
            )

            # Processar páginas extraídas
            for page_data in extraction_result.pages:
                # Classificação
                document_type = folder_hint or self.classifier.classify(page_data.text)
                nivel_risco = self.classifier.nivel_risco(document_type)

                # Ajustar perfil do parser ao tipo identificado
                if document_type and document_type != "desconhecido":
                    from .profiles import get_profile as _get_profile
                    self.parser.profile = _get_profile(document_type)

                # Extração de campos
                parsed = self.parser.parse(page_data.text)

                extra_fields = parsed.extra_fields or {}
                extra_fields.update({
                    "extraction_strategy": page_data.strategy,
                    "extraction_source": page_data.source,
                    "text_confidence": page_data.text_confidence,
                    "fallback_reason": page_data.fallback_reason or "",
                })

                records.append(
                    DocumentRecord(
                        source_file=str(pdf_path),
                        page_number=page_data.page_number,
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
                        raw_text=page_data.text,
                        metadata={
                            "text_source": page_data.source,
                            "table_count": len(page_data.tables or []),
                            "processes_geometric": parsed.processes_from_geometry,
                            **extra_fields,
                        },
                    )
                )

                # Extrair tabelas se disponíveis
                for table_index, cells in enumerate(page_data.tables or [], start=1):
                    tables.append(
                        TableRecord(
                            source_file=str(pdf_path),
                            page_number=page_data.page_number,
                            table_index=table_index,
                            document_type=document_type,
                            cells=cells,
                            metadata={
                                "text_source": page_data.source,
                                "extraction_strategy": page_data.strategy,
                            },
                        )
                    )

                # Lógica de interrupção por homônimos
                if parsed.status == "NADA CONSTAR":
                    logger.info(f"NADA CONSTAR detectado - interrompendo processamento do arquivo")
                    break

        except Exception as e:
            logger.error(f"FallbackExtractor falhou: {e}")
            logger.info("Ativando fallback legado (HybridReader)...")

            # FALLBACK DE EMERGÊNCIA: Sistema legado HybridReader
            try:
                pages = self.reader.read_pages(pdf_path)
                for page in pages:
                    document_type = folder_hint or self.classifier.classify(page.text)
                    nivel_risco = self.classifier.nivel_risco(document_type)
                    parsed = self.parser.parse(page.text)
                    extra_fields = parsed.extra_fields or {}
                    extra_fields["extraction_strategy"] = "HybridReader (Legacy Fallback)"

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
            except Exception as legacy_error:
                logger.error(f"Até o legado falhou: {legacy_error}")
                raise RuntimeError(f"Ambos os sistemas falharam para {pdf_path.name}: {e}")

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
