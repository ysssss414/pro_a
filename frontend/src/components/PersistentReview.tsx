import { useEffect, useRef, useState } from "react";
import { mutateReview, WorkbenchError } from "../api/workbench";
import type { DecisionOperation, NativeItem, PersistentReview as Review, ReviewOperation, ReviewPacket, ReviewRow } from "../api/workbench";
import { ReviewItemDetail, showNative } from "./ReviewItemDetail";

type Props = { packet: ReviewPacket; review: Review; csrf: string; refresh: () => Promise<ReviewPacket> };
const queueNames: Record<string, string> = { all: "All native rows", needs_review: "Needs Review", high_attention: "Warnings",
  entity_resolution: "Entity Resolution", parent_placement: "Parent Placement", deferred: "Deferred", completed: "Completed",
  recently_decided: "Recently Decided", excluded: "Excluded / Non-reviewable" };

function ReviewEditor({ packet, review, csrf, refresh, row, item, reviewer }: Props & { row: ReviewRow; item: NativeItem; reviewer: string }) {
  const [decision, setDecision] = useState(row.state?.decision ?? "");
  const [reason, setReason] = useState(row.state?.reason ?? "");
  const [target, setTarget] = useState(row.state?.target_node_id ?? "");
  const [undoReason, setUndoReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [conflict, setConflict] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const pending = useRef<{ action: "decisions" | "undo"; body: object } | null>(null);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);

  async function submit(action: "decisions" | "undo") {
    if (!reviewer.trim() || (action === "decisions" ? !reason.trim() || !decision : !undoReason.trim())) {
      setMessage("Enter an explicit reviewer, decision and reason."); return;
    }
    const base: ReviewOperation = { basis_id: review.basis_id, expected_revision: review.revision,
      operation_id: crypto.randomUUID(), reviewer, reason: action === "decisions" ? reason : undoReason };
    if (!pending.current) pending.current = { action, body: action === "decisions"
      ? { ...base, candidate_id: item.candidate_id, decision, target_node_id: decision === "REUSE" ? target : "" } satisfies DecisionOperation
      : { ...base, candidate_id: item.candidate_id, event_id: row.undo_event_id } };
    const attempted = pending.current;
    const current = new AbortController();
    controller.current = current;
    setBusy(true); setMessage("");
    try {
      await mutateReview(packet.artifact_id, attempted.action, attempted.body, csrf, current.signal);
      const restored = await refresh();
      if (current.signal.aborted) return;
      const state = restored.review?.enabled ? restored.review.rows.find(entry => entry.candidate_id === item.candidate_id)?.state : null;
      setDecision(state?.decision ?? ""); setReason(state?.reason ?? ""); setTarget(state?.target_node_id ?? "");
      setUndoReason(""); setConflict(false); setUncertain(false); pending.current = null;
      setMessage("Saved durably. Audit history and progress are refreshed.");
    } catch (error) {
      if (current.signal.aborted) return;
      if (error instanceof WorkbenchError && error.status < 500) {
        setMessage(error.message);
        pending.current = null; setUncertain(false);
        if (error.code === "REVISION_CONFLICT" || error.code === "ALREADY_SEALED") {
          setConflict(true);
          try { await refresh(); } catch { setMessage("Unable to refresh authoritative state. Your attempted input remains here."); }
        }
      } else {
        setUncertain(true);
        setMessage("The save outcome is not yet confirmed. Retry the original operation without changing its identity.");
      }
    } finally { if (!current.signal.aborted) setBusy(false); }
  }

  return <div className="review-editor">
    <h3>Current saved decision</h3>
    <p>{row.state ? `${row.state.decision} · ${row.state.reviewer} · revision ${row.state.revision}` : "Undecided — no advisory decision selected."}</p>
    {row.state && <p>Saved reason: {row.state.reason}</p>}
    {row.nonpromotable && <p>Native nonpromotable state: {row.decision_effect}</p>}
    {Object.entries(row.blocked_decisions).length > 0 && <details><summary>Unavailable actions and native constraints</summary><pre>{showNative(row.blocked_decisions)}</pre></details>}
    {review.status !== "SEALED" && <>
      <form onSubmit={event => { event.preventDefault(); void submit("decisions"); }} onKeyDown={event => {
        if (event.ctrlKey && event.key === "Enter") { event.preventDefault(); event.currentTarget.requestSubmit(); }
      }}>
        <label>Decision <select value={decision} disabled={busy || uncertain} required onChange={event => { setDecision(event.target.value); setTarget(""); }}>
          <option value="">Choose explicitly</option>
          {decision && !row.available_decisions.includes(decision) && <option value={decision} disabled>{decision} (attempted; currently unavailable)</option>}
          {row.available_decisions.map(action => <option key={action} value={action}>{action}</option>)}
        </select></label>
        {decision === "REUSE" && <label>Exact reuse target <select required value={target} disabled={busy || uncertain} onChange={event => setTarget(event.target.value)}>
          <option value="">Select the exact native target</option>{row.reuse_target && <option value={row.reuse_target}>{row.reuse_target}</option>}
        </select></label>}
        <label>Decision reason <textarea required maxLength={8000} value={reason} disabled={busy || uncertain} onChange={event => setReason(event.target.value)} /></label>
        <button type="submit" disabled={busy || uncertain || !row.available_decisions.includes(decision)}>{conflict ? "Retry with refreshed revision" : "Save decision"}</button>
        <span> Ctrl+Enter saves this explicit decision.</span>
      </form>
      {row.undo_event_id !== null && <div>
        <label>Undo reason <input value={undoReason} disabled={busy || uncertain} onChange={event => setUndoReason(event.target.value)} /></label>
        <button type="button" disabled={busy || uncertain || !undoReason.trim()} onClick={() => void submit("undo")}>Undo last Save</button>
      </div>}
      {uncertain && <button type="button" disabled={busy} onClick={() => void submit(pending.current?.action ?? "decisions")}>Retry original operation</button>}
    </>}
    {message && <p role="status">{message}</p>}
  </div>;
}

