"""Utilities for extracting a first-pass procedural review from court case PDFs."""
from __future__ import annotations

import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")


_DATE_RE = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")
_MONEY_RE = re.compile(
    r"(?:R\$\s*)?\b\d{1,3}(?:\.\d{3})*,\d{2}\b",
    re.IGNORECASE,
)

_EVENT_PATTERNS: list[tuple[str, list[str]]] = [
    # Most specific — evaluated first so they win over generic matches
    ("transito_em_julgado",    ["transito em julgado"]),
    ("arquivamento_baixa",     ["arquivamento", "baixa definitiva", "baixado"]),
    ("acordao",                ["acordao"]),
    ("sentenca",               ["sentenca", "julgo procedente", "julgo improcedente", "julgo extinto", "julgo parcialmente procedente"]),
    ("decisao",                ["decisao interlocutoria", "decisao monocratica", "decido", "defiro", "indefiro"]),
    ("audiencia",              ["audiencia de conciliacao", "audiencia de instrucao", "pauta de audiencia", "audiencia realizada", "audiencia designada"]),
    ("recurso",                ["recurso de apelacao", "apelacao civel", "agravo de instrumento", "agravo regimental", "embargos declaratorios", "apelacao interposta"]),
    ("replica",                ["replica"]),
    ("contestacao",            ["contestacao"]),
    ("peticao_inicial",        ["peticao inicial"]),
    ("acordo",                 ["homologo o acordo", "acordo homologado", "autocomposicao"]),
    ("intimacao_citacao",      ["intimacao", "intime-se", "citacao", "cite-se", "mandado de citacao"]),
    ("distribuicao_ajuizamento", ["distribuicao", "distribuido", "ajuizamento", "ajuizada", "protocolada"]),
    ("despacho",               ["despacho", "ato ordinatorio"]),
    ("prazo",                  ["prazo de ", "prazo para contestar", "prazo para recorrer", "prazo para cumprimento", "prazo assinado"]),
    ("movimentacao",           ["juntada", "expedicao", "conclusos"]),
    # Generic — only reached when nothing more specific matched
    ("fatos_narrados",         ["fatos narrados", "data dos fatos", "data da ocorrencia"]),
]

_IMPORTANT_EVENT_TYPES = {
    "decisao",
    "sentenca",
    "despacho",
    "acordao",
    "acordo",
    "transito_em_julgado",
    "arquivamento_baixa",
}


def _norm(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text.lower()).strip()


def _clean_snippet(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" -:;,.")[:220]


def _parse_date(value: str) -> datetime | None:
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _event_type_for_context(context: str) -> str:
    normalized = _norm(context)
    for event_type, keywords in _EVENT_PATTERNS:
        if any(keyword in normalized for keyword in keywords):
            return event_type
    return "data_relevante"


def _label_event_type(event_type: str) -> str:
    labels = {
        "distribuicao_ajuizamento": "Distribuicao / ajuizamento",
        "fatos_narrados": "Fatos narrados",
        "peticao_inicial": "Peticao inicial",
        "contestacao": "Contestacao",
        "replica": "Replica",
        "recurso": "Recurso",
        "despacho": "Despacho",
        "decisao": "Decisao",
        "sentenca": "Sentenca",
        "acordao": "Acordao",
        "audiencia": "Audiencia",
        "intimacao_citacao": "Intimacao / citacao",
        "prazo": "Prazo processual",
        "movimentacao": "Movimentacao processual",
        "transito_em_julgado": "Transito em julgado",
        "arquivamento_baixa": "Arquivamento / baixa",
        "acordo": "Acordo",
        "data_relevante": "Data relevante",
    }
    return labels.get(event_type, event_type.replace("_", " ").title())


