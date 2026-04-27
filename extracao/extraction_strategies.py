"""
Sistema de Fallback para Extração de PDFs com 3 estratégias progressivas.

Estratégia 1: PdfPlumber (padrão, mais rápido)
Estratégia 2: PyMuPDF/Fitz (alternativa, confiável)
Estratégia 3: PDF2Image + OCR (último recurso para PDFs escaneados)

Cada estratégia retorna PageText com metadados sobre qual método foi usado.
"""

from __future__ import annotations

import logging
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    import fitz
    _FITZ_AVAILABLE = True
except ImportError:
    fitz = None
    _FITZ_AVAILABLE = False

import pdfplumber

try:
    import pytesseract
    from PIL import Image
    import pdf2image
    _OCR_AVAILABLE = True
except ImportError:
    pytesseract = None
    Image = None
    pdf2image = None
    _OCR_AVAILABLE = False


logger = logging.getLogger(__name__)


@dataclass
class PageText:
    """Representa uma página extraída com metadados sobre a estratégia usada."""
    page_number: int
    text: str
    tables: Optional[list[list[list[str | None]]]] = None
    source: str = "unknown"  # "plumber" | "fitz" | "pdf2image_ocr"
    strategy: str = "unknown"  # Nome descritivo da estratégia usada
    extraction_success: bool = True  # Indica se a extração foi bem-sucedida
    fallback_reason: Optional[str] = None  # Por que caiu no fallback
    text_confidence: float = 1.0  # Confiança na qualidade do texto (0-1)


@dataclass
class ExtractionResult:
    """Resultado da extração de um arquivo PDF."""
    file_path: Path
    pages: list[PageText]
    strategy_used: str  # Estratégia principal que funcionou
    is_scanned: bool = False  # Se detectou que é documento escaneado
    fallback_count: int = 0  # Quantos fallbacks foram usados


class ExtractionStrategy(ABC):
    """Interface abstrata para estratégias de extração."""

    @abstractmethod
    def extract(self, pdf_path: Path, extract_tables: bool = True) -> list[PageText]:
        """
        Extrai texto e tabelas do PDF.

        Args:
            pdf_path: Caminho do arquivo PDF
            extract_tables: Se deve extrair tabelas estruturadas

        Returns:
            Lista de PageText representando cada página

        Raises:
            Exception: Quando a estratégia falha
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Retorna o nome descritivo da estratégia."""
        pass


class PdfPlumberStrategy(ExtractionStrategy):
    """
    Estratégia 1: PdfPlumber
    - Melhor para PDFs com texto nativo
    - Extrai tabelas estruturadas
    - Mantém informações geométricas
    """

    def __init__(self, extract_tables: bool = True):
        self.extract_tables = extract_tables

    def get_name(self) -> str:
        return "PdfPlumber (Estratégia 1)"

    def extract(self, pdf_path: Path, extract_tables: bool = True) -> list[PageText]:
        """Extrai usando pdfplumber."""
        pages: list[PageText] = []
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                for index, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""

                    if not text.strip():
                        # Pdfplumber falhou em extrair texto desta página
                        raise ValueError(f"Página {index}: nenhum texto extraído")

                    tables = page.extract_tables() if extract_tables else []

                    pages.append(
                        PageText(
                            page_number=index,
                            text=text,
                            tables=tables,
                            source="plumber",
                            strategy=self.get_name(),
                            extraction_success=True,
                            text_confidence=1.0,
                        )
                    )
            return pages
        except Exception as e:
            logger.warning(f"PdfPlumber falhou: {str(e)}")
            raise


