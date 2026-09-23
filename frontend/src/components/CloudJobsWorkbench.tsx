import { FormEvent, useCallback, useEffect, useRef, useState } from "react";

import {
  getCloudJob, getCloudJobArtifacts, getCloudJobEvents, listCloudJobs, submitCloudJob,
  type CloudJob, type JobEvent,
} from "../api/cloudJobs";
import { getSession, listPackets, loginWorkbench, type PacketSummary, WorkbenchError } from "../api/workbench";

type Session = { actor: string; mode: string; csrf_token?: string };
const noopAuthenticated = () => undefined;

function operationId() {
  return crypto.randomUUID ? crypto.randomUUID() : "stage6-00000000-0000-4000-8000-" + Date.now();
}

function Login({ onLogin }: { onLogin: (value: Session) => void }) {
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); const controller = new AbortController(); setBusy(true); setError("");
    try { await loginWorkbench(token, controller.signal); onLogin(await getSession(controller.signal)); }
    catch (reason) { setError((reason as Error).message); setBusy(false); }
  }
  return <main className="jobs-login"><form onSubmit={submit}><span className="eyebrow">Durable cloud jobs</span>
    <h1>Sign in to inspect job execution</h1><p>The request thread only enqueues Workbench state. A separate worker owns provider dispatch.</p>
    <label>Workbench token<input type="password" value={token} onChange={(event) => setToken(event.target.value)} autoFocus /></label>
    {error && <p role="alert" className="jobs-error">{error}</p>}
    <button disabled={busy || token.length < 32}>{busy ? "Signing in…" : "Sign in"}</button></form></main>;
}

function Usage({ job }: { job: CloudJob }) {
  return job.usage.status === "UNKNOWN" ? <strong>Usage unknown</strong> : <strong>
    {job.usage.input_tokens} input · {job.usage.output_tokens} output · {job.usage.total_tokens} total
  </strong>;
}

