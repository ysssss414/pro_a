import { useState } from "react";
import { request } from "../api/workbench";

type Batch = {
  proposal_id: string; approved: boolean; counts: Record<string, number>; status: string;
  binding_matches: boolean; current_revision: number; advice: Record<string, { items: Array<{ candidate_id: string; judgment: string; reason: string }> }>;
  evidence: unknown;
  proposal: { kind: string; binding: object; expected_revision: number; reason: string; items: Array<Record<string, unknown>> };
};

export function ReviewBatch({ handle, csrf, refresh }: { handle: string; csrf: string; refresh: () => Promise<unknown> }) {
  const [id, setId] = useState(new URLSearchParams(window.location.search).get("batch") ?? "");
  const [batch, setBatch] = useState<Batch | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [result, setResult] = useState("");
  const [sidecar, setSidecar] = useState("");
  const base = `/reviews/${encodeURIComponent(handle)}`;
  const load = async () => {
    setBusy(true); setError(""); setBatch(null); setConfirmed(false); setResult(""); setSidecar("");
    try { setBatch(await request<Batch>(`${base}/batches/${encodeURIComponent(id)}`, new AbortController().signal)); }
    catch { setError("Cannot load this frozen proposal. Check its ID and sign-in session."); }
    finally { setBusy(false); }
  };
  const approve = async () => {
    if (!batch || !confirmed) return;
    setBusy(true); setError("");
    try {
      const saved = await request<{ status: string; result: { sidecar_id?: string } }>(`${base}/batch-approval`, new AbortController().signal, {
        method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
        body: JSON.stringify({ proposal_id: batch.proposal_id, confirm: true }),
      });
      setResult(saved.status); setSidecar(saved.result.sidecar_id ?? ""); setConfirmed(false); await refresh();
    } catch { setError("Batch did not complete. Saved native operations remain recorded. Resume only this exact proposal; drift requires a new review."); }
    finally { setBusy(false); }
  };
  const qualify = async () => {
    setBusy(true); setError("");
    try {
      await request(`/attribution/${encodeURIComponent(handle)}/qualify`, new AbortController().signal, {
        method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
        body: JSON.stringify({ object_id: sidecar }),
      });
      setResult("SHADOW_QUALIFIED");
    } catch { setError("Shadow qualification failed. The sealed review is preserved; retry after checking the Workbench."); }
    finally { setBusy(false); }
  };
  const disagreements = batch?.advice.A.items.filter(a => batch.advice.B.items.find(b => b.candidate_id === a.candidate_id)?.judgment !== a.judgment) ?? [];
  const drift = batch && (!batch.binding_matches || (!batch.approved && batch.current_revision !== batch.proposal.expected_revision));
  return <section aria-label="Frozen batch approval">
    <h2>整批人工确认 / Frozen batch approval</h2>
    <label>Proposal SHA-256 <input disabled={busy} value={id} onChange={e => { setId(e.target.value); setBatch(null); setConfirmed(false); setSidecar(""); setResult(""); }} /></label>
    <button disabled={busy || !/^[a-f0-9]{64}$/.test(id)} onClick={() => void load()}>查看冻结方案</button>
    {error && <p role="alert">{error}</p>}
    {result && <p role="status">{result} · Canonical unchanged</p>}
    {sidecar && <button disabled={busy || result === "SHADOW_QUALIFIED"} onClick={() => void qualify()}>生成 Shadow Qualification（不执行 Apply）</button>}
    {batch && <>
      <p>{batch.proposal.kind} · {batch.proposal_id} · revision {batch.proposal.expected_revision}</p>
      <p>{Object.entries(batch.counts).map(([name, count]) => `${name}: ${count}`).join(" · ")}</p>
      <p>A/B 分歧：{disagreements.length}。执行身份为本地操作者登记，未经平台证明独立性。</p>
      <p>{batch.proposal.reason}</p>
      <table><thead><tr><th>Candidate / Claim</th><th>决定、理由及精确目标</th></tr></thead><tbody>
        {batch.proposal.items.map(item => <tr key={String(item.candidate_id ?? item.claim_id)}><td>{String(item.candidate_id ?? item.claim_id)}</td><td><pre>{JSON.stringify(item, null, 2)}</pre></td></tr>)}
      </tbody></table>
      <details><summary>全部 A/B 意见及理由</summary><pre>{JSON.stringify(batch.advice, null, 2)}</pre></details>
      <details><summary>候选证据与实体身份</summary><pre>{JSON.stringify(batch.evidence, null, 2)}</pre></details>
      <details><summary>冻结 Packet / Context / Basis</summary><pre>{JSON.stringify(batch.proposal.binding, null, 2)}</pre></details>
      <p>批准将逐项保存本方案并执行不可逆 Seal。中断时保留已保存操作，可恢复同一方案。Seal 后决定不可修改；不会执行 Canonical Apply。</p>
      {drift && <p role="alert">方案身份或 revision 已变化，禁止批准。</p>}
      <label><input type="checkbox" checked={confirmed} disabled={busy || !!drift || !!result} onChange={e => setConfirmed(e.target.checked)} />我已查看全部决定、A/B 分歧、证据、精确 Node ID 与角色，批准此完整方案及 Seal。</label>
      <button disabled={busy || !confirmed || !!drift || !!result} onClick={() => void approve()}>{batch.approved ? "恢复同一批准方案并 Seal" : "批准整批并 Seal"}</button>
    </>}
  </section>;
}
