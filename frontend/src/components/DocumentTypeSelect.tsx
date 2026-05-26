import { Label } from "@/components/ui/label";

export const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  civel_estadual: "Certidão Cível Estadual",
  criminal_estadual: "Certidão Criminal Estadual",
  execucao_criminal_estadual: "Certidão de Execuções Criminais Estadual",
  tj_falencia: "Certidão de Falência / Recuperação Judicial",
  tj_segundo_grau: "Certidão TJSP 2º Grau",
  cnd_estadual: "Certidão Negativa Estadual",
  cnd_federal: "Certidão Negativa Federal",
  cndt: "CNDT",
  ceat: "CEAT / TRT15",
  civel_federal: "Certidão Cível Federal / TRF",
  criminal_federal: "Certidão Criminal Federal / TRF",
  eleitoral: "Certidão Eleitoral / Fins Eleitorais",
  desconhecido: "Tipo desconhecido",
};

export const DOCUMENT_TYPE_OPTIONS = Object.values(DOCUMENT_TYPE_LABELS);

interface DocumentTypeSelectProps {
  value: string;
  onChange: (value: string) => void;
}

export function DocumentTypeSelect({ value, onChange }: DocumentTypeSelectProps) {
  return (
    <div className="space-y-2">
      <Label htmlFor="document-type" className="font-semibold text-foreground">
        Tipo Documental
      </Label>
      <select
        id="document-type"
        className="flex h-10 w-full rounded-md border border-input bg-white px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {DOCUMENT_TYPE_OPTIONS.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </div>
  );
}
