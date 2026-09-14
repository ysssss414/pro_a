import { useEffect, useMemo, useState } from "react";

import {
  getSession, getViewWorkbench, qualifyViewDraft, reconcileViewReceipt, saveViewDraft,
  validateViewDraft, type CurrentViewWorkbenchState, type ViewEvidence,
} from "../api/workbench";

interface Props { nodeId: string; onOpenSource: (sourceId: string) => void; onOpenClaim?: (claimId: string) => void; }
const list = (value: unknown): string[] => Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
const text = (value: unknown): string => typeof value === "string" ? value : "";
const lines = (value: string): string[] => value.split("\n").map((item) => item.trim()).filter(Boolean);

function EvidenceCard({ item, primary, context, onPrimary, onContext, onOpenSource, onOpenClaim }: {
  item: ViewEvidence; primary: boolean; context: boolean; onPrimary: () => void;
  onContext: () => void; onOpenSource: () => void; onOpenClaim: () => void;
}) {
  return <article className="view-workbench-evidence">
    <div><strong>{item.statement}</strong><span>{item.role === "subject" ? "Subject / primary eligible" : item.role === "context" ? "Context only" : "Related only"}{item.officially_referenced ? " · referenced by official View" : ""}</span></div>
    <p>{item.evidence_excerpt || "Evidence span unresolved"}</p>
    <dl className="metadata-grid">
      <div><dt>Evidence date</dt><dd>{item.business_date ?? "unknown"}</dd></div>
      <div><dt>Date basis</dt><dd>{item.freshness_basis}</dd></div>
      <div><dt>Status</dt><dd>{item.status}</dd></div>
      <div><dt>Locator</dt><dd>{item.source_locator ? JSON.stringify(item.source_locator) : item.evidence_pointer || "unresolved"}</dd></div>
    </dl>
    <div className="view-workbench-evidence-actions">
      <label><input type="checkbox" checked={primary} disabled={!item.primary_eligible} onChange={onPrimary} /> Primary Evidence</label>
      <label><input type="checkbox" checked={context} disabled={item.role !== "context"} onChange={onContext} /> Context only</label>
      <button type="button" onClick={onOpenClaim}>Open Claim</button><button type="button" onClick={onOpenSource}>Open Source</button><code>{item.claim_id}</code>
    </div>
  </article>;
}

