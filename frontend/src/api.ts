export type AnalystAction = "APPROVE_CASE" | "DISMISS_CASE" | "ESCALATE_CASE";
export type RiskDecision = "APPROVE" | "VERIFY" | "MANUAL_REVIEW";
export interface Case {
  case_id: string;
  status: string;
  priority: number;
  opened_at: string;
  merchant_id: string;
  return_id: string;
  order_value_paise: number;
  final_risk: number;
  decision: RiskDecision;
  evidence_count: number;
}
export interface CaseList {
  items: Case[];
  total: number;
  page: number;
  size: number;
}
export interface Evidence {
  rule_id: string;
  evidence: string;
}
export interface Assessment {
  decision: RiskDecision;
  final_risk: number;
  ml_probability: number;
  graph_risk: number;
  rule_risk: number;
  evidence: { rules?: Evidence[] };
  model_version: string;
  policy_version: string;
  explanation: Explanation;
  uncertainty: Uncertainty;
}
export interface ExplanationFactor {
  feature: string;
  value: number;
  direction: "increases_risk" | "reduces_risk";
  strength: number;
  evidence: string;
}
export interface Explanation {
  method: "deterministic_signal_explanation_not_shap";
  explanation_version: string;
  model_version: string;
  policy_version: string;
  top_increasing_factors: ExplanationFactor[];
  top_reducing_factors: ExplanationFactor[];
  signal_contributions: { model: number; network: number; rules: number };
  summary: string;
  human_review_notice: string;
}
export interface Uncertainty {
  state: "HIGH_CONFIDENCE" | "BORDERLINE" | "INSUFFICIENT_HISTORY";
  reason: string;
  method: "heuristic_not_statistical_confidence";
  version: string;
}
export interface CaseDetail extends Case {
  assessment: Assessment;
}
export interface AuditEvent {
  event_type: string;
  occurred_at: string;
  payload: Record<string, unknown>;
}
export interface Graph {
  nodes: {
    id: string;
    type: string;
    label: string;
    case_id?: string;
    risk?: number;
  }[];
  edges: { source: string; target: string; type: string }[];
  statistics: {
    linked_account_count: number;
    shared_connection_count: number;
    connection_types: string[];
    total_connected_return_value_paise: number;
    highest_risk_linked_case: { case_id: string; risk: number } | null;
    first_seen_at: string | null;
    last_seen_at: string | null;
    risk_distribution: Record<string, number>;
  };
}
export interface FeedbackAnalytics {
  confirmed_abuse_count: number;
  legitimate_return_count: number;
  insufficient_evidence_count: number;
  total_labelled_cases: number;
  analyst_model_agreement_rate: number | null;
  potential_false_positive_count: number;
  feedback_coverage_percentage: number;
  definition: string;
  automatic_retraining: false;
}
export interface ThresholdRow {
  label: string;
  source: "validation" | "locked_test" | "operational";
  policy_version: string;
  verify_threshold: number;
  manual_review_threshold: number;
  precision: number | null;
  recall: number | null;
  f1: number | null;
  false_positives_per_1000_legitimate: number | null;
  verification_rate: number | null;
  manual_review_rate: number | null;
  estimated_prevented_loss_paise: number | null;
  false_positive_cost_paise: number | null;
  net_estimated_savings_paise: number | null;
  note: string;
}
export interface TestMetrics {
  precision: number;
  recall: number;
  f1: number;
  pr_auc: number;
  roc_auc: number;
  brier_score: number;
  confusion_matrix: [[number, number], [number, number]];
  decision_rates: Record<string, number>;
}
export interface ModelMetrics {
  model_version: string;
  operational_policy_version: string;
  evaluation: { test_metrics: TestMetrics; policy_version: string };
  synthetic_only: boolean;
}
export interface BusinessMetrics {
  policy_version: string;
  business: Record<string, number>;
  live: { assessments: number; decision_counts: Record<RiskDecision, number> };
  synthetic_only: boolean;
}
const base =
  import.meta.env.VITE_API_BASE_URL ??
  (import.meta.env.DEV ? "http://localhost:8000" : "");
export class ApiError extends Error {
  constructor(
    message: string,
    public requestId?: string,
  ) {
    super(message);
  }
}
interface ErrorBody {
  error?: { message?: string; request_id?: string };
}
async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(base + path, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  const body: unknown = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = body as ErrorBody;
    throw new ApiError(
      error.error?.message ?? "Service unavailable",
      error.error?.request_id,
    );
  }
  return body as T;
}
export const api = {
  ready: () =>
    call<{ status: string; database: string; model: string }>("/ready"),
  cases: (page = 1) => call<CaseList>(`/api/v1/cases?page=${page}&size=20`),
  case: (id: string) => call<CaseDetail>(`/api/v1/cases/${id}`),
  audit: (id: string) =>
    call<{ items: AuditEvent[] }>(`/api/v1/cases/${id}/audit`),
  graph: (id: string) => call<Graph>(`/api/v1/cases/${id}/graph`),
  decision: (id: string, action: AnalystAction) =>
    call<Case>(`/api/v1/cases/${id}/decision`, {
      method: "POST",
      body: JSON.stringify({ action }),
    }),
  feedback: (id: string, disposition: string, note = "") =>
    call<{ status: string }>(`/api/v1/cases/${id}/feedback`, {
      method: "POST",
      body: JSON.stringify({ disposition, note }),
    }),
  export: (id: string) =>
    call<Record<string, unknown>>(`/api/v1/cases/${id}/export`),
  model: () => call<ModelMetrics>("/api/v1/metrics/model"),
  business: () => call<BusinessMetrics>("/api/v1/metrics/business"),
  feedbackMetrics: () => call<FeedbackAnalytics>("/api/v1/metrics/feedback"),
  thresholds: () =>
    call<{ rows: ThresholdRow[]; disclosure: string }>(
      "/api/v1/metrics/thresholds",
    ),
};
