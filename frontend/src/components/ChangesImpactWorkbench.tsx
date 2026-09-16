import { useEffect, useMemo, useState } from "react";

import {
  getImpactChanges,
  getSession,
  saveImpactAttention,
  type DirectImpactItem,
  type ImpactChange,
  type ImpactChangesResult,
  type ImpactAttentionState,
} from "../api/workbench";

const reasonLabels: Record<string, string> = {
  SOURCE_CONTAINS_CLAIM: "Claim is recorded from this Source",
  CLAIM_ATTRIBUTED_TO_NODE: "Claim has explicit Node attribution",
  NODE_HAS_OFFICIAL_VIEW: "Explicitly attributed Node has an official Current View",
  CLAIM_CITED_BY_VIEW: "Official Current View explicitly cites this Claim",
  STAGED_VIEW_DEPENDENCY: "Staged View draft explicitly uses this Claim",
  RECORDED_CONTRADICTION: "Recorded contradiction",
  TEMPORAL_SUPERSESSION: "Recorded temporal update",
  RECORDED_RELATION_EVIDENCE: "Recorded relation evidence",
};

const outcomeLabels = {
  NO_CHANGE: "No Change",
  MINOR: "Minor",
  MATERIAL: "Material",
  THESIS: "Thesis",
} as const;

function itemTitle(item: DirectImpactItem) {
  const target = item.path_steps[item.path_steps.length - 1];
  return target?.label || item.target_id;
}

function pathText(item: DirectImpactItem) {
  return item.path_steps.map((step) => `${step.object_type}: ${step.label}`).join(" → ");
}

function ImpactCard({ item, selected, onSelect, onOpenOfficialView }: {
  item: DirectImpactItem;
  selected: boolean;
  onSelect: () => void;
  onOpenOfficialView: (nodeId: string, viewId: string) => void;
}) {
  const node = item.path_steps.find((step) => step.object_type === "NODE");
  const canOpen = item.target_type === "VIEW" && node;
  return (
    <article className={`direct-impact-card ${selected ? "is-selected" : ""}`}>
      <button type="button" className="impact-card-select" onClick={onSelect} aria-pressed={selected}>
        <span className="impact-card-kicker">{item.target_type.replace("_", " ")} · {item.official_or_staged}</span>
        <strong>{itemTitle(item)}</strong>
        <span>{reasonLabels[item.reason_code] ?? item.reason_code}</span>
        <small>{pathText(item)}</small>
      </button>
      <div className="impact-card-meta">
        {item.attribution_role && <span>Attribution: {item.attribution_role}</span>}
        <span>Status: {item.current_status || "unknown"}</span>
        {!item.is_current_impact && <span className="noncurrent-chip">Provenance only · not current Impact</span>}
        {item.attention_state && <span>Attention: {outcomeLabels[item.attention_state.outcome]} · {item.attention_state.status}</span>}
      </div>
      {canOpen && <button type="button" onClick={() => onOpenOfficialView(node.object_id, item.target_id)}>Open official View</button>}
    </article>
  );
}

function ItemGroup({ title, items, selectedId, onSelect, onOpenOfficialView, empty }: {
  title: string;
  items: DirectImpactItem[];
  selectedId: string | null;
  onSelect: (item: DirectImpactItem) => void;
  onOpenOfficialView: (nodeId: string, viewId: string) => void;
  empty: string;
}) {
  return (
    <section className="impact-workbench-section">
      <div className="section-title-row"><h2>{title}</h2><span className="count-label">{items.length}</span></div>
      {items.length === 0 ? <p className="empty-inline">{empty}</p> : items.map((item) => (
        <ImpactCard key={item.impact_id} item={item} selected={item.impact_id === selectedId}
          onSelect={() => onSelect(item)} onOpenOfficialView={onOpenOfficialView} />
      ))}
    </section>
  );
}