export function CurrentViewWorkbench({ nodeId, onOpenSource, onOpenClaim = () => undefined }: Props) {
  const [state, setState] = useState<CurrentViewWorkbenchState | null>(null);
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  const [reviewer, setReviewer] = useState("Human View Operator");
  const [reason, setReason] = useState("Explicit staged Current View maintenance");
  const [mode, setMode] = useState<"INITIAL" | "UPDATE">("INITIAL");
  const [changeLevel, setChangeLevel] = useState<"initial" | "minor" | "material" | "thesis">("initial");
  const [content, setContent] = useState<Record<string, unknown>>({});
  const [primary, setPrimary] = useState<string[]>([]); const [context, setContext] = useState<string[]>([]);
  const [qualified, setQualified] = useState<{ object_id: string; predicted_diff: Record<string, unknown> } | null>(null);
  const [receiptId, setReceiptId] = useState(""); const [verified, setVerified] = useState("");

  const load = async (signal: AbortSignal) => {
    const result = await getViewWorkbench(nodeId, signal); setState(result);
    const draft = result.draft;
    setMode(draft?.mode ?? (result.official ? "UPDATE" : "INITIAL"));
    setChangeLevel(draft?.change_level ?? (result.official ? "minor" : "initial"));
    setContent(draft?.content ?? result.official?.content_json ?? {
      one_line_conclusion: "", core_logic: [], key_facts: [], core_disagreements: [],
      assumptions_to_verify: [], investment_implication: "", major_risks: [], knowledge_gaps: [],
      key_watch_items: [], recent_change: "", evidence_claim_ids: [],
      type_specific: result.node.primary_type === "Product" ? {
        applications: [], demand_drivers: [], supply_capacity: [], pricing: [], major_suppliers: [], product_evolution: [],
      } : {},
    });
    setPrimary(draft?.primary_claim_ids ?? []); setContext(draft?.context_claim_ids ?? []);
    setReviewer(draft?.reviewer ?? "Human View Operator");
  };
  useEffect(() => {
    const controller = new AbortController(); setState(null); setError(""); setQualified(null); setVerified("");
    load(controller.signal).catch((failure: Error) => { if (failure.name !== "AbortError") setError(failure.message); });
    return () => controller.abort();
  }, [nodeId]);
  const csrf = async (signal: AbortSignal) => (await getSession(signal)).csrf_token ?? "";
  const run = async (action: (token: string, signal: AbortSignal) => Promise<void>) => {
    const controller = new AbortController(); setBusy(true); setError("");
    try { await action(await csrf(controller.signal), controller.signal); }
    catch (failure) { setError((failure as Error).message); } finally { setBusy(false); }
  };
  const toggle = (values: string[], value: string, setter: (value: string[]) => void) => setter(values.includes(value) ? values.filter((item) => item !== value) : [...values, value]);
  const setField = (field: string, value: unknown) => setContent((current) => ({ ...current, [field]: value }));
  const changed = useMemo(() => {
    const official = state?.official?.content_json ?? {};
    return [...new Set([...Object.keys(official), ...Object.keys(content)])].filter((field) => JSON.stringify(official[field]) !== JSON.stringify(content[field]));
  }, [content, state?.official]);
  if (error && !state) return <div className="tab-empty is-error" role="alert">Current View Workbench unavailable: {error}</div>;
  if (!state) return <div className="tab-empty">Loading Current View Workbench…</div>;
  const brokenOfficialEvidence = state.official_evidence.filter((item) => !item.resolved);
  const officialPrimaryCount = state.official?.trigger_claim_ids.length ?? 0;
  const contextCount = state.available_evidence.filter((item) => item.role === "context").length;
  const save = () => run(async (token, signal) => {
    await saveViewDraft(nodeId, { basis_sha256: state.basis_sha256, expected_revision: state.draft?.revision ?? 0,
      operation_id: crypto.randomUUID(), reviewer, reason, mode,
      expected_official_view_id: mode === "UPDATE" ? state.official?.view_id ?? "" : "",
      content: { ...content, evidence_claim_ids: primary }, primary_claim_ids: primary,
      context_claim_ids: context, change_level: changeLevel }, token, signal);
    await load(signal); setQualified(null);
  });
  const validate = () => run(async (token, signal) => {
    if (!state.draft) return;
    await validateViewDraft(nodeId, { basis_sha256: state.draft.basis_sha256, expected_revision: state.draft.revision,
      operation_id: crypto.randomUUID(), reviewer, reason, draft_id: state.draft.draft_id }, token, signal);
    await load(signal);
  });
  const qualify = () => run(async (token, signal) => {
    if (!state.draft) return;
    setQualified(await qualifyViewDraft(nodeId, state.draft.draft_id, state.draft.revision, token, signal)); await load(signal);
  });
  const reconcile = () => run(async (token, signal) => {
    const result = await reconcileViewReceipt(nodeId, receiptId, token, signal); setVerified(result.official_view_id); await load(signal);
  });
  const unsupported = !state.capabilities.initial_supported && !state.capabilities.update_supported;
  return <section className="current-view-workbench" aria-labelledby="current-view-workbench-heading">
    <div className="view-workbench-title"><div><p className="eyebrow">Server-persisted maintenance</p><h3 id="current-view-workbench-heading">Current View Workbench</h3></div><span>Web canonical access: READ ONLY</span></div>
    <div className="view-state-strip"><strong>OFFICIAL: {state.official?.view_id ?? "NO_EXISTING_VIEW"}</strong><strong>DRAFT: {state.draft ? `${state.draft.status} r${state.draft.revision}` : "NONE"}</strong><strong>PRIOR: {state.previous_official?.view_id ?? "NONE"}</strong>{state.baseline_views.length > 0 && <strong>BASELINE: {state.baseline_views.length} excluded</strong>}</div>
    <nav className="view-workbench-nav" aria-label="Current View Workbench sections"><a href="#official-state">Current View</a><a href="#view-evidence">Evidence</a><a href="#view-history">History / Changes</a><a href="#view-draft">Draft</a></nav>
    <section id="official-state"><h4>Official state</h4><p>{text(state.official?.content_json.one_line_conclusion) || "No official Current View."}</p>
      {state.official && <><dl className="metadata-grid"><div><dt>Revision</dt><dd>{state.official.version} · {state.official.view_id}</dd></div><div><dt>Change level</dt><dd>{state.official.change_level}</dd></div><div><dt>Predecessor</dt><dd>{state.official.previous_view_id ?? "NONE"}</dd></div><div><dt>Activation date</dt><dd>{state.official.confirmed_at || state.official.revision_date || "unknown"}</dd></div></dl><h5>Core structured logic</h5><ul>{list(state.official.content_json.core_logic).map((item) => <li key={item}>{item}</li>)}</ul><p><strong>Why it changed:</strong> {text(state.official.content_json.recent_change) || "No structured reason recorded."}</p></>}
      <small>Selection: status=official; {state.selection_rule}. A newer draft never changes this result.</small></section>
    <section id="view-evidence"><h4>Evidence and freshness</h4><p>{officialPrimaryCount} official primary citation(s) · {contextCount} available context-only Claim(s). Dates use business evidence dates; missing dates remain unknown.</p>
      {brokenOfficialEvidence.map((item) => <div className="review-warning" role="alert" key={item.claim_id}>EVIDENCE_NOT_FOUND — official citation {item.claim_id} is unresolved.</div>)}
      {state.available_evidence.length === 0 ? <p>No resolvable Claim evidence.</p> : state.available_evidence.map((item) => <EvidenceCard key={item.claim_id} item={{ ...item, officially_referenced: state.official?.trigger_claim_ids.includes(item.claim_id) ?? false }} primary={primary.includes(item.claim_id)} context={context.includes(item.claim_id)} onPrimary={() => toggle(primary, item.claim_id, setPrimary)} onContext={() => toggle(context, item.claim_id, setContext)} onOpenClaim={() => onOpenClaim(item.claim_id)} onOpenSource={() => onOpenSource(item.source.source_id)} />)}</section>
    <section id="view-history"><h4>History / Changes</h4><p>{state.history.map((view, index) => `${index === 0 ? "OFFICIAL" : "PRIOR_OFFICIAL"}: ${view.version} (${view.view_id})`).join(" · ") || "No official history."}</p><p>Uncertainty: {[...state.uncertainty.core_disagreements, ...state.uncertainty.assumptions_to_verify, ...state.uncertainty.knowledge_gaps].join(" · ") || "None recorded."}</p>{state.official_comparison && <details><summary>Exact official vs predecessor comparison</summary><pre>{JSON.stringify(state.official_comparison, null, 2)}</pre></details>}</section>
    <section id="view-draft"><h4>Staged draft — never official before verified external activation</h4>
      {unsupported ? <div className="review-warning" role="alert">UNSUPPORTED_NODE_TYPE — maintenance is limited to Company and Product.</div> : <>
        {state.draft?.status === "STALE" && <div className="review-warning" role="alert">BASELINE_STALE — explicit re-evaluation required.</div>}
        <div className="view-draft-form">
          <label>Mode<select aria-label="View draft mode" value={mode} onChange={(event) => setMode(event.target.value as "INITIAL" | "UPDATE")}><option value={state.official ? "UPDATE" : "INITIAL"}>{state.official ? "UPDATE" : "INITIAL"}</option></select></label>
          <label>Change level<select aria-label="View change level" value={changeLevel} onChange={(event) => setChangeLevel(event.target.value as typeof changeLevel)}>{(state.official ? ["minor", "material", "thesis"] : ["initial"]).map((value) => <option key={value}>{value}</option>)}</select></label>
          <label>Reviewer<input aria-label="View reviewer" value={reviewer} onChange={(event) => setReviewer(event.target.value)} /></label><label>Reason<input aria-label="View draft reason" value={reason} onChange={(event) => setReason(event.target.value)} /></label>
          <label>One-line conclusion<textarea aria-label="One-line conclusion" value={text(content.one_line_conclusion)} onChange={(event) => setField("one_line_conclusion", event.target.value)} /></label>
          <label>Core logic (one per line)<textarea aria-label="Core logic" value={list(content.core_logic).join("\n")} onChange={(event) => setField("core_logic", lines(event.target.value))} /></label>
          <label>Key facts (one per line)<textarea aria-label="Key facts" value={list(content.key_facts).join("\n")} onChange={(event) => setField("key_facts", lines(event.target.value))} /></label>
          <label>Investment implication<textarea aria-label="Investment implication" value={text(content.investment_implication)} onChange={(event) => setField("investment_implication", event.target.value)} /></label>
          <label>Major risks<textarea aria-label="Major risks" value={list(content.major_risks).join("\n")} onChange={(event) => setField("major_risks", lines(event.target.value))} /></label>
          <label>Core disagreements<textarea aria-label="Core disagreements" value={list(content.core_disagreements).join("\n")} onChange={(event) => setField("core_disagreements", lines(event.target.value))} /></label>
          <label>Assumptions to verify<textarea aria-label="Assumptions to verify" value={list(content.assumptions_to_verify).join("\n")} onChange={(event) => setField("assumptions_to_verify", lines(event.target.value))} /></label>
          <label>Knowledge gaps<textarea aria-label="Knowledge gaps" value={list(content.knowledge_gaps).join("\n")} onChange={(event) => setField("knowledge_gaps", lines(event.target.value))} /></label>
          <label>Key watch items<textarea aria-label="Key watch items" value={list(content.key_watch_items).join("\n")} onChange={(event) => setField("key_watch_items", lines(event.target.value))} /></label>
          <label>Recent change<textarea aria-label="Recent change" value={text(content.recent_change)} onChange={(event) => setField("recent_change", event.target.value)} /></label>
        </div>
        <div className="official-draft-compare"><strong>OFFICIAL vs DRAFT changed fields</strong><code>{changed.join(", ") || "NO_EFFECTIVE_CHANGE"}</code></div>
        <div className="review-actions"><button type="button" disabled={busy} onClick={save}>Save draft on server</button><button type="button" disabled={busy || !state.draft || state.draft.status === "STALE"} onClick={validate}>Validate existing quality contract</button><button type="button" disabled={busy || state.draft?.status !== "VALIDATED"} onClick={qualify}>Qualify for external operator</button></div>
      </>}
      {error && <div className="review-warning" role="alert">{error}</div>}
      {qualified && <div className="qualified-view-package"><h4>READY_FOR_OPERATOR_ACTION</h4><p>Adapter phase42-view-v1 · Production authorized: false</p><code>{qualified.object_id}</code><details><summary>Exact predicted View diff</summary><pre>{JSON.stringify(qualified.predicted_diff, null, 2)}</pre></details></div>}
      <div className="receipt-reconcile"><label>Registered activation receipt<input aria-label="Registered activation receipt" value={receiptId} onChange={(event) => setReceiptId(event.target.value)} /></label><button type="button" disabled={busy || !receiptId} onClick={reconcile}>Verify registered receipt</button>{verified && <strong>VERIFIED — official View {verified}</strong>}</div>
      <p>No browser activation route exists. An external operator must inspect, register, confirm and execute the exact package.</p>
    </section>
  </section>;
}
