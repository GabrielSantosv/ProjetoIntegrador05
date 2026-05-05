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
      <Card>
        <CardHeader>
          <CardTitle>Novo processamento</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4 md:grid-cols-[1fr_1fr_auto]" onSubmit={form.handleSubmit(onSubmit)}>
            <div className="space-y-2">
              <Label htmlFor="title">Titulo</Label>
              <Input id="title" placeholder="Certidao do processo..." {...form.register("title")} />
              {form.formState.errors.title && <p className="text-sm text-destructive">{form.formState.errors.title.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="file">PDF</Label>
              <Input id="file" type="file" accept="application/pdf" {...form.register("file")} />
              {form.formState.errors.file && <p className="text-sm text-destructive">{form.formState.errors.file.message}</p>}
            </div>
            <Button className="self-end" disabled={form.formState.isSubmitting}>
              <Upload className="h-4 w-4" />
              Enviar
            </Button>
          </form>
        </CardContent>
      </Card>

      {showPreview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-[90%] max-w-4xl bg-white rounded shadow-lg overflow-hidden">
            <div className="p-4 flex items-center justify-between border-b">
              <h3 className="text-lg font-medium">Pré-visualizar PDF</h3>
              <div className="space-x-2">
                <Button variant="secondary" onClick={cancelPreview} type="button">
                  Cancelar
                </Button>
                <Button onClick={confirmUpload} type="button">
                  Confirmar e Enviar
                </Button>
              </div>
            </div>
            <div className="p-4">
              {previewUrl ? (
                <object data={previewUrl} type="application/pdf" width="100%" height={600}>
                  <p>
                    Não foi possível visualizar o PDF. <a href={previewUrl} target="_blank" rel="noreferrer">Abrir em nova aba</a>
                  </p>
                </object>
              ) : (
                <p>Sem arquivo para pré-visualização</p>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
