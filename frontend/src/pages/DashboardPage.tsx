import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { AlertTriangle, ArrowLeft, CheckCircle2, ChevronRight, Circle, ClipboardList, Clock3, FileText } from "lucide-react";
import type { ReactNode } from "react";
import { Link, useParams } from "react-router-dom";

import { DocumentTable } from "@/components/DocumentTable";
import { UploadDocumentForm } from "@/components/UploadDocumentForm";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchDocuments, fetchFolder, fetchSummary, uploadDocument, type LegalDocument } from "@/lib/api";

export function DashboardPage() {
  const { folderId = "" } = useParams();
  const queryClient = useQueryClient();
  const { data: folder } = useQuery({
    queryKey: ["folder", folderId],
    queryFn: () => fetchFolder(folderId),
    enabled: Boolean(folderId),
    retry: false,
  });
  const documentsQuery = useQuery({ queryKey: ["documents", folderId], queryFn: () => fetchDocuments(folderId) });
  const summaryQuery = useQuery({ queryKey: ["summary", folderId], queryFn: () => fetchSummary(folderId) });
  const uploadMutation = useMutation({
    mutationFn: uploadDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", folderId] });
      queryClient.invalidateQueries({ queryKey: ["summary", folderId] });
    },
  });

  const summary = summaryQuery.data ?? { total: 0, done: 0, failed: 0, needs_ocr: 0, processing: 0 };
  const uploadError = getErrorMessage(uploadMutation.error);

  return (
    <div className="space-y-6">
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
          <span className="text-foreground font-semibold">Análise de Certidão</span>
        </div>
        <h1 className="text-2xl font-bold text-foreground">Análise de Certidão</h1>
      </div>

      <section className="grid gap-4 md:grid-cols-5">
        <Metric title="Total" value={summary.total} icon={<FileText className="h-5 w-5" />} />
        <Metric title="Concluidos" value={summary.done} icon={<CheckCircle2 className="h-5 w-5" />} />
        <Metric title="Em fila" value={summary.processing} icon={<Clock3 className="h-5 w-5" />} />
        <Metric title="Requer OCR" value={summary.needs_ocr} icon={<AlertTriangle className="h-5 w-5" />} />
        <Metric title="Falhas" value={summary.failed} icon={<AlertTriangle className="h-5 w-5" />} />
      </section>

      <CertidaoChecklist documents={documentsQuery.data ?? []} />

      <UploadDocumentForm
        onUpload={async (values) => {
          await uploadMutation.mutateAsync({ ...values, folderId });
        }}
      />

      {uploadMutation.isError && (
        <p className="text-sm text-destructive">Nao foi possivel enviar o PDF: {uploadError}</p>
      )}

      {documentsQuery.isLoading ? (
        <p>Carregando documentos...</p>
      ) : (
        <DocumentTable
          documents={documentsQuery.data ?? []}
          folderId={folderId}
          onDeleted={() => {
            queryClient.invalidateQueries({ queryKey: ["documents", folderId] });
            queryClient.invalidateQueries({ queryKey: ["summary", folderId] });
          }}
        />
      )}
    </div>
  );
}

function getErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return "erro desconhecido";
}

// The backend can store document_type as either the internal key (e.g. "cnd_federal")
// OR as the human-readable label (e.g. "Certidão Negativa Federal"), depending on the code path.
// We maintain both directions so the checklist works regardless.
const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  civel_estadual:              "Certidão Cível Estadual",
  criminal_estadual:           "Certidão Criminal Estadual",
  execucao_criminal_estadual:  "Certidão de Execuções Criminais Estadual",
  tj_falencia:                 "Certidão de Falência / Recuperação Judicial",
  tj_segundo_grau:             "Certidão TJSP 2º Grau",
  cnd_estadual:                "Certidão Negativa Estadual",
  cnd_federal:                 "Certidão Negativa Federal",
  cndt:                        "CNDT",
  ceat:                        "CEAT / TRT15",
  civel_federal:               "Certidão Cível Federal / TRF",
  criminal_federal:            "Certidão Criminal Federal / TRF",
  eleitoral:                   "Certidão Eleitoral / Fins Eleitorais",
};

// Inverted: lowercase label → key (e.g. "certidão negativa federal" → "cnd_federal")
const LABEL_TO_KEY: Record<string, string> = Object.fromEntries(
  Object.entries(DOCUMENT_TYPE_LABELS).map(([k, v]) => [v.toLowerCase(), k]),
);

