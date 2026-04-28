"""
app.py — Interface Streamlit do Sistema de Extração Jurídica
Gera cards visuais por PDF analisado, replicando o padrão das telas de análise.
"""

import io
import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Adiciona o diretório raiz ao path para importar o pacote extracao
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from extracao.pipeline import DocumentPipeline
from extracao.classifier import RISK_MAP

# ─────────────────────────────────────────────
# Configuração da página
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Sistema de Extração Jurídica",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CSS customizado — estilo dos cards
# ─────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  .card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 4px;
    flex-wrap: wrap;
    gap: 8px;
  }

  .card-filename {
    font-size: 16px;
    font-weight: 600;
    color: #111827;
    font-family: 'Inter', sans-serif;
  }

  .card-subtitle {
    font-size: 12px;
    color: #6b7280;
    margin-bottom: 16px;
  }

  .badge {
    font-size: 11px;
    font-weight: 500;
    padding: 4px 10px;
    border-radius: 20px;
    white-space: nowrap;
  }

  .badge-maximo    { background: #fee2e2; color: #991b1b; }
  .badge-medio     { background: #fef3c7; color: #92400e; }
  .badge-informativo { background: #d1fae5; color: #065f46; }
  .badge-negativa  { background: #d1fae5; color: #065f46; }
  .badge-desconhecido { background: #f3f4f6; color: #374151; }

  .info-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 16px;
  }

  .info-box {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 12px 16px;
  }

  .info-box-label {
    font-size: 10px;
    font-weight: 600;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 6px;
  }

  .info-box-value {
    font-size: 13px;
    color: #111827;
    line-height: 1.6;
  }

  .status-nada  { color: #059669; font-weight: 600; }
  .status-positiva { color: #d97706; font-weight: 600; }
  .status-nao-constam { color: #059669; font-weight: 600; }

  .processo-list {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 14px;
  }

  .processo-list-label {
    font-size: 10px;
    font-weight: 600;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 10px;
  }

  .processo-item {
    margin-bottom: 10px;
    padding-bottom: 10px;
    border-bottom: 1px solid #e5e7eb;
  }

  .processo-item:last-child {
    margin-bottom: 0;
    padding-bottom: 0;
    border-bottom: none;
  }

  .processo-numero {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    font-weight: 500;
    color: #1d4ed8;
  }

  .processo-detalhe {
    font-size: 12px;
    color: #6b7280;
    margin-top: 2px;
  }

  .alerta-box {
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 12px;
    color: #78350f;
    line-height: 1.6;
    margin-top: 8px;
  }

  .alerta-box code {
    font-family: 'JetBrains Mono', monospace;
    background: #fef3c7;
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 11px;
  }

  .info-box code {
    font-family: 'JetBrains Mono', monospace;
    background: #e5e7eb;
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 11px;
    color: #374151;
  }

  .metrica-row {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
    flex-wrap: wrap;
  }

  .metrica {
    flex: 1;
    min-width: 120px;
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 14px 16px;
    text-align: center;
  }

  .metrica-valor {
    font-size: 28px;
    font-weight: 600;
    color: #111827;
    line-height: 1;
    margin-bottom: 4px;
  }

  .metrica-label {
    font-size: 11px;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .metrica-vermelho .metrica-valor { color: #dc2626; }
  .metrica-amarelo .metrica-valor  { color: #d97706; }
  .metrica-verde .metrica-valor    { color: #059669; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

TIPO_DESCRICAO = {
    "civel_estadual":    "Certidão Estadual de Distribuições Cíveis — TJSP",
    "criminal_estadual": "Certidão Estadual de Distribuições Criminais — TJSP",
    "cnd_federal":       "Certidão Negativa de Débitos Federais — RFB/PGFN",
    "cnd_estadual":      "Certidão Negativa de Débitos Estaduais — SEFAZ-SP",
    "trf3":              "Certidão Judicial — Tribunal Regional Federal",
    "civel_federal":     "Certidão Judicial Cível — CJF (multi-região)",
    "criminal_federal":  "Certidão Judicial Criminal — CJF (multi-região)",
    "cndt":              "Certidão Negativa de Débitos Trabalhistas — TST",
    "ceat":              "Certidão de Ações Trabalhistas",
    "eleitoral":         "Certidão para Fins Eleitorais",
    "desconhecido":      "Tipo não identificado",
}

RISCO_BADGE = {
    "maximo":      ("badge-maximo",     "risco máximo"),
    "medio":       ("badge-medio",      "risco médio"),
    "informativo": ("badge-informativo","informativo"),
}

STATUS_LABEL = {
    "NADA CONSTAR": '<span class="status-nada">NADA CONSTAR</span>',
    "POSITIVA":     '<span class="status-positiva">CONSTAR</span>',
    "NÃO CONSTAM":  '<span class="status-nao-constam">NÃO CONSTAM</span>',
}


def badge_tipo_risco(tipo: str, risco: str) -> str:
    cls, texto = RISCO_BADGE.get(risco, ("badge-desconhecido", risco))
    label = f"{tipo} · {texto}" if tipo != "desconhecido" else "desconhecido"
    return f'<span class="badge {cls}">{label}</span>'


def badge_negativa(tipo: str) -> str:
    return f'<span class="badge badge-negativa">{tipo} · NEGATIVA PURA</span>'


def formatar_status_html(status: str | None, tem_homonimos: bool) -> str:
    if not status:
        return '<span class="status-positiva">não determinado</span>'
    linhas = []
    if status == "NADA CONSTAR":
        linhas.append(f'<span class="status-nada">NADA CONSTAR</span> (CPF qualificado)')
        if tem_homonimos:
            linhas.append(f'<span class="status-positiva">CONSTAR</span> (homônimos não qualificados)')
    elif status in ("POSITIVA", "NÃO CONSTAM"):
        linhas.append(STATUS_LABEL.get(status, status))
    else:
        linhas.append(status)
    return "<br>".join(linhas)


def processos_geo_list(geo_raw: str) -> list[str]:
    """Converte string '["proc1", "proc2"]' em lista."""
    if not geo_raw or geo_raw in ("[]", "", "None"):
        return []
    try:
        val = json.loads(geo_raw.replace("'", '"'))
        return val if isinstance(val, list) else []
    except Exception:
        return []


def agrupar_por_arquivo(records: list) -> dict:
    """Agrupa DocumentRecords por arquivo fonte."""
    grupos: dict = {}
    for r in records:
        fname = Path(r.source_file).name
        grupos.setdefault(fname, []).append(r)
    return grupos


def render_card_pdf(filename: str, records: list) -> None:
    """Renderiza um card completo para um arquivo PDF."""
    if not records:
        return

    # Pega o primeiro record como representante do arquivo
    rep = records[0]
    tipo = rep.document_type or "desconhecido"
    risco = rep.nivel_risco or "informativo"
    status = rep.status
    total_paginas = len(records)

    # Detecta se tem homônimos (processos geométricos presentes com NADA CONSTAR)
    todos_geo: list[str] = []
    for r in records:
        geo = processos_geo_list(str(r.metadata.get("processes_geometric", "[]")))
        todos_geo.extend(geo)

    tem_homonimos = bool(todos_geo) and status == "NADA CONSTAR"
    is_negativa_pura = status == "NADA CONSTAR" and not tem_homonimos

    # Certidão nº (extrai do raw_text se possível)
    certidao_num = ""
    raw = rep.raw_text or ""
    import re
    m = re.search(r"CERTIDÃO\s+N[Oº°][\.:]\s*([\d]+)", raw, re.IGNORECASE)
    if m:
        certidao_num = f" · Certidão nº {m.group(1)}"
    m2 = re.search(r"Nº\s+([\d]+/\d+)", raw)
    if m2 and not certidao_num:
        certidao_num = f" · Nº {m2.group(1)}"

    folhas_txt = f"{total_paginas} {'folha' if total_paginas == 1 else 'folhas'}"
    descricao = TIPO_DESCRICAO.get(tipo, tipo)

    # Badge
    if is_negativa_pura:
        badge_html = badge_negativa(tipo)
    else:
        badge_html = badge_tipo_risco(tipo, risco)

    # ── Monta HTML do card ──
    html = f"""
    <div class="card">
      <div class="card-header">
        <span class="card-filename">{filename}</span>
        {badge_html}
      </div>
      <div class="card-subtitle">{descricao}{certidao_num} · {folhas_txt}</div>

      <div class="info-grid">
        <div class="info-box">
          <div class="info-box-label">{'TITULAR (QUALIFICADO)' if status == 'NADA CONSTAR' else 'TITULAR'}</div>
          <div class="info-box-value">
    """

    nome = rep.name or "—"
    cpf  = rep.cpf  or "—"
    html += f"<strong>{nome}</strong><br>CPF: {cpf}"

    # RG e nascimento do raw_text
    rg_m = re.search(r"RG[:\s]+([0-9.\-X]+)", raw, re.IGNORECASE)
    if rg_m:
        html += f"<br>RG: {rg_m.group(1)}"
    nasc_m = re.search(r"nascido\s+em\s+(\d{2}/\d{2}/\d{4})", raw, re.IGNORECASE)
    local_m = re.search(r"natural\s+de\s+([A-ZÀ-Ü][a-zà-ü\s]+ - [A-Z]{2})", raw)
    if nasc_m and local_m:
        html += f"<br>Nasc: {nasc_m.group(1)} · {local_m.group(1)}"
    elif nasc_m:
        html += f"<br>Nasc: {nasc_m.group(1)}"

    html += f"""
          </div>
        </div>
        <div class="info-box">
          <div class="info-box-label">STATUS {'CERTIDÃO' if tem_homonimos else ''}</div>
          <div class="info-box-value">
            {formatar_status_html(status, tem_homonimos)}
    """

    if is_negativa_pura:
        html += "<br>Sem bloco de homônimos<br>Certidão de 1 folha apenas" if total_paginas == 1 else ""

    # Para TRF: mostrar regiões
    if "trf" in tipo or "civel_federal" in tipo or "criminal_federal" in tipo:
        regioes_m = re.findall(r"TRIBUNAL REGIONAL FEDERAL DA (\d)ª REGIÃO", raw, re.IGNORECASE)
        if regioes_m:
            regioes_txt = " · ".join([f"TRF {r}ª" for r in sorted(set(regioes_m))])
            html += f"<br>{regioes_txt}"
        data_emissao = rep.date or ""
        if data_emissao:
            html += f"<br>Emitido: {data_emissao}"

    html += """
          </div>
        </div>
      </div>
    """

    # ── Processos detectados ──
    if todos_geo:
        # Agrupa processos por foro/vara (simplificado)
        label_geo = "PROCESSOS DETECTADOS VIA MARCADOR «»"
        if tem_homonimos:
            label_geo += " (HOMÔNIMOS — NÃO QUALIFICADOS)"

        html += f"""
      <div class="processo-list">
        <div class="processo-list-label">{label_geo}</div>
        """

        # Mostra até 10 processos
        for proc in todos_geo[:10]:
            # Tenta encontrar contexto do processo no raw_text
            ctx = ""
            idx = raw.find(proc)
            if idx > -1:
                trecho = raw[max(0, idx-80):idx+120]
                # Extrai foro
                foro_m = re.search(r"Foro\s+(?:de\s+)?([A-ZÀ-Ü][a-zA-Zà-ü\s]+)\s*[-–]\s*(\d+ª?\s*Vara[^\.]*)", trecho)
                acao_m = re.search(r"(?:Ação|Crime|Inquérito|Falência)[^\.·\n]{5,60}", trecho, re.IGNORECASE)
                data_m = re.search(r"Data:\s*(\d{2}/\d{2}/\d{4})", trecho)
                reqte_m = re.search(r"Reqte:\s*([^\n·\*]{3,40})", trecho)

                partes = []
                if foro_m:
                    partes.append(f"Foro {foro_m.group(1).strip()} – {foro_m.group(2).strip()}")
                if acao_m:
                    partes.append(acao_m.group(0).strip())
                if data_m:
                    partes.append(f"Data: {data_m.group(1)}")
                if reqte_m:
                    partes.append(f"Reqte: {reqte_m.group(1).strip()}")
                ctx = " · ".join(partes)

            html += f"""
        <div class="processo-item">
          <div class="processo-numero">» {proc}</div>
          {'<div class="processo-detalhe">' + ctx + '</div>' if ctx else ''}
        </div>
            """

        if len(todos_geo) > 10:
            html += f'<div class="processo-detalhe">+ {len(todos_geo)-10} processos adicionais</div>'

        html += "</div>"

    # ── Para TRF: estrutura de páginas ──
    if ("trf" in tipo or "civel_federal" in tipo or "criminal_federal" in tipo) and total_paginas > 1:
        html += """
      <div class="processo-list">
        <div class="processo-list-label">ESTRUTURA: 1 CERTIDÃO = N REGIÕES (PÁGINAS SEPARADAS POR TRIBUNAL)</div>
        """
        # Mapeia regiões encontradas
        regioes_info = {
            "1": "TRF 1ª Região (bases: PJe, SEEU, JEF Virtual, Proc. Digital...)",
            "2": "TRF 2ª Região (Eproc ES, RJ, TRF2)",
            "3": "TRF 3ª Região (SAIP 1º/2º grau, PJe)",
            "5": "TRF 5ª Região (PJE-AL/CE/PB/PE/RN/SE/T5, TEBAS, ESPARTA)",
        }
        for reg, desc in regioes_info.items():
            if f"{reg}ª REGIÃO" in raw.upper():
                html += f'<div class="processo-detalhe">· {desc}</div>'

        cod_m = re.search(r"Código de validação:\s*([A-Z0-9.]+)", raw)
        if cod_m:
            html += f'<div class="processo-detalhe" style="margin-top:6px">Código validação: <code style="font-family:monospace;font-size:11px">{cod_m.group(1)}</code></div>'

        html += "</div>"

    # ── Alertas e observações ──
    alertas = []

    if tipo == "desconhecido":
        alertas.append("Tipo não identificado pelo classificador. Verifique se o PDF está na pasta correta ou se o conteúdo é um documento jurídico reconhecido.")

    if "trf" in tipo or "civel_federal" in tipo:
        alertas.append('Caso especial: "NÃO CONSTAM" (padrão CJF) — diferente do padrão "NADA CONSTAR" dos documentos TJSP. O <code>NADA_CONSTAR_REGEX</code> atual precisa cobrir essa variação.')

    if tem_homonimos:
        alertas.append('Padrão detectado: documento tem dois blocos — primeiro o CPF qualificado com NADA CONSTAR, depois homônimos com CONSTAR. O sistema deve encerrar após o primeiro bloco (lógica de interrupção do <code>pipeline.py</code>) e marcar status = NADA CONSTAR para o CPF-alvo. Os processos do bloco de homônimos devem ser descartados ou marcados como <code>homonimo=True</code>.')

    if tipo in ("civel_estadual",) and "FALÊNCIA" in raw.upper():
        alertas.append('Versão da certidão de falência. O gatilho de classificação é a frase "PEDIDOS DE FALÊNCIA, CONCORDATAS, RECUPERAÇÕES JUDICIAIS" — atualmente o <code>classifier.py</code> não detecta esse subtipo explicitamente, classificaria como <code>civel_estadual</code> genérico.')

    if is_negativa_pura and total_paginas == 1:
        alertas.append("Padrão mais simples: certidão totalmente negativa, sem segundo bloco. O parser encontra NADA CONSTAR logo após o CPF e interrompe na página 1. Nenhum processo a extrair.")

    if tipo == "cnd_estadual" or ("secretaria da fazenda" in raw.lower() and tipo == "desconhecido"):
        alertas.append('CND Estadual SEFAZ-SP: mover para pasta <code>03_CNDT/</code> e adicionar keyword <code>"secretaria da fazenda"</code> ao classifier para detectar esse tipo.')

    for alerta in alertas:
        html += f'<div class="alerta-box">{alerta}</div>'

    html += "</div>"  # fecha card

    st.markdown(html, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Sidebar — configurações
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚖️ Sistema de Extração Jurídica")
    st.markdown("---")

    cpf_alvo = st.text_input(
        "CPF do titular (filtra homônimos)",
        placeholder="000.000.000-00",
        help="Informe o CPF-alvo para ativar a lógica anti-homônimo no pipeline."
    )

    perfil = st.selectbox(
        "Perfil de extração",
        ["generic", "civel_estadual", "criminal_estadual", "cnd_federal", "trf3", "cndt", "ceat"],
        help="Perfil de regex para extração de campos. Use 'generic' para detectar automaticamente."
    )

    ativar_ocr = st.checkbox(
        "Ativar OCR (PDFs escaneados)",
        value=False,
        help="Ativa Tesseract para páginas sem camada de texto. Mais lento."
    )

    extrair_tabelas = st.checkbox("Extrair tabelas estruturadas", value=True)

    st.markdown("---")
    st.markdown("**Sobre**")
    st.caption("Extração automática de certidões jurídicas. Versão 1.0 · Projeto Integrador 05")


# ─────────────────────────────────────────────
# Área principal
# ─────────────────────────────────────────────
st.markdown("# Sistema de Extração Jurídica")
st.markdown("Envie os PDFs das certidões para análise automática de risco e extração de dados.")

uploaded_files = st.file_uploader(
    "Arraste os PDFs aqui ou clique para selecionar",
    type=["pdf"],
    accept_multiple_files=True,
    help="Aceita múltiplos PDFs. Certidões TJSP, TRF, CNDT, CND Estadual/Federal."
)

if not uploaded_files:
    st.info("Aguardando PDFs. Envie os arquivos pelo campo acima para iniciar a análise.")
    st.stop()

# ─────────────────────────────────────────────
# Processamento
# ─────────────────────────────────────────────
if st.button("▶ Processar documentos", type="primary", use_container_width=True):

    # Salva PDFs em temp dir
    import tempfile, shutil
    tmp_dir = Path(tempfile.mkdtemp())

    try:
        for f in uploaded_files:
            dest = tmp_dir / f.name
            dest.write_bytes(f.read())

        pipeline = DocumentPipeline(
            prefer_reader="plumber",
            profile=perfil,
            enable_ocr=ativar_ocr,
            extract_tables=extrair_tabelas,
            cpf_alvo=cpf_alvo.strip() if cpf_alvo else None,
        )

        with st.spinner("Processando documentos..."):
            progress = st.progress(0)
            pdfs = list(tmp_dir.glob("*.pdf"))
            all_records, all_tables = [], []

            for i, pdf_path in enumerate(pdfs):
                progress.progress((i + 1) / len(pdfs), text=f"Processando {pdf_path.name}...")
                recs, tabs = pipeline.process_file(pdf_path)
                all_records.extend(recs)
                all_tables.extend(tabs)

            progress.empty()

        # Guarda resultado na sessão
        st.session_state["records"] = all_records
        st.session_state["tables"] = all_tables
        st.session_state["processed"] = True

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ─────────────────────────────────────────────
# Exibição dos resultados
# ─────────────────────────────────────────────
if st.session_state.get("processed") and st.session_state.get("records"):
    records = st.session_state["records"]
    tables  = st.session_state["tables"]

    # ── Métricas gerais ──
    total   = len(set(r.source_file for r in records))
    maximo  = sum(1 for r in records if r.nivel_risco == "maximo")
    medio   = sum(1 for r in records if r.nivel_risco == "medio")
    info    = sum(1 for r in records if r.nivel_risco == "informativo")
    n_proc  = sum(len(processos_geo_list(str(r.metadata.get("processes_geometric","[]")))) for r in records)

    st.markdown(f"""
    <div class="metrica-row">
      <div class="metrica">
        <div class="metrica-valor">{total}</div>
        <div class="metrica-label">PDFs analisados</div>
      </div>
      <div class="metrica metrica-vermelho">
        <div class="metrica-valor">{maximo}</div>
        <div class="metrica-label">Risco máximo</div>
      </div>
      <div class="metrica metrica-amarelo">
        <div class="metrica-valor">{medio}</div>
        <div class="metrica-label">Risco médio</div>
      </div>
      <div class="metrica metrica-verde">
        <div class="metrica-valor">{info}</div>
        <div class="metrica-label">Informativo</div>
      </div>
      <div class="metrica">
        <div class="metrica-valor">{n_proc}</div>
        <div class="metrica-label">Processos extraídos</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Análise por documento")

    # ── Cards por arquivo ──
    grupos = agrupar_por_arquivo(records)
    for filename, recs in grupos.items():
        render_card_pdf(filename, recs)

    # ── Download Excel ──
    st.markdown("---")
    st.markdown("### Download")

    exporter = pipeline.exporter
    df_pages  = exporter.to_dataframe(records)
    df_tables = exporter.tables_to_dataframe(tables)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_pages.to_excel(writer, sheet_name="pages", index=False)
        df_tables.to_excel(writer, sheet_name="tables", index=False)
    output.seek(0)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="⬇ Baixar analise_consolidada.xlsx",
            data=output,
            file_name="analise_consolidada.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with col2:
        csv_data = df_pages.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            label="⬇ Baixar como CSV",
            data=csv_data,
            file_name="analise_consolidada.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # ── Tabela expandível ──
    with st.expander("Ver tabela completa de registros"):
        colunas = ["source_file", "document_type", "nivel_risco", "status", "cpf", "name", "process_number", "date"]
        colunas_existentes = [c for c in colunas if c in df_pages.columns]
        st.dataframe(df_pages[colunas_existentes], use_container_width=True)