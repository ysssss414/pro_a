import { FormEvent, useCallback, useEffect, useRef, useState } from "react";

import {
  createNote, getResearchClaim, getResearchClaims, getResearchCoverage, getResearchHome,
  getResearchNode, getResearchRelation, getResearchSource, getResearchSources, searchResearch,
  updateNote, type Note, type ResearchRouteKind, type SearchResult,
} from "../api/research";
import { getSession, loginWorkbench, WorkbenchError } from "../api/workbench";
import { UnifiedResearchInspector } from "./UnifiedResearchInspector";
import type { InspectorData } from "./inspectorSelection";
import type { NodeDomainContext } from "../api/research";

type Route = { kind: ResearchRouteKind; id?: string };
type Data = Record<string, any>;
export type Session = { actor: string; mode: string; csrf_token?: string };

function parseRoute(): Route {
  const path = window.location.pathname;
  const match = path.match(/^\/(node|claim|source|relation)\/([^/]+)\/?$/);
  if (match) return { kind: match[1] as ResearchRouteKind, id: decodeURIComponent(match[2]) };
  if (path === "/coverage" || path === "/coverage/") return { kind: "coverage" };
  if (path === "/research/claims") return { kind: "claims" };
  if (path === "/research/sources") return { kind: "sources" };
  return { kind: "home" };
}

function pathFor(kind: ResearchRouteKind, id?: string) {
  if (kind === "home") return "/research";
  if (kind === "coverage") return "/coverage";
  if (kind === "claims" || kind === "sources") return "/research/" + kind;
  return "/" + kind + "/" + encodeURIComponent(id ?? "");
}

function objectRoute(item: SearchResult): Route {
  if (item.object_type === "NODE") return { kind: "node", id: item.object_id };
  if (item.object_type === "CLAIM") return { kind: "claim", id: item.object_id };
  if (item.object_type === "SOURCE") return { kind: "source", id: item.object_id };
  return { kind: "node", id: item.node_id ?? item.object_id };
}

function uuid() {
  return crypto.randomUUID ? crypto.randomUUID() : "00000000-0000-4000-8000-" + Date.now().toString().padStart(12, "0");
}

function Empty({ children }: { children: string }) {
  return <p className="research-empty">{children}</p>;
}

function Identity({ label, id, meta }: { label: string; id: string; meta?: string }) {
  return <div className="research-identity"><h1>{label}</h1>{meta && <p>{meta}</p>}<code>{id}</code></div>;
}

function PageNav({ page, onCursor }: { page: Data; onCursor: (value: string) => void }) {
  if (!page || page.total <= page.limit) return null;
  return <div className="research-pagination" aria-label="Pagination">
    <button disabled={page.previous_cursor === null} onClick={() => onCursor(page.previous_cursor ?? "")}>Previous</button>
    <span>{page.offset + 1}–{Math.min(page.offset + page.limit, page.total)} of {page.total}</span>
    <button disabled={page.next_cursor === null} onClick={() => onCursor(page.next_cursor ?? "")}>Next</button>
  </div>;
}

function DirectImpact({ impact, navigate }: { impact: Data | undefined; navigate: (route: Route) => void }) {
  const items = impact?.items ?? [];
  return <section className="research-section" aria-labelledby="direct-impact-heading">
    <div className="research-section-heading"><h2 id="direct-impact-heading">Direct Impact</h2><span>deterministic paths only</span></div>
    {!items.length ? <Empty>No recorded direct impact paths.</Empty> : <div className="research-card-list">{items.slice(0, 20).map((item: Data) =>
      <article className="research-card impact-compact" key={item.impact_id}>
        <div><strong>{item.reason_code}</strong><span className={item.is_current_impact ? "state-current" : "state-noncurrent"}>{item.official_or_staged}</span></div>
        <p>{item.relationship_types?.join(" · ")}</p>
        <ol className="compact-path">{item.path_steps?.map((step: Data, index: number) => <li key={index}>
          {step.object_type === "NODE" || step.object_type === "CLAIM" || step.object_type === "SOURCE" || step.object_type === "RELATION"
            ? <button onClick={() => navigate({ kind: step.object_type.toLowerCase() as ResearchRouteKind, id: step.object_id })}>{step.label}</button>
            : <span>{step.label}</span>}
          <small>{step.object_type} · {step.status}</small>
        </li>)}</ol>
      </article>)}</div>}
  </section>;
}

