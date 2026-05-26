import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowLeft, Check, Copy, Pencil, RefreshCw } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { deleteRGDocument, fetchFolder, fetchRGDocument, getRGImageUrl, getRGImageVersoUrl } from "@/lib/api";

const RG_FIELD_LABELS: Record<string, string> = {
  data_nascimento: "Data de Nascimento",
  municipio:       "Município",
  nome_pai:        "Nome do Pai",
  nome_mae:        "Nome da Mãe",
  rg:              "RG",
  cpf:             "CPF",
  nome:            "Nome Completo",
};

const FIELD_ORDER = ["data_nascimento", "municipio", "nome_pai", "nome_mae", "rg", "cpf", "nome"] as const;

export function RGDetailPage() {
  const { folderId = "", rgId = "" } = useParams();
  const navigate = useNavigate();
  const { data: folder } = useQuery({
    queryKey: ["folder", folderId],
    queryFn: () => fetchFolder(folderId),
    enabled: Boolean(folderId),
    retry: false,
  });

  const [fieldEdits, setFieldEdits] = useState<Record<string, string>>({});
  const [reviewedFields, setReviewedFields] = useState<Set<string>>(new Set());
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState("");

  const query = useQuery({
    queryKey: ["rg", rgId],
    queryFn: () => fetchRGDocument(rgId),
    enabled: Boolean(rgId),
    refetchInterval: (q) => q.state.data?.status === "processing" ? 2000 : false,
  });

  if (query.isLoading) return (
    <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
      <RefreshCw className="h-10 w-10 animate-spin text-primary opacity-20" />
      <p className="text-muted-foreground animate-pulse">Carregando...</p>
    </div>
  );

  if (!query.data || query.isError) return (
    <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
      <AlertTriangle className="h-10 w-10 text-destructive" />
      <p className="text-destructive font-bold">RG não encontrado.</p>
      <Button asChild variant="outline">
        <Link to={`/folders/${folderId}/rg`}>Voltar</Link>
      </Button>
    </div>
  );

  const doc = query.data;
  const imageUrl = getRGImageUrl(doc.id);
  const imageVersoUrl = doc.image_path_verso ? getRGImageVersoUrl(doc.id) : null;

  const [sides] = (() => {
    const parts = (doc.lado_detectado || "").split("/");
    return [parts];
  })();

  async function handleDelete() {
    const confirmed = window.confirm(`Excluir "${doc.original_filename}"?`);
    if (!confirmed) return;
    await deleteRGDocument(doc.id);
    navigate(`/folders/${folderId}/rg`);
  }

  function startEdit(key: string) {
    setEditDraft(fieldEdits[key] ?? (doc as any)[key] ?? "");
    setEditingField(key);
  }

  function saveEdit(key: string) {
    setFieldEdits((prev) => ({ ...prev, [key]: editDraft }));
    setEditingField(null);
  }

  function toggleReviewed(key: string) {
    setReviewedFields((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  }

  function copyToClipboard(val: string) {
    navigator.clipboard.writeText(val).catch(() => {});
  }

  const reviewedCount = reviewedFields.size;
  const totalFields = FIELD_ORDER.length;

  return (
    <div className="max-w-4xl mx-auto py-4 space-y-6 pb-10">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <Button asChild variant="ghost" size="sm">
            <Link to={`/folders/${folderId}/rg`}>
              <ArrowLeft className="h-4 w-4" />
              Extração de RG
            </Link>
          </Button>
          <h1 className="mt-2 text-2xl font-bold text-foreground truncate">
            {doc.nome || doc.original_filename}
          </h1>
          {doc.nome && (
            <p className="text-sm text-muted-foreground">{doc.original_filename}</p>
          )}
        </div>
        <Button variant="destructive" size="sm" onClick={handleDelete}>
          Excluir
        </Button>
      </div>

      {/* Status bar */}
      <div className="flex flex-wrap items-center gap-4 px-4 py-3 rounded-lg border bg-muted/20 text-xs">
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground font-medium">Status</span>
          <span className={`px-2 py-0.5 rounded-full font-bold tracking-wider uppercase ${
            doc.status === "done"   ? "bg-green-100 text-green-700" :
            doc.status === "failed" ? "bg-red-100 text-red-700" :
                                      "bg-blue-100 text-blue-700 animate-pulse"
          }`}>
            {doc.status === "done" ? "Concluído" : doc.status === "failed" ? "Falha" : "Processando"}
          </span>
        </div>
        {doc.ocr_method && (
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground font-medium">Método OCR</span>
            <span className="font-semibold text-foreground">{doc.ocr_method}</span>
          </div>
        )}
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground font-medium">Enviado em</span>
          <span className="font-semibold text-foreground">{new Date(doc.created_at).toLocaleString()}</span>
        </div>
        {reviewedCount > 0 && (
          <div className="flex items-center gap-1 text-green-700 font-medium">
            <Check className="h-3.5 w-3.5" />
            {reviewedCount}/{totalFields} campos revisados
          </div>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        {/* Extracted fields */}
        <Card>
          <CardHeader className="pb-3 border-b bg-muted/5">
            <CardTitle className="text-base">Dados Extraídos</CardTitle>
          </CardHeader>
          <CardContent className="pt-6">
            {doc.status === "processing" ? (
              <div className="py-10 text-center space-y-3">
                <RefreshCw className="h-8 w-8 animate-spin mx-auto text-primary opacity-30" />
                <p className="text-sm text-muted-foreground italic">Extraindo dados do RG...</p>
              </div>
            ) : doc.status === "failed" ? (
              <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-5 text-center space-y-2">
                <AlertTriangle className="h-8 w-8 text-destructive opacity-40 mx-auto" />
                <p className="text-sm font-bold text-destructive">Falha na extração</p>
                {doc.error_message && (
                  <p className="text-xs text-muted-foreground">{doc.error_message}</p>
                )}
              </div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                {FIELD_ORDER.map((key) => {
                  const rawValue = (doc as any)[key] as string;
                  const isReviewed = reviewedFields.has(key);
                  const isEditing = editingField === key;
                  const displayValue = fieldEdits[key] ?? rawValue ?? "";

                  return (
                    <div
                      key={key}
                      className={`group flex flex-col gap-2 rounded-lg border bg-card p-4 shadow-sm transition-all ${
                        isReviewed ? "border-green-300 bg-green-50/40" : "hover:border-primary/30"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex flex-col gap-0.5">
                          <dt className="text-[10px] font-black uppercase text-primary/60 tracking-widest leading-tight">
                            {RG_FIELD_LABELS[key] ?? key}
                          </dt>
                          {doc.ocr_method && (
                            <span className="w-fit text-[9px] font-semibold tracking-wide text-muted-foreground/60 bg-muted/50 px-1.5 py-0.5 rounded">
                              {formatOcrMethod(doc.ocr_method)}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-1 shrink-0">
                          {isReviewed ? (
                            <button
                              onClick={() => toggleReviewed(key)}
                              className="flex items-center gap-1 text-[10px] font-bold text-green-700 bg-green-100 px-2 py-0.5 rounded-full border border-green-200 hover:bg-green-200 transition-colors"
                            >
                              <Check className="h-3 w-3" />
                              Revisado
                            </button>
                          ) : (
                            <button
                              onClick={() => toggleReviewed(key)}
                              className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 rounded bg-muted px-2 py-0.5 text-[10px] font-bold text-muted-foreground hover:bg-green-100 hover:text-green-700"
                            >
                              <Check className="h-3 w-3" />
                              Revisar
                            </button>
                          )}
                          {!isEditing && (
                            <button
                              onClick={() => startEdit(key)}
                              className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 rounded bg-primary/10 px-2 py-0.5 text-[10px] font-bold text-primary hover:bg-primary/20"
                            >
                              <Pencil className="h-3 w-3" />
                              Editar
                            </button>
                          )}
                          {!isEditing && (
                            <button
                              onClick={() => copyToClipboard(displayValue)}
                              className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 rounded bg-primary/10 px-2 py-0.5 text-[10px] font-bold text-primary hover:bg-primary/20"
                            >
                              <Copy className="h-3 w-3" />
                              Copiar
                            </button>
                          )}
                        </div>
                      </div>

                      {isEditing ? (
                        <div className="space-y-2">
                          <input
                            type="text"
                            className="w-full text-sm border rounded px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-primary/30 font-medium bg-background"
                            value={editDraft}
                            onChange={(e) => setEditDraft(e.target.value)}
                            onKeyDown={(e) => { if (e.key === "Enter") saveEdit(key); if (e.key === "Escape") setEditingField(null); }}
                            autoFocus
                          />
                          <div className="flex gap-2">
                            <button
                              onClick={() => saveEdit(key)}
                              className="flex items-center gap-1 text-[11px] font-bold text-green-700 bg-green-50 border border-green-200 px-2 py-1 rounded hover:bg-green-100 transition-colors"
                            >
                              <Check className="h-3 w-3" /> Salvar
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
                        <dd className="font-semibold text-sm leading-snug break-words">
                          {displayValue
                            ? <span className="text-foreground">{displayValue}</span>
                            : <span className="text-destructive/60 italic text-xs font-normal">Falha na extração</span>}
                        </dd>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Image preview */}
        <Card>
          <CardHeader className="pb-3 border-b bg-muted/5">
            <CardTitle className="text-base">Imagens do RG</CardTitle>
          </CardHeader>
          <CardContent className="pt-4 space-y-3">
            <RGImageBox
              url={imageUrl}
              label={sides[0] ? _sideLabel(sides[0]) : "Foto 1"}
            />
            {imageVersoUrl && (
              <RGImageBox
                url={imageVersoUrl}
                label={sides[1] ? _sideLabel(sides[1]) : "Foto 2"}
              />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function formatOcrMethod(method: string): string {
  const labels: Record<string, string> = {
    pytesseract:  "Tesseract OCR",
    windows_ocr:  "Windows OCR",
    pdf_text:     "PDF Texto",
    pdf_images:   "PDF Imagens OCR",
    failed:       "Falha na leitura",
  };
  return labels[method] ?? method;
}

function _sideLabel(side: string): string {
  if (side === "frente") return "Frente";
  if (side === "verso") return "Verso";
  return side.charAt(0).toUpperCase() + side.slice(1);
}

function RGImageBox({ url, label }: { url: string; label: string }) {
  return (
    <div className="space-y-1">
      <p className="text-[10px] font-black uppercase tracking-widest text-primary/60">{label}</p>
      <div className="rounded-md border overflow-hidden bg-muted/10">
        <img
          src={url}
          alt={label}
          className="w-full object-contain max-h-[400px]"
          onError={(e) => {
            (e.currentTarget as HTMLImageElement).style.display = "none";
            (e.currentTarget.nextElementSibling as HTMLElement)!.style.display = "flex";
          }}
        />
        <div className="hidden h-32 items-center justify-center text-muted-foreground text-sm italic">
          Imagem não disponível
        </div>
      </div>
    </div>
  );
}
