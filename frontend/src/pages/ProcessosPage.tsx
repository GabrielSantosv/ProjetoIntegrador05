import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ChevronRight, ExternalLink, FileText, RefreshCw, Scale, Trash2, Upload } from "lucide-react";
import type { ReactNode } from "react";
import { Link, useParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  deleteProcessDocument,
  fetchDocuments,
  fetchFolder,
  fetchProcessDocuments,
  getProcessPdfUrl,
  uploadProcessDocument,
  type LegalDocument,
  type ProcessDocument,
  type ProcessTimelineEvent,
  type ProcessObjeto,
  type ProcessValores,
  type ProcessPartesDetalhadas,
} from "@/lib/api";

type ProcessDetail = { number: string; is_homonimo: boolean; action_type: string };
type ProcessItem = ProcessDetail & { sourceDoc: LegalDocument };

export function ProcessosPage() {
  const { folderId = "" } = useParams();
  const queryClient = useQueryClient();
  const { data: folder } = useQuery({
    queryKey: ["folder", folderId],
    queryFn: () => fetchFolder(folderId),
    enabled: Boolean(folderId),
    retry: false,
  });
  const { data: documents = [], isLoading } = useQuery({
    queryKey: ["documents", folderId],
    queryFn: () => fetchDocuments(folderId),
  });
  const { data: processDocs = [] } = useQuery({
    queryKey: ["process-documents", folderId],
    queryFn: () => fetchProcessDocuments(folderId),
    refetchInterval: (q) =>
      (q.state.data ?? []).some((doc) => doc.status === "processing") ? 3000 : false,
  });

  const uploadMutation = useMutation({
    mutationFn: uploadProcessDocument,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["process-documents", folderId] }),
  });
  const deleteMutation = useMutation({
    mutationFn: deleteProcessDocument,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["process-documents", folderId] }),
  });

  const processes = documents
    .filter((doc) => doc.status === "done")
    .flatMap((doc) => extractProcessesFromDoc(doc).map((process) => ({ ...process, sourceDoc: doc })));

  const uniqueProcesses = dedupeProcesses(processes);
  const analysesByProcess = groupAnalysesByProcess(processDocs);
  const totalMain = uniqueProcesses.filter((p) => !p.is_homonimo).length;
  const totalHomonimos = uniqueProcesses.filter((p) => p.is_homonimo).length;
  const totalAnalyses = processDocs.length;

  async function handleUpload(process: ProcessItem, file: File | undefined) {
    if (!file) return;
    await uploadMutation.mutateAsync({
      folderId,
      processNumber: process.number,
      sourceDocumentId: process.sourceDoc.id,
      file,
    });
  }

  async function handleDeleteAnalysis(analysis: ProcessDocument) {
    const confirmed = window.confirm(`Excluir a analise do PDF "${analysis.original_filename}"?`);
    if (!confirmed) return;
    await deleteMutation.mutateAsync(analysis.id);
  }

  return (
    <div className="max-w-5xl mx-auto py-4 space-y-6">
      <div>
        <Button asChild variant="ghost" size="sm" className="-ml-2 mb-2">
          <Link to={`/folders/${folderId}`}>
            <ArrowLeft className="h-4 w-4" />
            {folder?.name ?? "Pasta"}
          </Link>
        </Button>
        <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
          <Link to="/" className="hover:text-foreground transition-colors">Pastas</Link>
          <ChevronRight className="h-3.5 w-3.5" />
          <Link to={`/folders/${folderId}`} className="hover:text-foreground transition-colors">
            {folder?.name ?? "Pasta"}
          </Link>
          <ChevronRight className="h-3.5 w-3.5" />
          <span className="text-foreground font-semibold">Análise de Processos</span>
        </div>
        <h1 className="text-2xl font-bold text-foreground">Análise de Processos</h1>
      </div>

      {uniqueProcesses.length > 0 && (
        <div className="grid gap-3 md:grid-cols-4">
          <Metric label="Processos principais" value={totalMain} />
          <Metric label="Homônimos" value={totalHomonimos} tone="amber" />
          <Metric label="PDFs analisados" value={totalAnalyses} />
          <Metric label="Em processamento" value={processDocs.filter((doc) => doc.status === "processing").length} tone="blue" />
        </div>
      )}

      {isLoading ? (
        <p className="text-muted-foreground text-sm">Carregando certidões...</p>
      ) : uniqueProcesses.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-center space-y-4 border-2 border-dashed rounded-xl text-muted-foreground">
          <Scale className="h-14 w-14 opacity-20" />
          <div>
            <p className="font-semibold text-base">Nenhum processo encontrado</p>
            <p className="text-sm mt-1">
              Processe certidões na{" "}
              <Link to={`/folders/${folderId}/certidao`} className="text-primary hover:underline font-medium">
                Análise de Certidão
              </Link>{" "}
              para que os processos extraídos apareçam aqui.
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {uniqueProcesses.map((process) => (
            <ProcessCard
              key={process.number}
              folderId={folderId}
              process={process}
              analyses={analysesByProcess.get(process.number) ?? []}
              uploading={uploadMutation.isPending}
              deleting={deleteMutation.isPending}
              onUpload={handleUpload}
              onDeleteAnalysis={handleDeleteAnalysis}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function extractProcessesFromDoc(doc: LegalDocument): ProcessDetail[] {
  const raw = (doc.extracted_data || {}) as Record<string, unknown>;
  if (Array.isArray(raw.processes_detail) && (raw.processes_detail as unknown[]).length > 0) {
    return raw.processes_detail as ProcessDetail[];
  }
  if (Array.isArray(raw.process_numbers) && (raw.process_numbers as unknown[]).length > 0) {
    return (raw.process_numbers as string[]).map((number) => ({ number, is_homonimo: false, action_type: "" }));
  }
  const fromEntities = doc.entities
    .filter((e) => e.category === "Processos" || e.label === "PROCESSO" || e.type === "PROCESSO")
    .map((e) => e.text || e.value || "")
    .filter(Boolean);
  return fromEntities.map((number) => ({ number, is_homonimo: false, action_type: "" }));
}

function dedupeProcesses(processes: ProcessItem[]): ProcessItem[] {
  const seen = new Map<string, ProcessItem>();
  for (const process of processes) {
    const current = seen.get(process.number);
    if (!current || (current.is_homonimo && !process.is_homonimo)) {
      seen.set(process.number, process);
    }
  }
  return Array.from(seen.values());
}

function groupAnalysesByProcess(analyses: ProcessDocument[]) {
  const map = new Map<string, ProcessDocument[]>();
  for (const analysis of analyses) {
    const list = map.get(analysis.process_number) ?? [];
    list.push(analysis);
    map.set(analysis.process_number, list);
  }
  return map;
}

function ProcessCard({
  process,
  folderId,
  analyses,
  uploading,
  deleting,
  onUpload,
  onDeleteAnalysis,
}: {
  process: ProcessItem;
  folderId: string;
  analyses: ProcessDocument[];
  uploading: boolean;
  deleting: boolean;
  onUpload: (process: ProcessItem, file: File | undefined) => Promise<void>;
  onDeleteAnalysis: (analysis: ProcessDocument) => Promise<void>;
}) {
  const latest = analyses[0];
  const data = latest?.analysis_data ?? {};
  const latestEvents = data.latest_events ?? [];
  const decisions = data.important_decisions ?? [];
  const inputId = `process-pdf-${process.number.replace(/[^a-zA-Z0-9]/g, "-")}`;

  return (
    <Card>
      <CardHeader className="pb-3 border-b bg-muted/5">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div className="min-w-0">
            <p className="text-[11px] font-semibold text-primary/70 uppercase tracking-wide">
              {process.sourceDoc.document_type || "Certidão"}
              {process.action_type ? ` · ${process.action_type}` : ""}
            </p>
            <CardTitle className="font-mono text-base mt-0.5">{process.number}</CardTitle>
            {process.is_homonimo && (
              <span className="mt-2 inline-block rounded bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-700">
                Homônimo
              </span>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <input
              id={inputId}
              type="file"
              accept="application/pdf"
              className="hidden"
              onChange={(event) => onUpload(process, event.target.files?.[0]).finally(() => {
                event.currentTarget.value = "";
              })}
            />
            <Button asChild variant="outline" size="sm" disabled={uploading}>
              <label htmlFor={inputId} className="cursor-pointer">
                <Upload className="h-4 w-4" />
                Enviar PDF
              </label>
            </Button>
            <Button asChild variant="ghost" size="sm">
              <Link to={`/folders/${folderId}/certidao/${process.sourceDoc.id}`}>
                <ExternalLink className="h-4 w-4" />
                Ver certidão
              </Link>
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-4">
        {!latest ? (
          <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
            Nenhum PDF processual enviado para este processo ainda.
          </div>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-3 text-xs">
              <StatusBadge status={latest.status} />
              <span className="text-muted-foreground">Arquivo: <b className="text-foreground">{latest.original_filename}</b></span>
              <Button asChild variant="ghost" size="sm" className="h-7 px-2">
                <a href={getProcessPdfUrl(latest.id)} target="_blank" rel="noreferrer">
                  <FileText className="h-3.5 w-3.5" />
                  Abrir PDF
                </a>
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2 text-destructive hover:text-destructive"
                disabled={deleting}
                onClick={() => onDeleteAnalysis(latest)}
              >
                <Trash2 className="h-3.5 w-3.5" />
                Excluir análise
              </Button>
            </div>

            {latest.status === "processing" ? (
              <div className="flex items-center gap-2 text-sm text-blue-700">
                <RefreshCw className="h-4 w-4 animate-spin" />
                Analisando PDF processual...
              </div>
            ) : latest.status === "failed" || latest.status === "needs_ocr" ? (
              <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {latest.error_message || "Nao foi possivel analisar o PDF."}
              </div>
            ) : (
              <AnalysisView data={data} decisions={decisions} latestEvents={latestEvents} />
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function Metric({ label, value, tone = "default" }: { label: string; value: number; tone?: "default" | "amber" | "blue" }) {
  const color = tone === "amber" ? "text-amber-700" : tone === "blue" ? "text-blue-700" : "text-foreground";
  return (
    <div className="rounded-lg border bg-card p-4">
      <p className="text-xs text-muted-foreground font-medium">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

function StatusBadge({ status }: { status: ProcessDocument["status"] }) {
  const classes = {
    done: "bg-green-100 text-green-700",
    processing: "bg-blue-100 text-blue-700",
    failed: "bg-red-100 text-red-700",
    needs_ocr: "bg-amber-100 text-amber-700",
  }[status];
  const label = {
    done: "Analisado",
    processing: "Processando",
    failed: "Falhou",
    needs_ocr: "Requer OCR",
  }[status];
  return <span className={`rounded-full px-2 py-1 text-[11px] font-bold ${classes}`}>{label}</span>;
}

// ─── Full analysis view ───────────────────────────────────────────────────────

function AnalysisView({
  data,
  decisions,
  latestEvents,
}: {
  data: ReturnType<typeof Object.assign> & import("@/lib/api").ProcessAnalysisData;
  decisions: ProcessTimelineEvent[];
  latestEvents: ProcessTimelineEvent[];
}) {
  const objeto  = data.objeto         as ProcessObjeto         | undefined;
  const partes  = data.partes_detalhadas as ProcessPartesDetalhadas | undefined;
  const valores = data.valores_detalhados as ProcessValores    | undefined;

  return (
    <div className="space-y-4">

      {/* Objeto da ação + Partes */}
      <div className="grid gap-4 lg:grid-cols-2">
        <InfoPanel title="Objeto da Ação">
          {objeto?.resumo ? (
            <p className="text-sm leading-relaxed text-foreground mb-3">{objeto.resumo}</p>
          ) : (
            <p className="text-sm text-muted-foreground italic mb-3">
              {data.case_description || data.subject || "Descrição não disponível."}
            </p>
          )}
          {objeto?.causa_de_pedir && (
            <div className="mt-2">
              <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-0.5">Causa de Pedir</p>
              <p className="text-xs text-foreground">{objeto.causa_de_pedir}</p>
            </div>
          )}
          {objeto?.pedido_principal && (
            <div className="mt-2">
              <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-0.5">Pedido Principal</p>
              <p className="text-xs text-foreground">{objeto.pedido_principal}</p>
            </div>
          )}
          {objeto?.fato_gerador && (
            <div className="mt-2">
              <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-0.5">Fato Gerador</p>
              <p className="text-xs text-foreground">{objeto.fato_gerador}</p>
            </div>
          )}
        </InfoPanel>

        <InfoPanel title="Partes Envolvidas">
          {partes?.autores && partes.autores.length > 0 ? (
            <div className="mb-3">
              <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1">
                {partes.autores.length === 1 ? "Autor" : "Autores"}
              </p>
              {partes.autores.map((a, i) => <p key={i} className="text-sm text-foreground">{a}</p>)}
            </div>
          ) : data.parties?.autor && (
            <div className="mb-3">
              <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1">Autor</p>
              <p className="text-sm text-foreground">{data.parties.autor}</p>
            </div>
          )}
          {partes?.reus && partes.reus.length > 0 ? (
            <div className="mb-3">
              <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1">
                {partes.reus.length === 1 ? "Réu" : "Réus"}
              </p>
              {partes.reus.map((r, i) => <p key={i} className="text-sm text-foreground">{r}</p>)}
            </div>
          ) : data.parties?.reu && (
            <div className="mb-3">
              <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1">Réu</p>
              <p className="text-sm text-foreground">{data.parties.reu}</p>
            </div>
          )}
          {partes?.outros && partes.outros.length > 0 && (
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1">Outros Envolvidos</p>
              {partes.outros.map((o, i) => <p key={i} className="text-xs text-muted-foreground">{o}</p>)}
            </div>
          )}
        </InfoPanel>
      </div>

      {/* 3. Linha do tempo */}
      <InfoPanel title="Linha do Tempo Processual">
        <ChronologicalTimeline
          movements={data.movements ?? latestEvents}
          decisions={decisions}
        />
      </InfoPanel>

      {/* Valores */}
      <InfoPanel title="Valores Envolvidos">
        {valores && Object.values(valores).some((v) => v && (typeof v === "string" ? v : (v as string[]).length > 0)) ? (
          <div className="space-y-2">
            {valores.valor_atualizado && <ValorRow label="Valor atualizado"   value={valores.valor_atualizado} highlight />}
            {valores.valor_causa      && <ValorRow label="Valor da causa"     value={valores.valor_causa} />}
            {valores.honorarios       && <ValorRow label="Honorários"         value={valores.honorarios} />}
            {valores.multas           && <ValorRow label="Multas"             value={valores.multas} />}
            {valores.custas           && <ValorRow label="Custas"             value={valores.custas} />}
            {valores.outros?.map((v, i) => <ValorRow key={i} label="Outro" value={v} />)}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground italic">
            {data.main_amount || (data.amounts?.[0]) || "Valores não identificados."}
          </p>
        )}
      </InfoPanel>

      {data.resumo_final && (
        <InfoPanel title="Resumo Final do Processo">
          <p className="text-sm text-foreground leading-relaxed">{data.resumo_final}</p>
        </InfoPanel>
      )}

      {/* 5. Situação atual + Próximo passo */}
      {(data.situacao_atual || data.proximo_passo) && (
        <div className="grid gap-4 lg:grid-cols-2">
          {data.situacao_atual && (
            <InfoPanel title="Situação Processual Atual">
              <p className="text-sm text-foreground leading-relaxed">{data.situacao_atual as string}</p>
            </InfoPanel>
          )}
          {data.proximo_passo && (
            <InfoPanel title="Próximo Passo">
              <p className="text-sm text-foreground leading-relaxed">{data.proximo_passo as string}</p>
            </InfoPanel>
          )}
        </div>
      )}

      {/* 6. Patrimônio + Obrigações */}
      {((data.patrimonio as string[] | undefined)?.length || (data.obrigacoes as string[] | undefined)?.length) ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {(data.patrimonio as string[]).length > 0 && (
            <InfoPanel title="Patrimônio e Execução">
              <ul className="space-y-1">
                {(data.patrimonio as string[]).map((p, i) => (
                  <li key={i} className="text-xs text-foreground flex gap-1.5">
                    <span className="text-muted-foreground mt-0.5">•</span>{p}
                  </li>
                ))}
              </ul>
            </InfoPanel>
          )}
          {(data.obrigacoes as string[]).length > 0 && (
            <InfoPanel title="Obrigações Impostas">
              <ul className="space-y-1">
                {(data.obrigacoes as string[]).map((o, i) => (
                  <li key={i} className="text-xs text-foreground flex gap-1.5">
                    <span className="text-muted-foreground mt-0.5">•</span>{o}
                  </li>
                ))}
              </ul>
            </InfoPanel>
          )}
        </div>
      ) : null}

      {/* 7. Cessão de Crédito */}
      {(() => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const cessao = data.cessao_credito as Record<string, any> | undefined;
        if (!cessao || !cessao.ocorreu) return null;
        return (
          <InfoPanel title="Cessão de Crédito">
            <div className="rounded-md border border-amber-500/30 bg-amber-50/50 dark:bg-amber-950/20 px-3 py-2 mb-3">
              <p className="text-xs font-semibold text-amber-700 dark:text-amber-400">
                O crédito deste processo foi cedido a terceiro. Verifique o cessionário antes de negociar.
              </p>
            </div>
            <div className="grid gap-x-6 gap-y-2 sm:grid-cols-2">
              {cessao.cedente && (
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-0.5">Cedente</p>
                  <p className="text-sm text-foreground">{cessao.cedente}</p>
                </div>
              )}
              {cessao.cessionario && (
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-0.5">Cessionário</p>
                  <p className="text-sm text-foreground">{cessao.cessionario}</p>
                  {cessao.cessionario_cnpj && (
                    <p className="text-xs text-muted-foreground">CNPJ: {cessao.cessionario_cnpj}</p>
                  )}
                </div>
              )}
              {cessao.percentual_cedido && (
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-0.5">Percentual Cedido</p>
                  <p className="text-sm text-foreground">{cessao.percentual_cedido}</p>
                </div>
              )}
              {cessao.valor_nominal_cedido && (
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-0.5">Valor Nominal Cedido</p>
                  <p className="text-sm font-medium text-foreground">{cessao.valor_nominal_cedido}</p>
                </div>
              )}
              {cessao.preco_aquisicao && (
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-0.5">Preço de Aquisição</p>
                  <p className="text-sm text-foreground">{cessao.preco_aquisicao}</p>
                </div>
              )}
              {cessao.data_cessao && (
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-0.5">Data da Cessão</p>
                  <p className="text-sm text-foreground">{cessao.data_cessao}</p>
                </div>
              )}
              {cessao.instrumento && (
                <div className="sm:col-span-2">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-0.5">Instrumento</p>
                  <p className="text-xs text-foreground">{cessao.instrumento}</p>
                </div>
              )}
              {cessao.processo_depre && (
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-0.5">Processo DEPRE</p>
                  <p className="text-xs text-foreground">{cessao.processo_depre}</p>
                </div>
              )}
              {cessao.status_habilitacao && (
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-0.5">Status da Habilitação</p>
                  <p className="text-xs text-foreground">{cessao.status_habilitacao}</p>
                </div>
              )}
              {cessao.observacoes && (
                <div className="sm:col-span-2">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-0.5">Observações</p>
                  <p className="text-xs text-muted-foreground">{cessao.observacoes}</p>
                </div>
              )}
            </div>
          </InfoPanel>
        );
      })()}

    </div>
  );
}

function ValorRow({ label, value, highlight = false }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="flex justify-between items-center text-xs">
      <span className="text-muted-foreground">{label}</span>
      <span className={`font-bold ${highlight ? "text-primary" : "text-foreground"}`}>{value}</span>
    </div>
  );
}

function InfoPanel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-lg border bg-muted/10 p-4">
      <p className="mb-2 text-[11px] font-black uppercase tracking-wider text-primary">{title}</p>
      <div className="text-sm leading-relaxed text-foreground">{children}</div>
    </div>
  );
}

const IMPORTANT_TYPES = new Set(["decisao", "sentenca", "acordao", "transito_em_julgado", "arquivamento_baixa"]);

function parseDateForSort(event: ProcessTimelineEvent): string {
  if (event.sort_date) return event.sort_date;
  const m = event.date.match(/^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$/);
  if (m) {
    const year = m[3].length === 2 ? `20${m[3]}` : m[3];
    return `${year}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}`;
  }
  return event.date;
}

function ChronologicalTimeline({
  movements,
  decisions,
}: {
  movements: ProcessTimelineEvent[];
  decisions: ProcessTimelineEvent[];
}) {
  const all = [...(movements ?? []), ...(decisions ?? [])];
  const seen = new Set<string>();
  const unique: ProcessTimelineEvent[] = [];
  for (const e of all) {
    const key = `${e.date}|${e.event_type}|${(e.description || e.excerpt || "").slice(0, 40)}`;
    if (!seen.has(key)) {
      seen.add(key);
      unique.push(e);
    }
  }
  unique.sort((a, b) => parseDateForSort(a).localeCompare(parseDateForSort(b)));

  if (unique.length === 0) {
    return <p className="text-muted-foreground italic text-sm">Nenhuma movimentação identificada.</p>;
  }

  return (
    <ul className="space-y-3">
      {unique.map((event, index) => {
        const isKey = IMPORTANT_TYPES.has(event.event_type);
        const raw = event.description || event.excerpt || "";
        const text = raw.length > 180 ? raw.slice(0, 180) + "…" : raw;
        return (
          <li
            key={`${event.date}-${event.event_type}-${index}`}
            className={`text-xs leading-relaxed pl-2.5 ${isKey ? "border-l-2 border-primary" : "border-l border-muted"}`}
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono font-bold text-foreground">{event.date}</span>
              {event.label && event.label !== "Data relevante" && (
                <span
                  className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                    isKey ? "bg-primary text-primary-foreground" : "bg-primary/10 text-primary"
                  }`}
                >
                  {event.label}
                </span>
              )}
            </div>
            {text && <p className="mt-0.5 text-muted-foreground">{text}</p>}
          </li>
        );
      })}
    </ul>
  );
}
