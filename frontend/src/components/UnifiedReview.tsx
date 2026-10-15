import { useEffect, useState } from "react";
import { request } from "../api/workbench";

type Native = { candidate_id: string; content_sha256: string; decision: string; reason: string; target_node_id: string };
type Link = { node_id: string; role: string };
type Attribution = { claim_id: string; content_sha256: string; outcome: string; scope: string; links: Link[]; reason: string };
type Candidate = { candidate_id: string; candidate_type: string; content_sha256: string; allowed_decisions: string[]; content: Record<string, unknown> };
type Universe = { claims: Record<string, { scope: string }>; nodes: Record<string, { node_id: string; content: Record<string, unknown> }> };
type Context = { binding: Record<string, unknown>; revision: number; status: string; candidates: Candidate[];
  capabilities?: Record<string, { available_decisions: string[]; blocked_decisions: Record<string, string>; reuse_target: string | null }>;
  advice: Record<string, { items: Array<{ candidate_id: string; judgment: string; reason: string }> }>;
  approved_proposal_id: string | null; proposal_ids: string[] };
type Preview = { binding: Record<string, unknown>; revision: number; universe: Universe; universe_sha256: string };
type Proposal = { proposal_id: string; approved: boolean; status: string; result: unknown; progress?: { stage: string; completed_steps: number; total_steps: number };
  proposal: { native_items: Native[]; attribution_items: Attribution[]; reason: string; universe: Universe; binding: Record<string, unknown>; expected_revision: number; universe_sha256: string } };

