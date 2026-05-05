import { zodResolver } from "@hookform/resolvers/zod";
import { Upload } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import React, { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const schema = z.object({
  title: z.string().min(3, "Use um titulo com pelo menos 3 caracteres"),
  file: z.instanceof(FileList).refine((files) => files.length === 1, "Selecione um PDF"),
});

export type UploadFormValues = z.infer<typeof schema>;

interface Props {
  onUpload: (values: { title: string; file: File }) => Promise<void>;
}

export function UploadDocumentForm({ onUpload }: Props) {
  const form = useForm<UploadFormValues>({ resolver: zodResolver(schema) });
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewFile, setPreviewFile] = useState<File | null>(null);
  const [showPreview, setShowPreview] = useState(false);

  async function onSubmit(values: UploadFormValues) {
    // Instead of uploading immediately, open a preview modal
    const file = values.file[0];
    const url = URL.createObjectURL(file);
    setPreviewFile(file);
    setPreviewUrl(url);
    setShowPreview(true);
  }

  async function confirmUpload() {
    if (!previewFile) return;
    try {
      await onUpload({ title: form.getValues().title, file: previewFile });
    } finally {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setShowPreview(false);
      setPreviewFile(null);
      setPreviewUrl(null);
      form.reset();
    }
  }

  function cancelPreview() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setShowPreview(false);
    setPreviewFile(null);
    setPreviewUrl(null);
  }

  return (
    <>
      <Card className="border-2 border-primary/20 hover:border-primary/40 hover:shadow-lg transition-all">
        <CardHeader className="bg-gradient-to-r from-primary/5 to-transparent">
          <CardTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5 text-primary" />
            Novo Processamento
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-6">
          <form className="grid gap-4 md:grid-cols-[1fr_1fr_auto]" onSubmit={form.handleSubmit(onSubmit)}>
            <div className="space-y-2">
              <Label htmlFor="title" className="font-semibold text-foreground">Título do Documento</Label>
              <Input 
                id="title" 
                placeholder="Ex: Certidão do processo 001/2024" 
                {...form.register("title")}
                className="focus:ring-2 focus:ring-primary/30"
              />
              {form.formState.errors.title && <p className="text-sm text-destructive font-medium">⚠️ {form.formState.errors.title.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="file" className="font-semibold text-foreground">Selecionar PDF</Label>
              <Input 
                id="file" 
                type="file" 
                accept="application/pdf" 
                {...form.register("file")}
                className="file:cursor-pointer file:font-semibold file:text-primary hover:file:text-primary/80"
              />
              {form.formState.errors.file && <p className="text-sm text-destructive font-medium">⚠️ {form.formState.errors.file.message}</p>}
            </div>
            <Button 
              className="self-end bg-primary hover:bg-primary/80 text-white font-semibold shadow-md hover:shadow-lg" 
              disabled={form.formState.isSubmitting}
            >
              <Upload className="h-4 w-4" />
              {form.formState.isSubmitting ? "Enviando..." : "Enviar"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {showPreview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="w-[90%] max-w-4xl bg-white rounded-lg shadow-2xl overflow-hidden animate-in fade-in zoom-in-95">
            <div className="p-4 flex items-center justify-between border-b bg-gradient-to-r from-primary/5 to-transparent">
              <h3 className="text-lg font-bold text-foreground">📄 Pré-visualizar PDF</h3>
              <div className="space-x-2 flex">
                <Button variant="secondary" onClick={cancelPreview} type="button" className="hover:bg-red-100">
                  ✕ Cancelar
                </Button>
                <Button onClick={confirmUpload} type="button" className="bg-green-600 hover:bg-green-700 text-white">
                  ✓ Confirmar e Enviar
                </Button>
              </div>
            </div>
            <div className="p-4 bg-gray-50">
              {previewUrl ? (
                <object data={previewUrl} type="application/pdf" width="100%" height={600} className="border border-gray-300 rounded">
                  <p className="text-center text-muted-foreground">
                    Não foi possível visualizar o PDF. <a href={previewUrl} target="_blank" rel="noreferrer" className="text-primary font-semibold hover:underline">Abrir em nova aba →</a>
                  </p>
                </object>
              ) : (
                <p className="text-center text-muted-foreground py-8">Sem arquivo para pré-visualização</p>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
