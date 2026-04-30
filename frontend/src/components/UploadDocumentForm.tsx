import { zodResolver } from "@hookform/resolvers/zod";
import { Upload } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

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

  async function onSubmit(values: UploadFormValues) {
    await onUpload({ title: values.title, file: values.file[0] });
    form.reset();
  }

  return (
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
  );
}
