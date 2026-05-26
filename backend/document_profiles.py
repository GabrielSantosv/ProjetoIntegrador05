"""Reusable document classification profiles.

Profiles are based on textual evidence, not file names. The classifier
normalizes accents/case/punctuation before matching these keywords.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


KeywordGroup = Sequence[str]


@dataclass(frozen=True)
class DocumentProfile:
    name: str
    required_keywords: Sequence[KeywordGroup]
    optional_keywords: Sequence[str]
    min_score: int
    priority: int


DOCUMENT_PROFILES: tuple[DocumentProfile, ...] = (
    DocumentProfile(
        name="civel_estadual",
        required_keywords=(
            ("tribunal de justica do estado de sao paulo", "poder judiciario"),
            ("certidao estadual de distribuicoes civeis", "distribuicoes civeis"),
        ),
        optional_keywords=(
            "diretoria de servico tecnico de informacoes civeis",
            "estadual civel",
            "certidao estadual civel",
        ),
        min_score=70,
        priority=100,
    ),
    DocumentProfile(
        name="criminal_estadual",
        required_keywords=(
            ("tribunal de justica do estado de sao paulo", "poder judiciario"),
            ("certidao estadual de distribuicoes criminais", "acoes criminais"),
        ),
        optional_keywords=(
            "diretoria de servico tecnico de informacoes criminais",
            "criminal estadual",
            "certidao criminal estadual",
        ),
        min_score=70,
        priority=100,
    ),
    DocumentProfile(
        name="execucao_criminal_estadual",
        required_keywords=(
            ("tribunal de justica do estado de sao paulo", "poder judiciario"),
            ("execucoes criminais",),
        ),
        optional_keywords=(
            "certidao de execucoes criminais",
            "criminal estadual",
        ),
        min_score=70,
        priority=110,
    ),
    DocumentProfile(
        name="tj_falencia",
        required_keywords=(
            ("tribunal de justica do estado de sao paulo", "poder judiciario"),
            ("pedidos de falencia", "pedido de falencia", "certidao de falencia", "falencia recuperacao judicial"),
        ),
        optional_keywords=(
            "recuperacao judicial",
            "falencia",
            "distribuicoes civeis",
        ),
        min_score=70,
        priority=105,
    ),
    DocumentProfile(
        name="tj_segundo_grau",
        required_keywords=(
            ("tribunal de justica do estado de sao paulo", "poder judiciario"),
            ("segunda instancia", "segunda instancia", "2 grau", "2o grau"),
        ),
        optional_keywords=(
            "tj 2 grau",
            "tjsp 2 grau",
        ),
        min_score=60,
        priority=90,
    ),
    DocumentProfile(
        name="cndt",
        required_keywords=(
            ("certidao negativa de debitos trabalhistas",),
            ("tribunal superior do trabalho", "justica do trabalho", "tst"),
        ),
        optional_keywords=(
            "banco nacional de devedores trabalhistas",
            "debitos trabalhistas",
            "cndt",
        ),
        min_score=78,
        priority=120,
    ),
    DocumentProfile(
        name="ceat",
        required_keywords=(
            ("trt15", "tribunal regional do trabalho da 15", "justica do trabalho"),
            ("ceat", "acoes trabalhistas", "certidao eletronica de acoes trabalhistas"),
        ),
        optional_keywords=(
            "certidao de acoes trabalhistas",
        ),
        min_score=70,
        priority=115,
    ),
    DocumentProfile(
        name="cnd_federal",
        required_keywords=(
            ("certidao negativa de debitos relativos aos tributos federais", "debitos relativos aos tributos federais"),
            ("receita federal do brasil", "procuradoria geral da fazenda nacional", "divida ativa da uniao"),
        ),
        optional_keywords=(
            "ministerio da fazenda",
            "pgfn",
            "rfb",
            "nao constam pendencias",
            "codigo de controle",
            "validade",
        ),
        min_score=76,
        priority=115,
    ),
    DocumentProfile(
        name="cnd_estadual",
        required_keywords=(
            ("secretaria da fazenda", "secretaria da fazenda e planejamento"),
            ("debitos tributarios nao inscritos", "debitos tributarios", "divida ativa", "cadin"),
        ),
        optional_keywords=(
            "estado de sao paulo",
            "procuradoria geral do estado",
            "nao constam debitos",
            "certidao negativa",
            "cnd estadual",
        ),
        min_score=72,
        priority=110,
    ),
    DocumentProfile(
        name="civel_federal",
        required_keywords=(
            ("tribunal regional federal", "justica federal"),
            ("certidao judicial civel", "distribuicao civel", "acoes civeis"),
        ),
        optional_keywords=(
            "conselho da justica federal",
            "nada consta",
            "certidao negativa",
            "cpf",
            "processos civeis",
            "trf civel",
        ),
        min_score=72,
        priority=105,
    ),
    DocumentProfile(
        name="criminal_federal",
        required_keywords=(
            ("tribunal regional federal", "justica federal"),
            ("certidao judicial criminal", "criminal negativa", "acoes criminais"),
        ),
        optional_keywords=(
            "conselho da justica federal",
            "nada consta",
            "certidao negativa",
            "fins criminais",
            "cpf",
            "trf criminal",
        ),
        min_score=72,
        priority=104,
    ),
    DocumentProfile(
        name="eleitoral",
        required_keywords=(
            ("tribunal regional federal", "justica federal"),
            ("fins eleitorais", "certidao judicial para fins eleitorais"),
        ),
        optional_keywords=(
            "certidao negativa",
            "nada consta",
            "crimes eleitorais",
            "conselho da justica federal",
            "cpf",
            "eleitoral",
        ),
        min_score=72,
        priority=103,
    ),
)


UNKNOWN_DOCUMENT_TYPE = "desconhecido"

# Mapping from internal slugs to human-readable labels
DOCUMENT_TYPE_LABELS = {
    "civel_estadual": "Certidão Cível Estadual",
    "criminal_estadual": "Certidão Criminal Estadual",
    "execucao_criminal_estadual": "Certidão de Execuções Criminais Estadual",
    "tj_falencia": "Certidão de Falência / Recuperação Judicial",
    "tj_segundo_grau": "Certidão TJSP 2º Grau",
    "cnd_estadual": "Certidão Negativa Estadual",
    "cnd_federal": "Certidão Negativa Federal",
    "cndt": "CNDT",
    "ceat": "CEAT / TRT15",
    "civel_federal": "Certidão Cível Federal / TRF",
    "criminal_federal": "Certidão Criminal Federal / TRF",
    "eleitoral": "Certidão Eleitoral / Fins Eleitorais",
    "desconhecido": "Tipo desconhecido",
}
