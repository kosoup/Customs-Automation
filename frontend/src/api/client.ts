import axios from "axios";
import type {
  Declaration,
  DeclarationListItem,
  ValidationResult,
} from "../types";

const api = axios.create({ baseURL: "http://localhost:8000/api" });

export async function listDeclarations(
  status?: string,
  page = 1
): Promise<DeclarationListItem[]> {
  const params: Record<string, string | number> = { page };
  if (status) params.status = status;
  const { data } = await api.get("/declarations", { params });
  return data;
}

export async function getDeclaration(id: number): Promise<Declaration> {
  const { data } = await api.get(`/declarations/${id}`);
  return data;
}

export async function createDeclaration(
  body: Partial<Declaration>
): Promise<Declaration> {
  const { data } = await api.post("/declarations", body);
  return data;
}

export async function updateDeclaration(
  id: number,
  body: Partial<Declaration>
): Promise<Declaration> {
  const { data } = await api.put(`/declarations/${id}`, body);
  return data;
}

export async function deleteDeclaration(id: number): Promise<void> {
  await api.delete(`/declarations/${id}`);
}

export async function validateDeclaration(
  id: number
): Promise<ValidationResult> {
  const { data } = await api.post(`/declarations/${id}/validate`);
  return data;
}

export async function getStats(): Promise<Record<string, number>> {
  const { data } = await api.get("/declarations/stats/summary");
  return data;
}

export async function submitDeclaration(
  id: number,
  method: "utradehub" | "file_export" = "file_export"
): Promise<object> {
  const { data } = await api.post(`/declarations/${id}/submit`, null, {
    params: { method },
  });
  return data;
}

export async function trackDeclaration(id: number): Promise<Record<string, string | null>> {
  const { data } = await api.get(`/declarations/${id}/track`);
  return data;
}

export function exportFileUrl(id: number, fmt: "xlsx" | "csv" = "xlsx") {
  return `http://localhost:8000/api/declarations/${id}/export-file?fmt=${fmt}`;
}

export async function uploadInvoice(
  file: File,
  templateName?: string
): Promise<{ invoice: object; declaration_id: number; parsed_data: object }> {
  const form = new FormData();
  form.append("file", file);
  if (templateName) form.append("template_name", templateName);
  const { data } = await api.post("/invoices/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}
