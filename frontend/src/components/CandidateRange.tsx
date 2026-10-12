import { useState } from "react";
import { request } from "../api/workbench";

type Evidence = { evidence_ref: string; source_start: number; source_end: number; text: string; locator: string };
type Attempt = { attempt_id: string; identity: string; claims: Array<{ observation_id: string; statement: string; status: string; errors: string[] }>; evidence: Evidence[] };

export function CandidateRange({ runId, csrf, refresh }: { runId: string; csrf: string; refresh: () => Promise<void> }) {
  const [attempts, setAttempts] = useState<Attempt[]>([]);
  const [target, setTarget] = useState("");
  const [evidence, setEvidence] = useState("");
  const [span, setSpan] = useState<[number, number] | null>(null);
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const attempt = attempts.find(a => a.claims.some(c => c.observation_id === target));
  const unit = attempt?.evidence.find(e => e.evidence_ref === evidence);
  async function load() {
    setBusy(true);
    try { setAttempts((await request<{ attempts: Attempt[] }>(`/source-operations/runs/${runId}/candidate-inputs`, new AbortController().signal)).attempts); }
    catch (error) { setMessage((error as Error).message); } finally { setBusy(false); }
  }
  async function submit() {
    if (!attempt || !unit || !span || !reason.trim()) return;
    setBusy(true);
    try {
      await request(`/source-operations/runs/${runId}/attempts/${attempt.attempt_id}/candidate-range`, new AbortController().signal,
        { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf }, body: JSON.stringify({
          idempotency_key: `range-${crypto.randomUUID()}`, input_identity: attempt.identity, observation_id: target,
          evidence_ref: unit.evidence_ref, source_start: span[0], source_end: span[1], reason: reason.trim(),
        }) });
      setMessage("Exact range revision queued for a new review. Original Raw and previous authorizations are unchanged.");
      await refresh();
    } catch (error) { setMessage((error as Error).message); } finally { setBusy(false); }
  }
  return <details><summary>Correct an Evidence range</summary>
    <p>Select the exact original text. This changes the candidate Evidence selection and requires a new Packet and Human Seal.</p>
    <button disabled={busy} onClick={() => void load()}>Load candidate ranges</button>
    {attempts.length > 0 && <>
      <label>Claim <select value={target} onChange={e => { setTarget(e.target.value); setEvidence(""); setSpan(null); }}>
        <option value="">Choose a Claim</option>{attempts.flatMap(a => a.claims.map(c => <option key={c.observation_id} value={c.observation_id}>{c.statement} · {c.status}</option>))}
      </select></label>
      <label>Evidence unit <select value={evidence} onChange={e => { setEvidence(e.target.value); setSpan(null); }}>
        <option value="">Choose original Evidence</option>{attempt?.evidence.map(u => <option key={u.evidence_ref} value={u.evidence_ref}>{u.locator} · {u.evidence_ref}</option>)}
      </select></label>
      {unit && <label>Select the original range<textarea readOnly value={unit.text} onSelect={e => {
        const input = e.currentTarget;
        const lo = Array.from(unit.text.slice(0, input.selectionStart)).length;
        const hi = Array.from(unit.text.slice(0, input.selectionEnd)).length;
        setSpan(hi > lo ? [unit.source_start + lo, unit.source_start + hi] : null);
      }} /></label>}
      <label>Revision reason <input maxLength={8000} value={reason} onChange={e => setReason(e.target.value)} /></label>
      <button disabled={busy || !span || !reason.trim()} onClick={() => void submit()}>Submit exact range for new review</button>
    </>}
    {message && <p role="status">{message}</p>}
  </details>;
}