export function CloudJobsWorkbench({ onAuthenticated = noopAuthenticated }: { onAuthenticated?: () => void }) {
  const [session, setSession] = useState<Session | null | undefined>(undefined);
  const [packets, setPackets] = useState<PacketSummary[]>([]);
  const [jobs, setJobs] = useState<CloudJob[]>([]);
  const [selectedId, setSelectedId] = useState(() => new URLSearchParams(window.location.search).get("job") ?? "");
  const [selected, setSelected] = useState<CloudJob | null>(null);
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [artifacts, setArtifacts] = useState<Array<{ result_artifact_id: string; sha256: string; validation_status: string; created_at: string }>>([]);
  const [artifactId, setArtifactId] = useState("");
  const [lastSubmission, setLastSubmission] = useState<{ idempotency_key: string; input_artifact_id: string; operation_kind: string } | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const pageController = useRef<AbortController | null>(null);
  const mutationController = useRef<AbortController | null>(null);

  const refresh = useCallback(async (jobId = selectedId) => {
    pageController.current?.abort(); const current = new AbortController(); pageController.current = current;
    try {
      const page = await listCloudJobs(current.signal);
      if (current.signal.aborted) return;
      setJobs(page.items);
      if (jobId) {
        const [job, eventPage, artifactPage] = await Promise.all([
          getCloudJob(jobId, current.signal), getCloudJobEvents(jobId, current.signal),
          getCloudJobArtifacts(jobId, current.signal),
        ]);
        if (!current.signal.aborted) { setSelected(job); setEvents(eventPage.items); setArtifacts(artifactPage.items); }
      }
    } catch (reason) {
      if ((reason as Error).name !== "AbortError") setError((reason as Error).message);
    }
  }, [selectedId]);

  useEffect(() => {
    const current = new AbortController();
    getSession(current.signal).then(setSession).catch((reason) => {
      if ((reason as WorkbenchError).status === 401) setSession(null);
      else if ((reason as Error).name !== "AbortError") { setSession(null); setError((reason as Error).message); }
    });
    return () => current.abort();
  }, []);

  useEffect(() => {
    if (!session) return;
    onAuthenticated();
    const current = new AbortController();
    listPackets(current.signal).then((value) => {
      if (!current.signal.aborted) { setPackets(value.packets); setArtifactId((old) => old || value.packets[0]?.artifact_id || ""); }
    }).catch((reason) => { if ((reason as Error).name !== "AbortError") setError((reason as Error).message); });
    void refresh();
    return () => current.abort();
  }, [session, onAuthenticated, refresh]);

  useEffect(() => {
    if (!session) return;
    const active = jobs.some((job) => job.status === "QUEUED" || job.status === "RUNNING");
    if (!active) return;
    const timer = window.setInterval(() => void refresh(), 750);
    return () => window.clearInterval(timer);
  }, [jobs, refresh, session]);

  useEffect(() => () => { pageController.current?.abort(); mutationController.current?.abort(); }, []);

  function choose(job: CloudJob) {
    const url = new URL(window.location.href); url.searchParams.set("job", job.job_id);
    window.history.pushState(null, "", url); setSelectedId(job.job_id); setSelected(job); setError("");
    void refresh(job.job_id);
  }

  async function send(body: { idempotency_key: string; input_artifact_id: string; operation_kind: string }) {
    mutationController.current?.abort(); const current = new AbortController(); mutationController.current = current;
    setBusy(true); setError(""); setMessage("");
    try {
      const response = await submitCloudJob(body, session?.csrf_token ?? "", current.signal);
      if (!current.signal.aborted) {
        setLastSubmission(body); setSelectedId(response.job.job_id); setSelected(response.job);
        const url = new URL(window.location.href); url.searchParams.set("job", response.job.job_id); window.history.pushState(null, "", url);
        setMessage(response.duplicate ? "Existing durable job returned; no new provider work created." : "Durable job queued for the separate worker.");
        await refresh(response.job.job_id);
      }
    } catch (reason) { if ((reason as Error).name !== "AbortError") setError((reason as Error).message); }
    finally { if (!current.signal.aborted) setBusy(false); }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (artifactId) void send({ idempotency_key: operationId(), input_artifact_id: artifactId, operation_kind: "SEMANTIC_DECOMPOSITION" });
  }

  if (session === undefined) return <main className="jobs-loading">Opening durable Jobs…</main>;
  if (session === null) return <Login onLogin={setSession} />;

  return <main className="jobs-workspace"><header className="jobs-hero"><div><span className="eyebrow">Cloud contract · offline-capable operations</span>
    <h1>Durable Jobs</h1><p>Enqueue registered immutable inputs and inspect the single-worker audit trail.</p></div>
    <button onClick={() => void refresh()} disabled={busy}>Refresh</button></header>
    <section className="jobs-submit"><h2>Submit registered input</h2><form onSubmit={submit}>
      <label>Registered artifact<select aria-label="Registered artifact" value={artifactId} onChange={(event) => setArtifactId(event.target.value)}>
        {!packets.length && <option value="">No registered artifacts</option>}
        {packets.map((packet) => <option key={packet.artifact_id} value={packet.artifact_id}>{packet.source.source_id} · {packet.artifact_id}</option>)}
      </select></label><label>Operation<input value="SEMANTIC_DECOMPOSITION" readOnly /></label>
      <button disabled={busy || !artifactId}>{busy ? "Submitting…" : "Queue durable job"}</button>
      <button type="button" disabled={busy || !lastSubmission} onClick={() => lastSubmission && void send(lastSubmission)}>Retry same submission</button>
    </form>{message && <p role="status" className="jobs-message">{message}</p>}{error && <p role="alert" className="jobs-error">{error}</p>}</section>
    <div className="jobs-layout"><section className="jobs-list"><div className="jobs-heading"><h2>Jobs</h2><span>{jobs.length}</span></div>
      {!jobs.length ? <p>No durable jobs.</p> : jobs.map((job) => <button key={job.job_id} className={job.job_id === selectedId ? "selected" : ""} onClick={() => choose(job)}>
        <span className={`job-state state-${job.status.toLowerCase()}`}>{job.status}</span><strong>{job.operation_kind}</strong><code>{job.job_id}</code><small>{job.provider} · {job.requested_model} · {job.attempt_count} attempts</small>
      </button>)}</section>
      <section className="job-detail">{!selected ? <p>Select a job to inspect its durable state.</p> : <>
        <div className="jobs-heading"><div><span className={`job-state state-${selected.status.toLowerCase()}`}>{selected.status}</span><h2>{selected.operation_kind}</h2></div><code>{selected.job_id}</code></div>
        {selected.recovery_required && <div className="recovery-banner" role="alert">Recovery required. Automatic provider retry is blocked.</div>}
        <dl className="job-facts"><div><dt>Input</dt><dd>{selected.input.source_id}<br/><code>{selected.input.artifact_id}</code><br/><code>{selected.input.sha256}</code></dd></div>
          <div><dt>Provider / requested model</dt><dd>{selected.provider} / {selected.requested_model}</dd></div>
          <div><dt>Reported model / request</dt><dd>{selected.provider_reported_model || "Not reported"} · {selected.model_identity_status || "pending"}<br/><code>{selected.provider_request_id || "No provider request ID"}</code></dd></div>
          <div><dt>Runtime / prompt</dt><dd><code>{String(selected.runtime_identity.git_sha || "")}</code><br/>{String(selected.prompt_identity.prompt_id)} v{String(selected.prompt_identity.prompt_version)}</dd></div>
          <div><dt>Configuration</dt><dd><code>{String(selected.configuration_identity.configuration_sha256 || "")}</code></dd></div>
          <div><dt>Retry owner / attempts</dt><dd>{selected.retry_owner} · {selected.attempt_count}/{selected.budget.max_attempts}</dd></div>
          <div><dt>Usage</dt><dd><Usage job={selected} /></dd></div>
          <div><dt>Validation / result</dt><dd>{selected.validation_status} · {selected.result_artifact?.artifact_id || "No result registered"}</dd></div>
          <div><dt>Created / started / ended</dt><dd><time>{selected.created_at}</time><br/><time>{selected.started_at || "Not started"}</time><br/><time>{selected.ended_at || "Not ended"}</time></dd></div>
          <div><dt>Last sanitized error</dt><dd>{selected.last_error || "None"}</dd></div></dl>
        <h3>Immutable events</h3><ol className="job-events">{events.map((event) => <li key={event.sequence}><span>{event.sequence}</span><strong>{event.event_type}</strong><time>{event.created_at}</time></li>)}</ol>
        <h3>Private result references</h3>{!artifacts.length ? <p>No result artifact.</p> : artifacts.map((artifact) => <div className="job-artifact" key={artifact.result_artifact_id}><strong>{artifact.validation_status}</strong><code>{artifact.result_artifact_id}</code><small>SHA-256 {artifact.sha256}</small></div>)}
      </>}</section></div>
  </main>;
}
