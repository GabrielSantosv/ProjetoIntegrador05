import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ChevronRight, Eye, IdCard, RefreshCw, Trash2, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { deleteRGDocument, fetchFolder, fetchRGDocuments, uploadRG, type RGDocument } from "@/lib/api";

const FIELD_LABELS: Record<string, string> = {
  data_nascimento: "Nascimento",
  municipio:       "Município",
  nome_pai:        "Pai",
  nome_mae:        "Mãe",
  rg:              "RG",
  cpf:             "CPF",
  nome:            "Nome",
};
const FIELD_ORDER = ["data_nascimento", "municipio", "nome_pai", "nome_mae", "rg", "cpf", "nome"] as const;

export function RGPage() {
  const { folderId = "" } = useParams();
  const queryClient = useQueryClient();
  const { data: folder } = useQuery({
    queryKey: ["folder", folderId],
    queryFn: () => fetchFolder(folderId),
    enabled: Boolean(folderId),
    retry: false,
  });
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);

  const { data: rgs = [], isLoading } = useQuery({
    queryKey: ["rgs", folderId],
    queryFn: () => fetchRGDocuments(folderId),
    refetchInterval: (q) =>
      (q.state.data ?? []).some((r) => r.status === "processing") ? 3000 : false,
  });

  const uploadMutation = useMutation({
    mutationFn: (files: File[]) => uploadRG(files, folderId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rgs", folderId] });
      setPendingFiles([]);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteRGDocument,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["rgs", folderId] }),
  });

  function handleFiles(fileList: FileList | null) {
    if (!fileList) return;
    const arr = Array.from(fileList).slice(0, 2);
    setPendingFiles(arr);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  }

  function handleProcess() {
    if (pendingFiles.length === 0) return;
    uploadMutation.mutate(pendingFiles);
  }

  async function handleDelete(rg: RGDocument) {
    const confirmed = window.confirm(`Excluir "${rg.original_filename}"?`);
    if (!confirmed) return;
    deleteMutation.mutate(rg.id);
  }

  const summary = {
    total: rgs.length,
    done: rgs.filter((r) => r.status === "done").length,
    processing: rgs.filter((r) => r.status === "processing").length,
    failed: rgs.filter((r) => r.status === "failed").length,
  };

  return (
    <div className="max-w-4xl mx-auto py-4 space-y-6">
      {/* Header */}
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
          <span className="text-foreground font-semibold">Extração de RG</span>
        </div>
        <h1 className="text-2xl font-bold text-foreground">Extração de RG</h1>
      </div>

      {/* Summary bar */}
      {rgs.length > 0 && (
        <div className="flex flex-wrap gap-4 px-4 py-3 rounded-lg border bg-muted/20 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground font-medium">Total</span>
            <span className="font-bold text-foreground">{summary.total}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground font-medium">Concluídos</span>
            <span className="font-bold text-green-700">{summary.done}</span>
          </div>
          {summary.processing > 0 && (
            <div className="flex items-center gap-2 animate-pulse">
              <span className="text-blue-600 font-medium">Processando</span>
              <span className="font-bold text-blue-700">{summary.processing}</span>
            </div>
          )}
          {summary.failed > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-red-600 font-medium">Falhas</span>
              <span className="font-bold text-red-700">{summary.failed}</span>
            </div>
          )}
        </div>
      )}

      {/* Upload zone */}
      <div className="space-y-3">
        <div
          className={`flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-10 text-center transition-colors cursor-pointer ${
            dragOver
              ? "border-primary bg-primary/5"
              : pendingFiles.length > 0
              ? "border-green-400 bg-green-50/20"
              : "border-muted-foreground/30 hover:border-primary/50 hover:bg-muted/10"
          }`}
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,.pdf"
            multiple
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
          <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Upload className="h-7 w-7" />
          </div>
          <div>
            <p className="font-semibold text-foreground">Insira o RG</p>
            {pendingFiles.length > 0 ? (
              <div className="mt-1 space-y-0.5">
                {pendingFiles.map((f, i) => (
                  <p key={i} className="text-sm text-green-700 font-medium">{f.name}</p>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground mt-1">
                Arraste ou clique — PNG, JPG, BMP, PDF (até 2 arquivos)
              </p>
            )}
          </div>
        </div>

        {pendingFiles.length > 0 && (
          <div className="flex items-center gap-3">
            <Button disabled={uploadMutation.isPending} onClick={handleProcess}>
              {uploadMutation.isPending ? (
                <><RefreshCw className="h-4 w-4 mr-2 animate-spin" />Enviando...</>
              ) : "Processar"}
            </Button>
            <button
              className="text-xs text-muted-foreground hover:underline"
              onClick={() => setPendingFiles([])}
            >
              Limpar
            </button>
            {uploadMutation.isError && (
              <p className="text-xs text-destructive font-medium">Erro ao enviar.</p>
            )}
          </div>
        )}
      </div>

      {/* List */}
      {isLoading ? (
        <p className="text-sm text-muted-foreground text-center">Carregando...</p>
      ) : rgs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center space-y-3 text-muted-foreground">
          <IdCard className="h-12 w-12 opacity-20" />
          <p className="font-medium">Nenhum RG enviado ainda</p>
          <p className="text-sm">Envie uma imagem ou PDF acima para extrair os dados.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {rgs.map((rg) => (
            <RGListCard key={rg.id} rg={rg} folderId={folderId} onDelete={() => handleDelete(rg)} />
          ))}
        </div>
      )}
    </div>
  );
}

