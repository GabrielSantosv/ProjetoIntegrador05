import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface DocumentNameInputProps {
  value: string;
  onChange: (value: string) => void;
}

export function DocumentNameInput({ value, onChange }: DocumentNameInputProps) {
  return (
    <div className="space-y-2">
      <Label htmlFor="document-name" className="font-semibold text-foreground">
        Nome do Documento
      </Label>
      <Input
        id="document-name"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Nome final do documento"
      />
    </div>
  );
}
