import { FilePenLine, RefreshCw, Send, X } from "lucide-react";

import { DocumentNameInput } from "@/components/DocumentNameInput";
import { DocumentTypeSelect } from "@/components/DocumentTypeSelect";
import { Button } from "@/components/ui/button";

interface PdfPreviewModalProps {
  file: File;
  previewUrl: string;
  detectedDocumentType: string;
  detectedDocumentTypeCode?: string;
  selectedDocumentType: string;
  documentName: string;
  isSubmitting?: boolean;
  error?: string | null;
  onChangeDocumentType: (value: string) => void;
  onChangeDocumentName: (value: string) => void;
  onConfirm: () => void;
  onCancel: () => void;
  onReplaceFile: () => void;
}

export function PdfPreviewModal({
  file,
  previewUrl,
  detectedDocumentType,
  detectedDocumentTypeCode,
  selectedDocumentType,
  documentName,
  isSubmitting = false,
  error,
  onChangeDocumentType,
  onChangeDocumentName,
  onConfirm,
  onCancel,
  onReplaceFile,
}: PdfPreviewModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-3">
      <div className="flex max-h-[94vh] w-full max-w-6xl flex-col overflow-hidden rounded-lg bg-white shadow-2xl">
        <header className="flex items-start justify-between gap-3 border-b px-5 py-4">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold">Pre-visualizacao do PDF</h2>
            <p className="truncate text-sm text-muted-foreground">{file.name}</p>
          </div>
          <Button variant="ghost" size="icon" title="Fechar" onClick={onCancel} disabled={isSubmitting}>
            <X className="h-4 w-4" />
          </Button>
        </header>

        <div className="grid min-h-0 flex-1 gap-0 lg:grid-cols-[360px_1fr]">
          <aside className="space-y-4 border-b p-5 lg:border-b-0 lg:border-r">
            <DocumentNameInput value={documentName} onChange={onChangeDocumentName} />
            <DocumentTypeSelect value={selectedDocumentType} onChange={onChangeDocumentType} />

            <div className="rounded-md border bg-muted/50 p-3 text-sm">
              <div className="flex items-center gap-2 font-medium">
                <FilePenLine className="h-4 w-4 text-primary" />
                Tipo detectado automaticamente
              </div>
              <p className="mt-1 text-muted-foreground">{detectedDocumentType || "Tipo desconhecido"}</p>
              {detectedDocumentTypeCode ? (
                <p className="mt-1 text-xs text-muted-foreground">
                  Contexto do tipo: <span className="font-medium">{detectedDocumentTypeCode}</span>
                </p>
              ) : null}
            </div>

            {error && <p className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}

            <div className="flex flex-wrap gap-2 pt-1">
              <Button type="button" variant="outline" onClick={onReplaceFile} disabled={isSubmitting}>
                <RefreshCw className="h-4 w-4" />
                Alterar PDF
              </Button>
              <Button type="button" variant="ghost" onClick={onCancel} disabled={isSubmitting}>
                Cancelar
              </Button>
              <Button type="button" onClick={onConfirm} disabled={isSubmitting || !documentName.trim()}>
                <Send className="h-4 w-4" />
                {isSubmitting ? "Enviando..." : "Confirmar e Enviar"}
              </Button>
            </div>
          </aside>

          <section className="min-h-[60vh] bg-muted p-3 lg:min-h-0">
            <object data={previewUrl} type="application/pdf" className="h-[68vh] w-full rounded-md border bg-white lg:h-full">
              <div className="flex h-full items-center justify-center rounded-md border bg-white p-6 text-center text-sm text-muted-foreground">
                Nao foi possivel carregar o PDF neste navegador. Use Alterar PDF para escolher outro arquivo.
              </div>
            </object>
          </section>
        </div>
      </div>
    </div>
  );
}
