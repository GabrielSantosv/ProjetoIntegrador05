import { Download, Eye, FileText, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { deleteDocument, downloadExport, type LegalDocument } from "@/lib/api";

const statusLabels: Record<string, string> = {
  pending: "Pendente",
  processing: "Processando",
  done: "Concluido",
  failed: "Falhou",
};

export function DocumentTable({ documents, onDeleted }: { documents: LegalDocument[]; onDeleted?: () => void }) {
  async function handleDelete(document: LegalDocument) {
    const confirmed = window.confirm(`Excluir "${document.title}" e apagar o PDF salvo?`);
    if (!confirmed) return;
    await deleteDocument(document.id);
    onDeleted?.();
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Documentos</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="py-3 font-medium">Titulo</th>
                <th className="py-3 font-medium">Tipo</th>
                <th className="py-3 font-medium">Status</th>
                <th className="py-3 font-medium">Risco</th>
                <th className="py-3 text-right font-medium">Acoes</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id} className="border-b last:border-0 hover:bg-primary/5 transition-colors duration-100">
                  <td className="py-3">
                    <div className="flex items-center gap-2 font-medium text-foreground">
                      <FileText className="h-4 w-4 text-primary" />
                      <span className="font-semibold">{doc.title}</span>
                    </div>
                  </td>
                  <td className="py-3 text-muted-foreground">{doc.document_type || "-"}</td>
                  <td className="py-3">
                    <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                      doc.status === 'done' ? 'bg-green-100 text-green-800' :
                      doc.status === 'processing' ? 'bg-blue-100 text-blue-800' :
                      doc.status === 'failed' ? 'bg-red-100 text-red-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {statusLabels[doc.status]}
                    </span>
                  </td>
                  <td className="py-3">
                    <span className={`font-semibold ${
                      doc.risk_score > 70 ? 'text-red-600' :
                      doc.risk_score > 40 ? 'text-orange-600' :
                      'text-green-600'
                    }`}>
                      {doc.risk_score}/100
                    </span>
                  </td>
                  <td className="py-3">
                    <div className="flex justify-end gap-2">
                      <Button asChild variant="outline" size="icon" title="Ver detalhes do documento">
                        <Link to={`/documents/${doc.id}`}>
                          <Eye className="h-4 w-4" />
                        </Link>
                      </Button>
                      {doc.status === "done" && (
                        <Button variant="ghost" size="icon" title="Exportar em Excel" onClick={() => downloadExport(doc.id, "excel")}>
                          <Download className="h-4 w-4" />
                        </Button>
                      )}
                      <Button variant="destructive" size="icon" title="Excluir documento (sem volta)" onClick={() => handleDelete(doc)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
