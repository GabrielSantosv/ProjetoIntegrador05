import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Clock3, FileText } from "lucide-react";
import type { ReactNode } from "react";

import { DocumentTable } from "@/components/DocumentTable";
import { RiskPieChart } from "@/components/RiskPieChart";
import { UploadDocumentForm } from "@/components/UploadDocumentForm";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchDocuments, fetchSummary, uploadDocument } from "@/lib/api";

export function DashboardPage() {
  const queryClient = useQueryClient();
  const documentsQuery = useQuery({ queryKey: ["documents"], queryFn: fetchDocuments });
  const summaryQuery = useQuery({ queryKey: ["summary"], queryFn: fetchSummary });
  const uploadMutation = useMutation({
    mutationFn: uploadDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["summary"] });
    },
  });

  const summary = summaryQuery.data ?? { total: 0, done: 0, failed: 0, processing: 0, avg_risk: 0 };

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-4">
        <Metric title="Total" value={summary.total} icon={<FileText className="h-5 w-5" />} />
        <Metric title="Concluidos" value={summary.done} icon={<CheckCircle2 className="h-5 w-5" />} />
        <Metric title="Em fila" value={summary.processing} icon={<Clock3 className="h-5 w-5" />} />
        <Metric title="Falhas" value={summary.failed} icon={<AlertTriangle className="h-5 w-5" />} />
      </section>

      <section className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <UploadDocumentForm
          onUpload={async (values) => {
            await uploadMutation.mutateAsync(values);
          }}
        />
        <Card>
          <CardHeader>
            <CardTitle>Risco medio</CardTitle>
          </CardHeader>
          <CardContent>
            <RiskPieChart risk={Math.round(summary.avg_risk)} />
            <p className="text-center text-2xl font-semibold">{Math.round(summary.avg_risk)}/100</p>
          </CardContent>
        </Card>
      </section>

      {uploadMutation.isError && <p className="text-sm text-destructive">Nao foi possivel enviar o PDF.</p>}
      {documentsQuery.isLoading ? (
        <p>Carregando documentos...</p>
      ) : (
        <DocumentTable
          documents={documentsQuery.data ?? []}
          onDeleted={() => {
            queryClient.invalidateQueries({ queryKey: ["documents"] });
            queryClient.invalidateQueries({ queryKey: ["summary"] });
          }}
        />
      )}
    </div>
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
