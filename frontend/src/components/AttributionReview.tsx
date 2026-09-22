import { useEffect, useRef, useState } from "react";
import { getAttribution, mutateAttribution } from "../api/attribution";
import type { AttributionState } from "../api/attribution";
import { WorkbenchError } from "../api/workbench";
import { showNative } from "./ReviewItemDetail";

type Props = { handle: string; csrf: string };
function AttributionEditor({ handle, csrf, state, claim, refresh }: Props & { state: AttributionState;
  claim: AttributionState["claims"][number]; refresh: () => Promise<void> }) {
  const saved = state.decisions[claim.candidate_id];
  const [outcome, setOutcome] = useState(saved?.outcome ?? "");
  const [links, setLinks] = useState(saved?.links ?? []);
  const [reviewer, setReviewer] = useState(state.reviewer);
  const [reason, setReason] = useState(saved?.reason ?? "");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const pending = useRef<object | null>(null);
  const control = useRef<AbortController | null>(null);
  useEffect(() => () => control.current?.abort(), []);
  async function save() {
    if (!outcome || !reason.trim() || !(state.reviewer || reviewer).trim()) { setMessage("Choose an outcome and enter the reviewer and reason explicitly."); return; }
    if (!pending.current) pending.current = { basis_id: state.basis_id, expected_revision: state.revision, operation_id: crypto.randomUUID(),
      reviewer: state.reviewer || reviewer, reason, claim_id: claim.candidate_id, outcome, links, scope: claim.scope };
    const current = new AbortController(); control.current = current; setBusy(true); setMessage("");
    try {
      await mutateAttribution(handle, "decisions", pending.current, csrf, current.signal);
      await refresh(); pending.current = null; setUncertain(false); setMessage("Attribution saved durably.");
    } catch (error) {
      if (current.signal.aborted) return;
      if (error instanceof WorkbenchError && error.status < 500) {
        pending.current = null; setUncertain(false); setMessage(error.message);
        if (error.code === "REVISION_CONFLICT") { try { await refresh(); } catch { setMessage("Refresh failed. Your attempted attribution remains here."); } }
      } else { setUncertain(true); setMessage("Save outcome is unconfirmed. Retry the original attribution operation."); }
    } finally { if (!current.signal.aborted) setBusy(false); }
  }
  return <section aria-label="Claim attribution editor">
    <h3>{claim.candidate_id}</h3><p>{String(claim.content.statement ?? "")}</p>
    <blockquote>{String(claim.content.evidence_excerpt ?? "")}</blockquote><p>Evidence: {String(claim.content.evidence_pointer ?? "")}</p>
    <p>Native Claim scope: {claim.scope || "Not provided"}</p><p>Saved outcome: {saved?.outcome ?? "Undecided"}</p>
    {saved && <p>Saved attribution reason: {saved.reason}</p>}
    {state.status === "DRAFT" && <>
      <label>Attribution reviewer <input value={state.reviewer || reviewer} disabled={Boolean(state.reviewer) || busy || uncertain} onChange={e => setReviewer(e.target.value)} /></label>
      <label>Attribution outcome <select value={outcome} disabled={busy || uncertain} onChange={e => { setOutcome(e.target.value); setLinks([]); }}>
        <option value="">Choose explicitly</option>{["LINK", "MULTI_LINK", "NO_LINK", "DEFER"].map(value => <option key={value}>{value}</option>)}
      </select></label>
      <p>NO_LINK keeps the accepted Claim without Node links. DEFER remains unresolved and blocks qualification.</p>
      {(outcome === "LINK" || outcome === "MULTI_LINK") && <fieldset disabled={busy || uncertain}><legend>Explicit Node attributions</legend>
        {state.nodes.map(node => {
          const selected = links.find(link => link.node_id === node.node_id);
          return <div key={node.node_id}>
            <label><input type="checkbox" checked={Boolean(selected)} onChange={e => setLinks(e.target.checked ? [...links, { node_id: node.node_id, role: "" }] : links.filter(link => link.node_id !== node.node_id))} />{node.node_id} · {node.decision} · {String(node.content.proposed_name ?? "")}{node.provenance?.includes("company_material_intent") ? " · Company Material operator target (not automatically attributed)" : ""}</label>
            {selected && <label>Role for {node.node_id} <select value={selected.role} onChange={e => setLinks(links.map(link => link.node_id === node.node_id ? { ...link, role: e.target.value } : link))}>
              <option value="">Choose role explicitly</option>{Object.keys(state.roles).map(role => <option key={role}>{role}</option>)}
            </select></label>}
            <details><summary>Node identity and native context · {node.node_id}</summary><pre>{showNative(node.content)}</pre></details>
          </div>;
        })}
      </fieldset>}
      <label>Attribution reason <textarea value={reason} maxLength={8000} disabled={busy || uncertain} onChange={e => setReason(e.target.value)} /></label>
      <button type="button" disabled={busy || !outcome || !reason.trim() || links.some(link => !link.role)} onClick={() => void save()}>{uncertain ? "Retry original attribution" : "Save attribution"}</button>
    </>}
    {message && <p role="status">{message}</p>}
  </section>;
}

