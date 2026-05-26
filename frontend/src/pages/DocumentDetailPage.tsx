import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { AlertTriangle, Check, ChevronDown, ChevronUp, Copy, Download, FileText, Pencil, RefreshCw, Trash2 } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { deleteDocument, downloadExport, fetchDocument, reprocessDocument, type LegalDocument } from "@/lib/api";
import { STATUS_LABELS } from "@/constants/documentStatus";

type DisplayField = { label: string; value: unknown };
type DisplayEntity = { category: string; label: string; text: string };
type ProcessDetail = { number: string; is_homonimo: boolean; action_type: string };
type ProcessItem = ProcessDetail | string;

export function DocumentDetailPage() {
  const { id = "", folderId = "" } = useParams();
  const navigate = useNavigate();

  const [fieldEdits, setFieldEdits] = useState<Record<string, string>>({});
  const [reviewedFields, setReviewedFields] = useState<Set<string>>(new Set());
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState("");

  const query = useQuery({
    queryKey: ["document", id],
    queryFn: () => fetchDocument(id),
    enabled: Boolean(id),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "processing" || status === "pending" ? 3000 : false;
    },
  });

  if (query.isLoading) return (
    <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
      <RefreshCw className="h-12 w-12 animate-spin text-primary opacity-20" />
      <p className="text-muted-foreground animate-pulse font-medium">Carregando detalhes do documento...</p>
    </div>
  );

  if (!query.data || query.isError) return (
    <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
      <AlertTriangle className="h-12 w-12 text-destructive" />
      <p className="text-destructive font-bold">Documento nao encontrado ou erro ao carregar.</p>
      <Button asChild variant="outline"><Link to={`/folders/${folderId}/certidao`}>Voltar para o Dashboard</Link></Button>
    </div>
  );

  const document = query.data;
  const displayEntities = normalizeEntities(document);
  const displayFields = buildDisplayFields(document, displayEntities);
  const previewUrl = getAbsoluteBackendUrl(
    document.preview_url || document.pdf_url || document.file_url || `/api/documents/${document.id}/file`,
  );

  async function handleDelete() {
    const confirmed = window.confirm(`Excluir "${document.title}" e apagar o PDF salvo?`);
    if (!confirmed) return;
    await deleteDocument(document.id);
    navigate(`/folders/${folderId}/certidao`);
  }

  async function handleReprocess() {
    await reprocessDocument(document.id);
    query.refetch();
  }

  function copyToClipboard(val: string) {
    navigator.clipboard.writeText(val).catch((error) => console.warn("Copy failed", error));
  }

  function startEdit(label: string, currentValue: unknown) {
    setEditDraft(String(fieldEdits[label] ?? currentValue ?? ""));
    setEditingField(label);
  }

  function saveEdit(label: string) {
    setFieldEdits((prev) => ({ ...prev, [label]: editDraft }));
    setEditingField(null);
  }

  function toggleReviewed(label: string) {
    setReviewedFields((prev) => {
      const next = new Set(prev);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500 pb-10">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <Button asChild variant="ghost" size="sm">
            <Link to={`/folders/${folderId}/certidao`}>Voltar</Link>
          </Button>
          <h1 className="mt-2 truncate text-2xl font-bold text-foreground">{document.title}</h1>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-sm text-muted-foreground">{document.document_type || "Aguardando classificacao"}</span>
            {document.status === "processing" && (
              <span className="flex items-center gap-1 text-xs font-bold text-blue-600 animate-pulse bg-blue-50 px-2 py-0.5 rounded-full uppercase tracking-wider">
                <RefreshCw className="h-3 w-3 animate-spin" />
                Processando...
              </span>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => downloadExport(document.id, "excel")} disabled={document.status !== "done"}>
            <Download className="h-4 w-4" />
            Excel
          </Button>
          <Button variant="outline" size="sm" onClick={() => downloadExport(document.id, "word")} disabled={document.status !== "done"}>
            <FileText className="h-4 w-4" />
            Word
          </Button>
          {(document.status === "failed" || document.status === "needs_ocr") && (
            <Button variant="outline" size="sm" onClick={handleReprocess}>
              <RefreshCw className="h-4 w-4" />
              Reprocessar
            </Button>
          )}
          <Button variant="destructive" size="sm" onClick={handleDelete}>
            <Trash2 className="h-4 w-4" />
            Excluir
          </Button>
        </div>
      </div>

      {/* Status bar */}
      <div className="flex flex-wrap items-center gap-4 px-4 py-3 rounded-lg border bg-muted/20 text-xs">
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground font-medium">Status</span>
          <span className={`px-2 py-0.5 rounded-full font-bold tracking-wider uppercase ${
            document.status === "done"      ? "bg-green-100 text-green-700" :
            document.status === "failed"    ? "bg-red-100 text-red-700" :
            document.status === "needs_ocr" ? "bg-amber-100 text-amber-700" :
                                              "bg-blue-100 text-blue-700 animate-pulse"
          }`}>
            {STATUS_LABELS[document.status] || document.status}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground font-medium">Criado em</span>
          <span className="font-semibold text-foreground">{new Date(document.created_at).toLocaleString()}</span>
        </div>
        {document.status === "needs_ocr" && (
          <div className="flex items-center gap-1 text-amber-700">
            <AlertTriangle className="h-3.5 w-3.5" />
            <span className="font-medium">OCR necessario para analise completa</span>
          </div>
        )}
        {document.status === "failed" && document.error_message && (
          <div className="flex items-center gap-1 text-destructive">
            <AlertTriangle className="h-3.5 w-3.5" />
            <span className="font-medium">{document.error_message}</span>
          </div>
        )}
      </div>

      {/* PDF Preview */}
      <Card>
        <CardHeader className="pb-3 border-b bg-muted/5">
          <CardTitle className="text-base flex items-center gap-2">
            <FileText className="h-4 w-4 text-primary" />
            Pre-visualizacao do Documento
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="h-[700px] w-full overflow-hidden rounded-md border bg-muted/10 shadow-inner">
            {previewUrl ? (
              <iframe src={previewUrl} title={`Preview de ${document.title}`} className="h-full w-full bg-white" />
            ) : (
              <div className="flex h-full items-center justify-center text-muted-foreground italic">
                Visualizacao indisponivel.
              </div>
            )}
          </div>
          {previewUrl && (
            <p className="mt-3 text-xs text-muted-foreground text-center">
              O PDF nao abriu?{" "}
              <a className="font-bold text-primary hover:underline underline-offset-2" href={previewUrl} target="_blank" rel="noreferrer">
                Clique aqui para abrir em tela cheia
              </a>
            </p>
          )}
        </CardContent>
      </Card>

      {/* Extracted Data */}
      <Card>
        <CardHeader className="pb-3 border-b bg-muted/5">
          <CardTitle className="text-base flex items-center gap-2">
            <RefreshCw className="h-4 w-4 text-primary" />
            Dados Extraidos via IA
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-6">
          {document.status === "processing" ? (
            <div className="py-10 text-center space-y-3">
              <RefreshCw className="h-8 w-8 animate-spin mx-auto text-primary opacity-30" />
              <p className="text-sm text-muted-foreground font-medium italic">A IA esta extraindo os dados do documento...</p>
            </div>
          ) : displayFields.length === 0 ? (
            <div className="rounded-lg border border-dashed p-10 text-center">
              <p className="text-muted-foreground font-medium">Nenhum campo estruturado foi identificado.</p>
              <p className="text-xs text-muted-foreground mt-1">Isso pode ocorrer se o PDF for uma imagem de baixa qualidade ou se os campos nao seguirem padroes conhecidos.</p>
            </div>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {displayFields.map((field) => {
                if (field.label === "process_numbers" && Array.isArray(field.value)) {
                  return (
                    <div key="process_numbers" className="col-span-full">
                      <ProcessNumbersCard items={field.value as ProcessItem[]} method={document.extraction_method} />
                    </div>
                  );
                }

                const isReviewed = reviewedFields.has(field.label);
                const isEditing = editingField === field.label;
                const displayValue = fieldEdits[field.label] ?? formatFieldValue(field.value);

                return (
                  <div
                    key={field.label}
                    className={`group relative flex flex-col gap-2 rounded-lg border bg-card p-4 shadow-sm transition-all ${
                      isReviewed ? "border-green-300 bg-green-50/40" : "hover:border-primary/30"
                    }`}
                  >
                    {/* Label row + action buttons */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex flex-col gap-0.5">
                        <dt className="text-[10px] font-black uppercase text-primary/60 tracking-widest leading-tight">
                          {formatFieldLabel(field.label)}
                        </dt>
                        {document.extraction_method && (
                          <span className="w-fit text-[9px] font-semibold tracking-wide text-muted-foreground/60 bg-muted/50 px-1.5 py-0.5 rounded">
                            {formatExtractionMethod(document.extraction_method)}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-1 shrink-0 flex-wrap justify-end">
                        {/* Reviewed toggle */}
                        {isReviewed ? (
                          <button
                            title="Clique para desmarcar"
                            onClick={() => toggleReviewed(field.label)}
                            className="flex items-center gap-1 text-[10px] font-bold text-green-700 bg-green-100 px-2 py-0.5 rounded-full border border-green-200 hover:bg-green-200 transition-colors"
                          >
                            <Check className="h-3 w-3" />
                            Revisado
                          </button>
                        ) : (
                          <button
                            title="Marcar como revisado"
                            onClick={() => toggleReviewed(field.label)}
                            className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 rounded bg-muted px-2 py-0.5 text-[10px] font-bold text-muted-foreground hover:bg-green-100 hover:text-green-700"
                          >
                            <Check className="h-3 w-3" />
                            Revisar
                          </button>
                        )}
                        {/* Edit button */}
                        {!isEditing && (
                          <button
                            title="Editar campo"
                            onClick={() => startEdit(field.label, field.value)}
                            className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 rounded bg-primary/10 px-2 py-0.5 text-[10px] font-bold text-primary hover:bg-primary/20"
                          >
                            <Pencil className="h-3 w-3" />
                            Editar
                          </button>
                        )}
                        {/* Copy button */}
                        {!isEditing && (
                          <button
                            title="Copiar valor"
                            onClick={() => copyToClipboard(displayValue)}
                            className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 rounded bg-primary/10 px-2 py-0.5 text-[10px] font-bold text-primary hover:bg-primary/20"
                          >
                            <Copy className="h-3 w-3" />
                            Copiar
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Value / Edit area */}
                    {isEditing ? (
                      <div className="space-y-2">
                        <textarea
                          className="w-full text-sm border rounded p-2 resize-none focus:outline-none focus:ring-2 focus:ring-primary/30 font-medium bg-background"
                          value={editDraft}
                          onChange={(e) => setEditDraft(e.target.value)}
                          rows={3}
                          autoFocus
                        />
                        <div className="flex gap-2">
                          <button
                            onClick={() => saveEdit(field.label)}
                            className="flex items-center gap-1 text-[11px] font-bold text-green-700 bg-green-50 border border-green-200 px-2 py-1 rounded hover:bg-green-100 transition-colors"
                          >
                            <Check className="h-3 w-3" />
                            Salvar
                          </button>
                          <button
                            onClick={() => setEditingField(null)}
                            className="text-[11px] text-muted-foreground hover:underline px-2 py-1"
                          >
                            Cancelar
                          </button>
                        </div>
                      </div>
                    ) : (
                      <dd className="break-words font-semibold text-sm text-foreground leading-snug">
                        {displayValue}
                      </dd>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ─── helpers ─────────────────────────────────────────────────────────────────

function getAbsoluteBackendUrl(url: string) {
  const apiBase = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";
  const apiOrigin = new URL(apiBase).origin;
  if (/^https?:\/\//i.test(url)) return url;
  return `${apiOrigin}${url.startsWith("/") ? url : `/${url}`}`;
}

function buildDisplayFields(doc: LegalDocument, entities: DisplayEntity[]): DisplayField[] {
  const rawData = doc.extracted_data || {};
  const parsedFields = Array.isArray((rawData as any).fields) ? (rawData as any).fields : [];
  const fieldMap = new Map<string, unknown>();

  const processesDetail: ProcessDetail[] = Array.isArray((rawData as any).processes_detail)
    ? (rawData as any).processes_detail
    : [];
  const legacyNumbers: string[] = Array.isArray((rawData as any).process_numbers)
    ? (rawData as any).process_numbers
    : [];
  const processItems: ProcessItem[] = processesDetail.length > 0 ? processesDetail : legacyNumbers;

  for (const field of parsedFields) {
    const label = String(field.field_name ?? field.fieldName ?? field.name ?? "").trim();
    if (label) fieldMap.set(label, field.field_value ?? field.value ?? "");
  }

  if (processItems.length > 0) fieldMap.delete("processo");

  const person = fieldMap.get("nome") || entities.find((e) => e.category === "Pessoas")?.text;
  const extractionMethod = doc.extraction_method || (rawData as any).extraction_method || (rawData as any).metodo_extracao;

  const essentials: DisplayField[] = [
    { label: "nome",           value: person },
    { label: "cpf",            value: fieldMap.get("cpf") },
    { label: "cnpj",           value: fieldMap.get("cnpj") },
    { label: "data",           value: fieldMap.get("data") },
    { label: "tipo_documental",value: doc.document_type },
    { label: "tipo_pdf",       value: formatPdfType(extractionMethod) },
    { label: "metodo_extracao",value: formatExtractionMethod(extractionMethod) },
  ];

  const processField: DisplayField | null =
    processItems.length > 0 ? { label: "process_numbers", value: processItems } : null;

  const used = new Set(essentials.map((f) => f.label));
  const additional = Array.from(fieldMap.entries())
    .filter(([label]) => !used.has(label))
    .map(([label, value]) => ({ label, value }));

  const rest = [...essentials, ...additional].filter(
    (f) => f.value !== null && f.value !== undefined && f.value !== "",
  );

  const skippedEntityCategories = new Set<string>(["Processos"]);
  if (person) skippedEntityCategories.add("Pessoas");
  if (fieldMap.get("cpf") || fieldMap.get("cnpj")) skippedEntityCategories.add("CPF/CNPJ");

  const entityCategoryOrder = [
    "Pessoas",
    "CPF/CNPJ",
    "Órgãos/Tribunais",
    "Situação/Resultado",
    "Outros",
  ];

  // Entity groups rendered as plain string fields — same card style as other fields
  const entityGroupFields: DisplayField[] = entityCategoryOrder
    .filter((cat) => !skippedEntityCategories.has(cat))
    .map((cat) => ({
      label: cat,
      value: entities
        .filter((e) => e.category === cat)
        .map((e) => e.text)
        .join("  ·  "),
    }))
    .filter((f) => String(f.value).length > 0);

  return processField
    ? [processField, ...rest, ...entityGroupFields]
    : [...rest, ...entityGroupFields];
}

function normalizeEntities(doc: LegalDocument): DisplayEntity[] {
  const sourceEntities = (
    ((doc.extracted_data as any)?.organized_entities || doc.entities || []) as LegalDocument["entities"]
  );
  const seen = new Set<string>();
  return sourceEntities
    .map((entity) => {
      const category = entity.category || mapLegacyEntityCategory(entity.label || entity.type || entity.entity || "");
      const text = cleanDisplayEntityText(entity.text || entity.value || "");
      return { category, label: category, text };
    })
    .filter((e) => e.category && e.text && isDisplayableEntity(e))
    .filter((e) => {
      const key = `${e.category}:${e.text.toLocaleLowerCase("pt-BR")}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
}

function mapLegacyEntityCategory(label: string) {
  const n = label.toUpperCase();
  if (n === "PESSOA") return "Pessoas";
  if (n === "LOCAL") return "Locais";
  if (n === "TEMPO" || n === "DATA") return "Datas";
  if (n === "CPF" || n === "CNPJ" || n === "CPF_CNPJ") return "CPF/CNPJ";
  if (n === "PROCESSO") return "Processos";
  return label || "Outros";
}

function cleanDisplayEntityText(value: string) {
  return value.replace(/^(PESSOA|LOCAL|TEMPO|DATA|CPF|CNPJ|PROCESSO)\s*[:\-]?\s*/i, "").replace(/\s+/g, " ").trim();
}

function isDisplayableEntity(entity: DisplayEntity) {
  const normalized = entity.text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
  const blocked = ["da fe", "dar fe", "pe dos feitos", "podera ser completada", "certidao estadual de distribuicoes", "poder judiciario", "justica federal", "tribunal regional"];
  if (blocked.some((term) => normalized.includes(term))) return false;
  if (entity.category === "Pessoas") return entity.text.split(/\s+/).length >= 2 && entity.text.split(/\s+/).length <= 6;
  return true;
}

function formatFieldLabel(key: string) {
  const labels: Record<string, string> = {
    nome:                  "Nome Completo",
    cpf:                   "Número do CPF",
    cnpj:                  "Número do CNPJ",
    processo:              "Número do Processo",
    process_numbers:       "Processos Encontrados",
    numero_processo:       "Processo Judicial",
    data:                  "Data da Certidao",
    valor:                 "Valor Envolvido",
    tipo_documental:       "Classificacao IA",
    tipo_pdf:              "Tipo de Documento",
    metodo_extracao:       "Metodo de Leitura",
    tipo_acao:             "Tipo de Acao",
    situacao_processual:   "Situacao Processual",
    vara:                  "Vara Judiciaria",
    foro:                  "Foro / Comarca",
    risco:                 "Pontuacao de Risco",
    nivel_risco:           "Nivel de Risco",
    revisao_manual:        "Exige Revisao",
    validacao:             "Status de Validacao",
    // entity group categories — already human-readable, pass through
    Locais:                    "Locais",
    "Órgãos/Tribunais":        "Órgãos / Tribunais",
    Datas:                     "Datas",
    "Classes processuais":     "Classes Processuais",
    "Situação/Resultado":      "Situação / Resultado",
    "Termos jurídicos relevantes": "Termos Jurídicos",
    Outros:                    "Outros",
  };
  return labels[key] ?? key.replace(/_/g, " ");
}

function formatPdfType(method: unknown): string {
  const textMethods = ["pdfplumber", "fitz", "pdfplumber_quick", "fitz_quick"];
  const ocrMethods  = ["ocr", "windows_ocr"];
  const m = String(method || "");
  if (textMethods.includes(m)) return "Texto Nato / Digital";
  if (ocrMethods.includes(m))  return "Imagem Digitalizada / OCR";
  return "";
}

function formatExtractionMethod(method: unknown): string {
  const labels: Record<string, string> = {
    pdfplumber:               "pdfplumber - texto nato do PDF",
    pdfplumber_quick:         "pdfplumber quick - texto nato do PDF",
    fitz:                     "PyMuPDF/fitz - texto nato do PDF",
    fitz_quick:               "PyMuPDF/fitz quick - texto nato do PDF",
    ocr:                      "Tesseract OCR - imagem digitalizada",
    windows_ocr:              "Windows OCR - imagem digitalizada",
    hybrid:                   "Hibrido",
    preview_metadata_fallback:"Metadados do Upload",
    quick_empty:              "Leitura rapida sem texto",
    failed:                   "Falha na leitura",
    error:                    "Erro",
  };
  if (!method) return "";
  return labels[String(method)] ?? String(method);
}

function formatFieldValue(value: unknown) {
  if (value === null || value === undefined || value === "" || value === false) return "-";
  if (typeof value === "boolean") return value ? "Sim" : "Nao";
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
}

// ─── ProcessNumbersCard ───────────────────────────────────────────────────────

function ProcessNumbersCard({ items, method }: { items: ProcessItem[]; method?: string }) {
  const [expanded, setExpanded] = useState(false);
  const COLLAPSE_THRESHOLD = 4;

  const normalized: ProcessDetail[] = items.map((item) =>
    typeof item === "string" ? { number: item, is_homonimo: false, action_type: "" } : item,
  );

  const mainProcesses = normalized.filter((p) => !p.is_homonimo);
  const homonimos     = normalized.filter((p) => p.is_homonimo);
  const hasHomonimos  = homonimos.length > 0;

  const mainToShow = expanded ? mainProcesses : mainProcesses.slice(0, COLLAPSE_THRESHOLD);
  const showToggle = mainProcesses.length > COLLAPSE_THRESHOLD;

  const title = normalized.length === 1 && !hasHomonimos ? "NÚMERO DO PROCESSO" : "PROCESSOS ENCONTRADOS";

  return (
    <div className="rounded-lg border bg-card p-4 shadow-sm hover:border-primary/30 transition-all space-y-3">
      <div className="flex flex-col gap-0.5">
        <dt className="text-[10px] font-black uppercase text-primary/60 tracking-widest">{title}</dt>
        {method && (
          <span className="w-fit text-[9px] font-semibold tracking-wide text-muted-foreground/60 bg-muted/50 px-1.5 py-0.5 rounded">
            {formatExtractionMethod(method)}
          </span>
        )}
      </div>

      {normalized.length > 1 && (
        <p className="text-[11px] text-muted-foreground font-medium">
          {mainProcesses.length > 0 && `${mainProcesses.length} processo(s) principal(is)`}
          {hasHomonimos && mainProcesses.length > 0 && " · "}
          {hasHomonimos && `${homonimos.length} homônimo(s)`}
        </p>
      )}

      {mainProcesses.length > 0 && (
        <div className="space-y-2">
          {hasHomonimos && (
            <p className="text-[10px] font-black uppercase text-primary/60 tracking-widest">Processos Principais</p>
          )}
          <div className="space-y-2">
            {mainToShow.map((p) => <ProcessRow key={p.number} process={p} />)}
          </div>
          {showToggle && (
            <button
              className="flex items-center gap-1 text-[11px] font-bold text-primary hover:underline"
              onClick={() => setExpanded((prev) => !prev)}
            >
              {expanded ? (
                <><ChevronUp className="h-3 w-3" />Ver menos</>
              ) : (
                <><ChevronDown className="h-3 w-3" />Ver mais {mainProcesses.length - COLLAPSE_THRESHOLD} processo(s)</>
              )}
            </button>
          )}
        </div>
      )}

      {hasHomonimos && (
        <div className="border-t pt-3 space-y-2">
          <div className="flex items-center gap-2">
            <p className="text-[10px] font-black uppercase text-amber-600 tracking-widest">Processos Homônimos</p>
            <span className="rounded bg-amber-100 text-amber-700 text-[10px] font-black px-1.5 py-0.5 border border-amber-200">
              {homonimos.length}
            </span>
          </div>
          <p className="text-[11px] text-amber-700/80 italic">
            Exigem declaração de ciência assinada pelo requerente.
          </p>
          <div className="space-y-2">
            {homonimos.map((p) => <ProcessRow key={p.number} process={p} isHomonimoStyle />)}
          </div>
        </div>
      )}
    </div>
  );
}


function ProcessRow({ process, isHomonimoStyle = false }: { process: ProcessDetail; isHomonimoStyle?: boolean }) {
  return (
    <div className="space-y-0.5">
      <code
        className={`font-mono font-semibold text-sm px-2 py-0.5 rounded border select-all inline-block ${
          isHomonimoStyle
            ? "text-amber-800 bg-amber-50 border-amber-200"
            : "text-foreground bg-muted/50 border-muted"
        }`}
      >
        {process.number}
      </code>
      {process.action_type && (
        <p className="text-[11px] text-muted-foreground ml-1 italic">{process.action_type}</p>
      )}
    </div>
  );
}
