import { useEffect, useState, type ReactNode } from "react";

import { getNodeDomainContext, type NodeDomainContext, type ResearchRouteKind } from "../api/research";
import { CurrentViewWorkbench } from "./CurrentViewWorkbench";
import { CompanyMaterialsPanel } from "./CompanyMaterialsPanel";
import {
  currentViewSummary, relationSummary, selectInspectorClaims, selectLatestEvidence,
  selectOpenGaps, selectRelatedSources, type InspectorData,
} from "./inspectorSelection";

type Route = { kind: ResearchRouteKind; id?: string };
type Navigate = (route: Route, values?: Record<string, string>) => void;
const LIMIT = { claims: 3, evidence: 3, impact: 3, gaps: 3, sources: 5, relations: 3 };

function Section({ title, meta, children, className = "" }: { title: string; meta?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={`research-section unified-section ${className}`} aria-label={title}>
    <div className="research-section-heading"><h2>{title}</h2>{meta && <span>{meta}</span>}</div>{children}
  </section>;
}

function More({ total, limit, expanded, onClick, noun }: { total: number; limit: number; expanded: boolean; onClick: () => void; noun: string }) {
  if (total <= limit) return null;
  return <button type="button" className="inspector-more" aria-expanded={expanded} onClick={onClick}>
    {expanded ? `Show less ${noun}` : `Show all ${total} ${noun}`}
  </button>;
}

export function UnifiedResearchInspector({ data, domainContext, navigate, notesSection }: {
  data: InspectorData; domainContext?: NodeDomainContext | null; navigate: Navigate; notesSection: ReactNode;
}) {
  const [loadedContext, setLoadedContext] = useState<NodeDomainContext | null>(null);
  const [contextError, setContextError] = useState("");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [workbenchOpen, setWorkbenchOpen] = useState(false);
  useEffect(() => {
    if (domainContext !== undefined) return;
    const controller = new AbortController();
    setLoadedContext(null); setContextError("");
    getNodeDomainContext(data.node.node_id, controller.signal).then((value) => {
      if (!controller.signal.aborted) setLoadedContext(value);
    }).catch((reason) => {
      if (!controller.signal.aborted) setContextError((reason as Error).message);
    });
    return () => controller.abort();
  }, [data.node.node_id, domainContext]);

  const context = domainContext === undefined ? loadedContext : domainContext;
  const nodeId = data.node.node_id;
  const open = (kind: ResearchRouteKind, id: string) => navigate({ kind, id }, { from_node: nodeId });
  const toggle = (key: string) => setExpanded((value) => ({ ...value, [key]: !value[key] }));
  const claims = selectInspectorClaims(data);
  const evidence = selectLatestEvidence(data);
  const gaps = selectOpenGaps(data);
  const sources = selectRelatedSources(data);
  const relations = relationSummary(data);
  const view = currentViewSummary(data.current_view);
  const sourceBounded = sources.length >= 20 && data.coverage.sources <= sources.length;
  const sourceTotal = sourceBounded ? `at least ${sources.length} (bounded)` : String(data.coverage.sources);
  const sourceById = new Map(sources.map((source) => [source.source_id, source]));
  const visible = <T,>(items: T[], key: keyof typeof LIMIT) => expanded[key] ? items : items.slice(0, LIMIT[key]);

  return <div className="unified-inspector" aria-label={`Research Inspector for ${data.node.canonical_name}`}>
    <header className="inspector-identity">
      <div className="inspector-identity-top"><h1>{data.node.canonical_name}</h1><span>{data.node.primary_type}</span></div>
      <div className="inspector-badges"><span>Canonical Production Node</span><span>{data.node.status}</span></div>
      {data.node.description && <p>{data.node.description}</p>}
      {!!data.node.aliases?.length && <p>Aliases: {data.node.aliases.join(" · ")}</p>}
      <code>{nodeId}</code>
    </header>

    <Section title="Domains / Navigation Context">
      {contextError ? <p role="alert" className="research-error">Unable to load navigation context: {contextError}</p>
        : !context ? <p role="status" className="research-empty">Loading navigation context…</p>
          : context.navigation_contexts.length ? <div className="inspector-context-list">{context.navigation_contexts.map((item) =>
            <span key={`${item.domain_id}:${item.root_node_id}`}>{item.display_name}</span>)}</div>
            : <p className="research-empty">No navigation context recorded.</p>}
      <p className="inspector-small-label">Operational assignment</p>
      <p className="inspector-subtle">{context?.operational_domain_assignments.map((item) => item.primary_domain).join(" · ") || "None recorded"}</p>
    </Section>

    <Section title="Current View" meta={data.current_view?.version ?? "No official View"} className="inspector-view">
      {data.current_view ? <>
        {view.conclusion ? <p className="inspector-conclusion">{view.conclusion}</p> : <p className="research-empty">No one-line conclusion recorded.</p>}
        {!!view.support.length && <ul>{view.support.map((item, index) => <li key={index}>{item}</li>)}</ul>}
        {view.recentChange && <p><strong>Recent change</strong> · {view.recentChange}</p>}
        <small>{[data.current_view.change_level, data.current_view.revision_date || data.current_view.confirmed_at].filter(Boolean).join(" · ")}</small>
      </> : <p className="research-empty">No official Current View.</p>}
    </Section>

    {data.node.primary_type === "Company" && data.node.status === "active" &&
      <CompanyMaterialsPanel companyId={nodeId} navigate={navigate} />}

    <Section title="Key Claims" meta={`${visible(claims, "claims").length} visible of ${data.claims.total} linked`}>
      {!claims.length ? <p className="research-empty">No explicit Claims linked.</p> : visible(claims, "claims").map(({ claim, label }) =>
        <article className="inspector-row" key={claim.claim_id}><span className="inspector-tag">{label}</span>
          <strong>{claim.statement}</strong><small>{claim.business_date} · {claim.status}</small>
          <button onClick={() => open("claim", claim.claim_id)}>Open Claim</button></article>)}
      {data.claims.total > data.claims.items.length && <p className="inspector-bounded">Showing selection from {data.claims.items.length} of {data.claims.total} returned Claims; official trigger details outside this page are unavailable.</p>}
      <More total={claims.length} limit={LIMIT.claims} expanded={!!expanded.claims} onClick={() => toggle("claims")} noun="Claims" />
      {data.claims.total > data.claims.items.length && <button className="inspector-more" onClick={() => navigate({ kind: "claims" }, { node_id: nodeId })}>Browse all linked Claims</button>}
    </Section>

    <Section title="Latest Evidence" meta="explicit Node links">
      {!evidence.length ? <p className="research-empty">No recent Evidence available.</p> : visible(evidence, "evidence").map((claim) =>
        <article className="inspector-row" key={claim.claim_id}><strong>{claim.statement}</strong>
          {claim.evidence_excerpt && <p>{claim.evidence_excerpt}</p>}
          <small>{claim.business_date} · {claim.status} · {claim.source_title}{sourceById.get(claim.source_id)?.source_rank ? ` · ${sourceById.get(claim.source_id)?.source_rank}` : ""}</small>
          <div className="inspector-actions"><button onClick={() => open("claim", claim.claim_id)}>Open Claim</button><button onClick={() => open("source", claim.source_id)}>Open Source</button></div></article>)}
      {data.claims.total > data.claims.items.length && <p className="inspector-bounded">Latest Evidence is selected from {data.claims.items.length} of {data.claims.total} linked Claims in the bounded Node page.</p>}
      <More total={evidence.length} limit={LIMIT.evidence} expanded={!!expanded.evidence} onClick={() => toggle("evidence")} noun="Evidence" />
    </Section>

    <div className="inspector-pair">
      <Section title="Direct Impact" meta={`${data.impact?.items.length ?? 0} paths`}>
        {!data.impact?.items.length ? <p className="research-empty">No recorded Direct Impact paths.</p>
          : visible(data.impact.items, "impact").map((item) => <article className="inspector-row" key={item.impact_id}>
            <strong>{item.reason_code}</strong><small>{item.official_or_staged} · {item.relationship_types.join(" · ")}</small>
            <ol className="inspector-path">{item.path_steps.map((step, index) => <li key={index}>
              {["NODE", "CLAIM", "SOURCE", "RELATION"].includes(step.object_type)
                ? <button onClick={() => open(step.object_type.toLowerCase() as ResearchRouteKind, step.object_id)}>{step.label}</button>
                : <span>{step.label}</span>} <small>{step.object_type} · {step.status}</small></li>)}</ol>
          </article>)}
        <More total={data.impact?.items.length ?? 0} limit={LIMIT.impact} expanded={!!expanded.impact} onClick={() => toggle("impact")} noun="paths" />
      </Section>
      <Section title="Open Gaps" meta={`${gaps.length} unresolved`}>
        {!gaps.length ? <p className="research-empty">No open Knowledge Gaps.</p> : visible(gaps, "gaps").map((gap) =>
          <article className="inspector-row" key={gap.gap_id}><strong>{gap.title}</strong><small>{gap.status} · freshness due {gap.freshness_due || "not set"}</small></article>)}
        <More total={gaps.length} limit={LIMIT.gaps} expanded={!!expanded.gaps} onClick={() => toggle("gaps")} noun="open gaps" />
        {data.knowledge_gaps.length > gaps.length && <details className="inspector-detail"><summary>Show all gaps ({data.knowledge_gaps.length})</summary>
          {data.knowledge_gaps.map((gap) => <p key={gap.gap_id}>{gap.title} · {gap.status}</p>)}</details>}
      </Section>
    </div>

    <Section title="Research Question">
      {data.research_question ? <><p className="inspector-question">{data.research_question.question}</p>
        {data.research_question.current_answer && <p>{data.research_question.current_answer}</p>}
        <small>{data.research_question.status} · confidence {data.research_question.confidence ?? "unknown"}</small>
        {!!data.research_question.key_variables?.length && <p>Key variables: {data.research_question.key_variables.join(" · ")}</p>}</>
        : <p className="research-empty">No Research Question.</p>}
    </Section>

    <Section title="Related Sources" meta={`Showing ${visible(sources, "sources").length} of ${sourceTotal}`}>
      {!sources.length ? <p className="research-empty">No linked Sources.</p> : visible(sources, "sources").map((source) =>
        <article className="inspector-row" key={source.source_id}><strong>{source.title}</strong>
          <small>{[source.organization, source.publication_time || source.ingested_at, source.source_type, source.source_rank].filter(Boolean).join(" · ")}</small>
          <button onClick={() => open("source", source.source_id)}>Open Source</button></article>)}
      <More total={sources.length} limit={LIMIT.sources} expanded={!!expanded.sources} onClick={() => toggle("sources")} noun="Sources" />
    </Section>

    <Section title="Relations" meta={`${relations.count} recorded`}>
      {!relations.count ? <p className="research-empty">No recorded Relations.</p> : <>
        <p className="inspector-subtle">{Object.entries(relations.statuses).map(([status, count]) => `${status} ${count}`).join(" · ")}</p>
        <p className="inspector-subtle">{Object.entries(relations.types).map(([type, count]) => `${type} ${count}`).join(" · ")}</p>
        {visible(data.relations, "relations").map((relation) => <article className="inspector-row" key={relation.relation_id}>
          <strong>{relation.from_name} → {relation.relation_type} → {relation.to_name}</strong>
          <small>{relation.status} · {relation.evidence_count} evidence links</small>
          <button onClick={() => open("relation", relation.relation_id)}>Open Relation</button></article>)}
        <More total={relations.count} limit={LIMIT.relations} expanded={!!expanded.relations} onClick={() => toggle("relations")} noun="Relations" />
      </>}
    </Section>

    <Section title="Research Coverage" meta={data.coverage.knowledge_level || "level unknown"}>
      <p className="inspector-subtle">{data.coverage.claims ?? data.claims.total} Claims · {sourceBounded ? `${sources.length}+` : data.coverage.sources} Sources · {data.coverage.official_views ?? Number(!!data.current_view)} official Views · {data.coverage.questions ?? Number(!!data.research_question)} Questions · {data.coverage.gaps ?? data.knowledge_gaps.length} Gaps</p>
    </Section>

    {notesSection}
    <details className="research-section inspector-maintenance" onToggle={(event) => setWorkbenchOpen(event.currentTarget.open)}>
      <summary>Open Current View details / Workbench</summary>
      {workbenchOpen && <CurrentViewWorkbench nodeId={nodeId} onOpenSource={(id) => open("source", id)} onOpenClaim={(id) => open("claim", id)} />}
    </details>
  </div>;
}