function AttentionEditor({ item, csrf, onSaved }: {
  item: DirectImpactItem;
  csrf: string;
  onSaved: (state: ImpactAttentionState) => void;
}) {
  const [outcome, setOutcome] = useState<keyof typeof outcomeLabels | "">(item.attention_state?.outcome ?? "");
  const [reviewer, setReviewer] = useState(item.attention_state?.reviewer ?? "");
  const [reason, setReason] = useState(item.attention_state?.reason ?? "");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    setOutcome(item.attention_state?.outcome ?? "");
    setReviewer(item.attention_state?.reviewer ?? "");
    setReason(item.attention_state?.reason ?? "");
    setMessage(null);
  }, [item.impact_id, item.attention_state]);

  const save = async () => {
    if (!outcome || !reviewer.trim() || !reason.trim()) return;
    const controller = new AbortController();
    setBusy(true);
    setMessage(null);
    try {
      const result = await saveImpactAttention(item.impact_id, {
        snapshot_id: item.snapshot_id,
        expected_revision: item.attention_state?.revision ?? 0,
        operation_id: crypto.randomUUID(),
        reviewer: reviewer.trim(),
        reason: reason.trim(),
        outcome,
      }, csrf, controller.signal);
      onSaved(result.attention_state);
      setMessage("Attention outcome saved in Workbench state.");
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="impact-workbench-section attention-editor">
      <h2>Attention State</h2>
      <p>Actor-recorded Workbench state only. It does not change canonical knowledge or an official View.</p>
      {item.attention_state?.status === "STALE" && <p className="module-error">This outcome belongs to an older evidence snapshot.</p>}
      <fieldset><legend>Human impact outcome</legend>{Object.entries(outcomeLabels).map(([value, label]) => (
        <label key={value}><input type="radio" name="impact-outcome" value={value} checked={outcome === value}
          onChange={() => setOutcome(value as keyof typeof outcomeLabels)} />{label}</label>
      ))}</fieldset>
      <label>Reviewer<input value={reviewer} onChange={(event) => setReviewer(event.target.value)} /></label>
      <label>Reason<textarea value={reason} onChange={(event) => setReason(event.target.value)} /></label>
      <button type="button" disabled={busy || !outcome || !reviewer.trim() || !reason.trim()} onClick={() => void save()}>
        {busy ? "Saving…" : "Save attention outcome"}
      </button>
      {message && <p role="status">{message}</p>}
    </section>
  );
}

