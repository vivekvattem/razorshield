export type AnalystAction = "APPROVE_CASE" | "DISMISS_CASE" | "ESCALATE_CASE";
export type RiskDecision = "APPROVE" | "VERIFY" | "MANUAL_REVIEW";
export interface Case { case_id: string; status: string; priority: number; opened_at: string; merchant_id: string; return_id: string; order_value_paise: number; final_risk: number; decision: RiskDecision; evidence_count: number }
export interface CaseList { items: Case[]; total: number; page: number; size: number }
export interface Evidence { rule_id: string; evidence: string }
export interface Assessment { decision: RiskDecision; final_risk: number; ml_probability: number; graph_risk: number; rule_risk: number; evidence: { rules?: Evidence[] }; model_version: string; policy_version: string }
export interface CaseDetail extends Case { assessment: Assessment }
export interface AuditEvent { event_type: string; occurred_at: string; payload: Record<string, unknown> }
export interface Graph { nodes: { id: string; type: string }[]; edges: { source: string; target: string }[]; statistics: Record<string, number> }
export interface TestMetrics { precision: number; recall: number; f1: number; pr_auc: number; roc_auc: number; brier_score: number; decision_rates: Record<string, number> }
export interface ModelMetrics { model_version: string; evaluation: { test_metrics: TestMetrics }; synthetic_only: boolean }
export interface BusinessMetrics { policy_version: string; business: Record<string, number>; synthetic_only: boolean }
const base = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
export class ApiError extends Error { constructor(message: string, public requestId?: string) { super(message); } }
interface ErrorBody { error?: { message?: string; request_id?: string } }
async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(base + path, { ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  const body: unknown = await response.json().catch(() => ({}));
  if (!response.ok) { const error = body as ErrorBody; throw new ApiError(error.error?.message ?? "Service unavailable", error.error?.request_id); }
  return body as T;
}
export const api = {
  ready: () => call<{ status: string; database: string; model: string }>("/ready"),
  cases: (page = 1) => call<CaseList>(`/api/v1/cases?page=${page}&size=20`),
  case: (id: string) => call<CaseDetail>(`/api/v1/cases/${id}`), audit: (id: string) => call<{ items: AuditEvent[] }>(`/api/v1/cases/${id}/audit`),
  graph: (id: string) => call<Graph>(`/api/v1/cases/${id}/graph`), decision: (id: string, action: AnalystAction) => call<Case>(`/api/v1/cases/${id}/decision`, { method: "POST", body: JSON.stringify({ action }) }),
  feedback: (id: string, disposition: string, note = "") => call<{status:string}>(`/api/v1/cases/${id}/feedback`, { method: "POST", body: JSON.stringify({ disposition, note }) }),
  export: (id: string) => call<Record<string, unknown>>(`/api/v1/cases/${id}/export`),
  model: () => call<ModelMetrics>("/api/v1/metrics/model"), business: () => call<BusinessMetrics>("/api/v1/metrics/business"),
};