export function AttributionReview({ handle, csrf }: Props) {
  const [state, setState] = useState<AttributionState | null>(null);
  const [selected, setSelected] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [sealReason, setSealReason] = useState("");
  const [emptyReviewer, setEmptyReviewer] = useState("");
  const [receiptId, setReceiptId] = useState("");
  const pendingSeal = useRef<object | null>(null);
  const control = useRef<AbortController | null>(null);
  async function refresh() {
    const current = new AbortController(); control.current = current;
    const value = await getAttribution(handle, current.signal);
    if (!current.signal.aborted) { setState(value); setSelected(old => old || value.claims[0]?.candidate_id || ""); }
  }
  useEffect(() => { void refresh().catch(error => setMessage(error.message)); return () => control.current?.abort(); }, [handle]);
  async function action(name: "seal" | "qualify" | "reconcile") {
    if (!state) return;
    const current = new AbortController(); control.current = current; setBusy(true); setMessage("");
    try {
      if (name === "seal" && !pendingSeal.current) pendingSeal.current = { basis_id: state.basis_id, expected_revision: state.revision,
        operation_id: crypto.randomUUID(), reviewer: state.reviewer || emptyReviewer, reason: sealReason, confirm: confirmed };
      const body = name === "seal" ? pendingSeal.current! : { object_id: name === "qualify" ? state.sidecar?.object_id : receiptId || state.receipt?.object_id };
      await mutateAttribution(handle, name, body, csrf, current.signal);
      await refresh(); pendingSeal.current = null;
      setMessage(name === "reconcile" ? "VERIFIED — registered execution receipt and canonical post-state match." : name === "qualify" ? "Qualified — External Operator Action Required. Qualification has not changed canonical knowledge." : "Attribution sidecar sealed. Production promotion remains separate.");
    } catch (error) {
      if (error instanceof WorkbenchError && error.status < 500) pendingSeal.current = null;
      setMessage(error instanceof Error ? error.message : "Operation unavailable.");
    } finally { setBusy(false); }
  }
  const claim = state?.claims.find(row => row.candidate_id === selected);
  return <section aria-label="Attribution Workbench"><h2>Claim–Node Attribution</h2>
    <p>Native Review = Complete · Attribution Review = Separate · Production Promotion = Separate.</p>
    <p>Node support is evidence context. Every canonical Claim–Node link requires its own explicit human decision.</p>
    {state && <>
      <p>{state.status} · revision {state.revision} · {state.completed} / {state.required} accepted Claims reviewed</p>
      <button type="button" disabled={busy} onClick={() => void refresh().catch(error => setMessage(error.message))}>Refresh attribution and receipts</button>
      <section aria-label="Accepted Claims">{state.claims.map(row => <button key={row.candidate_id} onClick={() => setSelected(row.candidate_id)}>{row.candidate_id} · {state.decisions[row.candidate_id]?.outcome ?? "Undecided"}</button>)}</section>
      {claim && <AttributionEditor key={claim.candidate_id} handle={handle} csrf={csrf} state={state} claim={claim} refresh={refresh} />}
      <details><summary>Native attribution roles</summary><pre>{showNative(state.roles)}</pre></details>
      <details><summary>Attribution audit history</summary><pre>{showNative(state.audit)}</pre></details>
      {state.status === "DRAFT" && <section aria-label="Attribution seal confirmation">
        <h3>Seal separate attribution sidecar</h3><p>{state.completed} / {state.required} outcomes saved. DEFER will block qualification. Sealing does not authorize Production changes.</p>
        {!state.reviewer && <label>Attribution seal reviewer <input value={emptyReviewer} onChange={e => setEmptyReviewer(e.target.value)} /></label>}
        <label>Attribution seal reason <textarea value={sealReason} onChange={e => setSealReason(e.target.value)} /></label>
        <label><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} /> I confirm immutable attribution sealing.</label>
        <button type="button" disabled={busy || !confirmed || !sealReason.trim() || !(state.reviewer || emptyReviewer).trim() || state.completed !== state.required} onClick={() => void action("seal")}>Seal attribution sidecar</button>
      </section>}
      {state.sidecar && <><p>Attribution sidecar: {state.sidecar.object_id}</p><button type="button" disabled={busy} onClick={() => void action("qualify")}>Run shadow qualification</button></>}
      {state.qualification && <section aria-label="Qualified operational handoff"><h3>Qualified — External Operator Action Required</h3>
        <p>{state.qualification.adapter_version} · {state.qualification.object_id}</p><p>Baseline SHA-256: {state.qualification.baseline_sha256}</p>
        <p>{state.qualification.operator_action}</p><p>Private Source metadata values are withheld here and bound by hashes; the external operator must inspect complete canonical rows before authorization.</p>
        <details open><summary>Exact predicted changes · {state.qualification.diff_id}</summary><pre>{showNative(state.qualification.changes)}</pre></details>
        <details><summary>Generic shadow qualification</summary><pre>{showNative(state.qualification.shadow_validation)}</pre></details>
        <label>Registered execution receipt ID <input value={receiptId || state.receipt?.object_id || ""} onChange={e => setReceiptId(e.target.value)} /></label>
        <button type="button" disabled={busy || !(receiptId || state.receipt)} onClick={() => void action("reconcile")}>Verify registered execution receipt</button>
        {state.receipt && <><h3>Verified external execution receipt</h3><pre>{showNative(state.receipt)}</pre></>}
      </section>}
    </>}
    {message && <p role="status">{message}</p>}
  </section>;
}