function resolveTypeKey(documentType: string): string {
  if (!documentType) return "";
  if (DOCUMENT_TYPE_LABELS[documentType]) return documentType;           // already a key
  return LABEL_TO_KEY[documentType.toLowerCase()] ?? "";                 // was a label
}

const CERTIDAO_CHECKLIST = [
  { type: "civel_estadual",              label: "Cível Estadual (TJSP)" },
  { type: "criminal_estadual",           label: "Criminal Estadual (TJSP)" },
  { type: "execucao_criminal_estadual",  label: "Execuções Criminais Estadual" },
  { type: "tj_falencia",                 label: "Falência / Recuperação Judicial" },
  { type: "tj_segundo_grau",             label: "TJSP 2º Grau" },
  { type: "cnd_federal",                 label: "Negativa Federal (Receita / PGFN)" },
  { type: "cnd_estadual",                label: "Negativa Estadual (SEFAZ)" },
  { type: "cndt",                        label: "CNDT (Débitos Trabalhistas)" },
  { type: "ceat",                        label: "CEAT / TRT15" },
  { type: "civel_federal",               label: "Cível Federal (TRF)" },
  { type: "criminal_federal",            label: "Criminal Federal (TRF)" },
  { type: "eleitoral",                   label: "Eleitoral / Fins Eleitorais" },
] as const;

function CertidaoChecklist({ documents }: { documents: LegalDocument[] }) {
  // Normalize each document's type to its internal key, then index by key.
  const byType = new Map<string, LegalDocument>();
  for (const doc of documents) {
    const key = resolveTypeKey(doc.document_type ?? "");
    if (!key) continue;
    const existing = byType.get(key);
    if (!existing || (doc.status === "done" && existing.status !== "done")) {
      byType.set(key, doc);
    }
  }

  const submittedCount = CERTIDAO_CHECKLIST.filter((item) => byType.has(item.type)).length;
  const total = CERTIDAO_CHECKLIST.length;

  const statusLabel: Record<string, string> = {
    done:        "Enviada",
    processing:  "Processando...",
    needs_ocr:   "Requer OCR",
    failed:      "Falhou",
    pending:     "Na fila",
  };

  return (
    <Card>
      <CardHeader className="pb-3 border-b bg-muted/5">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <ClipboardList className="h-4 w-4 text-primary" />
            Checklist de Certidões
          </CardTitle>
          <span className="text-xs font-semibold text-muted-foreground">
            {submittedCount}/{total} identificadas
          </span>
        </div>
        {submittedCount > 0 && (
          <div className="mt-2 h-1.5 w-full rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full bg-green-500 transition-all duration-500"
              style={{ width: `${(submittedCount / total) * 100}%` }}
            />
          </div>
        )}
      </CardHeader>
      <CardContent className="pt-4">
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {CERTIDAO_CHECKLIST.map(({ type, label }) => {
            const doc = byType.get(type);
            const isDone = doc?.status === "done";
            const isWarning = doc && doc.status !== "done";

            return (
              <div
                key={type}
                className={`flex items-center gap-2.5 rounded-lg border px-3 py-2 text-xs transition-colors ${
                  isDone
                    ? "border-green-200 bg-green-50/60"
                    : isWarning
                    ? "border-amber-200 bg-amber-50/40"
                    : "border-muted bg-card"
                }`}
              >
                {isDone ? (
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-green-600" />
                ) : isWarning ? (
                  <AlertTriangle className="h-4 w-4 shrink-0 text-amber-500" />
                ) : (
                  <Circle className="h-4 w-4 shrink-0 text-muted-foreground/30" />
                )}
                <div className="min-w-0">
                  <p className={`font-semibold truncate ${
                    isDone ? "text-green-800" : isWarning ? "text-amber-800" : "text-muted-foreground"
                  }`}>
                    {label}
                  </p>
                  <p className="text-[10px] text-muted-foreground truncate">
                    {doc ? (statusLabel[doc.status] ?? doc.status) : " "}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

function Metric({ title, value, icon }: { title: string; value: number; icon: ReactNode }) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between p-5">
        <div>
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="text-2xl font-semibold">{value}</p>
        </div>
        <div className="flex h-10 w-10 items-center justify-center rounded-md bg-muted text-primary">{icon}</div>
      </CardContent>
    </Card>
  );
}
