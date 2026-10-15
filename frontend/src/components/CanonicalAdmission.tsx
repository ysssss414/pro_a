import { useEffect, useState } from "react";
import { request } from "../api/workbench";

type Change = { action: string; table: string; key: Record<string, unknown>; values: Record<string, unknown>;
  withheld_columns: Array<{ column: string; sha256: string }> };
type Plan = { object_id: string; envelope_id: string; diff_id: string; changes: Change[];
  insert_counts: Record<string, number>; unchanged_count: number; evidence: unknown; excluded: unknown[];
  native_items: unknown[]; attribution_items: Array<{ claim_id: string; outcome: string; reason: string }>;
  pre_state_sha256: string; post_state_sha256: string; governance: string };
type Admission = { status: string; plan: Plan | null; approval?: { object_id: string }; execution?: unknown; receipt?: unknown; history_verification?: unknown };

export function CanonicalAdmission({ handle, csrf }: { handle: string; csrf: string }) {
  const [value, setValue] = useState<Admission | null>(null);
  const [error, setError] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const base = `/reviews/${encodeURIComponent(handle)}/admission`;
  const call = (suffix = "", body?: unknown) => request<Admission>(base + suffix, new AbortController().signal,
    body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf }, body: JSON.stringify(body) });

  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const load = async () => {
      try {
        let next = await call();
        if (next.status === "QUALIFICATION_REQUIRED") next = await call("/prepare", {});
        if (!stopped) {
          setValue(next); setError("");
          if (["AUTHORIZED_PENDING_OPERATOR", "RUNNING", "COMMITTED"].includes(next.status)) timer = setTimeout(() => void load(), 5000);
        }
      } catch (e) { if (!stopped) setError(e instanceof Error ? e.message : "入库状态读取失败"); }
    };
    void load();
    return () => { stopped = true; clearTimeout(timer); };
  }, [handle, csrf, value?.approval?.object_id]);

  const refresh = async () => {
    setBusy(true);
    try { setValue(await call()); setError(""); }
    catch (e) { setError(e instanceof Error ? e.message : "读取失败"); }
    finally { setBusy(false); }
  };
  const approve = async () => {
    if (!value?.plan || !confirmed) return;
    setBusy(true); setError("");
    try { setValue(await call("/approval", { proposal_id: value.plan.object_id, confirm: true })); setConfirmed(false); }
    catch (e) {
      // Lost HTTP response is not a failed authorization. Read durable status;
      // never submit a different plan or invoke an Operator from the browser.
      try { setValue(await call()); } catch { /* retain the displayed plan */ }
      setError(e instanceof Error ? e.message : "批准响应未知，请刷新核验");
    } finally { setBusy(false); }
  };
  const plan = value?.plan;
  return <section aria-label="Canonical Admission"><h2>第二次人工确认：Canonical 正式入库</h2>
    <p>独立 Operator 执行冻结方案；来源陈述仍为 SOURCE_ASSERTION / UNVERIFIED / CLUE_ONLY。此批准不证明现实真实性，不更新 Official Current View。</p>
    {error && <p role="alert">{error}</p>}
    <button disabled={busy} onClick={() => void refresh()}>刷新入库状态</button>
    {value && <p role="status">{value.status}</p>}
    {value?.approval && <p>执行状态反映最后持久检查点。响应丢失不代表事务未提交；Operator 重启后依据 Grant 和 Receipt 恢复同一授权。</p>}
    {plan && <>
      <p>Admission Plan：{plan.object_id}</p><p>Envelope：{plan.envelope_id}</p><p>Diff：{plan.diff_id}</p>
      <h3>审核结果、Evidence 与风险</h3>
      <p>排除 / 待核实候选：{plan.excluded.length}；完全一致无需新增：{plan.unchanged_count}</p>
      {plan.attribution_items.filter(i => i.outcome === "NO_LINK").map(i => <p key={i.claim_id}>尚无归属：{i.claim_id} · {i.reason}</p>)}
      <details><summary>第一轮审核的完整决定、Evidence 与限定条件</summary><pre>{JSON.stringify({ native: plan.native_items, attribution: plan.attribution_items, evidence: plan.evidence, excluded: plan.excluded }, null, 2)}</pre></details>
      <h3>精确 Canonical Diff</h3>
      <p>{Object.entries(plan.insert_counts).map(([table, count]) => `${table}: INSERT ${count}`).join(" / ") || "零新增对象（exact no-op）"}</p>
      <table><thead><tr><th>表 / 操作</th><th>精确身份</th><th>全部可披露字段（含 Evidence / Role）</th><th>隐藏字段及 SHA-256</th></tr></thead><tbody>
        {plan.changes.map((c, i) => <tr key={i}><td>{c.table} · {c.action}</td><td><pre>{JSON.stringify(c.key, null, 2)}</pre></td>
          <td><pre>{JSON.stringify(c.values, null, 2)}</pre></td><td>{c.withheld_columns.map(w => <p key={w.column}>{w.column}: {w.sha256}</p>)}</td></tr>)}
      </tbody></table>
      <p>隐藏字段未在本页展示原文；其字节受冻结 Envelope / Diff 约束，由独立 Operator 完整核验。</p>
      <p>预测 Pre-State：{plan.pre_state_sha256}</p><p>预测 Post-State：{plan.post_state_sha256}</p>
      <details><summary>完整冻结绑定、Baseline、Runtime 与授权范围</summary><pre>{JSON.stringify(plan, null, 2)}</pre></details>
      {value?.status === "AWAITING_SECOND_APPROVAL" && <>
        <label><input type="checkbox" disabled={busy} checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />我已查看上述精确变更、证据、隐藏字段范围及哈希，批准此 Plan 的一次性 INSERT / no-op。</label>
        <button disabled={busy || !confirmed} onClick={() => void approve()}>确认本次 Canonical 正式入库</button>
      </>}
    </>}
    {value?.approval && <p>Production Human Approval：{value.approval.object_id}</p>}
    {value?.execution != null && <pre>{JSON.stringify(value.execution, null, 2)}</pre>}
    {value?.receipt != null && <><h3>正式回执与实际变更</h3><pre>{JSON.stringify(value.receipt, null, 2)}</pre><pre>{JSON.stringify(value.history_verification, null, 2)}</pre></>}
  </section>;
}