function FollowupNotes({ objectType, objectId, notes: initialNotes, csrf }:
  { objectType: string; objectId: string; notes: Note[]; csrf: string }) {
  const [notes, setNotes] = useState(initialNotes ?? []);
  const [text, setText] = useState("");
  const [status, setStatus] = useState<Note["status"]>("OPEN");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => setNotes(initialNotes ?? []), [initialNotes]);
  useEffect(() => () => controller.current?.abort(), []);

  async function add(event: FormEvent) {
    event.preventDefault();
    if (!text.trim()) return;
    controller.current?.abort(); controller.current = new AbortController(); setSaving(true); setError("");
    try {
      const response = await createNote({ operation_id: uuid(), object_type: objectType, object_id: objectId,
        text: text.trim(), status }, csrf, controller.current.signal);
      if (!controller.current.signal.aborted) { setNotes((items) => [response.note, ...items]); setText(""); }
    } catch (reason) { if ((reason as Error).name !== "AbortError") setError((reason as Error).message); }
    finally { if (!controller.current?.signal.aborted) setSaving(false); }
  }

  async function change(note: Note, nextStatus: Note["status"]) {
    controller.current?.abort(); controller.current = new AbortController(); setError("");
    try {
      const response = await updateNote(note.note_id, { operation_id: uuid(), expected_revision: note.revision,
        text: note.text, status: nextStatus }, csrf, controller.current.signal);
      if (!controller.current.signal.aborted) setNotes((items) => items.map((item) => item.note_id === note.note_id ? response.note : item));
    } catch (reason) { if ((reason as Error).name !== "AbortError") setError((reason as Error).message); }
  }

  return <section className="research-section notes-section">
    <div className="research-section-heading"><h2>Follow-up notes</h2><span>private · noncanonical · {notes.filter((note) => note.status === "OPEN").length} open</span></div>
    <form onSubmit={add} className="note-compose"><textarea aria-label="Follow-up note" value={text} onChange={(e) => setText(e.target.value)} placeholder="Record a concrete follow-up…" />
      <select aria-label="Note status" value={status} onChange={(e) => setStatus(e.target.value as Note["status"])}><option>OPEN</option><option>DEFERRED</option><option>DONE</option></select>
      <button disabled={saving || !text.trim()}>{saving ? "Saving…" : "Add note"}</button></form>
    {error && <p className="research-error" role="alert">{error}</p>}
    {!notes.length ? <Empty>No follow-up notes.</Empty> : <div className="note-list">{notes.map((note) => <article key={note.note_id}>
      <p>{note.text}</p><div><span>{note.operator} · revision {note.revision}</span>
      <select aria-label={`Status for ${note.text}`} value={note.status} onChange={(e) => void change(note, e.target.value as Note["status"])}><option>OPEN</option><option>DEFERRED</option><option>DONE</option></select></div>
    </article>)}</div>}
  </section>;
}

function Breadcrumbs({ route, navigate }: { route: Route; navigate: (route: Route) => void }) {
  const fromNode = new URLSearchParams(window.location.search).get("from_node");
  return <nav className="research-breadcrumbs" aria-label="Breadcrumbs">
    <button onClick={() => navigate({ kind: "home" })}>Research Home</button><span>/</span>
    {fromNode && route.kind !== "node" && <><button onClick={() => navigate({ kind: "node", id: fromNode })}>Origin Node</button><span>/</span></>}
    <strong>{route.kind === "home" ? "Home" : route.kind}{route.id ? ` · ${route.id}` : ""}</strong>
  </nav>;
}

