import { useQuery } from "@tanstack/react-query";
import { Download, FileText, Trash2 } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { RiskPieChart } from "@/components/RiskPieChart";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { deleteDocument, downloadExport, fetchDocument } from "@/lib/api";
import { Copy } from "lucide-react";

export function DocumentDetailPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const query = useQuery({ queryKey: ["document", id], queryFn: () => fetchDocument(id), enabled: Boolean(id) });
  const doc = query.data;

  if (query.isLoading) return <p>Carregando documento...</p>;
  if (!doc) return <p>Documento nao encontrado.</p>;

  // Normalize extracted fields: backend may return { fields: [ {field_name, field_value}, ... ] }
  const rawData = doc.extracted_data || {};
  const displayFields: Array<{ label: string; value: unknown }> = [];
  if (Array.isArray((rawData as any).fields)) {
    for (const f of (rawData as any).fields) {
      displayFields.push({ label: f.field_name ?? f.fieldName ?? String(f.name ?? ""), value: f.field_value ?? f.value ?? "" });
    }
  } else {
    for (const [k, v] of Object.entries(rawData)) {
      displayFields.push({ label: k, value: v });
    }
  }

  // Normalize entities: accept both { label,text,score } and { type,value,confidence }
  const displayEntities = (doc.entities || [])
    .map((e: any) => ({ label: e.label ?? e.type ?? e.entity ?? "", text: e.text ?? e.value ?? e.field_value ?? "" }))
    .filter((e: any) => e.text && e.text !== "");

  async function handleDelete() {
    if (!doc) return;
    const confirmed = window.confirm(`Excluir "${doc.title}" e apagar o PDF salvo?`);
    if (!confirmed) return;
    await deleteDocument(doc.id);
    navigate("/");
  }

  const apiBase = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";
  const previewUrl = doc.id ? `${apiBase}/documents/${doc.id}/file` : null;

  function copyToClipboard(val: string) {
    try {
      navigator.clipboard.writeText(val);
    } catch (e) {
      console.warn('Copy failed', e);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <Button asChild variant="ghost" size="sm">
            <Link to="/">Voltar</Link>
          </Button>
          <h1 className="mt-2 text-2xl font-semibold truncate">{doc.title}</h1>
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

      <section className="grid gap-6 lg:grid-cols-[1fr_380px]">
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Pré-visualização</CardTitle>
            </CardHeader>
            <CardContent>
              {previewUrl ? (
                <div className="w-full h-[640px] border rounded overflow-hidden">
                  <object data={previewUrl} type="application/pdf" width="100%" height="100%"> 
                    <p className="p-4">Não foi possível carregar preview. <a className="text-primary" href={previewUrl} target="_blank" rel="noreferrer">Abrir em nova aba</a></p>
                  </object>
                </div>
              ) : (
                <p className="text-muted-foreground">Arquivo não disponível para pré-visualização.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Dados extraídos</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 md:grid-cols-2">
                {displayFields.length === 0 ? (
                  <div className="rounded-md border p-4 text-muted-foreground">Nenhum dado extraído.</div>
                ) : (
                  displayFields.map((f) => (
                    <div key={String(f.label)} className="rounded-md border p-3 bg-white flex items-start justify-between gap-4">
                      <div>
                        <dt className="text-xs uppercase text-muted-foreground">{formatFieldLabel(String(f.label))}</dt>
                        <dd className="mt-1 break-words font-medium">{formatFieldValue(f.value)}</dd>
                      </div>
                      <div className="shrink-0">
                        <button className="inline-flex items-center gap-2 px-2 py-1 bg-muted rounded text-sm" onClick={() => copyToClipboard(String(f.value))} title="Copiar valor">
                          <Copy className="h-4 w-4" /> Copiar
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        <aside className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Risco</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col items-center gap-4">
              <RiskPieChart risk={doc.risk_score} />
              <p className="text-center text-2xl font-semibold">{doc.risk_score}/100</p>
              <div className="w-full">
                <p className="text-sm text-muted-foreground">Status: <span className="font-medium">{doc.status}</span></p>
                <p className="text-sm text-muted-foreground">Criado: <span className="font-medium">{new Date(doc.created_at).toLocaleString()}</span></p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Entidades</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {displayEntities.length === 0 ? (
                  <p className="text-muted-foreground">Nenhuma entidade identificada.</p>
                ) : (
                  displayEntities.map((entity, index) => (
                    <span key={`${entity.label}-${index}`} className="rounded-md bg-muted px-3 py-1 text-sm">
                      <strong className="mr-1">{entity.label}</strong>
                      {entity.text}
                    </span>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </aside>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Parecer jurídico</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="whitespace-pre-wrap leading-7">{doc.legal_opinion || "Parecer ainda nao gerado."}</p>
          {doc.error_message && <p className="mt-4 text-sm text-destructive">{doc.error_message}</p>}
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