export function UnifiedReview({ handle, csrf }: { handle: string; csrf: string }) {
  const [context, setContext] = useState<Context | null>(null);
  const [native, setNative] = useState<Native[]>([]);
  const [attrs, setAttrs] = useState<Attribution[]>([]);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [frozen, setFrozen] = useState<Proposal | null>(null);
  const [selected, setSelected] = useState("");
  const [reason, setReason] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const base = `/reviews/${encodeURIComponent(handle)}/unified`;
  const call = <T,>(suffix: string, body?: unknown) => request<T>(base + suffix, new AbortController().signal, body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf }, body: JSON.stringify(body),
  });
  const loadProposal = (p: Proposal) => {
    setFrozen(p); setNative(p.proposal.native_items); setAttrs(p.proposal.attribution_items); setReason(p.proposal.reason); setConfirmed(false);
    setPreview({ binding: p.proposal.binding, revision: p.proposal.expected_revision, universe: p.proposal.universe, universe_sha256: p.proposal.universe_sha256 });
  };
  const perform = async (fn: () => Promise<void>) => {
    setBusy(true); setError("");
    try { await fn(); } catch (e) { setError(e instanceof Error ? e.message : "审核验证失败。"); }
    finally { setBusy(false); }
  };
  useEffect(() => {
    let live = true;
    setBusy(true);
    call<Context>("").then(async ctx => {
      if (!live) return;
      setContext(ctx); setSelected(ctx.candidates[0]?.candidate_id ?? "");
      setNative(ctx.candidates.map(c => ({ candidate_id: c.candidate_id, content_sha256: c.content_sha256, decision: "", reason: "", target_node_id: "" })));
      if (ctx.approved_proposal_id) {
        const p = await call<Proposal>(`/proposals/${ctx.approved_proposal_id}`);
        if (live) loadProposal(p);
      }
    }).catch(e => { if (live) setError(e.message); }).finally(() => { if (live) setBusy(false); });
    return () => { live = false; };
  }, [handle]);
  const changeNative = (id: string, values: Partial<Native>) => {
    setNative(rows => rows.map(r => r.candidate_id === id ? { ...r, ...values } : r));
    setPreview(null); setAttrs([]); setFrozen(null); setConfirmed(false);
  };
  const changeAttr = (id: string, values: Partial<Attribution>) => {
    setAttrs(rows => rows.map(r => r.claim_id === id ? { ...r, ...values } : r)); setFrozen(null); setConfirmed(false);
  };
  const validateNative = () => perform(async () => {
    const p = await call<Preview>("/preview", { native_items: native }); setPreview(p); setFrozen(null); setConfirmed(false);
    setAttrs(Object.entries(p.universe.claims).map(([id, c]) => ({ claim_id: id, content_sha256: native.find(n => n.candidate_id === id)!.content_sha256,
      scope: c.scope, outcome: "", links: [], reason: "" })));
  });
  const prepare = () => perform(async () => {
    if (!preview) return;
    setFrozen(await call<Proposal>("/proposals", { binding: preview.binding, expected_revision: preview.revision, native_items: native, attribution_items: attrs, reason }));
    setConfirmed(false);
  });
  const approve = () => perform(async () => {
    if (!frozen || (!frozen.approved && !confirmed)) return;
    try {
      // Continuations consume the same durable approval; they do not approve a new plan.
      let result: Proposal;
      do {
        result = await call<Proposal>("/approval", { proposal_id: frozen.proposal_id, confirm: true });
        if (result.proposal_id !== frozen.proposal_id || !result.approved) throw new Error("批准身份不一致，执行已停止。");
        setFrozen(result); setConfirmed(false);
      } while (result.status !== "SEALED");
    }
    catch (e) {
      // A lost response may follow a durable approval or seal. Reload only this identity.
      setFrozen(await call<Proposal>(`/proposals/${frozen.proposal_id}`)); throw e;
    }
  });
  const candidate = context?.candidates.find(c => c.candidate_id === selected);
  const decision = native.find(n => n.candidate_id === selected);
  const attr = attrs.find(a => a.claim_id === selected);
  const locked = busy || !!frozen?.approved || context?.status === "SEALED";
  const unresolved = new Set(Object.values(context?.advice ?? {}).flatMap(a => a.items.filter(i => i.judgment !== "SUPPORTED").map(i => i.candidate_id)));
  return <section aria-label="Unified human review">
    <h2>统一人工审核 · Native + Attribution</h2>
    <p>逐项检查证据、准入和归属，完整方案只批准一次。SOURCE_ASSERTION / UNVERIFIED / CLUE_ONLY 保持不变；不执行入库。</p>
    {error && <p role="alert">{error} 执行中断时只恢复原批准方案。</p>}
    {!context && <p>须先按原规则选择审核模式并完成所需 AI Advice，然后刷新进入统一审核。</p>}
    {context && <>
      <p>Native {native.filter(n => n.decision && n.reason.trim()).length}/{native.length} · KEEP {native.filter(n => n.decision === "KEEP").length} · Attribution {attrs.filter(a => a.outcome && a.reason.trim()).length}/{attrs.length} · AI 待核实 {unresolved.size}</p>
      <p>主体不明确时可选择 NO_LINK / DEFER。修改 Native 会清空依赖的归属草稿，必须重新检查。</p>
      {!preview && !frozen?.approved && <p>尚未验证完整 Native 集合，归属草稿未冻结。</p>}
      <p>当前 Node / 依赖限制：{Object.values(context.capabilities ?? {}).filter(c => Object.keys(c.blocked_decisions).length > 0).length} 项（逐项查看原生验证原因）。</p>
      <div className="unified-review-grid">
        <nav aria-label="Unified candidates">{context.candidates.map(c => <button key={c.candidate_id} aria-pressed={selected === c.candidate_id} onClick={() => setSelected(c.candidate_id)}>
          {c.candidate_type} · {c.candidate_id} · {native.find(n => n.candidate_id === c.candidate_id)?.decision || "待审核"}{unresolved.has(c.candidate_id) ? " · AI 待核实" : ""}
        </button>)}</nav>
        <div aria-label="Evidence and AI Advice"><h3>原始 Evidence / AI Advice</h3>
          <p>{String(candidate?.content.statement ?? candidate?.content.proposed_name ?? "")}</p>
          <p>Evidence Pointer：{String(candidate?.content.evidence_pointer ?? "见下方支持证据")}</p>
          <blockquote>{String(candidate?.content.evidence_excerpt ?? "")}</blockquote>
          {candidate?.content.supporting_evidence != null && <pre>{JSON.stringify(candidate.content.supporting_evidence, null, 2)}</pre>}
          <details><summary>完整原始内容、限定条件与精确匹配</summary><pre>{JSON.stringify(candidate?.content, null, 2)}</pre></details>
          {Object.entries(context.advice).map(([slot, a]) => { const item = a.items.find(i => i.candidate_id === selected); return item && <p key={slot}>{slot}: {item.judgment} · {item.reason}</p>; })}
          <details><summary>全部 AI 身份与来源</summary><pre>{JSON.stringify(context.advice, null, 2)}</pre></details>
        </div>
        <div aria-label="Unified decisions">{candidate && decision && <>
          <h3>{candidate.candidate_type} 决定</h3>
          {Object.entries(context.capabilities?.[selected]?.blocked_decisions ?? {}).map(([action, cause]) => <p key={action}>{action} 当前限制：{cause}</p>)}
          <label>Native decision<select disabled={locked} value={decision.decision} onChange={e => changeNative(selected, { decision: e.target.value, target_node_id: "" })}>
            <option value="">请选择</option>{candidate.allowed_decisions.map(d => <option key={d}>{d}</option>)}
          </select></label>
          {decision.decision === "REUSE" && <label>Exact Node ID<input disabled={locked} value={decision.target_node_id} onChange={e => changeNative(selected, { target_node_id: e.target.value })} /></label>}
          <label>Native reason<textarea disabled={locked} value={decision.reason} onChange={e => changeNative(selected, { reason: e.target.value })} /></label>
          {candidate.candidate_type === "NODE" && <details><summary>Node 身份、精确匹配及依赖</summary><pre>{JSON.stringify(candidate.content, null, 2)}</pre></details>}
          {decision.decision === "KEEP" && !preview && <p>完成全部 Native 决定后预验证，生成合法归属候选。</p>}
          {attr && <>
            <h3>Claim–Node Attribution</h3><p>Scope：{attr.scope}</p>
            <label>Attribution outcome<select disabled={locked} value={attr.outcome} onChange={e => changeAttr(selected, { outcome: e.target.value, links: [] })}>
              <option value="">请选择</option>{["LINK", "MULTI_LINK", "NO_LINK", "DEFER"].map(o => <option key={o}>{o}</option>)}
            </select></label>
            {["LINK", "MULTI_LINK"].includes(attr.outcome) && <>
              {attr.links.map((link, index) => <div key={index}>
                <label>Target Node {index + 1}<select disabled={locked} value={link.node_id} onChange={e => changeAttr(selected, { links: attr.links.map((l, i) => i === index ? { ...l, node_id: e.target.value } : l) })}>
                  <option value="">请选择精确身份</option>{Object.entries(preview?.universe.nodes ?? {}).map(([id, n]) => <option key={id} value={id}>{String(n.content.proposed_name ?? id)} · {id}</option>)}
                </select></label>
                <label>Role {index + 1}<select disabled={locked} value={link.role} onChange={e => changeAttr(selected, { links: attr.links.map((l, i) => i === index ? { ...l, role: e.target.value } : l) })}>
                  <option value="">请选择</option>{["subject", "context", "related"].map(r => <option key={r}>{r}</option>)}
                </select></label>
                <button disabled={locked} onClick={() => changeAttr(selected, { links: attr.links.filter((_, i) => i !== index) })}>移除此关联</button>
              </div>)}
              <button disabled={locked || (attr.outcome === "LINK" && attr.links.length === 1)} onClick={() => changeAttr(selected, { links: [...attr.links, { node_id: "", role: "" }] })}>添加精确 Node 关联</button>
              {preview && !Object.keys(preview.universe.nodes).length && <p role="alert">没有合法 Node；请使用 NO_LINK / DEFER。</p>}
            </>}
            <label>Attribution reason<textarea disabled={locked} value={attr.reason} onChange={e => changeAttr(selected, { reason: e.target.value })} /></label>
          </>}
        </>}</div>
      </div>
      <button disabled={locked || native.some(n => !n.decision || !n.reason.trim())} onClick={() => void validateNative()}>预验证 Native 并建立归属候选</button>
      <label>整份方案审核理由<textarea disabled={locked} value={reason} onChange={e => { setReason(e.target.value); setFrozen(null); setConfirmed(false); }} /></label>
      <button disabled={locked || !preview || !reason.trim() || attrs.some(a => !a.outcome || !a.reason.trim())} onClick={() => void prepare()}>验证并冻结完整方案</button>
      {context.proposal_ids.length > 0 && !frozen && <label>读取已有冻结方案<select defaultValue="" disabled={busy} onChange={e => { if (e.target.value) void perform(async () => loadProposal(await call<Proposal>(`/proposals/${e.target.value}`))); }}>
        <option value="">选择 Proposal</option>{context.proposal_ids.map(p => <option key={p}>{p}</option>)}
      </select></label>}
    </>}
    {frozen && <section aria-label="Frozen unified proposal"><h3>完整冻结方案 · {frozen.status}</h3>
      <p>SHA-256：{frozen.proposal_id}</p>{frozen.progress && <p role="status">执行进度：{frozen.progress.stage} {frozen.progress.completed_steps}/{frozen.progress.total_steps}</p>}
      <table><thead><tr><th>Candidate</th><th>Native 决定与理由</th><th>Attribution 决定与理由</th></tr></thead><tbody>
        {frozen.proposal.native_items.map(n => { const a = frozen.proposal.attribution_items.find(i => i.claim_id === n.candidate_id); return <tr key={n.candidate_id}>
          <td>{n.candidate_id}</td><td>{n.decision} · {n.target_node_id}<p>{n.reason}</p></td><td>{a ? <>{a.outcome} · {a.scope}<p>{a.links.map(l => `${l.node_id} (${l.role})`).join(" / ")}</p><p>{a.reason}</p></> : "不属于本轮 KEEP Claim"}</td>
        </tr>; })}
      </tbody></table>
      <details><summary>完整冻结身份、AI 绑定与执行计划</summary><pre>{JSON.stringify(frozen.proposal, null, 2)}</pre></details>
      {frozen.status === "SEALED" ? <><p role="status">一次人工批准已完成 Native Seal 与 Attribution Seal；Canonical 未变。</p><pre>{JSON.stringify(frozen.result, null, 2)}</pre></> : <>
        {!frozen.approved && <label><input type="checkbox" checked={confirmed} disabled={busy} onChange={e => setConfirmed(e.target.checked)} />我已核对完整证据、AI 意见、Native 与 Attribution 决定，一次批准此完整方案及两阶段 Seal。</label>}
        <button disabled={busy || (!frozen.approved && !confirmed)} onClick={() => void approve()}>{frozen.approved ? "恢复同一已批准方案" : "一次批准 Native + Attribution"}</button>
      </>}
    </section>}
  </section>;
}
