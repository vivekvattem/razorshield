import { useEffect, useMemo, useRef, useState } from "react";
import {
  Link,
  Navigate,
  NavLink,
  Route,
  Routes,
  useLocation,
  useParams,
} from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import cytoscape from "cytoscape";
import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AnalystAction, api, ApiError, Case, Evidence } from "./api";
import { HeroNetworkIllustration } from "./components/illustrations/HeroNetworkIllustration";
import { HumanReviewIllustration } from "./components/illustrations/HumanReviewIllustration";
import { IsolatedVsConnectedIllustration } from "./components/illustrations/IsolatedVsConnectedIllustration";
import { HeroRiskCard } from "./components/HeroRiskCard";
import { useScrollSequence } from "./hooks/useScrollSequence";

const inr = (value: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value / 100);
const date = (value: string) => new Date(value).toLocaleString();
const statusClass = (value: string) => value.toLowerCase().replaceAll("_", "-");
const actions: AnalystAction[] = [
  "APPROVE_CASE",
  "DISMISS_CASE",
  "ESCALATE_CASE",
];
const decisionLabel = (value: string) =>
  ({
    APPROVE: "Safe to Approve",
    VERIFY: "Verification Needed",
    MANUAL_REVIEW: "Review Required",
  })[value] ?? value.replaceAll("_", " ");
const approvedProblem =
  "Merchants typically assess returns individually, allowing coordinated refund-abuse rings to hide across multiple accounts sharing devices, payment instruments and addresses. Transaction-only systems miss this network context, while aggressive fraud rules create false positives and delay legitimate refunds.";