def _extract_timeline(text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for match in _DATE_RE.finditer(text):
        start = max(0, match.start() - 100)
        end = min(len(text), match.end() + 200)
        context = text[start:end]
        event_type = _event_type_for_context(context)
        snippet = _clean_snippet(context)
        key = (match.group(1), event_type, snippet[:120])
        if key in seen:
            continue
        seen.add(key)
        parsed = _parse_date(match.group(1))
        events.append({
            "date": match.group(1),
            "sort_date": parsed.isoformat() if parsed else "",
            "event_type": event_type,
            "label": _label_event_type(event_type),
            "excerpt": snippet,
        })

    events.sort(key=lambda item: item["sort_date"] or "9999-99-99")
    return events[:80]


def _extract_amounts(text: str) -> list[str]:
    values: list[str] = []
    for match in _MONEY_RE.finditer(text):
        value = match.group(0)
        if not value.upper().startswith("R$"):
            start = max(0, match.start() - 4)
            if "R$" in text[start:match.start()].upper():
                value = "R$ " + value
        if value not in values:
            values.append(value)
        if len(values) >= 12:
            break
    return values


def _extract_movements(text: str) -> list[dict[str, str]]:
    movements: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    # Matches lines starting with a date (optionally followed by a time), then a separator, then description.
    # Handles SAJ/eProc formats: "15/03/2023 14:23 - Ato ordinatório..."
    line_re = re.compile(
        r"(?im)^\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})(?:\s+\d{2}:\d{2}(?::\d{2})?)?\s*[-–:|]?\s*(.{10,300})"
    )
    for match in line_re.finditer(text):
        desc = _clean_snippet(match.group(2))
        if len(desc.strip()) < 10:
            continue
        key = (match.group(1), desc[:50])
        if key in seen:
            continue
        seen.add(key)
        event_type = _event_type_for_context(desc)
        movements.append({
            "date": match.group(1),
            "event_type": event_type,
            "label": _label_event_type(event_type),
            "description": desc,
        })
        if len(movements) >= 60:
            break
    return movements


def _extract_important_decisions(timeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    important = [event for event in timeline if event["event_type"] in _IMPORTANT_EVENT_TYPES]
    return important[-10:]


def _extract_deadlines(text: str) -> list[dict[str, str]]:
    deadlines: list[dict[str, str]] = []
    pattern = re.compile(
        r"(?i)(.{0,160}\bprazo\b.{0,220}?\b(?:\d{1,3})\s+dias?.{0,160})"
    )
    for match in pattern.finditer(text):
        snippet = _clean_snippet(match.group(1))
        days_match = re.search(r"(\d{1,3})\s+dias?", snippet, re.IGNORECASE)
        deadlines.append({
            "days": days_match.group(1) if days_match else "",
            "description": snippet,
            "status": "pendente" if "pendente" in _norm(snippet) else "identificado",
        })
        if len(deadlines) >= 20:
            break
    return deadlines


def _extract_parties(text: str) -> dict[str, str]:
    """Extract plaintiff (autor), defendant (réu), and judge from the document header."""
    head = text[:8000]
    parties: dict[str, str] = {}

    patterns = [
        ("autor", re.compile(
            r"(?i)(?:autora?s?|requerentes?|reclamantes?|exequentes?|impetrantes?|promoventes?|polo\s+ativo|parte\s+autora?)\s*[:–\-]\s*([^\n\r;]{4,100})"
        )),
        ("reu", re.compile(
            r"(?i)(?:r[eé][uú]s?\b|requerid[ao]s?|reclamad[ao]s?|executad[ao]s?|impetrad[ao]s?|polo\s+passivo|parte\s+r[eé]?[uú]?)\s*[:–\-]\s*([^\n\r;]{4,100})"
        )),
        ("juiz", re.compile(
            r"(?i)(?:mm\.?\s*juiz[ao]?|juiz[ao]?\s+de\s+direito|magistrad[ao]|juiz[ao]?a?)\s*[:–\-]?\s*([^\n\r;,]{4,80})"
        )),
    ]

    for role, pattern in patterns:
        m = pattern.search(head)
        if m:
            name = re.sub(r"\s+", " ", m.group(1)).strip()[:80]
            if len(name) > 3:
                parties[role] = name

    # Fallback: "FULANO X BELTRANO" or "FULANO VS BELTRANO" title line
    if "autor" not in parties or "reu" not in parties:
        vs_m = re.search(
            r"([A-ZÁÉÍÓÚÂÊÔÃÕÇ][^\n]{4,70}?)\s+\bX\b\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][^\n]{4,70})",
            head
        )
        if vs_m:
            if "autor" not in parties:
                parties["autor"] = re.sub(r"\s+", " ", vs_m.group(1)).strip()[:80]
            if "reu" not in parties:
                parties["reu"] = re.sub(r"\s+", " ", vs_m.group(2)).strip()[:80]

    return parties


def _extract_subject_header(text: str) -> str:
    """Extract 'Assunto:' or 'Classe:' label from document header — more specific than _detect_subject."""
    head = text[:5000]
    for pattern in [
        re.compile(r'(?im)^(?:Assunto|Classe|Tipo\s+de\s+A[cç][aã]o)\s*[:\-]\s*(.{5,120})$'),
        re.compile(r'(?i)(?:Assunto|Classe)\s*[:\-]\s*(.{5,120})(?:\n|$|;)'),
    ]:
        m = pattern.search(head)
        if m:
            value = re.sub(r'\s+', ' ', m.group(1)).strip()
            if len(value) > 4:
                return value[:120]
    return ""


def _extract_case_description(text: str) -> str:
    """Extract a brief narrative describing what the case is about ('trata-se de...', etc.)."""
    head = text[:12000]
    patterns = [
        re.compile(r'(?i)trata[- ]se\s+de\s+(.{20,350}?)(?=\.\s{0,3}\n|\n\n|Ex\s+positis|Isso\s+posto|Ante\s+o\s+exposto|Assim,)', re.DOTALL),
        re.compile(r'(?i)cuida[- ]se\s+de\s+(.{20,300}?)(?=\.)', re.DOTALL),
        re.compile(r'(?i)a\s+presente\s+(?:a[cç][aã]o|demanda|execu[cç][aã]o)\s+(.{20,300}?)(?=\.)', re.DOTALL),
        re.compile(r'(?i)o[sa]?\s+(?:autor(?:as?|es?)?|requerentes?)\s+(?:alega[m]?|pede[m]?|pretende[m]?|narr[ao][m]?)\s*[,:]?\s*(.{30,300}?)(?=\.)', re.DOTALL),
    ]
    for pattern in patterns:
        m = pattern.search(head)
        if m:
            desc = re.sub(r'\s+', ' ', m.group(1)).strip()
            if len(desc) > 25:
                return desc[:320]
    return ""


def _extract_main_amount(text: str) -> str:
    """Extract the main debt or case value (valor da causa, valor do débito, etc.)."""
    head = text[:15000]
    _AMOUNT_VALUE = r'((?:R\$\s*)?\d{1,3}(?:\.\d{3})*,\d{2})'
    patterns = [
        re.compile(r'(?i)valor\s+(?:total\s+)?(?:da\s+d[ií]vida|do\s+d[eé]bito|do\s+d[eé]bito\s+atualizado|consolidado|principal)\s*[:\-]?\s*' + _AMOUNT_VALUE),
        re.compile(r'(?i)d[eé]bito\s+(?:total|atualizado|consolidado)\s*[:\-]?\s*' + _AMOUNT_VALUE),
        re.compile(r'(?i)valor\s+da\s+causa\s*[:\-]?\s*' + _AMOUNT_VALUE),
        re.compile(r'(?i)valor\s+(?:do\s+)?contrato\s*[:\-]?\s*' + _AMOUNT_VALUE),
        re.compile(r'(?i)principal\s*[:\-]\s*' + _AMOUNT_VALUE),
        re.compile(r'(?i)importa\s+(?:na\s+)?(?:quantia|soma)\s+de\s+' + _AMOUNT_VALUE),
        re.compile(r'(?i)no\s+valor\s+de\s+' + _AMOUNT_VALUE),
    ]
    for pattern in patterns:
        m = pattern.search(head)
        if m:
            raw = m.group(1).strip()
            if not raw.upper().startswith("R$"):
                raw = "R$ " + raw
            return raw
    return ""


def _detect_subject(text: str) -> str:
    normalized = _norm(text[:10000])
    subjects = [
        ("Criminal", ["acao penal", "ministerio publico", "denuncia", "vara criminal", "inquerito policial", "crime", "criminal"]),
        ("Trabalhista", ["reclamante", "reclamada", "verbas trabalhistas", "tribunal regional do trabalho", "trt", "reclamacao trabalhista"]),
        ("Falencia / recuperacao judicial", ["falencia", "recuperacao judicial", "concordata", "pedido de falencia"]),
        ("Divida ativa / execucao fiscal", ["divida ativa", "execucao fiscal", "fazenda publica", "certidao de divida ativa", "inscrita em divida ativa", "pgfn"]),
        ("Execucao civel / cumprimento de sentenca", ["cumprimento de sentenca", "execucao de sentenca", "penhora", "execucao civel"]),
        ("Indenizacao / responsabilidade civil", ["indenizacao", "danos morais", "danos materiais", "acidente", "responsabilidade civil", "reparacao de danos"]),
        ("Familia / sucessoes", ["alimentos", "divorcio", "inventario", "guarda", "familia", "pensao alimenticia", "uniao estavel"]),
        ("Possessorio / imobiliario", ["possessoria", "reintegracao de posse", "despejo", "usucapiao", "propriedade"]),
        ("Cobranca / contrato", ["acao de cobranca", "cobranca", "inadimplemento", "titulo executivo", "duplicata", "nota promissoria"]),
        ("Previdenciario", ["previdenciario", "inss", "beneficio previdenciario", "aposentadoria", "auxilio doenca"]),
    ]
    for label, keywords in subjects:
        if any(keyword in normalized for keyword in keywords):
            return label
    return ""


def _analyze_with_llm(text: str) -> dict:
    """
    Comprehensive OpenAI call — extracts all structured process fields.
    Uses start + end of document to capture header and movement history.
    Returns {} if key not set or call fails.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return {}
    try:
        import json as _json
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        if len(text) > 8000:
            excerpt = text[:3500] + "\n[...]\n" + text[-4500:]
        else:
            excerpt = text.strip()

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=3000,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "Você é um assistente jurídico brasileiro especializado em análise processual. Responda apenas com JSON válido em português. Use string vazia para campos não encontrados e lista vazia para listas sem itens.",
                },
                {
                    "role": "user",
                    "content": (
                        "Analise o texto de processo judicial abaixo e retorne JSON com estas chaves:\n\n"

                        "\"identificacao\": {\"tribunal\": str, \"comarca\": str, \"vara\": str, "
                        "\"classe_processual\": str (ex: Ação Monitória, Cumprimento de Sentença, Execução Fiscal), "
                        "\"assunto\": str, \"fase_atual\": str, \"data_distribuicao\": str DD/MM/YYYY, "
                        "\"valor_causa\": str R$ X.XXX,XX, \"instancia\": str (1ª instância / 2ª instância / STJ / STF)}\n\n"

                        "\"partes\": {\"autores\": [str], \"reus\": [str], "
                        "\"outros\": [str — terceiros, litisconsortes, espólio, herdeiros, assistentes]}\n\n"

                        "\"objeto\": {\"resumo\": str 5-8 frases cobrindo natureza da ação, relação entre as partes, "
                        "fatos que originaram o processo, valor e o que representa, decisões tomadas e fase atual; "
                        "\"causa_de_pedir\": str; \"pedido_principal\": str; \"pedidos_acessorios\": [str]; \"fato_gerador\": str}\n\n"

                        "\"valores\": {\"valor_causa\": str, \"valor_atualizado\": str, "
                        "\"honorarios\": str, \"multas\": str, \"custas\": str, \"outros\": [str]}\n\n"

                        "\"movimentacoes\": lista APENAS de eventos críticos com data real identificada, em ordem cronológica. "
                        "Inclua: ajuizamento/distribuição, audiências relevantes, perícias, sentenças, acórdãos, "
                        "decisões interlocutórias relevantes, recursos (apelação/agravo/embargos), "
                        "trânsito em julgado, penhoras/bloqueios/SISBAJUD, acordos homologados, arquivamento. "
                        "EXCLUA: citações rotineiras, intimações, despachos de expediente, juntadas, atos ordinatórios. "
                        "Cada item: {\"data\": DD/MM/YYYY obrigatório, \"tipo\": str, \"descricao\": str 1-2 frases}\n\n"

                        "\"riscos\": {\"nivel\": \"baixo\"|\"médio\"|\"alto\", "
                        "\"fatores\": [str — prescrição, decadência, nulidade, risco recursal, litigância de má-fé etc.]}\n\n"

                        "\"situacao_atual\": str descrevendo objetivamente em que pé está o processo hoje\n\n"

                        "\"resumo_final\": str mini resumo, em 2-4 frases, do fim/desfecho do processo. "
                        "OBRIGATORIO quando houver termo de acordo, acordo homologado, transacao, pagamento, "
                        "quitacao, extincao, transito em julgado, baixa, arquivamento ou cumprimento de obrigacao. "
                        "Explique o que foi combinado ou decidido, se foi homologado, se encerrou/extinguiu o processo "
                        "e o que ainda ficou pendente. Se nao houver desfecho identificado, use string vazia.\n\n"

                        "\"patrimonio\": [str — penhoras, bloqueios SISBAJUD/RENAJUD, imóveis, veículos, contas identificadas]\n\n"

                        "\"obrigacoes\": [str — obrigações impostas com valor/prazo quando houver]\n\n"

                        "\"proximo_passo\": str — o que se espera acontecer ou deve ser feito a seguir\n\n"

                        "\"cessao_credito\": objeto descrevendo se houve cessão/transferência de crédito. "
                        "IMPORTANTE: marque ocorreu=true se o texto contiver QUALQUER das seguintes situações: "
                        "(a) menção a cessionário, cedente, cessão de crédito, escritura pública de cessão; "
                        "(b) habilitação de crédito na DEPRE relacionada a cessão; "
                        "(c) comunicação de cessão ao juízo ou à DEPRE; "
                        "(d) FIDC ou fundo de investimento em direitos creditórios como parte; "
                        "(e) referência ao Provimento CSM nº 2.753/2024; "
                        "(f) transferência de titularidade do precatório ou RPV. "
                        "Mesmo que detalhes sejam parciais, marque ocorreu=true e preencha o que for possível. "
                        "Campos: {\"ocorreu\": true|false, "
                        "\"cedente\": str nome completo de quem cedeu o crédito, "
                        "\"cessionario\": str nome completo de quem recebeu o crédito, "
                        "\"cessionario_cnpj\": str CNPJ do cessionário se disponível, "
                        "\"percentual_cedido\": str ex: '70%' ou '100%', "
                        "\"valor_nominal_cedido\": str valor do crédito cedido ex: R$ 53.486,49, "
                        "\"preco_aquisicao\": str valor pago pela cessão ex: R$ 12.000,00, "
                        "\"data_cessao\": str DD/MM/YYYY data da escritura ou contrato de cessão, "
                        "\"instrumento\": str tipo e detalhes do documento ex: Escritura Pública de Cessão lavrada no Cartório X, "
                        "\"processo_depre\": str número do processo na DEPRE para habilitação se houver, "
                        "\"status_habilitacao\": str status atual: pendente de habilitação / habilitado / aguardando esclarecimentos / etc., "
                        "\"observacoes\": str outras informações relevantes sobre a cessão}. "
                        "Se não houver NENHUMA menção a cessão, retorne {\"ocorreu\": false} com demais campos como string vazia.\n\n"

                        f"Texto:\n{excerpt}"
                    ),
                },
            ],
        )
        data = _json.loads(response.choices[0].message.content)
        print(f"[LLM] análise OK — chaves retornadas: {list(data.keys())}", flush=True)
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        print(f"[LLM] ERRO na chamada OpenAI: {type(exc).__name__}: {exc}", flush=True)
        return {}


_CESSAO_KEYWORDS = re.compile(
    r"cess[aã]o\s+de\s+cr[eé]dito"
    r"|cession[aá]rio"
    r"|cedente"
    r"|escritura\s+p[uú]blica\s+de\s+cess[aã]o"
    r"|habilita[cç][aã]o\s+de\s+cr[eé]dito"
    r"|comunica[cç][aã]o\s+da\s+cess[aã]o"
    r"|Provimento\s+CSM"
    r"|FIDC"
    r"|fundo\s+de\s+investimento\s+em\s+direitos\s+credit[oó]rios",
    re.IGNORECASE,
)


def _detect_cessao_credito(text: str, partial: dict) -> dict:
    if not _CESSAO_KEYWORDS.search(text):
        return partial or {"ocorreu": False}

    result: dict[str, Any] = {**partial, "ocorreu": True}

    if not result.get("status_habilitacao"):
        if re.search(r"aguard(ando|a)\s+esclarecimentos", text, re.IGNORECASE):
            result["status_habilitacao"] = "Aguardando esclarecimentos"
        elif re.search(r"habilita[cç][aã]o\s+deferida", text, re.IGNORECASE):
            result["status_habilitacao"] = "Habilitação deferida"
        elif re.search(r"comunica[cç][aã]o\s+da\s+cess[aã]o", text, re.IGNORECASE):
            result["status_habilitacao"] = "Cessão comunicada ao juízo — habilitação em andamento"

    if not result.get("observacoes"):
        m = re.search(
            r"(cess[aã]o\s+de\s+cr[eé]dito[^.]{0,200}\.)",
            text, re.IGNORECASE | re.DOTALL,
        )
        if m:
            result["observacoes"] = m.group(1).strip()

    return result


def _extract_final_summary(text: str, llm_summary: str, latest_events: list[dict[str, Any]]) -> str:
    if llm_summary:
        return llm_summary

    normalized = _norm(text)
    highlights: list[str] = []

    if any(term in normalized for term in ("homologo o acordo", "acordo homologado", "termo de acordo")):
        m = re.search(
            r"(.{0,180}(?:termo\s+de\s+acordo|acordo\s+homologado|homologo\s+o\s+acordo).{0,260})",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if m:
            highlights.append("Houve acordo relevante no fim do processo: " + _clean_snippet(m.group(1)) + ".")
        else:
            highlights.append("Houve termo de acordo ou acordo homologado no fim do processo.")

    if "transito em julgado" in normalized:
        highlights.append("Consta transito em julgado.")

    if any(term in normalized for term in ("arquivamento", "baixa definitiva", "processo extinto")):
        highlights.append("Ha indicacao de encerramento, baixa ou arquivamento.")

    if highlights:
        return " ".join(highlights[:3])

    final_events = [
        event for event in latest_events
        if event.get("event_type") in {"acordo", "sentenca", "acordao", "transito_em_julgado", "arquivamento_baixa"}
    ]
    if final_events:
        event = final_events[-1]
        description = event.get("description") or event.get("excerpt") or ""
        label = event.get("label") or event.get("event_type") or "Evento final"
        date = event.get("date") or ""
        return _clean_snippet(f"{date} - {label}: {description}")

    return ""


def analyze_process_text(text: str, process_number: str = "") -> dict[str, Any]:
    if not process_number:
        num_match = re.search(r"\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}", text)
        if num_match:
            process_number = num_match.group(0)

    # Regex fallbacks (used when LLM unavailable)
    amounts      = _extract_amounts(text)
    subject      = _detect_subject(text)
    main_amount  = _extract_main_amount(text)
    parties      = _extract_parties(text)
    deadlines    = _extract_deadlines(text)

    llm = _analyze_with_llm(text)

    # ── Identification ──────────────────────────────────────────────
    identificacao = llm.get("identificacao") or {}

    # ── Object / Description ────────────────────────────────────────
    objeto = llm.get("objeto") or {}
    case_description = objeto.get("resumo") or _extract_case_description(text)

    # ── Parties ─────────────────────────────────────────────────────
    partes_llm = llm.get("partes") or {}
    autores = partes_llm.get("autores") or []
    reus    = partes_llm.get("reus")    or []
    if autores and not parties.get("autor"):
        parties["autor"] = autores[0]
    if reus and not parties.get("reu"):
        parties["reu"] = reus[0]

    # ── Values ──────────────────────────────────────────────────────
    valores_llm = llm.get("valores") or {}
    main_amount = (
        valores_llm.get("valor_atualizado")
        or valores_llm.get("valor_causa")
        or identificacao.get("valor_causa")
        or main_amount
    )

    # ── Movements ───────────────────────────────────────────────────
    llm_raw = llm.get("movimentacoes") or []
    if isinstance(llm_raw, list) and llm_raw:
        movements: list[dict[str, Any]] = []
        for item in llm_raw:
            if not isinstance(item, dict) or not item.get("data"):
                continue
            if re.search(r'[Xx?]{2}', item["data"]):
                continue
            parsed = _parse_date(item["data"])
            movements.append({
                "date":       item["data"],
                "sort_date":  parsed.isoformat() if parsed else "",
                "event_type": _event_type_for_context(item.get("tipo", "") + " " + item.get("descricao", "")),
                "label":      item.get("tipo", "Movimentação"),
                "description": item.get("descricao", ""),
            })
        movements.sort(key=lambda m: m["sort_date"] or "9999")
    else:
        movements = _extract_movements(text)
        movements.sort(key=lambda m: _parse_date(m["date"]) or datetime.min)

    decisions    = [m for m in movements if m["event_type"] in _IMPORTANT_EVENT_TYPES][-10:]
    latest_events = decisions[-6:] if len(decisions) >= 2 else movements[-6:]
    resumo_final = _extract_final_summary(text, llm.get("resumo_final") or "", latest_events)

    # ── Cessão de crédito: LLM result + regex fallback ──────────────
    cessao_credito = llm.get("cessao_credito") or {}
    if not cessao_credito.get("ocorreu"):
        cessao_credito = _detect_cessao_credito(text, cessao_credito)

    return {
        # ── New structured fields (from PDF spec) ──────────────────
        "identificacao":     identificacao,
        "partes_detalhadas": partes_llm,
        "objeto":            objeto,
        "valores_detalhados": valores_llm,
        "riscos":            llm.get("riscos")        or {},
        "situacao_atual":    llm.get("situacao_atual") or "",
        "resumo_final":      resumo_final,
        "patrimonio":        llm.get("patrimonio")    or [],
        "obrigacoes":        llm.get("obrigacoes")    or [],
        "proximo_passo":     llm.get("proximo_passo") or "",
        "cessao_credito":    cessao_credito,
        # ── Legacy fields (backward compat) ────────────────────────
        "process_number":    process_number,
        "subject":           identificacao.get("classe_processual") or identificacao.get("assunto") or subject,
        "case_description":  case_description,
        "parties":           parties,
        "amounts":           amounts,
        "main_amount":       main_amount,
        "movements":         movements,
        "important_decisions": decisions,
        "latest_events":     latest_events,
        "deadlines":         deadlines,
        "summary":           case_description or subject,
    }
