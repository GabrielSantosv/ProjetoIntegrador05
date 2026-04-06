"""Módulo de leitura e extração de texto de arquivos PDF.

Este módulo implementa três abordagens distintas para extrair texto de PDFs:

1. **Extração direta de texto** (sem conversão para imagem):
   - ``PdfPlumberReader``: usa a biblioteca *pdfplumber* para ler o conteúdo
     textual e as tabelas já embutidas no arquivo PDF.
   - ``PyMuPDFReader``: usa a biblioteca *PyMuPDF* (fitz) para ler o texto
     diretamente da estrutura interna do PDF.
   Nessas abordagens, **nenhuma conversão para imagem é realizada**; o texto é
   extraído do próprio fluxo de dados do arquivo.

2. **OCR sobre imagem** (conversão para imagem + reconhecimento de caracteres):
   - Quando ativado via ``HybridReader(enable_ocr=True)``, páginas que retornam
     menos de 25 caracteres (documentos escaneados ou com texto em imagem)
     passam pelo seguinte fluxo::

         PDF → PyMuPDF renderiza a página como Pixmap (imagem) →
         PIL converte o Pixmap em imagem RGB →
         Tesseract (pytesseract) reconhece o texto da imagem → texto

   - A escala padrão de renderização é 2×, o que equivale a ~144 DPI,
     suficiente para obter boa qualidade de OCR.

3. **Modelo de IA Donut** (conversão para imagem + inferência deep learning):
   - Abordagem separada, implementada em ``02_SCRIPTS/ia_huggingface.py``.
   - Usa *pdf2image* para converter cada página em imagem PNG e em seguida
     alimenta o modelo Donut (Vision Encoder-Decoder) da HuggingFace
     para responder perguntas sobre o documento.

O ``HybridReader`` combina as abordagens 1 e 2 automaticamente:

- Tenta primeiro o leitor preferido (padrão: *pdfplumber*).
- Se falhar ou não retornar texto, tenta o leitor alternativo (*PyMuPDF*).
- Se OCR estiver habilitado e a página ainda tiver texto insuficiente,
  converte a página em imagem e executa o Tesseract.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import fitz  # PyMuPDF
import pdfplumber
import pytesseract
from PIL import Image
from pypdf import PdfReader, PdfWriter


@dataclass
class PageText:
    """Representa o conteúdo extraído de uma única página de um PDF.

    Attributes:
        page_number: Número da página (1-based).
        text: Texto extraído da página.
        tables: Lista de tabelas extraídas (cada tabela é uma matriz de células).
        source: Identifica o método usado para extrair o texto
            (``"plumber"``, ``"fitz"``, ``"plumber+ocr"``, ``"fitz+ocr"`` etc.).
    """

    page_number: int
    text: str
    tables: list[list[list[str | None]]] | None = None
    source: str = "text"


class PDFReader(Protocol):
    """Protocolo comum a todos os leitores de PDF."""

    def read_pages(self, pdf_path: Path) -> list[PageText]:
        """Lê todas as páginas de *pdf_path* e retorna uma lista de :class:`PageText`."""
        ...


class PdfPlumberReader:
    """Extrai texto e tabelas diretamente do PDF usando *pdfplumber*.

    **Abordagem:** extração direta de texto — o PDF **não** é convertido em
    imagem. O *pdfplumber* interpreta os operadores gráficos do PDF e reconstrói
    o fluxo de texto posicionando cada caractere segundo suas coordenadas no
    espaço da página.

    É a leitura mais precisa para PDFs digitais (criados por software), pois
    respeita espaçamentos e ordens de leitura. Também extrai tabelas detectando
    bordas de linhas e agrupamentos de células.

    Args:
        extract_tables: Se ``True`` (padrão), tenta extrair tabelas além do
            texto corrido.
    """

    def __init__(self, extract_tables: bool = True) -> None:
        self.extract_tables = extract_tables

    def read_pages(self, pdf_path: Path) -> list[PageText]:
        """Lê *pdf_path* e retorna uma :class:`PageText` por página."""
        pages: list[PageText] = []
        with pdfplumber.open(pdf_path) as pdf:
            for index, page in enumerate(pdf.pages, start=1):
                text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
                tables = page.extract_tables() if self.extract_tables else []
                pages.append(PageText(page_number=index, text=text, tables=tables, source="plumber"))
        return pages


class PyMuPDFReader:
    """Extrai texto diretamente do PDF usando *PyMuPDF* (fitz).

    **Abordagem:** extração direta de texto — o PDF **não** é convertido em
    imagem. O PyMuPDF acessa a estrutura interna do PDF (``/Contents``) e
    reconstrói o texto a partir dos operadores de texto (``BT``/``ET``).

    É geralmente mais rápido que o *pdfplumber* e serve como alternativa
    quando aquele falha ou retorna texto vazio. Não extrai tabelas
    estruturadas por padrão.
    """

    def read_pages(self, pdf_path: Path) -> list[PageText]:
        """Lê *pdf_path* e retorna uma :class:`PageText` por página."""
        pages: list[PageText] = []
        with fitz.open(pdf_path) as doc:
            for index, page in enumerate(doc, start=1):
                text = page.get_text("text") or ""
                pages.append(PageText(page_number=index, text=text, tables=[], source="fitz"))
        return pages


class HybridReader:
    """Leitor híbrido que combina extração direta de texto com OCR opcional.

    **Processo de extração (por ordem de tentativa):**

    1. Tenta o leitor primário (padrão: :class:`PdfPlumberReader`).
       → Extração **direta** do PDF, sem conversão para imagem.
    2. Se o leitor primário falhar ou retornar páginas sem texto, tenta o
       leitor secundário (:class:`PyMuPDFReader`).
       → Também extração **direta**, sem conversão para imagem.
    3. Se ``enable_ocr=True`` e uma página tiver menos de 25 caracteres
       (indicando documento escaneado), aplica OCR::

           PyMuPDF renderiza a página como Pixmap (matrix=2×, ~144 DPI)
           → PIL converte Pixmap em imagem RGB
           → Tesseract (pytesseract) extrai texto da imagem

       Somente nesta etapa o PDF é **convertido em imagem** internamente.

    Args:
        prefer: Leitor primário. ``"plumber"`` (padrão) ou ``"fitz"``.
        enable_ocr: Se ``True``, ativa OCR para páginas com texto insuficiente.
        ocr_language: Idioma(s) passado ao Tesseract (padrão: ``"por+eng"``).
        extract_tables: Repassado ao :class:`PdfPlumberReader`.
    """

    def __init__(self, prefer: str = "plumber", enable_ocr: bool = False, ocr_language: str = "por+eng", extract_tables: bool = True) -> None:
        self.prefer = prefer
        self.enable_ocr = enable_ocr
        self.ocr_language = ocr_language
        self.plumber = PdfPlumberReader(extract_tables=extract_tables)
        self.fitz_reader = PyMuPDFReader()

    def read_pages(self, pdf_path: Path) -> list[PageText]:
        """Lê *pdf_path* aplicando a estratégia híbrida descrita na classe."""
        primary = self.plumber if self.prefer == "plumber" else self.fitz_reader
        secondary = self.fitz_reader if primary is self.plumber else self.plumber

        try:
            pages = primary.read_pages(pdf_path)
        except Exception:
            pages = secondary.read_pages(pdf_path)

        if not any(page.text.strip() for page in pages):
            pages = secondary.read_pages(pdf_path)

        if self.enable_ocr:
            pages = [self._maybe_ocr_page(pdf_path, page) for page in pages]

        return pages

    def _maybe_ocr_page(self, pdf_path: Path, page: PageText) -> PageText:
        """Aplica OCR à *page* somente se o texto extraído for insuficiente.

        Uma página é considerada insuficiente quando possui menos de 25
        caracteres não-espaço, o que normalmente indica que o conteúdo está
        armazenado como imagem (documento escaneado).
        """
        if len(page.text.strip()) >= 25:
            return page

        ocr_text = self._ocr_page(pdf_path, page.page_number)
        if not ocr_text.strip():
            return page

        merged_text = page.text.strip()
        if merged_text:
            merged_text = f"{merged_text}\n{ocr_text.strip()}"
        else:
            merged_text = ocr_text.strip()
        return PageText(page_number=page.page_number, text=merged_text, tables=page.tables, source=f"{page.source}+ocr")

    def _ocr_page(self, pdf_path: Path, page_number: int) -> str:
        """Converte a página para imagem e extrai texto via Tesseract (OCR).

        Fluxo interno:
            1. Abre o PDF com PyMuPDF.
            2. Renderiza a página como :class:`fitz.Pixmap` em escala 2× (~144 DPI).
            3. Converte o Pixmap em imagem RGB usando *Pillow*.
            4. Passa a imagem ao Tesseract via *pytesseract* para reconhecimento
               de caracteres no idioma definido em ``ocr_language``.

        Returns:
            Texto reconhecido pelo OCR, ou string vazia em caso de erro.
        """
        try:
            with fitz.open(pdf_path) as doc:
                page = doc[page_number - 1]
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
                return pytesseract.image_to_string(image, lang=self.ocr_language)
        except Exception:
            return ""


class PDFToolkit:
    """Utilitários para manipulação de arquivos PDF (mesclar e dividir)."""

    @staticmethod
    def merge(files: list[Path], output_path: Path) -> Path:
        """Mescla múltiplos PDFs em um único arquivo.

        Args:
            files: Lista de caminhos para os PDFs de entrada.
            output_path: Caminho do PDF de saída mesclado.

        Returns:
            O caminho *output_path* após a escrita do arquivo.
        """
        writer = PdfWriter()
        for file_path in files:
            reader = PdfReader(str(file_path))
            for page in reader.pages:
                writer.add_page(page)
        with output_path.open("wb") as handle:
            writer.write(handle)
        return output_path

    @staticmethod
    def split(pdf_path: Path, output_dir: Path) -> list[Path]:
        """Divide um PDF em arquivos de página única.

        Args:
            pdf_path: Caminho do PDF de entrada.
            output_dir: Diretório onde os PDFs individuais serão salvos.

        Returns:
            Lista de caminhos para os PDFs gerados (um por página).
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        reader = PdfReader(str(pdf_path))
        output_files: list[Path] = []
        for index, page in enumerate(reader.pages, start=1):
            writer = PdfWriter()
            writer.add_page(page)
            output_path = output_dir / f"{pdf_path.stem}_p{index}.pdf"
            with output_path.open("wb") as handle:
                writer.write(handle)
            output_files.append(output_path)
        return output_files
