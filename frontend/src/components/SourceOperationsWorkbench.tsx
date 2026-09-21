import { FormEvent, useCallback, useEffect, useRef, useState } from "react";

import { getSession, loginWorkbench, WorkbenchError } from "../api/workbench";
import { getSourceOperation, listSourceOperations, startSourceProcessing, uploadSource, type PrivateSource } from "../api/sourceOperations";

type Session = { actor: string; mode: string; csrf_token?: string };
const operationId = () => crypto.randomUUID ? `source-${crypto.randomUUID()}` : `source-${Date.now()}-00000000`;

export function SourceOperationsWorkbench({ onAuthenticated = () => undefined }: { onAuthenticated?: () => void }) {
  const [session, setSession] = useState<Session | null | undefined>(undefined);
  const [token, setToken] = useState("");
  const [sources, setSources] = useState<PrivateSource[]>([]);
  const [maxPdfBytes, setMaxPdfBytes] = useState<number | null>(null);
  const [selectedId, setSelectedId] = useState(() => window.location.pathname.split("/")[2] ?? "");
  const [selected, setSelected] = useState<PrivateSource | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const controller = useRef<AbortController | null>(null);

  const refresh = useCallback(async (sourceId = selectedId) => {
    controller.current?.abort(); const current = new AbortController(); controller.current = current;
    try {
      const page = await listSourceOperations(current.signal);
      if (current.signal.aborted) return;
      setSources(page.items);
      setMaxPdfBytes(page.capabilities.max_pdf_bytes);
      if (sourceId) setSelected(await getSourceOperation(sourceId, current.signal));
    } catch (reason) { if ((reason as Error).name !== "AbortError") setError((reason as Error).message); }
  }, [selectedId]);

  useEffect(() => {
    const current = new AbortController();
    getSession(current.signal).then((value) => { setSession(value); onAuthenticated(); }).catch((reason) => {
      if ((reason as WorkbenchError).status === 401) setSession(null); else setError((reason as Error).message);
    });
    return () => current.abort();
  }, [onAuthenticated]);
  useEffect(() => { if (session) void refresh(); }, [session, refresh]);
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
      window.history.pushState(null, "", `/source-operations/${encodeURIComponent(value.source_id)}`);
      setMessage(value.duplicate ? "Exact Source already registered. No bytes or processing job were duplicated." : "Clean PDF validated and stored as an immutable private Source.");
      await refresh(value.source_id);
    } catch (reason) { setError((reason as Error).message); } finally { setBusy(false); }
  }
  async function startProcessing() {
    if (!selected || !session?.csrf_token) return;
    const current = new AbortController(); setBusy(true); setError(""); setMessage("");
    try {
      const response = await startSourceProcessing(selected.source_id, { idempotency_key: operationId(), reprocess_reason: "" }, session.csrf_token, current.signal);
      setMessage(response.duplicate ? "Existing processing run returned; no cloud job was duplicated." : "Processing intent queued. A separate worker owns all provider calls.");
      await refresh(selected.source_id);
    } catch (reason) { setError((reason as Error).message); } finally { setBusy(false); }
  }
  function choose(value: PrivateSource) {
    setSelectedId(value.source_id); setSelected(null); setError("");
    window.history.pushState(null, "", `/source-operations/${encodeURIComponent(value.source_id)}`);
    void refresh(value.source_id);
  }

  if (session === undefined) return <main className="jobs-loading">Opening private Source operations…</main>;
  if (session === null) return <main className="jobs-login"><form onSubmit={signIn}><span className="eyebrow">Private Source operations</span>
    <h1>Sign in to upload and inspect Sources</h1><p>Uploads are private. Processing is queued and never calls a provider in the request.</p>
    <label>Workbench token<input type="password" value={token} onChange={(event) => setToken(event.target.value)} /></label>
    {error && <p role="alert" className="jobs-error">{error}</p>}<button disabled={busy || token.length < 32}>Sign in</button></form></main>;

  const run = selected?.latest_run;
  const stages = ["Validated", "Parsed", "Semantic Processing", "Packet Ready", "Human Review", "Attribution", "Qualified"];
  return <main className="jobs-workspace source-operations"><header className="jobs-hero"><div><span className="eyebrow">Private clean PDF · Golden Path</span>
    <h1>Source Operations</h1><p>Upload → durable processing → native review → attribution → staged result.</p></div><button onClick={() => void refresh()}>Refresh</button></header>
    <section className="jobs-submit"><h2>Upload one clean PDF</h2><form onSubmit={sendUpload}>
      <label>Private PDF<input aria-label="Private PDF" type="file" accept="application/pdf,.pdf" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /></label>
      <label>Boundary<input value={`${maxPdfBytes === null ? "Configured" : `${(maxPdfBytes / 1024 / 1024).toLocaleString()} MiB`} maximum · OCR unsupported`} readOnly /></label>
      <button disabled={busy || !file}>{busy ? "Validating…" : "Upload and validate"}</button></form>
      {message && <p role="status" className="jobs-message">{message}</p>}{error && <p role="alert" className="jobs-error">{error}</p>}</section>
    <div className="jobs-layout"><section className="jobs-list"><div className="jobs-heading"><h2>Private Sources</h2><span>{sources.length}</span></div>
      {sources.map((source) => <button key={source.source_id} className={source.source_id === selectedId ? "selected" : ""} onClick={() => choose(source)}>
        <span className={`job-state state-${(source.latest_run?.state ?? "registered").toLowerCase()}`}>{source.latest_run?.state ?? "REGISTERED"}</span>
        <strong>{source.safe_filename}</strong><code>{source.source_id}</code><small>{source.size_bytes.toLocaleString()} bytes · {source.validation.gate}</small></button>)}</section>
      <section className="job-detail">{!selected ? <p>Select a Source to inspect its product lineage.</p> : <>
        <div className="jobs-heading"><div><span className={`job-state state-${(run?.state ?? "registered").toLowerCase()}`}>{run?.state ?? "REGISTERED"}</span><h2>{selected.safe_filename}</h2></div><code>{selected.source_id}</code></div>
        {!run && <button disabled={busy || Boolean(selected.known_canonical_source_id)} onClick={() => void startProcessing()}>Start Processing</button>}
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