class PyMuPDFStrategy(ExtractionStrategy):
    """
    Estratégia 2: PyMuPDF (Fitz)
    - Alternativa confiável
    - Funciona bem com PDFs corruptíveis ou complexos
    - Menos informações geométricas que pdfplumber
    """

    def get_name(self) -> str:
        return "PyMuPDF (Estratégia 2)"

    def extract(self, pdf_path: Path, extract_tables: bool = True) -> list[PageText]:
        """Extrai usando PyMuPDF/Fitz."""
        if not _FITZ_AVAILABLE:
            raise ImportError("PyMuPDF (fitz) não instalado. Use: pip install pymupdf")

        pages: list[PageText] = []
        try:
            with fitz.open(str(pdf_path)) as doc:
                for index, page in enumerate(doc, start=1):
                    text = page.get_text("text") or ""

                    if not text.strip():
                        # Fitz também não conseguiu extrair
                        raise ValueError(f"Página {index}: nenhum texto extraído")

                    pages.append(
                        PageText(
                            page_number=index,
                            text=text,
                            tables=[] if extract_tables else [],
                            source="fitz",
                            strategy=self.get_name(),
                            extraction_success=True,
                            text_confidence=1.0,
                        )
                    )
            return pages
        except Exception as e:
            logger.warning(f"PyMuPDF falhou: {str(e)}")
            raise


class PDF2ImageOCRStrategy(ExtractionStrategy):
    """
    Estratégia 3: PDF2Image + Tesseract OCR
    - Converte PDF em imagens e usa OCR
    - LENTO mas funciona para PDFs escaneados
    - Última opção quando texto está oculto
    """

    def __init__(self, ocr_language: str = "por+eng", dpi: int = 200):
        self.ocr_language = ocr_language
        self.dpi = dpi

    def get_name(self) -> str:
        return "PDF2Image + OCR (Estratégia 3)"

    def extract(self, pdf_path: Path, extract_tables: bool = True) -> list[PageText]:
        """Extrai usando PDF2Image + Tesseract OCR."""
        if not _OCR_AVAILABLE:
            raise ImportError(
                "pdf2image ou pytesseract não instalados.\n"
                "Use: pip install pdf2image pytesseract pillow\n"
                "E instale Tesseract: https://github.com/UB-Mannheim/tesseract"
            )

        pages: list[PageText] = []
        try:
            logger.info(f"Convertendo PDF para imagens em {self.dpi}DPI...")

            # Converter PDF em imagens
            images = pdf2image.convert_from_path(
                str(pdf_path),
                dpi=self.dpi,
                fmt="ppm",
            )

            logger.info(f"Executando OCR em {len(images)} imagens...")

            for page_num, image in enumerate(images, start=1):
                # OCR da imagem
                text = pytesseract.image_to_string(image, lang=self.ocr_language)

                if not text.strip():
                    logger.warning(f"OCR retornou texto vazio para página {page_num}")
                    text = ""
                    confidence = 0.0
                else:
                    confidence = 0.7  # OCR é menos confiável

                pages.append(
                    PageText(
                        page_number=page_num,
                        text=text,
                        tables=[],  # OCR não extrai tabelas estruturadas
                        source="pdf2image_ocr",
                        strategy=self.get_name(),
                        extraction_success=len(text.strip()) > 0,
                        text_confidence=confidence,
                    )
                )

            return pages
        except Exception as e:
            logger.error(f"PDF2Image+OCR falhou: {str(e)}")
            raise


