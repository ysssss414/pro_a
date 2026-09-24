import { FormEvent, useCallback, useEffect, useRef, useState } from "react";

import { getSession, loginWorkbench, WorkbenchError } from "../api/workbench";
import { getCommunityDomains, getOperationalCapacity, getSourceOperation, importCommunity, listSourceOperations, previewCommunity, startSourceProcessing, uploadSource, type CommunityPreview, type OperationalCapacity, type PrivateSource } from "../api/sourceOperations";
import { getResearchCompany, searchResearchCompanies, type CompanyMaterialsPage } from "../api/research";

type Session = { actor: string; mode: string; csrf_token?: string };
const operationId = () => crypto.randomUUID ? `source-${crypto.randomUUID()}` : `source-${Date.now()}-00000000`;
const noopAuthenticated = () => undefined;
const materialKinds = ["earnings_report", "exchange_filing", "company_announcement", "investor_presentation", "investor_qa", "research_report", "community_material", "other"];
const sourceChannels = ["company_official", "exchange_official", "broker_research", "media", "knowledge_community", "user_upload", "other"];

export function SourceOperationsWorkbench({ onAuthenticated = noopAuthenticated }: { onAuthenticated?: () => void }) {
  const [session, setSession] = useState<Session | null | undefined>(undefined);
  const [token, setToken] = useState("");
  const [sources, setSources] = useState<PrivateSource[]>([]);
  const [maxPdfBytes, setMaxPdfBytes] = useState<number | null>(null);
  const [capacity, setCapacity] = useState<OperationalCapacity | null>(null);
  const [selectedId, setSelectedId] = useState(() => window.location.pathname.split("/")[2] ?? "");
  const [selected, setSelected] = useState<PrivateSource | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const contextId = new URLSearchParams(window.location.search).get("company") ?? "";
  const communityMode = new URLSearchParams(window.location.search).get("community") === "1";
  const [communityFile, setCommunityFile] = useState<File | null>(null);
  const [communityPreview, setCommunityPreview] = useState<CommunityPreview | null>(null);
  const [communityDomains, setCommunityDomains] = useState<Array<{ domain_id: string; version: string }>>([]);
  const [communityDomain, setCommunityDomain] = useState("");
  const [companyTarget, setCompanyTarget] = useState<CompanyMaterialsPage["company"] | null>(null);
  const [companyError, setCompanyError] = useState("");
  const [companyQuery, setCompanyQuery] = useState("");
  const [companyResults, setCompanyResults] = useState<CompanyMaterialsPage["company"][]>([]);
  const [materialKind, setMaterialKind] = useState("");
  const [sourceChannel, setSourceChannel] = useState("");
  const [materialDate, setMaterialDate] = useState("");
  const [operatorTitle, setOperatorTitle] = useState("");
  const controller = useRef<AbortController | null>(null);

  const refresh = useCallback(async (sourceId = selectedId) => {
    controller.current?.abort(); const current = new AbortController(); controller.current = current;
    try {
      const [page, currentCapacity] = await Promise.all([
        listSourceOperations(current.signal), getOperationalCapacity(current.signal),
      ]);
      if (current.signal.aborted) return;
      setSources(page.items);
      setMaxPdfBytes(page.capabilities.max_pdf_bytes);
      setCapacity(currentCapacity);
      if (sourceId) setSelected(await getSourceOperation(sourceId, current.signal));
    } catch (reason) { if (!current.signal.aborted) setError((reason as Error).message); }
  }, [selectedId]);

  useEffect(() => {
    const current = new AbortController();
    getSession(current.signal).then((value) => { if (!current.signal.aborted) { setSession(value); onAuthenticated(); } }).catch((reason) => {
      if (current.signal.aborted) return;
      if ((reason as WorkbenchError).status === 401) setSession(null); else setError((reason as Error).message);
    });
    return () => current.abort();
  }, [onAuthenticated]);
  useEffect(() => { if (session) void refresh(); }, [session, refresh]);
  useEffect(() => {
    if (!session || !communityMode) return;
    const current = new AbortController();
    getCommunityDomains(current.signal).then(value => { if (!current.signal.aborted) setCommunityDomains(value.items); })
      .catch(reason => { if (!current.signal.aborted) setError((reason as Error).message); });
    return () => current.abort();
  }, [session, communityMode]);
  useEffect(() => {
    if (!session || !contextId) return;
    const current = new AbortController();
    getResearchCompany(contextId, current.signal).then(target => { if (!current.signal.aborted) { setCompanyTarget(target); setCompanyError(""); } })
      .catch(reason => { if (!current.signal.aborted) { setCompanyTarget(null); setCompanyError((reason as Error).message); } });
    return () => current.abort();
  }, [session, contextId]);
  useEffect(() => {
    if (!selected?.latest_run || !["QUEUED", "PARSING", "EXTRACTION_PROCESSING", "SEMANTIC_PROCESSING", "PACKET_PREPARATION"].includes(selected.latest_run.state)) return;
    let stopped = false;
    let timer = 0;
    const poll = async () => {
      await refresh(selected.source_id);
      if (!stopped) timer = window.setTimeout(() => void poll(), 800);
    };
    timer = window.setTimeout(() => void poll(), 800);
    return () => { stopped = true; window.clearTimeout(timer); };
  }, [refresh, selected]);
  useEffect(() => () => controller.current?.abort(), []);

  async function signIn(event: FormEvent) {
    event.preventDefault(); const current = new AbortController(); setBusy(true); setError("");
    try { await loginWorkbench(token, current.signal); const value = await getSession(current.signal); setSession(value); onAuthenticated(); }
    catch (reason) { setError((reason as Error).message); } finally { setBusy(false); }
  }
  async function sendUpload(event: FormEvent) {
    event.preventDefault(); if (!file || !session?.csrf_token) return;
    const current = new AbortController(); setBusy(true); setError(""); setMessage("");
    try {
      const value = await uploadSource(file, session.csrf_token, current.signal);
      setSelectedId(value.source_id); setSelected(value);
      window.history.pushState(null, "", `/source-operations/${encodeURIComponent(value.source_id)}${contextId ? `?company=${encodeURIComponent(contextId)}` : ""}`);
      setMessage(value.duplicate ? "Exact Source already registered. No bytes or processing job were duplicated." : "Clean PDF validated and stored as an immutable private Source.");
      await refresh(value.source_id);
    } catch (reason) { setError((reason as Error).message); } finally { setBusy(false); }
  }
  async function startProcessing() {
    if (!selected || !session?.csrf_token) return;
    const current = new AbortController(); setBusy(true); setError(""); setMessage("");
    try {
      const company_material_intent = companyTarget ? {
        target_company_node_id: companyTarget.node_id, material_kind: materialKind,
        source_channel: sourceChannel, material_date: materialDate || null,
        operator_title: operatorTitle.trim() || null,
      } : undefined;
      const response = await startSourceProcessing(selected.source_id,
        { idempotency_key: operationId(), reprocess_reason: "", ...(company_material_intent ? { company_material_intent } : {}) },
        session.csrf_token, current.signal);
      setMessage(response.duplicate ? "Existing processing run returned; no cloud job was duplicated." : "Processing intent queued. A separate worker owns all provider calls.");
      await refresh(selected.source_id);
    } catch (reason) { setError((reason as Error).message); } finally { setBusy(false); }
  }
  function choose(value: PrivateSource) {
    setSelectedId(value.source_id); setSelected(null); setError("");
    window.history.pushState(null, "", `/source-operations/${encodeURIComponent(value.source_id)}${contextId ? `?company=${encodeURIComponent(contextId)}` : ""}`);
    void refresh(value.source_id);
  }

  if (session === undefined) return <main className="jobs-loading">Opening private Source operations…</main>;
  if (session === null) return <main className="jobs-login"><form onSubmit={signIn}><span className="eyebrow">Private Source operations</span>
    <h1>Sign in to upload and inspect Sources</h1><p>Uploads are private. Processing is queued and never calls a provider in the request.</p>
    <label>Workbench token<input type="password" value={token} onChange={(event) => setToken(event.target.value)} /></label>
    {error && <p role="alert" className="jobs-error">{error}</p>}<button disabled={busy || token.length < 32}>Sign in</button></form></main>;

  const run = selected?.latest_run;
  async function searchCompany(event: FormEvent) {
    event.preventDefault(); if (!companyQuery.trim()) return;
    const current = new AbortController(); setCompanyError("");
    try { setCompanyResults((await searchResearchCompanies(companyQuery.trim(), current.signal)).items); }
    catch (reason) { setCompanyError((reason as Error).message); }
  }
  async function inspectCommunity(event: FormEvent) {
    event.preventDefault(); if (!communityFile || !companyTarget || !session?.csrf_token) return;
    const current = new AbortController(); setBusy(true); setError(""); setCommunityPreview(null);
    try { setCommunityPreview(await previewCommunity(communityFile, companyTarget.node_id, session.csrf_token, current.signal)); }
    catch (reason) { setError((reason as Error).message); } finally { setBusy(false); }
  }
  async function sendCommunity() {
    if (!communityFile || !communityPreview || !companyTarget || !session?.csrf_token) return;
    const current = new AbortController(); setBusy(true); setError(""); setMessage("");
    try {
      const value = await importCommunity(communityFile, companyTarget.node_id, communityDomain || null, session.csrf_token, current.signal);
      setSelectedId(value.source.source_id);
      window.history.pushState(null, "", `/source-operations/${encodeURIComponent(value.source.source_id)}?company=${encodeURIComponent(companyTarget.node_id)}&community=1`);
      setMessage(value.duplicate ? "Existing Community processing run returned." : "Community material queued for private Source processing.");
      await refresh(value.source.source_id);
    } catch (reason) { setError((reason as Error).message); } finally { setBusy(false); }
  }
  const stages = ["Validated", "Parsed", "Semantic Processing", "Packet Ready", "Human Review", "Attribution", "Qualified"];
  return <main className="jobs-workspace source-operations"><header className="jobs-hero"><div><span className="eyebrow">Private clean PDF · Golden Path</span>
    <h1>Source Operations</h1><p>Upload → durable processing → native review → attribution → staged result.</p></div><button onClick={() => void refresh()}>Refresh</button></header>
    {capacity?.capacity_policy_version && <section className="jobs-submit" aria-label="Operational WIP capacity">
      <h2>Operational WIP · {capacity.wip_state}</h2>
      <p><strong>{capacity.operational_pending_rows}</strong> operational pending · {capacity.native_pending_rows} native pending</p>
      <p>{capacity.historical_lifecycle_closed} historical lifecycle closures: {capacity.human_user_qualified} HUMAN_USER qualified · {capacity.ai_policy_closed} AI policy closed.</p>
      <p>{capacity.followup_governance} follow-up governance items · new intake {capacity.new_intake_allowed ? "allowed" : "blocked"}.</p>
    </section>}
    <section className="jobs-submit" aria-label="Company Material Intent"><h2>Company Material Intent</h2>
      {contextId && !companyTarget && !companyError && <p role="status">Validating canonical Company…</p>}
      {companyError && <p role="alert" className="jobs-error">{companyError}</p>}
      {companyTarget ? <><p>Research target: <strong>{companyTarget.canonical_name}</strong> · {companyTarget.node_id}</p>
        <p>Operator routing context only. Human Review and Attribution decide Claim links.</p>
        {communityMode ? <p>Community import binds community_material · knowledge_community · LOW_TRUST_CLUE_ONLY. Material date and title remain unset.</p> : <><div className="source-material-fields"><label>Material Kind<select value={materialKind} onChange={event => setMaterialKind(event.target.value)}>
          <option value="">Select material kind</option>{materialKinds.map(kind => <option key={kind} value={kind}>{kind.replaceAll("_", " ")}</option>)}</select></label>
          <label>Source Channel<select value={sourceChannel} onChange={event => setSourceChannel(event.target.value)}>
            <option value="">Select source channel</option>{sourceChannels.map(channel => <option key={channel} value={channel}>{channel.replaceAll("_", " ")}</option>)}</select></label>
          <label>Material Date<input type="date" value={materialDate} onChange={event => setMaterialDate(event.target.value)} /></label>
          <label>Operator Title<input maxLength={240} value={operatorTitle} onChange={event => setOperatorTitle(event.target.value)} /></label></div>
        <p>Material date is operator supplied. Channel trust is for workflow display and does not set Source Rank.</p>
        {sourceChannel === "knowledge_community" && <p>Low-trust clue source. Independent corroboration may be required before thesis use.</p>}</>}
        <a href={`/node/${encodeURIComponent(companyTarget.node_id)}`}>Back to Company Research</a></>
        : !contextId && <form onSubmit={searchCompany}><label>Find canonical Company<input value={companyQuery} onChange={event => setCompanyQuery(event.target.value)} /></label>
          <button type="submit">Search Companies</button>
          {companyResults.map(target => <button key={target.node_id} type="button" onClick={() => {
            window.history.replaceState(null, "", `${window.location.pathname}?company=${encodeURIComponent(target.node_id)}`);
            setCompanyTarget(target); setCompanyResults([]);
          }}>{target.canonical_name} · {target.node_id}</button>)}</form>}
    </section>
    {communityMode && <section className="jobs-submit"><h2>Import Knowledge Community</h2>
      <p>Clue source only. Check the target and topic count before import; processing still requires Human Review and Attribution.</p>
      <form onSubmit={inspectCommunity}><label>ZSXQ export ZIP<input aria-label="ZSXQ export ZIP" type="file" accept="application/zip,.zip" onChange={event => { setCommunityFile(event.target.files?.[0] ?? null); setCommunityPreview(null); }} /></label>
        <button disabled={busy || !communityFile || !companyTarget}>{busy ? "Checking…" : "Preview bundle"}</button></form>
      {communityPreview && <div role="status"><p>Target: <strong>{communityPreview.target_company.canonical_name}</strong> · {communityPreview.target_company.node_id}</p>
        <p>ZSXQ input: {communityPreview.company_input} · Group: {communityPreview.group_label} ({communityPreview.group_id})</p>
        <p>{communityPreview.topic_count} topics · {communityPreview.date_min ?? "Unknown"} to {communityPreview.date_max ?? "Unknown"}</p>
        <p>{communityPreview.trust_policy} · Bundle <code>{communityPreview.bundle_sha256}</code></p>
        <label>Processing scope<select value={communityDomain} onChange={event => setCommunityDomain(event.target.value)}>
          <option value="">Shared Core — Domain pending</option>{communityDomains.map(item => <option key={`${item.domain_id}:${item.version}`} value={item.domain_id}>{item.domain_id} · {item.version}</option>)}</select></label>
        {!communityDomain && <p>Industry routing is intentionally deferred until the extracted evidence is reviewed.</p>}
        <button type="button" disabled={busy} onClick={() => void sendCommunity()}>Import and start processing</button></div>}</section>}
    {!communityMode && <section className="jobs-submit"><h2>Upload one clean PDF</h2><form onSubmit={sendUpload}>
      <label>Private PDF<input aria-label="Private PDF" type="file" accept="application/pdf,.pdf" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /></label>
      <label>Boundary<input value={`${maxPdfBytes === null ? "Configured" : `${(maxPdfBytes / 1024 / 1024).toLocaleString()} MiB`} maximum · OCR unsupported`} readOnly /></label>
      <button disabled={busy || !file}>{busy ? "Validating…" : "Upload and validate"}</button></form>
      {message && <p role="status" className="jobs-message">{message}</p>}</section>}
    {message && communityMode && <p role="status" className="jobs-message">{message}</p>}{error && <p role="alert" className="jobs-error">{error}</p>}
    <div className="jobs-layout"><section className="jobs-list"><div className="jobs-heading"><h2>Private Sources</h2><span>{sources.length}</span></div>
      {sources.map((source) => <button key={source.source_id} className={source.source_id === selectedId ? "selected" : ""} onClick={() => choose(source)}>
        <span className={`job-state state-${(source.latest_run?.state ?? "registered").toLowerCase()}`}>{source.latest_run?.state ?? "REGISTERED"}</span>
        <strong>{source.safe_filename}</strong><code>{source.source_id}</code><small>{source.size_bytes.toLocaleString()} bytes · {source.validation.gate}</small></button>)}</section>
      <section className="job-detail">{!selected ? <p>Select a Source to inspect its product lineage.</p> : <>
        <div className="jobs-heading"><div><span className={`job-state state-${(run?.state ?? "registered").toLowerCase()}`}>{run?.state ?? "REGISTERED"}</span><h2>{selected.safe_filename}</h2></div><code>{selected.source_id}</code></div>
        {!run && <><p>If no Domain is assigned, processing starts in Shared Core with Domain assignment pending.</p>
          <button disabled={busy || Boolean(selected.known_canonical_source_id) || Boolean(contextId && !companyTarget) || Boolean(companyTarget && (!materialKind || !sourceChannel))} onClick={() => void startProcessing()}>Start Processing</button></>}
        {run?.processing_scope_mode && <dl className="job-facts"><div><dt>Processing Scope</dt><dd>{run.processing_scope_mode === "SHARED_CORE" ? "Shared Core" : "Domain assigned"}</dd></div>
          <div><dt>Domain Assignment</dt><dd>{run.domain_assignment_status === "PENDING" ? "Pending" : run.primary_domain}</dd></div></dl>}
        {run?.domain_assignment_status === "PENDING" && <p>Industry routing is intentionally deferred until the extracted evidence is reviewed.</p>}
        {run?.company_material_intent && <dl className="job-facts"><div><dt>Target Company</dt><dd>{run.company_material_intent.target_company_name} · {run.company_material_intent.target_company_node_id}</dd></div>
          <div><dt>Material Kind</dt><dd>{run.company_material_intent.material_kind}</dd></div><div><dt>Source Channel / Trust Policy</dt><dd>{run.company_material_intent.source_channel} · {run.company_material_intent.material_trust_policy}</dd></div>
          <div><dt>Material Date</dt><dd>{run.company_material_intent.material_date ?? "Unknown"} {run.company_material_intent.material_date_basis ?? ""}</dd></div>
          <div><dt>Intent SHA</dt><dd><code>{run.company_material_intent_sha256}</code></dd></div></dl>}
        {run?.community_provenance && <dl className="job-facts"><div><dt>Community bundle</dt><dd><code>{run.community_provenance.bundle_id}</code><br/><code>{run.community_provenance.bundle_sha256}</code></dd></div>
          <div><dt>Provenance</dt><dd>Provider = zsxq · ZSXQ model routing metadata is private operational metadata.</dd></div>
          <div><dt>Trust</dt><dd>{run.community_provenance.trust_policy} · {run.community_provenance.topic_count} topics</dd></div>
          <div><dt>Group / dates</dt><dd>{run.community_provenance.group_id} · {run.community_provenance.date_min ?? "Unknown"} to {run.community_provenance.date_max ?? "Unknown"}</dd></div></dl>}
        {run?.error && <div className="recovery-banner" role="alert"><strong>{run.error.code}</strong><p>Failed at {run.error.stage}. Retry safe: {String(run.error.retry_safe)}.</p><p>{run.error.operator_action}</p></div>}
        <ol className="source-stage-list">{stages.map((stage) => <li key={stage}>{stage}</li>)}</ol>
        <dl className="job-facts"><div><dt>Source / processing run</dt><dd><code>{selected.source_id}</code><br/><code>{run?.processing_run_id ?? "Not started"}</code></dd></div>
          <div><dt>Content identity</dt><dd><code>{selected.source_sha256}</code><br/>{selected.size_bytes.toLocaleString()} bytes · {selected.validation.pages} pages</dd></div>
          <div><dt>Current stage</dt><dd>{run?.stage ?? "VALIDATED"}<br/>Checkpoint: {run?.native_checkpoint.completed_stage ?? "Source registered"}</dd></div>
          <div><dt>Runtime</dt><dd><code>{String(run?.runtime_identity.runtime_sha256 ?? "Not bound")}</code></dd></div>
          <div><dt>Usage</dt><dd>{run?.usage.status ?? "UNKNOWN"} · {run?.usage.attempts ?? 0} attempts<br/>{run?.usage.total_tokens ?? "unknown"} total tokens</dd></div>
          <div><dt>Native packet / review</dt><dd><code>{run?.packet_id ?? "Not ready"}</code><br/>{run?.review?.status ?? "Not started"}</dd></div>
          <div><dt>Attribution / qualification</dt><dd>{run?.attribution?.status ?? "Not ready"}<br/>{run?.qualification?.status ?? "Not qualified"}</dd></div>
          <div><dt>Provider jobs</dt><dd>{run?.jobs.map((job) => <span key={job.job_id}>{job.operation_kind} · {job.provider}/{job.requested_model} · {job.attempt_count}<br/><code>{job.job_id}</code><br/></span>) ?? "None"}</dd></div></dl>
        {run?.review?.deep_link && <p><a className="source-primary-link" href={run.review.deep_link}>Open Review Workbench</a></p>}
        {run?.activation_receipt && <p><a className="source-primary-link" href={`/source/${encodeURIComponent(selected.source_id)}`}>Inspect activated Source in Research</a></p>}
        <h3>Stable lineage</h3><ol className="job-events">{run?.lineage.map((item, index) => <li key={`${item.kind}-${item.id}`}><span>{index + 1}</span><strong>{item.kind}</strong><code>{item.id}</code></li>)}</ol>
      </>}</section></div>
  </main>;
}
