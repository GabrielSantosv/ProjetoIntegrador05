import axios from "axios";
import { useAuthStore } from "@/store/auth";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000/api",
  timeout: 60000,
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  console.debug("[API] request", {
    method: config.method,
    baseURL: config.baseURL,
    url: config.url,
  });
  return config;
});

api.interceptors.response.use(
  (response) => {
    console.debug("[API] response", {
      method: response.config.method,
      url: response.config.url,
      status: response.status,
    });
    return response;
  },
  (error) => {
    if (axios.isAxiosError(error)) {
      console.error("[API] axios error", {
        method: error.config?.method,
        baseURL: error.config?.baseURL,
        url: error.config?.url,
        code: error.code,
        message: error.message,
        status: error.response?.status,
        response: error.response?.data,
      });
    }
    return Promise.reject(error);
  },
);

export type DocumentStatus = "pending" | "processing" | "done" | "failed" | "needs_ocr";
export type ProcessAnalysisStatus = "processing" | "done" | "failed" | "needs_ocr";

export interface LegalDocument {
  id: number;
  title: string;
  file_url: string;
  preview_url?: string;
  pdf_url?: string;
  status: DocumentStatus;
  document_type: string;
  extraction_method?: string;
  extracted_data: Record<string, unknown>;
  entities: Array<{
    category?: string;
    label?: string;
    text?: string;
    value?: string;
    score?: number;
    type?: string;
    entity?: string;
    confidence?: number;
    source?: string;
  }>;
  legal_opinion: string;
  risk_score: number;
  error_message: string;
  created_at: string;
  updated_at: string;
  folder_id?: string;
}

export interface Summary {
  total: number;
  done: number;
  failed: number;
  needs_ocr: number;
  processing: number;
  avg_risk: number;
}

export interface UploadDocumentPayload {
  file: File;
  originalFilename: string;
  finalDocumentName: string;
  detectedDocumentType: string;
  finalDocumentType: string;
  documentTypeWasEdited: boolean;
  documentNameWasEdited: boolean;
  folderId?: string;
}