function ErrorState({ error, retry }: { error: unknown; retry: () => void }) {
  const detail =
    error instanceof ApiError ? error : new ApiError("Backend unavailable");
  return (
    <div className="error-state">
      <strong>Unable to load live risk data.</strong>
      <span>{detail.message}</span>
      {detail.requestId && <code>Request ID: {detail.requestId}</code>}
      <button onClick={retry}>Retry</button>
    </div>
  );
}
function Skeleton() {
  return <div className="skeleton" aria-label="Loading data" />;
}
function Badge({ value }: { value: string }) {
  return (
    <span className={`badge ${statusClass(value)}`}>
      {decisionLabel(value)}
    </span>
  );
}
function InfoTooltip({ label, copy }: { label: string; copy: string }) {
  return (
    <button
      className="info-tooltip"
      type="button"
      aria-label={`${label}: ${copy}`}
      data-tooltip={copy}
    >
      i
    </button>
  );
}
function ApplicationLayout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
    const viewTransitionDocument = document as Document & {
      startViewTransition?: (update: () => void) => { finished: Promise<void> };
    };
    viewTransitionDocument.startViewTransition?.(() => undefined);
  }, [location.pathname]);
  const client = useQueryClient();
  const ready = useQuery({
    queryKey: ["shell-ready"],
    queryFn: api.ready,
    retry: 1,
  });
  const model = useQuery({
    queryKey: ["shell-model"],
    queryFn: api.model,
    retry: 1,
  });
  const refresh = () => client.invalidateQueries();
  const lastUpdated = new Date(
    Math.max(ready.dataUpdatedAt, model.dataUpdatedAt),
  ).toLocaleTimeString();
  return (
    <div className="app-shell">
      <aside>
        <div className="brand">
          Razor<span>Shield</span>
        </div>
        <div className="workspace">PRODUCT</div>
        <nav>
          <NavLink to="/">
            <span>Home</span>
          </NavLink>
        </nav>
        <div className="workspace">OPERATIONS</div>
        <nav>
          <NavLink to="/risk-center">
            <span>Risk Center</span>
          </NavLink>
          <NavLink to="/cases">
            <span>Cases</span>
          </NavLink>
          <NavLink to="/networks">
            <span>Networks</span>
          </NavLink>
        </nav>
        <div className="workspace">INTELLIGENCE</div>
        <nav>
          <NavLink to="/model">
            <span>Model &amp; Metrics</span>
          </NavLink>
          <NavLink to="/safety">
            <span>Safety</span>
          </NavLink>
        </nav>
        <div className="sidebar-foot">
          <b>Demo workspace</b>
          <small>Synthetic data · Analyst view</small>
        </div>
      </aside>
      <main>
        <div className="topbar">
          <div>
            <span className="crumb">RAZORSHIELD / LIVE OPS</span>
          </div>
          <input
            aria-label="Search cases"
            placeholder="Search case reference"
          />
          <button onClick={refresh}>Refresh data</button>
          <span
            className={
              ready.error || model.error ? "status-error" : "status-dot"
            }
          >
            {ready.error || model.error
              ? "Backend unavailable"
              : `${model.data?.model_version ?? "Loading model"} · ${ready.data?.status ?? "checking"}`}
          </span>
          <small>Updated {lastUpdated}</small>
          <span className="profile">AV</span>
        </div>
        <div className="route-content" key={location.pathname} tabIndex={-1}>
          {children}
        </div>
      </main>
    </div>
  );
}
function Metric({
  label,
  value,
  tone,
  context,
}: {
  label: React.ReactNode;
  value: string;
  tone?: string;
  context?: string;
}) {
  return (
    <article className={`metric ${tone ?? ""}`}>
      <div className="metric-header">
        <span>{label}</span>
        <i aria-hidden="true" />
      </div>
      <strong>{value}</strong>
      {context && <small>{context}</small>}
    </article>
  );
}
function CaseRows({ cases }: { cases: Case[] }) {
  return (
    <div className="case-table">
      <div className="table-head">
        <span>CASE / MERCHANT</span>
        <span>AMOUNT</span>
        <span>FINAL SCORE</span>
        <span>EVIDENCE</span>
        <span>RECOMMENDED ACTION</span>
        <span>LAST RISK CHECK</span>
      </div>
      {cases.map((item) => (
        <Link
          to={`/cases/${item.case_id}`}
          className="table-row"
          key={item.case_id}
        >
          <span>
            <b>{item.return_id}</b>
            <small>{item.merchant_id}</small>
          </span>
          <span>{inr(item.order_value_paise)}</span>
          <span>
            <i className="risk-track">
              <em style={{ width: `${item.final_risk * 100}%` }} />
            </i>
            {Math.round(item.final_risk * 100)}%
          </span>
          <span>
            {item.evidence_count
              ? `${item.evidence_count} rule signal${item.evidence_count > 1 ? "s" : ""}`
              : "Network assessment"}
          </span>
          <Badge value={item.decision} />
          <time>{date(item.opened_at)}</time>
        </Link>
      ))}
    </div>
  );
}
function Overview() {
  const ready = useQuery({ queryKey: ["ready"], queryFn: api.ready, retry: 2 });
  const cases = useQuery({ queryKey: ["cases"], queryFn: () => api.cases() });
  const business = useQuery({ queryKey: ["business"], queryFn: api.business });
  const model = useQuery({ queryKey: ["model"], queryFn: api.model });
  const list = cases.data?.items ?? [];
  const counts = useMemo(
    () =>
      (["APPROVE", "VERIFY", "MANUAL_REVIEW"] as const).map((name) => ({
        name,
        value: business.data?.live.decision_counts[name] ?? 0,
      })),
    [business.data],
  );
  if (
    ready.isLoading ||
    cases.isLoading ||
    business.isLoading ||
    model.isLoading
  )
    return <Skeleton />;
  if (ready.error || cases.error || business.error || model.error)
    return (
      <ErrorState
        error={ready.error ?? cases.error ?? business.error ?? model.error}
        retry={() => {
          ready.refetch();
          cases.refetch();
          business.refetch();
          model.refetch();
        }}
      />
    );
  if (!ready.data || !cases.data || !business.data || !model.data)
    return <Skeleton />;
  const b = business.data.business;
  return (
    <>
      <section className="page-title">
        <div>
          <p>RISK CENTER</p>
          <h1>Returns risk, connected.</h1>
          <span>
            Identify coordinated return abuse without automatic customer action.
          </span>
        </div>
        <div className="model-chip">
          <span className="live-dot" /> {model.data.model_version} ·{" "}
          {ready.data.model}
        </div>
      </section>
      <section className="metric-grid">
        <Metric
          label="Returns Checked"
          value={String(business.data.live.assessments)}
          tone="blue"
          context="Current demo batch"
        />
        <Metric
          label="Cases Needing Attention"
          value={String(cases.data.total)}
          tone="verify"
          context="Open review work"
        />
        <Metric
          label="Review Required"
          value={String(counts[2].value)}
          tone="coral"
          context="Human decision required"
        />
        <Metric
          label="Estimated Loss Prevented"
          value={inr(b.estimated_prevented_loss_paise ?? 0)}
          tone="emerald"
          context="Estimated recovery"
        />
        <Metric
          label="Model Status"
          value={ready.data.model === "available" ? "Ready" : "Unavailable"}
          tone="cyan"
          context="Artifact verified"
        />
      </section>
      <section className="dashboard-grid">
        <article className="panel trend">
          <div className="panel-title">
            <div>
              <span>Decisions This Batch</span>
              <h2>Recommended next steps</h2>
            </div>
          </div>
          <div className="chart-frame">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={counts}
                  dataKey="value"
                  innerRadius={55}
                  outerRadius={82}
                  paddingAngle={4}
                >
                  {counts.map((_, i) => (
                    <Cell key={i} fill={["#31c48d", "#f5b942", "#fb6b62"][i]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="legend">
            {counts.map((x) => (
              <span key={x.name}>
                <i className={statusClass(x.name)} />
                {decisionLabel(x.name)} <b>{x.value}</b>
              </span>
            ))}
          </div>
        </article>
        <article className="panel">
          <div className="panel-title">
            <div>
              <span>Risk Levels Over Time</span>
              <h2>Recent risk checks</h2>
            </div>
          </div>
          <div className="chart-frame">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={list
                  .slice()
                  .sort((left, right) =>
                    left.opened_at.localeCompare(right.opened_at),
                  )
                  .map((item, index) => ({
                    name: `Check ${index + 1}`,
                    value: Math.round(item.final_risk * 100),
                  }))}
              >
                <XAxis dataKey="name" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="value" radius={6} fill="#4c9aff" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>
      </section>
      <section className="panel priority">
        <div className="panel-title">
          <div>
            <span>Cases Needing Attention</span>
            <h2>Latest analyst work</h2>
          </div>
          <Link to="/cases">View all cases →</Link>
        </div>
        {list.length ? (
          <CaseRows cases={list.slice(0, 5)} />
        ) : (
          <p className="empty">
            The connected backend has no review cases yet.
          </p>
        )}
      </section>
      <p className="disclaimer">
        Synthetic held-out performance demonstrates the evaluation pipeline and
        is not a claim of production accuracy.
      </p>
    </>
  );
}
function Queue() {
  const [term, setTerm] = useState("");
  const [decision, setDecision] = useState("ALL");
  const [sort, setSort] = useState("RISK");
  const q = useQuery({ queryKey: ["cases"], queryFn: () => api.cases() });
  if (q.isLoading) return <Skeleton />;
  if (q.error) return <ErrorState error={q.error} retry={q.refetch} />;
  const shown = (q.data?.items ?? [])
    .filter(
      (x) =>
        `${x.return_id} ${x.merchant_id} ${x.decision}`
          .toLowerCase()
          .includes(term.toLowerCase()) &&
        (decision === "ALL" || x.decision === decision),
    )
    .sort((a, b) =>
      sort === "RISK"
        ? b.final_risk - a.final_risk
        : b.opened_at.localeCompare(a.opened_at),
    );
  return (
    <>
      <section className="page-title">
        <div>
          <p>CASE MANAGEMENT</p>
          <h1>Cases</h1>
          <span>Evidence-led intervention. No automatic adverse outcome.</span>
        </div>
      </section>
      <section className="queue-tools">
        <input
          value={term}
          onChange={(e) => setTerm(e.target.value)}
          placeholder="Search merchant, case or action"
        />
        <select value={decision} onChange={(e) => setDecision(e.target.value)}>
          <option value="ALL">All actions</option>
          <option value="VERIFY">Verification Needed</option>
          <option value="MANUAL_REVIEW">Review Required</option>
        </select>
        <select value={sort} onChange={(e) => setSort(e.target.value)}>
          <option value="RISK">Highest risk</option>
          <option value="RECENT">Most recent</option>
        </select>
        <Badge value={`OPEN ${q.data?.total ?? 0}`} />
        <button onClick={() => q.refetch()}>Refresh</button>
      </section>
      <section className="panel">
        {shown.length ? (
          <CaseRows cases={shown} />
        ) : (
          <p className="empty">
            No cases match this search. Try clearing filters.
          </p>
        )}
      </section>
    </>
  );
}
function Graph({ id, feedback = false }: { id: string; feedback?: boolean }) {
  const host = useRef<HTMLDivElement>(null);
  const q = useQuery({ queryKey: ["graph", id], queryFn: () => api.graph(id) });
  useEffect(() => {
    const nodes = q.data?.nodes ?? [];
    if (!host.current || nodes.length < 2) return;
    const cy = cytoscape({
      container: host.current,
      elements: {
        nodes: nodes.map((data) => ({ data })),
        edges: (q.data?.edges ?? []).map((data) => ({ data })),
      },
      style: [
        {
          selector: "node",
          style: {
            "background-color": "#4c9aff",
            label: "data(id)",
            color: "#dcecff",
            "font-size": 10,
          },
        },
        { selector: "edge", style: { width: 2, "line-color": "#365477" } },
      ],
      layout: { name: "cose" },
    });
    return () => cy.destroy();
  }, [q.data]);
  if (q.isLoading) return <Skeleton />;
  if (q.error) return <ErrorState error={q.error} retry={q.refetch} />;
  return (
    <>
      <article className="panel graph-panel">
        <div className="panel-title">
          <div>
            <span>CONNECTIONS</span>
            <h2>Connected Identity Map</h2>
          </div>
        </div>
        {(q.data?.nodes.length ?? 0) > 1 ? (
          <div className="graph" ref={host} />
        ) : (
          <p className="empty">
            No linked identities are safely available. Raw tokens are never
            displayed.
          </p>
        )}
      </article>
      {feedback && <FeedbackTools id={id} />}
    </>
  );
}
function FeedbackTools({ id }: { id: string }) {
  const client = useQueryClient();
  const [note, setNote] = useState("");
  const feedback = useMutation({
    mutationFn: (disposition: string) => api.feedback(id, disposition, note),
    onSuccess: () => {
      setNote("");
      client.invalidateQueries({ queryKey: ["audit", id] });
    },
  });
  const evidenceExport = useMutation({
    mutationFn: () => api.export(id),
    onSuccess: (payload) => {
      const file = new Blob([JSON.stringify(payload, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(file);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `razorshield-evidence-${id}.json`;
      anchor.click();
      URL.revokeObjectURL(url);
    },
  });
  return (
    <div className="feedback-tools">
      <label>
        Analyst feedback{" "}
        <textarea
          value={note}
          onChange={(event) => setNote(event.target.value)}
          placeholder="Optional analyst note"
          maxLength={2000}
        />
      </label>
      <div className="actions">
        <button onClick={() => feedback.mutate("CONFIRMED_ABUSE")}>
          Mark Confirmed Abuse
        </button>
        <button onClick={() => feedback.mutate("LEGITIMATE_RETURN")}>
          Mark Legitimate
        </button>
        <button onClick={() => feedback.mutate("INSUFFICIENT_EVIDENCE")}>
          Request More Evidence
        </button>
        <button onClick={() => evidenceExport.mutate()}>
          Export evidence JSON
        </button>
      </div>
      {(feedback.error || evidenceExport.error) && (
        <ErrorState
          error={feedback.error ?? evidenceExport.error}
          retry={() =>
            feedback.error ? feedback.reset() : evidenceExport.mutate()
          }
        />
      )}
      {feedback.isSuccess && (
        <small>
          Feedback recorded as future model-improvement data; no automatic
          retraining occurs.
        </small>
      )}
    </div>
  );
}
function Detail() {
  const { id = "" } = useParams();
  const client = useQueryClient();
  const q = useQuery({ queryKey: ["case", id], queryFn: () => api.case(id) });
  const audit = useQuery({
    queryKey: ["audit", id],
    queryFn: () => api.audit(id),
  });
  const mutation = useMutation({
    mutationFn: (action: AnalystAction) => api.decision(id, action),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["case", id] });
      client.invalidateQueries({ queryKey: ["audit", id] });
    },
  });
  if (q.isLoading) return <Skeleton />;
  if (q.error || !q.data)
    return <ErrorState error={q.error} retry={q.refetch} />;
  if (audit.error)
    return <ErrorState error={audit.error} retry={audit.refetch} />;
  const item = q.data;
  const a = item.assessment;
  return (
    <>
      <Link className="back" to="/cases">
        ← Back to case queue
      </Link>
      <section className="detail-hero">
        <div
          className="gauge"
          style={
            { "--risk": `${a.final_risk * 360}deg` } as React.CSSProperties
          }
        >
          <div>
            <b>{Math.round(a.final_risk * 100)}%</b>
            <span>
              Final Risk Score
              <InfoTooltip
                label="Final Risk Score"
                copy="The combined result used to select the safest next step."
              />
            </span>
          </div>
        </div>
        <div>
          <p>CASE {item.return_id}</p>
          <h1>{decisionLabel(a.decision)}</h1>
          <span className="detail-meta">Recommended Action</span>
          <Badge value={item.status} />
          <span className="detail-meta">
            {item.merchant_id} · {inr(item.order_value_paise)} ·{" "}
            {date(item.opened_at)}
          </span>
        </div>
        <div className="notice-box">
          <b>Human decision required</b>
          <span>
            RazorShield recommends a bounded workflow; final customer action
            requires analyst review.
          </span>
        </div>
      </section>
      <section className="section-label">
        <span>WHY</span>
        <h2>Signals and evidence</h2>
      </section>
      <section className="metric-grid three">
        <Metric
          label={
            <>
              <span>Model Signal</span>
              <InfoTooltip
                label="Model Signal"
                copy="Risk estimated from order and customer behaviour."
              />
            </>
          }
          value={`${Math.round(a.ml_probability * 100)}%`}
        />
        <Metric
          label={
            <>
              <span>Network Signal</span>
              <InfoTooltip
                label="Network Signal"
                copy="Risk created by connections between accounts and shared identities."
              />
            </>
          }
          value={`${Math.round(a.graph_risk * 100)}%`}
        />
        <Metric
          label={
            <>
              <span>Rule Signal</span>
              <InfoTooltip
                label="Rule Signal"
                copy="Transparent warning conditions triggered by the return."
              />
            </>
          }
          value={`${Math.round(a.rule_risk * 100)}%`}
        />
      </section>
      <section className="detail-grid">
        <article className="panel">
          <div className="panel-title">
            <div>
              <span>WHY</span>
              <h2>Evidence</h2>
            </div>
          </div>
          {a.evidence.rules?.length ? (
            a.evidence.rules.map((e: Evidence) => (
              <div className="evidence" key={e.rule_id}>
                <b>!</b>
                <span>
                  <strong>{e.rule_id.replaceAll("_", " ")}</strong>
                  {e.evidence}
                </span>
              </div>
            ))
          ) : (
            <p className="empty">
              No deterministic rules triggered; model and graph evidence remain
              recorded.
            </p>
          )}
          <div className="actions">
            {actions.map((action) => (
              <button
                key={action}
                disabled={mutation.isPending}
                onClick={() => mutation.mutate(action)}
              >
                {action === "APPROVE_CASE"
                  ? "Mark Legitimate"
                  : action === "DISMISS_CASE"
                    ? "Request More Evidence"
                    : "Mark Confirmed Abuse"}
              </button>
            ))}
          </div>
        </article>
        <article className="panel">
          <div className="panel-title">
            <div>
              <span>HISTORY</span>
              <h2>Activity Timeline &amp; Audit History</h2>
            </div>
          </div>
          {audit.data?.items.map((event) => (
            <p
              className="audit"
              key={`${event.occurred_at}-${event.event_type}`}
            >
              <b>{event.event_type}</b>
              {date(event.occurred_at)}
            </p>
          ))}
        </article>
      </section>
      <Graph id={id} feedback />
      <p className="metadata">
        Model {a.model_version} · Policy {a.policy_version}
      </p>
    </>
  );
}
function Performance() {
  const q = useQuery({ queryKey: ["model"], queryFn: api.model });
  if (q.isLoading) return <Skeleton />;
  if (q.error || !q.data)
    return <ErrorState error={q.error} retry={q.refetch} />;
  const m = q.data.evaluation.test_metrics;
  return (
    <>
      <section className="page-title">
        <div>
          <p>LOCKED HELD-OUT EVALUATION</p>
          <h1>Model &amp; Metrics</h1>
          <span>
            Synthetic evaluation only — policy selection did not use the test
            split.
          </span>
        </div>
      </section>
      <section className="metric-grid six">
        {[
          ["Accuracy of Flagged Cases", m.precision],
          ["Abuse Cases Detected", m.recall],
          ["F1", m.f1],
          ["PR-AUC", m.pr_auc],
          ["ROC-AUC", m.roc_auc],
          ["Brier", m.brier_score],
        ].map(([label, value]) => (
          <Metric
            key={String(label)}
            label={
              label === "Accuracy of Flagged Cases" ? (
                <>
                  <span>{label}</span>
                  <InfoTooltip
                    label="Accuracy of Flagged Cases"
                    copy="Of the cases the model flags, this is the share that were abusive in the locked synthetic evaluation."
                  />
                </>
              ) : label === "Abuse Cases Detected" ? (
                <>
                  <span>{label}</span>
                  <InfoTooltip
                    label="Abuse Cases Detected"
                    copy="The share of abusive returns detected in the locked synthetic evaluation."
                  />
                </>
              ) : (
                String(label)
              )
            }
            value={`${(Number(value) * 100).toFixed(1)}%`}
          />
        ))}
      </section>
      <section className="dashboard-grid">
        <article className="panel">
          <span>COMPARISON WITH THE BASE ABUSE RATE</span>
          <h2>2.35× lift in flagged-case accuracy</h2>
          <div className="chart-frame">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={[
                  { name: "Actual Abuse Rate", value: 7.83 },
                  { name: "Accuracy of Flagged Cases", value: 18.4 },
                ]}
              >
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#4c9aff" radius={6} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p>
            18.4% accuracy of flagged cases is approximately 2.35× the 7.83%
            synthetic abuse prevalence. It is not a production claim.
          </p>
        </article>
        <article className="panel">
          <span>LIMITATIONS</span>
          <h2>Read before acting</h2>
          <p>
            Scores are decision support for coordinated return abuse only.
            Synthetic patterns and calibrated probabilities can differ
            materially from merchant production traffic.
          </p>
          <p className="disclaimer">
            Synthetic held-out performance demonstrates the evaluation pipeline
            and is not a claim of production accuracy.
          </p>
          <span>CONFUSION MATRIX</span>
          <div className="confusion-grid">
            {m.confusion_matrix.flat().map((value, index) => (
              <div key={index}>
                <b>{value}</b>
                <small>
                  {
                    [
                      "True negative",
                      "False positive",
                      "False negative",
                      "True positive",
                    ][index]
                  }
                </small>
              </div>
            ))}
          </div>
        </article>
      </section>
    </>
  );
}
const featureCards = [
  "Identity Graph Intelligence|Find coordinated accounts through shared tokenized identities.",
  "Point-in-Time Behaviour|Calculate customer and velocity signals using only information available at scoring time.",
  "Calibrated Risk|Return an interpretable abuse probability rather than an unbounded AI opinion.",
  "Cost-Sensitive Policy|Balance prevented loss, review cost and legitimate-customer friction.",
  "Evidence-First Review|Explain ML, graph and rule signals behind every case.",
  "Human-Gated Decisions|Never automatically reject a customer; adverse action requires analyst review.",
  "Versioned Audit Trail|Record model, policy, evidence and analyst actions for every assessment.",
  "Honest Evaluation|Report held-out results with a clear synthetic-data limitation.",
];
function PublicLayout({ children }: { children: React.ReactNode }) {
  const [activeSection, setActiveSection] = useState("how-it-works");

  useEffect(() => {
    const sections = ["how-it-works", "capabilities", "results", "safety"]
      .map((id) => document.getElementById(id))
      .filter((section): section is HTMLElement => section !== null);
    if (!sections.length) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible) setActiveSection(visible.target.id);
      },
      { rootMargin: "-96px 0px -55%", threshold: [0.1, 0.35, 0.7] },
    );
    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, []);

  return (
    <div className="public-shell">
      <header className="public-nav">
        <Link className="public-brand" to="/">
          Razor<span>Shield</span>
        </Link>
        <nav aria-label="Product navigation">
          {["how-it-works", "capabilities", "results", "safety"].map((id) => (
            <a
              key={id}
              className={activeSection === id ? "is-active" : ""}
              href={`#${id}`}
            >
              {id === "how-it-works"
                ? "How it works"
                : id[0].toUpperCase() + id.slice(1)}
            </a>
          ))}
        </nav>
        <div className="public-nav-actions">
          <Link className="public-button secondary" to="/networks">
            <span>View live demo</span>
            <svg className="button-icon" viewBox="0 0 16 16" aria-hidden="true">
              <path d="M6 4.5 11 8l-5 3.5z" />
            </svg>
          </Link>
          <Link className="public-button" to="/risk-center">
            <span>Open Risk Center</span>
            <svg className="button-icon" viewBox="0 0 16 16" aria-hidden="true">
              <path d="M3 8h9M8 4l4 4-4 4" />
            </svg>
          </Link>
        </div>
      </header>
      <main className="public-main">{children}</main>
      <footer className="public-footer">
        <span>RazorShield</span>
        <span>Synthetic demo data. Defense-only product experience.</span>
      </footer>
    </div>
  );
}
function CapabilityIcon({ index }: { index: number }) {
  return (
    <svg className="capability-icon" viewBox="0 0 32 32" aria-hidden="true">
      {index === 0 && (
        <>
          <circle cx="8" cy="16" r="4" />
          <circle cx="24" cy="8" r="4" />
          <circle cx="24" cy="24" r="4" />
          <path d="M11 14l9-4M11 18l9 4" />
        </>
      )}
      {index === 1 && (
        <>
          <path d="M5 22c5-14 10 9 22-13" />
          <circle cx="8" cy="18" r="2" />
          <circle cx="24" cy="9" r="2" />
        </>
      )}
      {index === 2 && (
        <>
          <path d="M16 4l9 4v7c0 7-4 11-9 13-5-2-9-6-9-13V8z" />
          <path d="M11 16l3 3 6-7" />
        </>
      )}
      {index === 3 && (
        <>
          <circle cx="16" cy="16" r="10" />
          <path d="M16 9v7l5 3" />
        </>
      )}
      {index === 4 && (
        <>
          <circle cx="16" cy="10" r="5" />
          <path d="M7 28c1-7 17-7 18 0M4 19h7M21 19h7" />
        </>
      )}
      {index === 5 && (
        <>
          <path d="M9 4h11l4 4v20H9zM13 16h7M13 21h7" />
          <path d="M13 11l2 2 4-4" />
        </>
      )}
    </svg>
  );
}
const networkStoryStages = [
  { label: "Returns", heading: "Three returns appear unrelated." },
  {
    label: "Connections",
    heading: "Shared identities reveal hidden connections.",
  },
  { label: "Risk", heading: "Network context changes the risk." },
  {
    label: "Review",
    heading: "The analyst receives evidence—not an automatic rejection.",
  },
];

function NetworkStory() {
  const { ref, started, activeStage } = useScrollSequence(
    networkStoryStages.length,
  );
  const visibleStage = activeStage || networkStoryStages.length;
  const currentStage = networkStoryStages[visibleStage - 1];

  return (
    <section
      ref={ref}
      className={`network-story${started ? " is-sequencing" : ""}`}
      aria-labelledby="network-story-heading"
    >
      <div className="network-story-copy">
        <p>NETWORK STORY</p>
        <h2 id="network-story-heading" aria-live="polite">
          {currentStage.heading}
        </h2>
        <ol
          className="network-story-progress"
          aria-label="Network story stages"
        >
          {networkStoryStages.map((stage, index) => (
            <li
              key={stage.label}
              className={visibleStage >= index + 1 ? "is-active" : ""}
            >
              <span>{index + 1}</span>
              {stage.label}
            </li>
          ))}
        </ol>
      </div>
      <div className="network-story-visual">
        <HeroNetworkIllustration
          activeStage={visibleStage}
          sequencing={started}
        />
      </div>
    </section>
  );
}

function HeroRiskComposition() {
  return (
    <div className="hero-risk-composition" aria-label="Network risk overview">
      <div className="hero-risk-glow" aria-hidden="true" />
      <svg
        className="hero-compact-network"
        viewBox="0 0 620 430"
        aria-hidden="true"
      >
        <g className="compact-network-lines">
          <path d="M84 108 C188 102 202 156 296 188" />
          <path d="M78 212 C166 208 216 206 296 216" />
          <path d="M88 318 C176 318 211 269 300 240" />
          <path d="M296 188 C365 132 420 126 486 152" />
          <path d="M296 216 C380 214 412 212 492 216" />
          <path d="M300 240 C375 288 431 290 492 278" />
        </g>
        <g className="compact-network-customers">
          <circle cx="62" cy="108" r="22" />
          <circle cx="56" cy="212" r="22" />
          <circle cx="66" cy="318" r="22" />
          <text x="62" y="113">
            A
          </text>
          <text x="56" y="217">
            B
          </text>
          <text x="66" y="323">
            C
          </text>
        </g>
        <g className="compact-network-identities">
          <rect x="274" y="168" width="44" height="40" rx="12" />
          <rect x="274" y="196" width="44" height="40" rx="12" />
          <rect x="274" y="224" width="44" height="40" rx="12" />
        </g>
        <g className="compact-network-case">
          <circle cx="506" cy="216" r="47" />
          <path d="M506 188l18 7v19c0 18-10 28-18 32-8-4-18-14-18-32v-19z" />
        </g>
      </svg>
      <span className="hero-network-status">Connected network detected</span>
      <span className="hero-network-stat">
        3 accounts · 3 shared identities
      </span>
      <HeroRiskCard />
    </div>
  );
}

function WorkflowIcon({ step }: { step: string }) {
  return (
    <svg className="workflow-icon" viewBox="0 0 48 48" aria-hidden="true">
      {step === "01" && (
        <>
          <circle cx="12" cy="24" r="5" />
          <circle cx="35" cy="13" r="5" />
          <circle cx="35" cy="35" r="5" />
          <path d="M16.5 21.5 30 15.5M16.5 26.5 30 32.5" />
        </>
      )}
      {step === "02" && (
        <>
          <path d="M24 7l12 5v10c0 11-6.5 16.5-12 19-5.5-2.5-12-8-12-19V12z" />
          <path d="M16 25h4l3-7 4 12 2-5h4" />
        </>
      )}
      {step === "03" && (
        <>
          <circle cx="24" cy="13" r="4" />
          <circle cx="11" cy="35" r="4" />
          <circle cx="24" cy="35" r="4" />
          <circle cx="37" cy="35" r="4" />
          <path d="M24 17v7M24 24H11M24 24v11M24 24h13" />
        </>
      )}
      {step === "04" && (
        <>
          <path d="M14 7h15l6 6v28H14z" />
          <path d="M29 7v7h6M19 24l3 3 6-7M19 33h11" />
        </>
      )}
    </svg>
  );
}

function Home() {
  const q = useQuery({ queryKey: ["home-cases"], queryFn: () => api.cases() });
  const ring = q.data?.items.find((x) => x.decision === "MANUAL_REVIEW");
  return (
    <>
      <section className="public-hero">
        <div className="home-hero-copy">
          <p>REFUND RISK INTELLIGENCE</p>
          <h1>
            See the network
            <br />
            <em>behind every</em> suspicious return.
          </h1>
          <h2>
            RazorShield connects customer behaviour, return history and
            tokenized identities to reveal coordinated refund abuse—without
            automatically rejecting legitimate customers.
          </h2>
          <div className="actions">
            <Link className="cta primary" to="/risk-center">
              <span>Open Risk Center</span>
              <svg
                className="button-icon"
                viewBox="0 0 16 16"
                aria-hidden="true"
              >
                <path d="M3 8h9M8 4l4 4-4 4" />
              </svg>
            </Link>
            <Link
              className="cta secondary"
              to={ring ? `/cases/${ring.case_id}` : "/networks"}
            >
              <span>Explore a detected network</span>
              <svg
                className="button-icon"
                viewBox="0 0 16 16"
                aria-hidden="true"
              >
                <path d="M4 4h8v8H4zM6 8h4M8 6v4" />
              </svg>
            </Link>
          </div>
          <div className="trust-row">
            <span>Explainable decisions</span>
            <span>Human review required</span>
            <span>Tokenized identities</span>
            <span>Defense-only</span>
          </div>
        </div>
        <HeroRiskComposition />
      </section>
      <NetworkStory />
      <section className="public-section problem-section" id="problem">
        <p>THE BUSINESS PROBLEM</p>
        <h1>
          Coordinated abuse hides in <em>ordinary-looking returns.</em>
        </h1>
        <div className="editorial-split">
          <div>
            <p className="body-copy">
              When returns are evaluated individually, shared devices, payment
              tokens and addresses remain disconnected. RazorShield joins these
              signals into one understandable investigation.
            </p>
            <p className="body-copy muted-copy">{approvedProblem}</p>
          </div>
          <IsolatedVsConnectedIllustration />
        </div>
      </section>
      <section className="public-section" id="how-it-works">
        <p>HOW RAZORSHIELD WORKS</p>
        <h1>
          From connected activity to the <em>safest action.</em>
        </h1>
        <div className="workflow-steps">
          <div className="workflow-connector" aria-hidden="true" />
          {[
            ["01", "Connect", "Tokenized activity"],
            ["02", "Analyse", "Point-in-time signals"],
            ["03", "Route safely", "Three bounded actions"],
            ["04", "Audit", "Versioned evidence"],
          ].map((x) => (
            <article key={x[0]}>
              <div className="workflow-card-topline">
                <em>{x[0]}</em>
                <WorkflowIcon step={x[0]} />
              </div>
              <b>{x[1]}</b>
              <span>{x[2]}</span>
            </article>
          ))}
        </div>
      </section>
      <section className="public-section" id="capabilities">
        <p>CAPABILITIES</p>
        <h1>Built for the return operations team.</h1>
        <div className="capability-grid">
          {featureCards.slice(0, 6).map((text, index) => {
            const [title, body] = text.split("|");
            return (
              <article key={title}>
                <CapabilityIcon index={index} />
                <b>{title}</b>
                <span>{body}</span>
              </article>
            );
          })}
        </div>
      </section>
      <section className="public-section product-preview-section">
        <p>PRODUCT PREVIEW</p>
        <div className="product-preview">
          <div>
            <span>Illustrative interface preview</span>
            <h2>Final Risk Score</h2>
            <strong>82%</strong>
            <Badge value="MANUAL_REVIEW" />
          </div>
          <div className="preview-signals">
            <span>
              Model Signal <b>61%</b>
            </span>
            <span>
              Network Signal <b>94%</b>
            </span>
            <span>
              Rule Signal <b>72%</b>
            </span>
          </div>
          <div className="preview-connections">
            <b>Shared Connections</b>
            <span>dev_token_91</span>
            <span>pay_token_42</span>
            <span>addr_token_07</span>
          </div>
        </div>
      </section>
      <section className="results public-section" id="results">
        <p>LOCKED SYNTHETIC RESULTS</p>
        <div>
          <Metric label="Abuse Cases Detected" value="64.3%" />
          <Metric label="Accuracy of Flagged Cases" value="18.4%" />
          <Metric label="Lift" value="2.35×" />
          <Metric label="Net estimated savings" value="₹16,656.66" />
          <Metric label="Automatic rejections" value="0" />
        </div>
        <small>
          Synthetic held-out performance demonstrates the evaluation pipeline
          and is not a claim of production accuracy.
        </small>
      </section>
      <section className="public-section safety-section" id="safety">
        <div className="editorial-split">
          <div>
            <p>HUMAN CONTROL AND SAFETY</p>
            <h1>
              Assist the analyst.
              <br />
              <em>Never reject automatically.</em>
            </h1>
            <div className="safety-list">
              <span>No automatic rejection</span>
              <span>Human decision required</span>
              <span>Tokenized identities</span>
              <span>Versioned models and policies</span>
              <span>Measured false-positive cost</span>
              <span>Defense-only system</span>
            </div>
          </div>
          <HumanReviewIllustration />
        </div>
      </section>
      <section className="final-cta">
        <p>READY TO INVESTIGATE</p>
        <h2>Investigate the network, not just the transaction.</h2>
        <div className="actions">
          <Link className="cta" to="/risk-center">
            Launch live demo
          </Link>
          <Link
            className="cta secondary"
            to={ring ? `/cases/${ring.case_id}` : "/networks"}
          >
            Review coordinated case
          </Link>
        </div>
      </section>
    </>
  );
}
function Networks() {
  const q = useQuery({ queryKey: ["rings"], queryFn: () => api.cases() });
  if (q.isLoading) return <Skeleton />;
  if (q.error) return <ErrorState error={q.error} retry={q.refetch} />;
  const review =
    q.data?.items.filter((x) => x.decision === "MANUAL_REVIEW") ?? [];
  return (
    <>
      <section className="page-title">
        <div>
          <p>NETWORKS</p>
          <h1>Connected Networks</h1>
          <span>
            Safe summaries only; raw identity tokens are never exposed.
          </span>
        </div>
      </section>
      <section className="panel">
        {review.length ? (
          <>
            <CaseRows cases={review} />
            <Graph id={review[0].case_id} />
          </>
        ) : (
          <p className="empty">
            No connected networks currently need review in this dataset.
          </p>
        )}
      </section>
    </>
  );
}
function Safety() {
  return (
    <>
      <section className="page-title">
        <div>
          <p>SAFETY</p>
          <h1>Built for bounded interventions.</h1>
        </div>
      </section>
      <section className="feature-grid">
        {[
          "Intended use|Decision support for coordinated refund and return abuse only.",
          "Human review|No automatic customer rejection or financial penalty.",
          "Tokenized identities|No raw card details, CVVs or sensitive credentials.",
          "Versioning|Every assessment records model, policy and evidence versions.",
          "Synthetic limitation|Evaluation is a pipeline demonstration, not production accuracy.",
          "False-positive monitoring|Business cost and review capacity remain visible to analysts.",
          "Defense-only scope|No bypass advice, customer messaging or offensive guidance.",
        ].map((text) => {
          const [title, body] = text.split("|");
          return (
            <article key={title}>
              <b>{title}</b>
              <span>{body}</span>
            </article>
          );
        })}
      </section>
    </>
  );
}
export default function App() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <PublicLayout>
            <Home />
          </PublicLayout>
        }
      />
      <Route
        path="/risk-center"
        element={
          <ApplicationLayout>
            <Overview />
          </ApplicationLayout>
        }
      />
      <Route
        path="/cases"
        element={
          <ApplicationLayout>
            <Queue />
          </ApplicationLayout>
        }
      />
      <Route
        path="/cases/:id"
        element={
          <ApplicationLayout>
            <Detail />
          </ApplicationLayout>
        }
      />
      <Route
        path="/networks"
        element={
          <ApplicationLayout>
            <Networks />
          </ApplicationLayout>
        }
      />
      <Route
        path="/model"
        element={
          <ApplicationLayout>
            <Performance />
          </ApplicationLayout>
        }
      />
      <Route
        path="/safety"
        element={
          <ApplicationLayout>
            <Safety />
          </ApplicationLayout>
        }
      />
      <Route
        path="/overview"
        element={<Navigate replace to="/risk-center" />}
      />
      <Route path="/rings" element={<Navigate replace to="/networks" />} />
      <Route path="/performance" element={<Navigate replace to="/model" />} />
      <Route path="/governance" element={<Navigate replace to="/safety" />} />
      <Route path="*" element={<Navigate replace to="/" />} />
    </Routes>
  );
}