export function ChangesImpactWorkbench({ onOpenOfficialView }: {
  onOpenOfficialView: (nodeId: string, viewId: string) => void;
}) {
  const [data, setData] = useState<ImpactChangesResult | null>(null);
  const [selectedSource, setSelectedSource] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [csrf, setCsrf] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    Promise.all([getImpactChanges(controller.signal), getSession(controller.signal)])
      .then(([result, session]) => {
        setData(result);
        setCsrf(session.csrf_token ?? "");
        const first = result.changes[0] ?? null;
        setSelectedSource((current) => current && result.changes.some((row) => row.source.source_id === current) ? current : first?.source.source_id ?? null);
        setSelectedId((current) => current && result.items.some((item) => item.impact_id === current) ? current : first?.items[0]?.impact_id ?? null);
        setError(null);
      })
      .catch((caught) => {
        if ((caught as Error).name !== "AbortError") setError((caught as Error).message);
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, []);

  const change: ImpactChange | null = data?.changes.find((row) => row.source.source_id === selectedSource) ?? null;
  const selected = change?.items.find((item) => item.impact_id === selectedId) ?? change?.items[0] ?? null;
  const directlyAffected = useMemo(() => change?.items.filter((item) => ["CLAIM", "NODE", "RELATION"].includes(item.target_type)) ?? [], [change]);
  const official = useMemo(() => change?.items.filter((item) => item.official_or_staged === "OFFICIAL") ?? [], [change]);
  const staged = useMemo(() => change?.items.filter((item) => item.official_or_staged === "STAGED") ?? [], [change]);
  const semantic = useMemo(() => change?.items.filter((item) => ["RECORDED_CONTRADICTION", "TEMPORAL_SUPERSESSION"].includes(item.reason_code) ||
    ["CATEGORICAL", "HISTORICAL"].includes(item.official_or_staged)) ?? [], [change]);

  const selectChange = (row: ImpactChange) => {
    setSelectedSource(row.source.source_id);
    setSelectedId(row.items[0]?.impact_id ?? null);
  };
  const updateAttention = (state: ImpactAttentionState) => {
    setData((current) => current && ({ ...current,
      items: current.items.map((item) => item.impact_id === selected?.impact_id ? { ...item, attention_state: state } : item),
      changes: current.changes.map((row) => ({ ...row, items: row.items.map((item) =>
        item.impact_id === selected?.impact_id ? { ...item, attention_state: state } : item) })),
    }));
  };

  if (loading) return <main className="impact-workbench"><p>Loading deterministic Impact paths…</p></main>;
  if (error) return <main className="impact-workbench"><div className="module-error" role="alert"><strong>Changes & Impact unavailable.</strong><p>{error}</p><p>Sign in through Review and prepare the Stage 4 Workbench schema.</p></div></main>;
  return (
    <main className="impact-workbench">
      <header className="impact-workbench-header">
        <div><span className="eyebrow">Deterministic attention routing</span><h1>Changes &amp; Impact</h1></div>
        <p>Only directly recorded evidence paths are shown. No economic inference, recommendation, score, or automatic View update is produced.</p>
      </header>
      <div className="impact-layout">
        <aside className="impact-change-list">
          <h2>Changes</h2>
          {data?.changes.map((row) => <button type="button" key={row.source.source_id}
            className={row.source.source_id === selectedSource ? "is-selected" : ""} onClick={() => selectChange(row)}>
            <strong>{row.source.title}</strong><span>{row.claim_count} Claims · {row.items.length} paths</span>
            <small>Evidence date: {row.evidence_date}</small>
          </button>)}
          {data?.changes.length === 0 && <p className="empty-inline">No recorded Sources.</p>}
        </aside>
        <div className="impact-detail-column">
          {change && <div className="impact-change-summary"><div><span>Origin</span><strong>{change.source.title}</strong></div>
            <div><span>Current status</span><strong>{change.current_status}</strong></div>
            <div><span>Snapshot</span><code>{change.snapshot_id.slice(0, 12)}</code></div></div>}
          <ItemGroup title="Directly Affected" items={directlyAffected} selectedId={selected?.impact_id ?? null}
            onSelect={(item) => setSelectedId(item.impact_id)} onOpenOfficialView={onOpenOfficialView} empty="No directly affected recorded object." />
          <ItemGroup title="Official Views" items={official} selectedId={selected?.impact_id ?? null}
            onSelect={(item) => setSelectedId(item.impact_id)} onOpenOfficialView={onOpenOfficialView} empty="No official Current View directly depends on this change." />
          <ItemGroup title="Staged View Work" items={staged} selectedId={selected?.impact_id ?? null}
            onSelect={(item) => setSelectedId(item.impact_id)} onOpenOfficialView={onOpenOfficialView} empty="No staged View draft directly depends on this change." />
          <section className="impact-workbench-section evidence-path-section">
            <h2>Evidence Paths</h2>
            {selected ? <><p className="impact-reason">Why this is here: {reasonLabels[selected.reason_code] ?? selected.reason_code}</p>
              <ol>{selected.path_steps.map((step) => <li key={`${step.object_type}:${step.object_id}`}><span>{step.object_type}</span><strong>{step.label}</strong><code>{step.object_id}</code><small>{step.status}</small></li>)}</ol>
              <p>Relationships: {selected.relationship_types.join(" → ")}</p></> : <p className="empty-inline">Select a path to inspect it.</p>}
          </section>
          <ItemGroup title="Contradictions / Temporal" items={semantic} selectedId={selected?.impact_id ?? null}
            onSelect={(item) => setSelectedId(item.impact_id)} onOpenOfficialView={onOpenOfficialView} empty="No recorded contradiction or temporal relationship. Absence does not confirm truth." />
          {selected && csrf && <AttentionEditor key={selected.impact_id} item={selected} csrf={csrf} onSaved={updateAttention} />}
        </div>
      </div>
    </main>
  );
}
