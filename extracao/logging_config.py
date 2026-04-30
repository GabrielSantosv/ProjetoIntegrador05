"""
Sistema de logging centralizado para o pipeline de extração.

Fornece informações detalhadas sobre quais estratégias foram usadas,
quais falharam e por quê, facilitando o debugging.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    name: str = "extracao",
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    verbose: bool = False,
) -> logging.Logger:
    """
    Configura logging global para o pipeline.

    Args:
        name: Nome do logger
        level: Nível de logging (DEBUG, INFO, WARNING, ERROR)
        log_file: Arquivo opcional para salvar logs
        verbose: Se True, usa DEBUG ao invés de INFO

    Returns:
        Logger configurado
    """
    if verbose:
        level = logging.DEBUG

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Evitar loggers duplicados
    logger.handlers.clear()

    # ===================================================================
    # Formatter detalhado com informações sobre estratégias
    # ===================================================================
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S"
    )

    simple_formatter = logging.Formatter(
        fmt="%(levelname)-8s | %(message)s"
    )

    # ===================================================================
    # Handler para console (stdout)
    # ===================================================================
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)

    # ===================================================================
    # Handler para arquivo (opcional)
    # ===================================================================
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # Arquivo sempre tem DEBUG
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)

    return logger


def create_extraction_logger(
    output_dir: Optional[Path] = None,
    verbose: bool = False,
) -> tuple[logging.Logger, Optional[logging.FileHandler]]:
    """
    Cria um logger específico para extração com rastreamento de estratégias.

    Args:
        output_dir: Diretório para salvar logs (opcional)
        verbose: Debug mode

    Returns:
        Tupla (logger, file_handler_ou_none)
    """
    log_file = None
    if output_dir:
        log_file = output_dir / "extraction.log"

    logger = setup_logging(
        name="extracao.pipeline",
        level=logging.DEBUG if verbose else logging.INFO,
        log_file=log_file,
        verbose=verbose,
    )

    return logger, None


# =========================================================================
# Utilitários para log estruturado de estratégias
# =========================================================================

class StrategyLogger:
    """Wrapper para logar tentativas e falhas de estratégias."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def strategy_attempt(self, strategy_name: str, attempt: int, total: int) -> None:
        """Log quando tenta uma estratégia."""
        self.logger.info(f"[{attempt}/{total}] Tentando {strategy_name}...")

    def strategy_success(self, strategy_name: str, pages: int, confidence: float) -> None:
        """Log quando uma estratégia succeeds."""
        self.logger.info(
            f"✓ {strategy_name} - SUCESSO! "
            f"({pages} páginas, confiança: {confidence:.1%})"
        )

    def strategy_failed(self, strategy_name: str, error: str, fallback: str) -> None:
        """Log quando uma estratégia falha."""
        self.logger.warning(
            f"✗ {strategy_name} falhou: {error[:80]}"
            f" → {fallback}"
        )

    def pdf_analysis(self, filename: str, is_scanned: bool, strategy: str) -> None:
        """Log análise inicial do PDF."""
        pdf_type = "ESCANEADO" if is_scanned else "TEXTO NATIVO"
        self.logger.info(f"\n{'='*70}")
        self.logger.info(f"Analisando: {filename}")
        self.logger.info(f"Tipo identificado: {pdf_type}")
        self.logger.info(f"Estratégia principal: {strategy}")
        self.logger.info(f"{'='*70}")

    def file_complete(self, filename: str, total_pages: int, fallback_count: int) -> None:
        """Log quando arquivo é completamente processado."""
        self.logger.info(
            f"\n✓ {filename}: {total_pages} páginas processadas "
            f"({fallback_count} fallback{'s' if fallback_count != 1 else ''})"
        )
