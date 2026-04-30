import { useQuery } from "@tanstack/react-query";
import { Download, FileText, Trash2 } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { RiskPieChart } from "@/components/RiskPieChart";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { deleteDocument, downloadExport, fetchDocument } from "@/lib/api";

export function DocumentDetailPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const query = useQuery({ queryKey: ["document", id], queryFn: () => fetchDocument(id), enabled: Boolean(id) });
  const doc = query.data;

  if (query.isLoading) return <p>Carregando documento...</p>;
  if (!doc) return <p>Documento nao encontrado.</p>;

  async function handleDelete() {
    if (!doc) return;
    const confirmed = window.confirm(`Excluir "${doc.title}" e apagar o PDF salvo?`);
    if (!confirmed) return;
    await deleteDocument(doc.id);
    navigate("/");
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Button asChild variant="ghost" size="sm">
            <Link to="/">Voltar</Link>
          </Button>
          <h1 className="mt-2 text-2xl font-semibold">{doc.title}</h1>
          <p className="text-sm text-muted-foreground">{doc.document_type || "Aguardando classificacao"}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => downloadExport(doc.id, "excel")}>
            <Download className="h-4 w-4" />
            Excel
          </Button>
          <Button onClick={() => downloadExport(doc.id, "word")}>
            <FileText className="h-4 w-4" />
            Word
          </Button>
          <Button variant="destructive" onClick={handleDelete}>
            <Trash2 className="h-4 w-4" />
            Excluir
          </Button>
        </div>
      </div>

      <section className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <Card>
          <CardHeader>
            <CardTitle>Dados extraidos</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid gap-3 md:grid-cols-2">
              {Object.entries(doc.extracted_data)
                .filter(([key]) => key !== "pages")
                .map(([key, value]) => (
                  <div key={key} className="rounded-md border p-3">
                    <dt className="text-xs uppercase text-muted-foreground">{formatFieldLabel(key)}</dt>
                    <dd className="mt-1 break-words font-medium">{formatFieldValue(value)}</dd>
                  </div>
                ))}
            </dl>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Risco</CardTitle>
          </CardHeader>
          <CardContent>
            <RiskPieChart risk={doc.risk_score} />
            <p className="text-center text-2xl font-semibold">{doc.risk_score}/100</p>
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Parecer juridico</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="whitespace-pre-wrap leading-7">{doc.legal_opinion || "Parecer ainda nao gerado."}</p>
          {doc.error_message && <p className="mt-4 text-sm text-destructive">{doc.error_message}</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Entidades</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {doc.entities.map((entity, index) => (
              <span key={`${entity.text}-${index}`} className="rounded-md bg-muted px-3 py-1 text-sm">
                {entity.label}: {entity.text}
              </span>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function formatFieldLabel(key: string) {
  const labels: Record<string, string> = {
    nome: "Nome",
    cpf: "CPF",
    numero_processo: "Numero do processo",
    data: "Data",
    valor: "Valor",
    tipo_acao: "Tipo de acao",
    situacao_processual: "Situacao processual",
    vara: "Vara",
    foro: "Foro",
    risco: "Risco",
    nivel_risco: "Nivel de risco",
    revisao_manual: "Revisao manual",
    texto_bruto_ocr: "Texto bruto OCR",
    metodo_extracao: "Metodo de extracao",
    validacao: "Validacao",
    geometria: "Geometria",
  };
  return labels[key] ?? key.replace(/_/g, " ");
}

function formatFieldValue(value: unknown) {
  if (value === null || value === undefined || value === "" || value === false) {
    return "-";
  }
  if (typeof value === "boolean") {
    return value ? "Sim" : "Nao";
  }
  if (typeof value === "object") {
    return JSON.stringify(value, null, 2);
  }
  return String(value);
}
