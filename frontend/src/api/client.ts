import type { AuditEntry, QuarantineRow, RunSummary, StatsOut, TriggerRunParams } from "./types";

const BASE_URL = "/api";

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

async function apiPost<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, { method: "POST" });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
  return res.json();
}

export function getStats(): Promise<StatsOut> {
  return apiGet("/stats");
}

export function listRuns(limit = 50): Promise<RunSummary[]> {
  return apiGet(`/runs?limit=${limit}`);
}

export function getRun(id: number): Promise<RunSummary> {
  return apiGet(`/runs/${id}`);
}

export function getRunAudit(id: number): Promise<AuditEntry[]> {
  return apiGet(`/runs/${id}/audit`);
}

export function triggerRun(params: TriggerRunParams): Promise<RunSummary> {
  const search = new URLSearchParams();
  search.set("row_count", String(params.row_count));
  search.set("failure_rate", String(params.failure_rate));
  if (params.failure_mode) search.set("failure_mode", params.failure_mode);
  if (params.seed !== undefined) search.set("seed", String(params.seed));
  if (params.use_llm !== undefined) search.set("use_llm", String(params.use_llm));
  return apiPost(`/runs/trigger?${search.toString()}`);
}

export async function triggerRunFromFile(file: File, useLlm?: boolean): Promise<RunSummary> {
  const search = new URLSearchParams();
  if (useLlm !== undefined) search.set("use_llm", String(useLlm));

  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BASE_URL}/runs/trigger?${search.toString()}`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `Upload failed: ${res.status}`);
  }
  return res.json();
}

export function listQuarantine(filters: { run_id?: number; resolved?: boolean } = {}): Promise<QuarantineRow[]> {
  const search = new URLSearchParams();
  if (filters.run_id !== undefined) search.set("run_id", String(filters.run_id));
  if (filters.resolved !== undefined) search.set("resolved", String(filters.resolved));
  const qs = search.toString();
  return apiGet(`/quarantine${qs ? `?${qs}` : ""}`);
}

export function resolveQuarantineRow(id: number): Promise<QuarantineRow> {
  return apiPost(`/quarantine/${id}/resolve`);
}