export function PersistentReview(props: Props) {
  const { packet, review, csrf, refresh } = props;
  const [queue, setQueue] = useState("all");
  const [selected, setSelected] = useState(packet.items[0]?.candidate_id ?? "");
  const [reviewer, setReviewer] = useState(review.reviewer);
  const [confirmation, setConfirmation] = useState<number | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [sealReason, setSealReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const pendingSeal = useRef<ReviewOperation & { confirm: boolean } | null>(null);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  useEffect(() => { if (review.reviewer) setReviewer(review.reviewer); }, [review.reviewer]);
  const visible = queue === "excluded" ? [] : review.rows.filter(row => queue === "all" || row.queues.includes(queue));
  if (queue === "recently_decided") visible.sort((a, b) => (b.state?.revision ?? 0) - (a.state?.revision ?? 0) || a.candidate_id.localeCompare(b.candidate_id));
  const item = packet.items.find(row => row.candidate_id === selected);
  const row = review.rows.find(row => row.candidate_id === selected);

  async function completion(seal: boolean) {
    const current = new AbortController(); controller.current = current;
    setBusy(true); setMessage("");
    try {
      if (seal) {
        if (!confirmed || confirmation === null || !sealReason.trim()) return;
        if (!pendingSeal.current) pendingSeal.current = { basis_id: review.basis_id, expected_revision: confirmation,
          operation_id: crypto.randomUUID(), reviewer, reason: sealReason, confirm: true };
        await mutateReview(packet.artifact_id, "seal", pendingSeal.current, csrf, current.signal);
        await refresh();
        pendingSeal.current = null; setConfirmation(null); setQueue("all");
        setMessage("Human review sealed. Production is unchanged; no promotion is authorized.");
      } else {
        const result = await mutateReview(packet.artifact_id, "validate", { basis_id: review.basis_id, expected_revision: review.revision }, csrf, current.signal);
        setConfirmation(result.revision); setConfirmed(false); setSealReason("");
        setMessage("Native completion validation passed. Inspect the confirmation before sealing.");
      }
    } catch (error) {
      if (current.signal.aborted) return;
      setMessage(error instanceof WorkbenchError ? error.message : "Completion outcome is unconfirmed. Retrying uses the same seal operation identity.");
      if (error instanceof WorkbenchError && error.status < 500) {
        pendingSeal.current = null;
        if (error.code === "REVISION_CONFLICT" || error.code === "ALREADY_SEALED") {
          setConfirmation(null);
          try { await refresh(); } catch { setMessage("Unable to refresh review state. Retry after restoring the application."); }
        }
      }
    } finally { if (!current.signal.aborted) setBusy(false); }
  }

  return <section aria-label="Persistent Review Workbench">
    <h2>Persistent Review Workbench · {review.status}</h2>
    <p>Review {review.review_id} · revision {review.revision}</p>
    <label>Reviewer <input value={reviewer} maxLength={200} disabled={Boolean(review.reviewer)} onChange={event => setReviewer(event.target.value)} /></label>
    <section aria-label="Review progress"><h3>Saved review progress</h3>
      <p>{review.progress.completed} / {review.progress.required} required rows completed · {review.progress.remaining} remaining</p>
      <p>{review.progress.excluded} excluded · {review.progress.deferred} deferred · {review.progress.nonpromotable} nonpromotable · {review.progress.invalid} invalid · {review.progress.dependency_blocked} parent CREATE blocked · {review.progress.warnings} warnings</p>
    </section>
    <label>Review queue <select value={queue} onChange={event => {
      const next = event.target.value; setQueue(next);
      setSelected(next === "excluded" ? "" : review.rows.find(entry => next === "all" || entry.queues.includes(next))?.candidate_id ?? "");
    }}>{Object.entries(queueNames).map(([key, name]) => <option key={key} value={key}>{name}</option>)}</select></label>
    <div className="review-items">
      <section aria-label="Review queue items">
        {queue === "excluded" ? <><p>These native audit-only relations cannot be decided.</p><pre>{showNative(packet.excluded_relation_inventory.candidate_ids)}</pre></>
          : visible.length === 0 ? <p>No rows in this queue.</p> : visible.map(entry => {
            const native = packet.items.find(item => item.candidate_id === entry.candidate_id)!;
            return <button type="button" key={entry.candidate_id} aria-pressed={selected === entry.candidate_id} onClick={() => setSelected(entry.candidate_id)}>{native.candidate_type} · {entry.candidate_id} · {entry.state?.decision ?? "Undecided"}</button>;
          })}
        {visible.length > 1 && <button type="button" onClick={() => setSelected(visible[(visible.findIndex(entry => entry.candidate_id === selected) + 1) % visible.length].candidate_id)}>Next item</button>}
      </section>
      {item && row && <ReviewItemDetail item={item} persistent>
        <ReviewEditor key={item.candidate_id} {...props} row={row} item={item} reviewer={reviewer} />
      </ReviewItemDetail>}
    </div>
    <section aria-label="Review audit history"><h3>Append-only review audit</h3>
      {review.audit.length === 0 ? <p>No human decisions have been saved.</p> : <ol>{review.audit.map(event => <li key={event.event_id}>
        <strong>{event.event_type} · revision {event.revision} · {event.candidate_id ?? "Review seal"}</strong>
        <p>{event.reviewer} ({event.actor}) · {event.created_at} · {event.reason}</p>
        <details><summary>Old and new state · event {event.event_id}</summary><pre>{showNative({ old_state: event.old_state, new_state: event.new_state })}</pre></details>
      </li>)}</ol>}
    </section>
    {review.status === "DRAFT" && <button type="button" disabled={busy} onClick={() => void completion(false)}>Validate completion</button>}
    {message && <p role="status">{message}</p>}
    {confirmation !== null && review.status === "DRAFT" && <section aria-label="Seal confirmation">
      <h3>Confirm review-only sealing</h3><p>Packet: {packet.packet_id} · validated revision {confirmation}</p>
      <p>{review.progress.completed} / {review.progress.required} completed · {review.progress.remaining} remaining · {review.progress.invalid} invalid</p>
      <p>{review.progress.deferred} deferred · {review.progress.nonpromotable} nonpromotable · {review.progress.warnings} warnings</p>
      <p>Sealing makes this human review immutable. Sealing does not modify Production. Sealing does not authorize promotion.</p>
      <label>Seal reason <textarea value={sealReason} maxLength={8000} onChange={event => setSealReason(event.target.value)} /></label>
      <label><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} /> I confirm review-only sealing and understand that it cannot be undone.</label>
      <button type="button" disabled={busy || !confirmed || !sealReason.trim()} onClick={() => void completion(true)}>Confirm seal</button>
    </section>}
    {review.sealed && <section aria-label="Sealed review result"><h3>Sealed result · read-only</h3>
      <p>Human review is complete. No qualification or promotion authority was created.</p>
      <pre>{showNative(review.sealed)}</pre>
    </section>}
  </section>;
}