class FallbackExtractor:
    """
    Orquestrador principal que tenta as estratégias em sequência.
    Implementa o padrão de fallback: tenta 1 → 2 → 3.
    """

    def __init__(
        self,
        prefer_strategy: str = "plumber",
        enable_ocr: bool = True,
        ocr_language: str = "por+eng",
        extract_tables: bool = True,
    ):
        """
        Args:
            prefer_strategy: "plumber" ou "fitz" (padrão ao começar)
            enable_ocr: Se deve permitir fallback para OCR
            ocr_language: Idiomas para OCR (ex: "por+eng")
            extract_tables: Se deve extrair tabelas estruturadas
        """
        self.prefer_strategy = prefer_strategy
        self.enable_ocr = enable_ocr
        self.ocr_language = ocr_language
        self.extract_tables = extract_tables

        # Estratégias em ordem de preferência
        self.strategies: list[ExtractionStrategy] = []
        self._setup_strategies()

    def _setup_strategies(self) -> None:
        """Configura as estratégias na ordem correta."""
        self.strategies.clear()

        # Estratégia 1 (preferida)
        if self.prefer_strategy == "fitz":
            self.strategies.append(PyMuPDFStrategy())
            self.strategies.append(PdfPlumberStrategy(self.extract_tables))
        else:
            self.strategies.append(PdfPlumberStrategy(self.extract_tables))
            self.strategies.append(PyMuPDFStrategy())

        # Estratégia 3 (OCR) apenas se habilitado
        if self.enable_ocr:
            self.strategies.append(
                PDF2ImageOCRStrategy(
                    ocr_language=self.ocr_language,
                    dpi=200
                )
            )

    def extract(self, pdf_path: Path) -> ExtractionResult:
        """
        Extrai texto do PDF usando fallback automático.

        Tenta as estratégias em ordem até uma delas funcionar.
        Registra qual estratégia foi usada nos metadados.

        Args:
            pdf_path: Caminho do arquivo PDF

        Returns:
            ExtractionResult com páginas extraídas e metadados

        Raises:
            RuntimeError: Se nenhuma estratégia conseguir extrair o PDF
        """
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF não encontrado: {pdf_path}")

        logger.info(f"\n{'='*70}")
        logger.info(f"Inicializando extração: {pdf_path.name}")
        logger.info(f"Estratégias disponíveis: {len(self.strategies)}")
        logger.info(f"{'='*70}")

        last_error: Optional[Exception] = None
        strategy_used: Optional[str] = None
        fallback_count = 0

        for idx, strategy in enumerate(self.strategies, start=1):
            try:
                logger.info(f"\n[{idx}/{len(self.strategies)}] Tentando {strategy.get_name()}...")
                pages = strategy.extract(pdf_path, self.extract_tables)

                # Validar resultado
                if not pages:
                    logger.warning(f"Estratégia retornou lista vazia")
                    raise ValueError("Nenhuma página foi extraída")

                # Sucesso!
                strategy_used = strategy.get_name()
                logger.info(f"✓ {strategy_used} - SUCESSO!")
                logger.info(f"  Páginas extraídas: {len(pages)}")
                logger.info(f"  Confiança média: {sum(p.text_confidence for p in pages) / len(pages):.1%}")

                return ExtractionResult(
                    file_path=pdf_path,
                    pages=pages,
                    strategy_used=strategy_used,
                    fallback_count=fallback_count,
                )

            except Exception as e:
                fallback_count += 1
                last_error = e
                error_msg = str(e)[:100]  # Primeiros 100 chars do erro
                logger.warning(f"✗ Falhou: {error_msg}")

                if idx < len(self.strategies):
                    next_strategy = self.strategies[idx].get_name()
                    logger.info(f"  → Caindo para fallback: {next_strategy}")

        # Nenhuma estratégia funcionou
        error_summary = f"Todas as {len(self.strategies)} estratégias falharam"
        logger.error(error_summary)
        if last_error:
            logger.error(f"Último erro: {last_error}")

        raise RuntimeError(
            f"{error_summary} para {pdf_path.name}. "
            f"Última tentativa: {str(last_error)}"
        )

    def is_scanned_pdf(self, pdf_path: Path, sample_pages: int = 2) -> bool:
        """
        Detecta se o PDF é primarily escaneado (baseado em texto).

        Estratégia: tenta extrair texto com pdfplumber nos primeiros N paginas.
        Se conseguir menos de 25 chars de texto, considera escaneado.

        Args:
            pdf_path: Caminho do PDF
            sample_pages: Quantas páginas amostrar

        Returns:
            True se parece ser escaneado, False se tem texto nativo
        """
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                total_chars = 0
                for page in pdf.pages[:sample_pages]:
                    text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
                    total_chars += len(text.strip())

                average_chars = total_chars / min(sample_pages, len(pdf.pages))
                is_scanned = average_chars < 25

                logger.debug(
                    f"Análise de documento escaneado: {average_chars:.0f} chars/página → "
                    f"{'ESCANEADO' if is_scanned else 'TEXTO NATIVO'}"
                )

                return is_scanned
        except Exception as e:
            logger.debug(f"Erro ao detectar se é escaneado: {e}")
            return False
