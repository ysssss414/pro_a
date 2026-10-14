import { useEffect, useState } from "react";
import { request } from "../api/workbench";

type Batch = {
  proposal_id: string; approved: boolean; counts: Record<string, number>; status: string;
  binding_matches: boolean; current_revision: number; advice: Record<string, { items: Array<{ candidate_id: string; judgment: string; reason: string }> }>;
  evidence: unknown;
  proposal: { kind: string; binding: { review_policy?: Policy }; expected_revision: number; reason: string; items: Array<Record<string, unknown>> };
};
type Policy = { version: string; mode: string; sha256: string };
type PolicyContext = { policy: Policy | null; binding: Record<string, string> };

export function ReviewBatch({ handle, csrf, refresh }: { handle: string; csrf: string; refresh: () => Promise<unknown> }) {
  const [id, setId] = useState(new URLSearchParams(window.location.search).get("batch") ?? "");
  const [batch, setBatch] = useState<Batch | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [result, setResult] = useState("");
  const [sidecar, setSidecar] = useState("");
  const [policy, setPolicy] = useState<PolicyContext | null>(null);
  const [mode, setMode] = useState("SINGLE_MODEL_HUMAN");
  const [policyConfirmed, setPolicyConfirmed] = useState(false);
  useEffect(() => { setPolicy(null); setBatch(null); setConfirmed(false); setPolicyConfirmed(false); setResult(""); setSidecar(""); }, [handle]);
  const base = `/reviews/${encodeURIComponent(handle)}`;
  const loadPolicy = async () => {
    setBusy(true); setError(""); setPolicyConfirmed(false);
    try { setPolicy(await request<PolicyContext>(`${base}/policy`, new AbortController().signal)); }
    catch { setError("无法读取冻结审核策略，请检查 Packet 与登录状态。"); }
    finally { setBusy(false); }
  };
  const selectPolicy = async () => {
    if (!policy || policy.policy || !policyConfirmed) return;
    setBusy(true); setError("");
    try {
      const selected = await request<Policy>(`${base}/policy`, new AbortController().signal, {
        method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
        body: JSON.stringify({ mode, binding: policy.binding, confirm: true }),
      });
      setPolicy({ ...policy, policy: selected }); setPolicyConfirmed(false);
    } catch { setError("策略未保存：已有意见、决定或冻结身份变化时禁止选择或切换模式。"); }
    finally { setBusy(false); }
  };
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
  const disagreements = batch?.advice.B ? batch.advice.A.items.filter(a => batch.advice.B.items.find(b => b.candidate_id === a.candidate_id)?.judgment !== a.judgment) : [];
  const unresolved = new Set(Object.values(batch?.advice ?? {}).flatMap(a => a.items.filter(i => i.judgment !== "SUPPORTED").map(i => i.candidate_id)));
  const drift = batch && (!batch.binding_matches || (!batch.approved && batch.current_revision !== batch.proposal.expected_revision));
  return <section aria-label="Frozen batch approval">
    <h2>整批人工确认 / Frozen batch approval</h2>
    <button disabled={busy} onClick={() => void loadPolicy()}>查看 / 选择审核模式</button>
    {policy && <div>
      <p>当前策略：{policy.policy ? `${policy.policy.mode} · ${policy.policy.version} · ${policy.policy.sha256}` : "未显式选择，保留历史 DUAL_MODEL_HUMAN 规则"}</p>
      {!policy.policy && <>
        <label>审核模式 <select disabled={busy} value={mode} onChange={e => { setMode(e.target.value); setPolicyConfirmed(false); }}>
          <option value="SINGLE_MODEL_HUMAN">单 AI + 人工（推荐）</option>
          <option value="DUAL_MODEL_HUMAN">双 AI + 人工（增强审核）</option>
        </select></label>
        <p>仅允许在 DRAFT / Revision 0、尚无意见和提案时选择。选择绑定当前 Packet 与 Context，之后不可静默切换。</p>
        <label><input type="checkbox" checked={policyConfirmed} disabled={busy} onChange={e => setPolicyConfirmed(e.target.checked)} />我确认此 Packet 使用所选审核模式。</label>
        <button disabled={busy || !policyConfirmed} onClick={() => void selectPolicy()}>确认审核模式</button>
      </>}
    </div>}
    <p>AI 检查原文支持性，包括主体、时间、数字单位、限定条件、预测、归属与因果推断。人工准入只积累可追溯线索：SOURCE_ASSERTION / UNVERIFIED / CLUE_ONLY，不确认现实真实性或发布官方 Current View。</p>
    <label>Proposal SHA-256 <input disabled={busy} value={id} onChange={e => { setId(e.target.value); setBatch(null); setConfirmed(false); setSidecar(""); setResult(""); }} /></label>
    <button disabled={busy || !/^[a-f0-9]{64}$/.test(id)} onClick={() => void load()}>查看冻结方案</button>
    {error && <p role="alert">{error}</p>}
    {result && <p role="status">{result} · Canonical unchanged</p>}
    {sidecar && <button disabled={busy || result === "SHADOW_QUALIFIED"} onClick={() => void qualify()}>生成 Shadow Qualification（不执行 Apply）</button>}
    {batch && <>
      <p>{batch.proposal.kind} · {batch.proposal_id} · revision {batch.proposal.expected_revision}</p>
      <p>{Object.entries(batch.counts).map(([name, count]) => `${name}: ${count}`).join(" · ")}</p>
      <p>Review Policy：{batch.proposal.binding.review_policy?.mode ?? "DUAL_MODEL_HUMAN（历史）"}。待核实候选：{unresolved.size}。{batch.advice.B && `A/B 分歧：${disagreements.length}。`}执行身份为本地配置记录，未经平台认证。</p>
      <p>{batch.proposal.reason}</p>
      <table><thead><tr><th>Candidate / Claim</th><th>决定、理由及精确目标</th></tr></thead><tbody>
        {batch.proposal.items.map(item => {
          const cid = String(item.candidate_id ?? item.claim_id);
          return <tr key={cid}><td>{cid}{unresolved.has(cid) && <strong> · 待核实</strong>}</td><td>
            <pre>{JSON.stringify(item, null, 2)}</pre>
            {Object.entries(batch.advice).map(([slot, advice]) => {
              const opinion = advice.items.find(i => i.candidate_id === cid);
              return opinion && <p key={slot}>{slot}: {opinion.judgment} · {opinion.reason}</p>;
            })}
            {Array.isArray(batch.evidence) && <details><summary>原始内容、Evidence 定位与精确匹配</summary><pre>{JSON.stringify(batch.evidence.find(e => e.candidate_id === cid), null, 2)}</pre></details>}
          </td></tr>;
        })}
      </tbody></table>
      <details><summary>全部 AI 意见及理由</summary><pre>{JSON.stringify(batch.advice, null, 2)}</pre></details>
      <details><summary>候选证据与实体身份</summary><pre>{JSON.stringify(batch.evidence, null, 2)}</pre></details>
      <details><summary>冻结 Packet / Context / Basis</summary><pre>{JSON.stringify(batch.proposal.binding, null, 2)}</pre></details>
      <p>批准将逐项保存本方案并执行不可逆 Seal。中断时保留已保存操作，可恢复同一方案。Seal 后决定不可修改；不会执行 Canonical Apply。</p>
      {drift && <p role="alert">方案身份或 revision 已变化，禁止批准。</p>}
      <label><input type="checkbox" checked={confirmed} disabled={busy || !!drift || !!result} onChange={e => setConfirmed(e.target.checked)} />我已查看全部决定、AI 意见与未解决问题、证据、精确 Node ID 与角色，批准此完整方案及 Seal。</label>
      <button disabled={busy || !confirmed || !!drift || !!result} onClick={() => void approve()}>{batch.approved ? "恢复同一批准方案并 Seal" : "批准整批并 Seal"}</button>
    </>}
  </section>;
}