export interface Folder {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface RiskFactor {
  rule: string;
  description: string;
  impact: number;
  type: "positive" | "negative";
}

export interface RiskAnalysis {
  score: number;
  base_score: number;
  classification: string;
  classification_color: string;
  description: string;
  risk_factors: RiskFactor[];
  positive_factors: RiskFactor[];
  negative_factors: RiskFactor[];
  calculation: {
    base_score: number;
    total_positive_impact: number;
    total_negative_impact: number;
    raw_score: number;
    final_score: number;
  };
  summary: string;
  document_type?: string;
  process_count?: number;
}

export interface DetectDocumentTypeResponse {
  document_type: string;
  document_label: string;
  score: number;
  matched_by: string;
}

export async function login(email: string, password: string) {
  const { data } = await api.post<{ access: string; refresh: string; email: string }>("/auth/token/", { email, password });
  return data;
}

export async function register(email: string, password: string) {
  const { data } = await api.post<{ access: string; refresh: string; email: string }>("/auth/register/", { email, password });
  return data;
}

export async function fetchFolders(): Promise<Folder[]> {
  const { data } = await api.get<Folder[]>("/folders/");
  return data;
}

export async function fetchFolder(id: string): Promise<Folder> {
  const { data } = await api.get<Folder>(`/folders/${id}`);
  return data;
}

export async function createFolder(name: string): Promise<Folder> {
  const { data } = await api.post<Folder>("/folders/", { name });
  return data;
}

export async function deleteFolder(id: string): Promise<void> {
  await api.delete(`/folders/${id}`);
}

export async function fetchDocuments(folderId?: string) {
  const { data } = await api.get<LegalDocument[]>("/documents/", { params: folderId ? { folder_id: folderId } : undefined });
  return data;
}

export async function fetchDocument(id: string) {
  const { data } = await api.get<LegalDocument>(`/documents/${id}`);
  return data;
}

export async function fetchSummary(folderId?: string) {
  const { data } = await api.get<Summary>("/documents/summary/", { params: folderId ? { folder_id: folderId } : undefined });
  return data;
}

export async function detectDocumentType(file: File): Promise<DetectDocumentTypeResponse> {
  const form = new FormData();
  form.append("file", file);
  try {
    console.debug("[API] chamando /documents/detect", { filename: file.name });
    const { data } = await api.post<DetectDocumentTypeResponse>("/documents/detect", form);
    return data;
  } catch (err) {
    console.error("[API] erro em detectDocumentType:", err);
    if (axios.isAxiosError(err)) {
      console.error("[API] detalhes:", {
        code: err.code,
        message: err.message,
        response: err.response?.data,
        status: err.response?.status,
        url: err.config?.url,
      });
    }
    throw err;
  }
}

export async function uploadDocument(payload: UploadDocumentPayload) {
  const form = new FormData();
  form.append("file", payload.file);
  form.append("title", payload.finalDocumentName);
  form.append("original_filename", payload.originalFilename);
  form.append("final_document_name", payload.finalDocumentName);
  form.append("detected_document_type", payload.detectedDocumentType);
  form.append("final_document_type", payload.finalDocumentType);
  form.append("document_type_was_edited", String(payload.documentTypeWasEdited));
  form.append("document_name_was_edited", String(payload.documentNameWasEdited));
  if (payload.folderId) form.append("folder_id", payload.folderId);
  
  try {
    console.debug("[API] chamando POST /documents/", { 
      filename: payload.originalFilename,
      finalName: payload.finalDocumentName 
    });
    const { data } = await api.post<LegalDocument>("/documents/", form);
    return data;
  } catch (err) {
    console.error("[API] erro em uploadDocument:", err);
    if (axios.isAxiosError(err)) {
      console.error("[API] detalhes:", {
        code: err.code,
        message: err.message,
        response: err.response?.data,
        status: err.response?.status,
        url: err.config?.url,
        isNetworkError: !err.response && err.code === "ERR_NETWORK"
      });
    }
    throw err;
  }
}

export async function deleteDocument(id: number) {
  await api.delete(`/documents/${id}/`);
}

export async function reprocessDocument(id: number) {
  const { data } = await api.post<{ id: number; status: DocumentStatus }>(`/documents/${id}/reprocess`);
  return data;
}

// ─── RG ───────────────────────────────────────────────────────────────────────

export interface RGDocument {
  id: number;
  original_filename: string;
  image_path: string;
  image_path_verso: string;
  lado_detectado: string;
  status: "processing" | "done" | "failed";
  ocr_method: string;
  nome: string;
  rg: string;
  cpf: string;
  data_nascimento: string;
  municipio: string;
  nome_mae: string;
  nome_pai: string;
  error_message: string;
  created_at: string;
  updated_at: string;
  folder_id?: string;
}

export async function fetchRGDocuments(folderId?: string): Promise<RGDocument[]> {
  const { data } = await api.get<RGDocument[]>("/rg/", { params: folderId ? { folder_id: folderId } : undefined });
  return data;
}

export async function fetchRGDocument(id: string): Promise<RGDocument> {
  const { data } = await api.get<RGDocument>(`/rg/${id}`);
  return data;
}

export async function uploadRG(files: File[], folderId?: string): Promise<{ id: number; status: string }> {
  const form = new FormData();
  for (const f of files) form.append("files", f);
  if (folderId) form.append("folder_id", folderId);
  const { data } = await api.post<{ id: number; status: string }>("/rg/", form);
  return data;
}

export async function deleteRGDocument(id: number): Promise<void> {
  await api.delete(`/rg/${id}`);
}

export function getRGImageUrl(id: number): string {
  const base = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";
  return `${base}/rg/${id}/image`;
}

export function getRGImageVersoUrl(id: number): string {
  const base = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";
  return `${base}/rg/${id}/image_verso`;
}

// ─── Documents export ─────────────────────────────────────────────────────────

// ─── Processos ────────────────────────────────────────────────────────────────

export interface ProcessTimelineEvent {
  date: string;
  sort_date?: string;
  event_type: string;
  label: string;
  excerpt?: string;
  description?: string;
}

export interface ProcessIdentificacao {
  tribunal?: string;
  comarca?: string;
  vara?: string;
  classe_processual?: string;
  assunto?: string;
  fase_atual?: string;
  data_distribuicao?: string;
  valor_causa?: string;
  instancia?: string;
}

export interface ProcessObjeto {
  resumo?: string;
  causa_de_pedir?: string;
  pedido_principal?: string;
  pedidos_acessorios?: string[];
  fato_gerador?: string;
}

export interface ProcessValores {
  valor_causa?: string;
  valor_atualizado?: string;
  honorarios?: string;
  multas?: string;
  custas?: string;
  outros?: string[];
}

export interface ProcessRiscos {
  nivel?: "baixo" | "médio" | "alto";
  fatores?: string[];
}

export interface ProcessPartesDetalhadas {
  autores?: string[];
  reus?: string[];
  outros?: string[];
}

export interface ProcessAnalysisData {
  // Structured fields (PDF spec)
  identificacao?: ProcessIdentificacao;
  partes_detalhadas?: ProcessPartesDetalhadas;
  objeto?: ProcessObjeto;
  valores_detalhados?: ProcessValores;
  riscos?: ProcessRiscos;
  situacao_atual?: string;
  resumo_final?: string;
  patrimonio?: string[];
  obrigacoes?: string[];
  proximo_passo?: string;
  // Legacy fields
  process_number?: string;
  subject?: string;
  case_description?: string;
  parties?: { autor?: string; reu?: string; juiz?: string };
  amounts?: string[];
  main_amount?: string;
  timeline?: ProcessTimelineEvent[];
  latest_events?: ProcessTimelineEvent[];
  important_decisions?: ProcessTimelineEvent[];
  deadlines?: Array<{ days?: string; description: string; status?: string }>;
  movements?: ProcessTimelineEvent[];
  summary?: string;
}

export interface ProcessDocument {
  id: number;
  folder_id: string;
  process_number: string;
  source_document_id?: number | null;
  original_filename: string;
  file_url: string;
  preview_url: string;
  status: ProcessAnalysisStatus;
  extraction_method: string;
  analysis_data: ProcessAnalysisData;
  summary: string;
  error_message: string;
  created_at: string;
  updated_at: string;
}

export async function fetchProcessDocuments(folderId?: string, processNumber?: string): Promise<ProcessDocument[]> {
  const params: Record<string, string> = {};
  if (folderId) params.folder_id = folderId;
  if (processNumber) params.process_number = processNumber;
  const { data } = await api.get<ProcessDocument[]>("/processes/", { params });
  return data;
}

export async function uploadProcessDocument(payload: {
  folderId: string;
  processNumber: string;
  sourceDocumentId?: number;
  file: File;
}): Promise<ProcessDocument> {
  const form = new FormData();
  form.append("folder_id", payload.folderId);
  form.append("process_number", payload.processNumber);
  if (payload.sourceDocumentId) form.append("source_document_id", String(payload.sourceDocumentId));
  form.append("file", payload.file);
  const { data } = await api.post<ProcessDocument>("/processes/", form);
  return data;
}

export async function deleteProcessDocument(id: number): Promise<void> {
  await api.delete(`/processes/${id}`);
}

export function getProcessPdfUrl(id: number): string {
  const base = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";
  return `${base}/processes/${id}/file`;
}

export async function downloadExport(id: number, format: "excel" | "word") {
  const endpoint = format === "excel" ? "export_excel" : "export_word";
  const extension = format === "excel" ? "csv" : "txt";
  const { data } = await api.get(`/documents/${id}/${endpoint}`, { responseType: "blob" });
  const url = URL.createObjectURL(data);
  const link = document.createElement("a");
  link.href = url;
  link.download = `documento-${id}.${extension}`;
  link.click();
  URL.revokeObjectURL(url);
}