export function ResearchLogin({ onLogin, title = "Research Explorer" }: { onLogin: (session: Session) => void; title?: string }) {
  const [token, setToken] = useState(""); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); const controller = new AbortController(); setBusy(true); setError("");
    try { await loginWorkbench(token, controller.signal); onLogin(await getSession(controller.signal)); }
    catch (reason) { setError((reason as Error).message); setBusy(false); }
  }
  return <main className="research-login"><form onSubmit={submit}><span className="eyebrow">{title}</span><h1>Sign in to investigate evidence</h1>
    <p>Uses the existing private Workbench session. Research reads are bounded and canonical data remains read-only.</p>
    <label>Workbench token<input type="password" value={token} onChange={(e) => setToken(e.target.value)} autoFocus /></label>
    {error && <p role="alert" className="research-error">{error}</p>}<button disabled={busy || token.length < 32}>{busy ? "Signing in…" : "Sign in"}</button></form></main>;
}

export function ResearchExplorer({ onAuthenticated = () => undefined }: { onAuthenticated?: () => void }) {
  const [route, setRoute] = useState<Route>(parseRoute);
  const [session, setSession] = useState<Session | null | undefined>(undefined);
  const [data, setData] = useState<Data | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [query, setQuery] = useState(() => new URLSearchParams(window.location.search).get("q") ?? "");
  const [searchType, setSearchType] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const pageController = useRef<AbortController | null>(null);
  const searchController = useRef<AbortController | null>(null);

  const navigate = useCallback((next: Route, values?: Record<string, string>) => {
    const params = new URLSearchParams(values);
    if (route.kind === "node" && route.id && next.kind !== "home" && next.kind !== "node") params.set("from_node", route.id);
    const url = pathFor(next.kind, next.id) + (params.size ? "?" + params : "");
    window.history.pushState(null, "", url); setRoute(next); setData(null); setError("");
  }, [route]);

  useEffect(() => {
    const pop = () => { setRoute(parseRoute()); setData(null); setError(""); };
    window.addEventListener("popstate", pop); return () => window.removeEventListener("popstate", pop);
  }, []);

  useEffect(() => {
    if (session) onAuthenticated();
  }, [session, onAuthenticated]);

  useEffect(() => {
    const controller = new AbortController();
    getSession(controller.signal).then(setSession).catch((reason) => {
      if ((reason as WorkbenchError).status === 401) setSession(null);
      else if ((reason as Error).name !== "AbortError") { setSession(null); setError((reason as Error).message); }
    });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!session) return;
    pageController.current?.abort(); const controller = new AbortController(); pageController.current = controller;
    setLoading(true); setError("");
    const params = Object.fromEntries(new URLSearchParams(window.location.search));
    let promise: Promise<Data>;
    if (route.kind === "node") promise = getResearchNode(route.id!, controller.signal);
    else if (route.kind === "claim") promise = getResearchClaim(route.id!, controller.signal);
    else if (route.kind === "source") promise = getResearchSource(route.id!, params, controller.signal);
    else if (route.kind === "relation") promise = getResearchRelation(route.id!, controller.signal);
    else if (route.kind === "coverage") promise = getResearchCoverage(params.cursor ?? "", controller.signal);
    else if (route.kind === "claims") promise = getResearchClaims(params, controller.signal);
    else if (route.kind === "sources") promise = getResearchSources(params, controller.signal);
    else promise = getResearchHome(controller.signal);
    promise.then((value) => { if (!controller.signal.aborted) setData(value); })
      .catch((reason) => { if ((reason as Error).name !== "AbortError" && !controller.signal.aborted) setError((reason as Error).message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [route, session]);

  useEffect(() => {
    searchController.current?.abort();
    if (query.trim().length < 2 || !session) { setResults([]); return; }
    const controller = new AbortController(); searchController.current = controller;
    const timer = window.setTimeout(() => {
      searchResearch(query, searchType, controller.signal)
        .then((value) => { if (!controller.signal.aborted) setResults(value.results); })
        .catch((reason) => { if ((reason as Error).name !== "AbortError" && !controller.signal.aborted) setError((reason as Error).message); });
    }, 160);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [query, searchType, session]);

  if (session === undefined) return <main className="research-loading">Opening Research Explorer…</main>;
  if (session === null) return <ResearchLogin onLogin={setSession} />;

  const go = (next: Route) => { setResults([]); setQuery(""); navigate(next); };
  const setCursor = (cursor: string) => navigate(route, { ...Object.fromEntries(new URLSearchParams(window.location.search)), cursor });

  return <main className="research-workspace">
    <section className="research-search-shell">
      <div><span className="eyebrow">Evidence navigation</span><h1>Research Explorer</h1></div>
      <div className="global-search"><label htmlFor="research-search">Search Nodes, Claims, Sources, Questions and Gaps</label>
        <div><input id="research-search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Company, product, evidence…" />
        <select aria-label="Search result type" value={searchType} onChange={(e) => setSearchType(e.target.value)}><option value="">All types</option><option value="NODE">Nodes</option><option value="CLAIM">Claims</option><option value="SOURCE">Sources</option><option value="RESEARCH_QUESTION">Questions</option><option value="GAP">Gaps</option></select></div>
        {!!results.length && <div className="global-results" role="listbox">{results.map((item) => <button key={`${item.object_type}:${item.object_id}`} onClick={() => go(objectRoute(item))}>
          <span>{item.object_type === "NODE" ? item.node_type : item.object_type}</span><strong>{item.label}</strong><small>{item.subtitle} · {item.object_id}</small></button>)}</div>}
      </div>
    </section>
    <Breadcrumbs route={route} navigate={go} />
    {loading && <p className="research-loading" role="status">Loading research snapshot…</p>}
    {error && <div className="research-error" role="alert"><strong>Unable to load this research page.</strong><span>{error}</span></div>}
    {!loading && data && <ResearchPage route={route} data={data} csrf={session.csrf_token ?? ""} navigate={navigate} setCursor={setCursor} />}
  </main>;
}

function ResearchPage({ route, data, csrf, navigate, setCursor }:
  { route: Route; data: Data; csrf: string; navigate: (route: Route, values?: Record<string, string>) => void; setCursor: (cursor: string) => void }) {
  const go = (kind: ResearchRouteKind, id?: string) => navigate({ kind, id });
  if (route.kind === "home") return <div className="research-content">
    <section className="research-hero"><div><span className="eyebrow">Daily research flow</span><h2>Start with a company, product or piece of evidence.</h2><p>Follow recorded paths through Current View, Direct Impact, Claims, Sources, relations and unresolved work.</p></div>
      <div className="hero-actions"><button onClick={() => go("claims")}>Browse Claims</button><button onClick={() => go("sources")}>Browse Sources</button><button onClick={() => go("coverage")}>Inspect Coverage</button></div></section>
    <div className="research-stats">{Object.entries(data.stats).map(([key, value]) => <div key={key}><strong>{String(value)}</strong><span>{key.replaceAll("_", " ")}</span></div>)}</div>
    <div className="research-columns"><section className="research-section"><div className="research-section-heading"><h2>Recent official Views</h2><span>canonical</span></div>
      {data.recent_official_views.map((view: Data) => <button className="research-row" key={view.view_id} onClick={() => navigate({ kind: "node", id: view.node_id }, { view: view.view_id })}><strong>{view.content_json?.one_line_conclusion ?? view.version}</strong><small>{view.change_level} · {view.revision_date}</small></button>)}</section>
    <section className="research-section"><div className="research-section-heading"><h2>Open gaps</h2><span>{data.open_gaps.length}</span></div>{data.open_gaps.length ? data.open_gaps.map((gap: Data) => <button className="research-row" key={gap.gap_id} onClick={() => go("node", gap.node_id)}><strong>{gap.title}</strong><small>{gap.canonical_name} · {gap.status}</small></button>) : <Empty>No open gaps.</Empty>}</section></div>
    <DirectImpact impact={data.impact} navigate={(r) => navigate(r)} />
    <section className="research-section"><div className="research-section-heading"><h2>Open follow-up notes</h2><span>private</span></div>{data.open_notes.length ? data.open_notes.map((note: Note) => <button className="research-row" key={note.note_id} disabled={!note.route_kind || note.route_kind === "home"} onClick={() => go(note.route_kind ?? "home", note.route_id)}><strong>{note.text}</strong><small>{note.object_type} · {note.object_id}</small></button>) : <Empty>No open follow-up notes.</Empty>}</section>
  </div>;

  if (route.kind === "claims") return <div className="research-content"><Identity label="Claims" id="canonical evidence index" meta="Bounded server-side filtering" />
    <FilterBar fields={[['q','Text'],['source_id','Source ID'],['node_id','Node ID'],['role','Role'],['nature','Nature'],['status','Status']]} route={route} navigate={navigate} />
    <ClaimList page={data} navigate={navigate} /><PageNav page={data} onCursor={setCursor} /></div>;

  if (route.kind === "sources") return <div className="research-content"><Identity label="Sources" id="safe source index" meta="Paths and arbitrary private metadata are excluded" />
    <FilterBar fields={[['q','Title / author / organization'],['source_type','Source type'],['status','Status'],['date_from','From date'],['date_to','To date']]} route={route} navigate={navigate} />
    <div className="research-card-list">{data.items.map((source: Data) => <button className="research-card research-card-button" key={source.source_id} onClick={() => go("source", source.source_id)}><strong>{source.title}</strong><span>{source.source_type} · {source.status}</span><small>{source.claim_count} Claims · {source.attributed_node_count} attributed Nodes · {source.business_date}</small></button>)}</div>
    <PageNav page={data} onCursor={setCursor} /></div>;

  if (route.kind === "node") {
    return <div className="research-content"><ResearchNodeInspector data={data as InspectorData} csrf={csrf} navigate={navigate} /></div>;
  }

  if (route.kind === "claim") {
    const claim = data.claim;
    return <div className="research-content"><Identity label={claim.statement} id={claim.claim_id} meta={`${claim.nature} · ${claim.status}`} />
      <section className="research-section evidence-focus"><div className="research-section-heading"><h2>Evidence</h2><span>{claim.fact_time || claim.publication_time || "date unknown"}</span></div><blockquote>{claim.evidence_excerpt || "No evidence excerpt recorded."}</blockquote><dl><dt>Pointer</dt><dd>{claim.evidence_pointer || "not recorded"}</dd><dt>Locator</dt><dd>{claim.source_locator?.locator ?? claim.source_locator?.status ?? "not recorded"}</dd><dt>Scope</dt><dd>{claim.scope || "not recorded"}</dd></dl></section>
      <section className="research-section"><div className="research-section-heading"><h2>Source</h2><span>{data.source.source_rank}</span></div><button className="research-row" onClick={() => navigate({ kind: "source", id: data.source.source_id }, { from_node: new URLSearchParams(window.location.search).get("from_node") ?? "" })}><strong>{data.source.title}</strong><small>{data.source.source_type} · {data.source.organization} · {data.source.publication_time}</small></button></section>
      <section className="research-section"><div className="research-section-heading"><h2>Explicit Node attribution</h2><span>recorded links only</span></div>{data.linked_nodes.length ? data.linked_nodes.map((node: Data) => <button className="research-row" key={node.node_id} onClick={() => go("node", node.node_id)}><strong>{node.canonical_name}</strong><small>{node.primary_type} · role {node.role}</small></button>) : <Empty>No explicit Claim–Node link.</Empty>}</section>
      <section className="research-section"><div className="research-section-heading"><h2>Official View citations</h2><span>drafts excluded</span></div>{data.official_view_citations.length ? data.official_view_citations.map((view: Data) => <button className="research-row" key={view.view_id} onClick={() => navigate({ kind: "node", id: view.node_id }, { view: view.view_id })}><strong>{view.canonical_name}</strong><small>{view.version} · {view.view_rank === 1 ? "current official" : "prior official"}</small></button>) : <Empty>No official View cites this Claim.</Empty>}</section>
      {(data.claim_relations.length > 0 || data.relation_evidence.length > 0) && <section className="research-section"><div className="research-section-heading"><h2>Contradiction &amp; relation metadata</h2><span>recorded only</span></div>{data.claim_relations.map((relation: Data) => <article className="research-card" key={relation.relation_id}><strong>{relation.relation_type}</strong><p>{relation.reason}</p><small>{relation.from_claim_id} → {relation.to_claim_id}</small></article>)}{data.relation_evidence.map((relation: Data) => <button className="research-row" key={`${relation.relation_id}:${relation.evidence_role}`} onClick={() => go("relation", relation.relation_id)}><strong>{relation.relation_type}</strong><small>{relation.evidence_role} · {relation.status}</small></button>)}</section>}
      <DirectImpact impact={data.impact} navigate={navigate} /><FollowupNotes objectType="CLAIM" objectId={claim.claim_id} notes={data.notes} csrf={csrf} />
    </div>;
  }

  if (route.kind === "source") {
    const source = data.source;
    return <div className="research-content"><Identity label={source.title} id={source.source_id} meta={`${source.source_type} · ${source.status}`} />
      <section className="research-section"><div className="research-section-heading"><h2>Safe Source metadata</h2><span>{source.source_rank}</span></div><dl className="source-safe-metadata"><dt>Organization</dt><dd>{source.organization || "not recorded"}</dd><dt>Author</dt><dd>{source.author || "not recorded"}</dd><dt>Published</dt><dd>{source.publication_time || "not recorded"}</dd><dt>Ingested</dt><dd>{source.ingested_at}</dd><dt>Processing</dt><dd>{source.ingestion_mode} · {source.analysis_mode}</dd></dl></section>
      <section className="research-section"><div className="research-section-heading"><h2>Claims from Source</h2><span>{data.claims.total}</span></div><FilterBar fields={[['claim_q','Text'],['claim_status','Status'],['claim_nature','Nature']]} route={route} navigate={navigate} /><ClaimList page={data.claims} navigate={navigate} /><PageNav page={data.claims} onCursor={(cursor) => navigate(route, { ...Object.fromEntries(new URLSearchParams(window.location.search)), claim_cursor: cursor })} /></section>
      <section className="research-section"><div className="research-section-heading"><h2>Explicitly connected Nodes</h2><span>source or Claim path</span></div>{data.explicit_nodes.map((node: Data) => <button className="research-row" key={node.node_id} onClick={() => go("node", node.node_id)}><strong>{node.canonical_name}</strong><small>{node.primary_type} · {node.attribution_path} path</small></button>)}</section>
      <DirectImpact impact={data.impact} navigate={navigate} /><FollowupNotes objectType="SOURCE" objectId={source.source_id} notes={data.notes} csrf={csrf} />
    </div>;
  }

  if (route.kind === "relation") {
    const relation = data.relation;
    return <div className="research-content"><Identity label={`${relation.from_name} → ${relation.relation_type} → ${relation.to_name}`} id={relation.relation_id} meta={`${relation.status} · confidence ${relation.confidence ?? "unknown"}`} />
      <div className="relation-endpoints"><button onClick={() => go("node", relation.from_node_id)}><span>Source Node</span><strong>{relation.from_name}</strong><small>{relation.from_type}</small></button><span>→ {relation.relation_type} →</span><button onClick={() => go("node", relation.to_node_id)}><span>Target Node</span><strong>{relation.to_name}</strong><small>{relation.to_type}</small></button></div>
      <section className="research-section"><div className="research-section-heading"><h2>Status &amp; time</h2><span>{data.status_semantics.current ? "CURRENT" : data.status_semantics.categorical ? "CATEGORICAL" : "HISTORICAL"}</span></div><dl><dt>Scope</dt><dd>{relation.scope || "not recorded"}</dd><dt>Valid from</dt><dd>{relation.valid_from || "not supplied"}</dd><dt>Valid to</dt><dd>{relation.valid_to || "not supplied"}</dd><dt>Temporal category</dt><dd>{relation.temporal_category || "not recorded"}</dd></dl></section>
      <section className="research-section"><div className="research-section-heading"><h2>Recorded evidence</h2><span>{data.evidence.length}</span></div>{data.evidence.length ? data.evidence.map((evidence: Data, index: number) => <article className="research-card" key={index}><strong>{evidence.evidence_role} · {evidence.provenance_mode}</strong><p>{evidence.statement || evidence.evidence_id || "Evidence identity unavailable"}</p><div className="card-actions">{evidence.claim_id && <button onClick={() => go("claim", evidence.claim_id)}>Open Claim</button>}{evidence.source_id && <button onClick={() => go("source", evidence.source_id)}>Open Source</button>}</div></article>) : <Empty>No recorded evidence link.</Empty>}</section>
      <section className="research-section"><div className="research-section-heading"><h2>Relation history</h2><span>same endpoints and type</span></div>{data.history.map((item: Data) => <article className="research-card" key={item.relation_id}><strong>{item.status}</strong><p>{item.scope}</p><small>{item.valid_from || "unknown"} → {item.valid_to || "open"}</small></article>)}</section>
      <FollowupNotes objectType="RELATION" objectId={relation.relation_id} notes={data.notes} csrf={csrf} />
    </div>;
  }

  return <div className="research-content"><Identity label="Coverage & research gaps" id="read-only analytical projection" meta="Coverage match ≠ safe attribution" />
    <div className="coverage-warning"><strong>Audit output only.</strong><span>Exact name and alias matches remain review signals and never create Claim–Node attribution.</span></div>
    <div className="research-stats">{Object.entries(data.summary.node_coverage).map(([key, value]) => <div key={key}><strong>{String(value)}</strong><span>{key.replaceAll("_", " ")}</span></div>)}</div>
    <section className="research-section"><div className="research-section-heading"><h2>Entity coverage</h2><span>{data.node_coverage.total}</span></div>{data.node_coverage.items.map((node: Data) => <button className="research-row" key={node.node_id} onClick={() => go("node", node.node_id)}><strong>{node.canonical_name}</strong><small>{node.knowledge_level} · {node.claim_count} Claims · {node.source_count} Sources</small></button>)}<PageNav page={data.node_coverage} onCursor={setCursor} /></section>
    <section className="research-section"><div className="research-section-heading"><h2>Unlinked Claims</h2><span>{data.unlinked_claims.total}</span></div>{data.unlinked_claims.items.map((claim: Data) => <button className="research-row" key={claim.claim_id} onClick={() => go("claim", claim.claim_id)}><strong>{claim.statement}</strong><small>{claim.audit_bucket} · no canonical link created</small></button>)}</section>
    <section className="research-section"><div className="research-section-heading"><h2>Known gaps</h2><span>{data.knowledge_gaps.length}</span></div>{data.knowledge_gaps.map((gap: Data) => <article className="research-card" key={gap.gap_id}><strong>{gap.title}</strong><p>{gap.description}</p><div className="card-actions"><button onClick={() => go("node", gap.node_id)}>Open {gap.canonical_name}</button></div><FollowupNotes objectType="GAP" objectId={gap.gap_id} notes={gap.notes ?? []} csrf={csrf} /></article>)}</section>
  </div>;
}

export function ResearchNodeInspector({ data, csrf, navigate, domainContext }:
  { data: InspectorData; csrf: string; navigate: (route: Route, values?: Record<string, string>) => void;
    domainContext?: NodeDomainContext | null }) {
  return <UnifiedResearchInspector key={data.node.node_id} data={data} domainContext={domainContext}
    navigate={navigate} notesSection={<FollowupNotes objectType="NODE" objectId={data.node.node_id} notes={data.notes} csrf={csrf} />} />;
}

function ClaimList({ page, navigate }: { page: Data; navigate: (route: Route) => void }) {
  if (!page.items.length) return <Empty>No Claims match these filters.</Empty>;
  return <div className="research-card-list">{page.items.map((claim: Data) => <button className="research-card research-card-button" key={claim.claim_id} onClick={() => navigate({ kind: "claim", id: claim.claim_id })}>
    <strong>{claim.statement}</strong><span>{claim.nature} · {claim.status} · {claim.business_date}</span><small>{claim.source_title} · {claim.linked_nodes.length} explicit Node links · {claim.official_view_citations.length} official View citations</small>
  </button>)}</div>;
}

function FilterBar({ fields, route, navigate }: { fields: string[][]; route: Route; navigate: (route: Route, values?: Record<string, string>) => void }) {
  const initial = Object.fromEntries(new URLSearchParams(window.location.search));
  const [values, setValues] = useState<Record<string, string>>(initial);
  useEffect(() => setValues(Object.fromEntries(new URLSearchParams(window.location.search))), [route.kind, route.id]);
  function submit(event: FormEvent) { event.preventDefault(); const next = { ...values }; delete next.cursor; delete next.claim_cursor; navigate(route, next); }
  return <form className="research-filters" onSubmit={submit}>{fields.map(([key, label]) => <label key={key}>{label}<input value={values[key] ?? ""} onChange={(e) => setValues({ ...values, [key]: e.target.value })} /></label>)}<button>Apply filters</button></form>;
}
