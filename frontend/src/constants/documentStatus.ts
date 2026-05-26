export const STATUS_LABELS: Record<string, string> = {
  pending: "Pendente",
  processing: "Processando",
  completed: "Processado",
  done: "Processado",
  needs_ocr: "Requer OCR",
  failed: "Falhou",
  error: "Erro",
};

export const STATUS_BADGE_VARIANTS: Record<string, string> = {
  pending: "secondary",
  processing: "secondary",
  completed: "default",
  done: "default",
  needs_ocr: "secondary",
  failed: "destructive",
  error: "destructive",
};

export function getStatusLabel(status?: string | null): string {
  if (!status) return "Desconhecido";
  return STATUS_LABELS[status] ?? status;
}