function RGListCard({ rg, folderId, onDelete }: { rg: RGDocument; folderId: string; onDelete: () => void }) {
  const hasFields = rg.status === "done";

  return (
    <Card className="hover:border-primary/30 transition-colors">
      <CardContent className="p-4 space-y-3">
        {/* Header row */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${
              rg.status === "done"   ? "bg-green-100 text-green-700" :
              rg.status === "failed" ? "bg-red-100 text-red-700" :
                                       "bg-blue-100 text-blue-600"
            }`}>
              {rg.status === "processing"
                ? <RefreshCw className="h-4 w-4 animate-spin" />
                : <IdCard className="h-4 w-4" />}
            </div>
            <div className="min-w-0">
              <p className="font-semibold text-sm text-foreground truncate">
                {rg.nome || rg.original_filename}
              </p>
              {rg.nome && (
                <p className="text-[11px] text-muted-foreground truncate">{rg.original_filename}</p>
              )}
              {rg.status === "failed" && (
                <p className="text-[11px] text-destructive">Falha na extração</p>
              )}
              {rg.status === "processing" && (
                <p className="text-[11px] text-blue-600 animate-pulse">Processando...</p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
              rg.status === "done"   ? "bg-green-100 text-green-700" :
              rg.status === "failed" ? "bg-red-100 text-red-700" :
                                       "bg-blue-100 text-blue-700 animate-pulse"
            }`}>
              {rg.status === "done" ? "Concluído" : rg.status === "failed" ? "Falha" : "Processando"}
            </span>
            <Button asChild variant="ghost" size="icon" title="Ver detalhes">
              <Link to={`/folders/${folderId}/rg/${rg.id}`}>
                <Eye className="h-4 w-4" />
              </Link>
            </Button>
            <Button variant="destructive" size="icon" title="Excluir" onClick={onDelete}>
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Inline extracted fields */}
        {hasFields && (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-2 pt-2 border-t">
            {FIELD_ORDER.map((key) => {
              const val = rg[key];
              return (
                <div key={key} className="min-w-0">
                  <p className="text-[9px] font-black uppercase tracking-widest text-primary/50">
                    {FIELD_LABELS[key]}
                  </p>
                  <p className={`text-xs font-semibold truncate ${val ? "text-foreground" : "text-destructive/50 italic"}`}>
                    {val || "Falha na extração"}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
