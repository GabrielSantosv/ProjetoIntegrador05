import axios from "axios";
import { useAuthStore } from "@/store/auth";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000/api",
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export type DocumentStatus = "pending" | "processing" | "done" | "failed";

export interface LegalDocument {
  id: number;
  title: string;
  file_url: string;
  status: DocumentStatus;
  document_type: string;
  extracted_data: Record<string, unknown>;
  entities: Array<{ label: string; text: string; score: number }>;
  legal_opinion: string;
  risk_score: number;
  error_message: string;
  created_at: string;
  updated_at: string;
}

export interface Summary {
  total: number;
  done: number;
  failed: number;
  processing: number;
  avg_risk: number;
}

export async function login(username: string, password: string) {
  const { data } = await api.post<{ access: string; refresh: string }>("/auth/token/", { username, password });
  return data;
}

export async function fetchDocuments() {
  const { data } = await api.get<LegalDocument[]>("/documents/");
  return data;
}

export async function fetchDocument(id: string) {
  const { data } = await api.get<LegalDocument>(`/documents/${id}/`);
  return data;
}

export async function fetchSummary() {
  const { data } = await api.get<Summary>("/documents/summary/");
  return data;
}

export async function uploadDocument(payload: { title: string; file: File }) {
  const form = new FormData();
  form.append("title", payload.title);
  form.append("file", payload.file);
  const { data } = await api.post<LegalDocument>("/documents/", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function deleteDocument(id: number) {
  await api.delete(`/documents/${id}/`);
}

export async function downloadExport(id: number, format: "excel" | "word") {
  const endpoint = format === "excel" ? "export_excel" : "export_word";
  const extension = format === "excel" ? "xlsx" : "docx";
  const { data } = await api.get(`/documents/${id}/${endpoint}/`, { responseType: "blob" });
  const url = URL.createObjectURL(data);
  const link = document.createElement("a");
  link.href = url;
  link.download = `documento-${id}.${extension}`;
  link.click();
  URL.revokeObjectURL(url);
}
