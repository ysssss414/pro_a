import { useCallback, useEffect, useState } from "react";

import {
  getNodeDomainContext, getResearchDomains, getResearchDomainTree, getResearchNode, getResearchStructureMap,
  getQualifiedStructureMap, getQualifiedOverlaySummary, getQualifiedGovernance, getQualifiedNode,
  getQualifiedCanonicalProvenance, searchQualified,
  searchResearch, type NavigationDomain, type NavigationNode, type NavigationTree,
  type NodeDomainContext, type ResearchRouteKind, type SearchResult, type StructureMapMode, type StructureMapResult,
  type QualifiedMapResult, type QualifiedIdentity,
} from "../api/research";
import { getSession, WorkbenchError } from "../api/workbench";
import { ResearchLogin, ResearchNodeInspector, type Session } from "./ResearchExplorer";
import type { InspectorData } from "./inspectorSelection";
import { SemanticStructureMap } from "./SemanticStructureMap";
import { QualifiedStructureMap } from "./QualifiedStructureMap";
import { QualifiedResearchInspector } from "./QualifiedResearchInspector";

function readLocation() {
  const params = new URLSearchParams(window.location.search);
  const overlay = params.get("overlay") === "qualified" ? "qualified" : "canonical";
  const qualified = overlay === "qualified" ? params.get("qualified") ?? "" : "";
  return { domain: params.get("domain") ?? "", node: qualified ? "" : params.get("node") ?? "",
    qualified, overlay, map: params.get("map") ?? "", depth: params.get("depth") ?? "" };
}

function ancestorPath(roots: NavigationNode[], nodeId: string): string[] {
  for (const root of roots) {
    if (root.node_id === nodeId) return [root.node_id];
    const path = ancestorPath(root.children, nodeId);
    if (path.length) return [root.node_id, ...path];
  }
  return [];
}

export function DomainHierarchyPanel({ domains, domainId, tree, loading, error, selectedNodeId, onDomain, onNode }:
  { domains: NavigationDomain[]; domainId: string; tree: NavigationTree | null; loading: boolean;
    error: string; selectedNodeId: string; onDomain: (id: string) => void; onNode: (id: string) => void }) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!tree) return;
    const path = ancestorPath(tree.roots, selectedNodeId);
    setExpanded(new Set([...tree.roots.map((root) => root.node_id), ...path.slice(0, -1)]));
  }, [tree, selectedNodeId]);

  function branch(node: NavigationNode) {
    const open = expanded.has(node.node_id);
    return <li key={`${node.node_id}:${node.depth}`} role="none">
      <div className="industry-tree-row" style={{ paddingInlineStart: `${node.depth * 16}px` }}>
        {node.has_children ? <button type="button" className="industry-toggle" aria-label={`${open ? "Collapse" : "Expand"} ${node.canonical_name}`}
          aria-expanded={open} onClick={() => setExpanded((current) => {
            const next = new Set(current); if (open) next.delete(node.node_id); else next.add(node.node_id); return next;
          })}>{open ? "▾" : "▸"}</button> : <span className="industry-toggle-spacer" aria-hidden="true" />}
        <button type="button" role="treeitem" aria-level={node.depth + 1} aria-selected={selectedNodeId === node.node_id}
          className={`industry-node ${selectedNodeId === node.node_id ? "is-selected" : ""}`}
          onClick={() => onNode(node.node_id)}>{node.canonical_name}<small>{node.primary_type}</small></button>
      </div>
      {node.anomaly && <p className="industry-anomaly" role="status">Hierarchy anomaly: {node.anomaly}</p>}
      {open && !!node.children.length && <ul role="group">{node.children.map(branch)}</ul>}
    </li>;
  }

  return <aside className="industry-hierarchy" aria-label="Domain and hierarchy">
    <div className="industry-pane-heading"><span className="eyebrow">Navigation context</span><h2>Domain / Hierarchy</h2></div>
    <label htmlFor="industry-domain">Domain</label>
    <select id="industry-domain" value={domainId} onChange={(event) => onDomain(event.target.value)}>
      {!domainId && <option value="">Select a domain</option>}
      {!!domainId && !domains.some((domain) => domain.domain_id === domainId) && <option value={domainId}>Unknown domain</option>}
      {domains.map((domain) => <option key={domain.domain_id} value={domain.domain_id}>{domain.display_name}</option>)}
    </select>
    {loading && <p role="status">Loading canonical hierarchy…</p>}
    {error && <p role="alert" className="research-error">{error}</p>}
    {!loading && !error && !domains.length && <p className="research-empty">No navigation domains are available.</p>}
    {!loading && !error && tree && <>
      <p className="industry-tree-count">{tree.visible_node_count} visible canonical Nodes</p>
      {tree.truncated && <p role="status" className="industry-truncation">Tree truncated: {tree.truncation_reasons.join(", ")}</p>}
      {tree.roots.length ? <div className="industry-tree-scroll"><ul role="tree" aria-label={`${tree.display_name} canonical hierarchy`}>
        {tree.roots.map(branch)}</ul></div> : <p className="research-empty">No active canonical roots are available.</p>}
    </>}
  </aside>;
}

export function IndustryExplorer({ onAuthenticated = () => undefined }: { onAuthenticated?: () => void }) {
  const [session, setSession] = useState<Session | null | undefined>(undefined);
  const [location, setLocation] = useState(readLocation);
  const [domains, setDomains] = useState<NavigationDomain[]>([]);
  const [domainsLoading, setDomainsLoading] = useState(true);
  const [domainsError, setDomainsError] = useState("");
  const [tree, setTree] = useState<NavigationTree | null>(null);
  const [treeLoading, setTreeLoading] = useState(false);
  const [treeError, setTreeError] = useState("");
  const [mapData, setMapData] = useState<StructureMapResult | null>(null);
  const [qualifiedMap, setQualifiedMap] = useState<QualifiedMapResult | null>(null);
  const [mapLoading, setMapLoading] = useState(false);
  const [mapError, setMapError] = useState("");
  const [nodeData, setNodeData] = useState<InspectorData | null>(null);
  const [context, setContext] = useState<NodeDomainContext | null>(null);
  const [nodeLoading, setNodeLoading] = useState(false);
  const [nodeError, setNodeError] = useState("");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [qualifiedResults, setQualifiedResults] = useState<Array<{ candidate_id: string; display_name: string;
    primary_type: string; qualification_stage: string }>>([]);
  const [qualifiedData, setQualifiedData] = useState<QualifiedIdentity | null>(null);
  const [canonicalProvenance, setCanonicalProvenance] = useState<any>(null);
  const [governance, setGovernance] = useState<any>(null);
  const [overlaySummary, setOverlaySummary] = useState<any>(null);
  const [governanceOpen, setGovernanceOpen] = useState(false);

  const navigate = useCallback((domain: string, node: string, map = "", depth = "", replace = false,
    overlay = location.overlay, qualified = "") => {
    const url = new URL("/industry", window.location.origin);
    if (domain) url.searchParams.set("domain", domain);
    if (qualified) url.searchParams.set("qualified", qualified);
    else if (node) url.searchParams.set("node", node);
    if (map) url.searchParams.set("map", map);
    if (map === "focus" && depth) url.searchParams.set("depth", depth);
    if (overlay === "qualified") url.searchParams.set("overlay", "qualified");
    window.history[replace ? "replaceState" : "pushState"](null, "", url);
    setLocation({ domain, node: qualified ? "" : node, qualified: overlay === "qualified" ? qualified : "",
      overlay, map, depth: map === "focus" ? depth : "" });
  }, [location.overlay]);
  const selectMapNode = useCallback((id: string) => navigate(location.domain, id, location.map, location.depth),
    [location.domain, location.map, location.depth, navigate]);
  const selectQualified = useCallback((id: string) => navigate(location.domain, "", location.map,
    location.depth, false, "qualified", id), [location.domain, location.map, location.depth, navigate]);
  const selectVisual = useCallback((visual: string) => {
    if (visual.startsWith("canonical:")) selectMapNode(visual.slice(10));
    else if (visual.startsWith("qualified-stage2:")) selectQualified(visual.slice(17));
    else if (visual.startsWith("qualified-stage3:")) selectQualified(visual.slice(17));
  }, [selectMapNode, selectQualified]);
  const openRelation = useCallback((id: string) => {
    window.history.pushState(null, "", `/relation/${encodeURIComponent(id)}`);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, []);

  const mode = (location.map || (location.node || location.qualified ? "relationship" : "hierarchy")) as StructureMapMode;
  const focusDepth = location.depth ? Number(location.depth) : 2;
  const modeValid = ["hierarchy", "relationship", "focus"].includes(mode);

  useEffect(() => {
    const pop = () => setLocation(readLocation());
    window.addEventListener("popstate", pop);
    return () => window.removeEventListener("popstate", pop);
  }, []);

  useEffect(() => {
    const url = new URL(window.location.href);
    if (location.qualified && url.searchParams.has("node")) {
      url.searchParams.delete("node");
      window.history.replaceState(null, "", url);
    } else if (location.overlay === "canonical" && url.searchParams.has("qualified")) {
      url.searchParams.delete("qualified");
      window.history.replaceState(null, "", url);
    }
  }, [location]);

  useEffect(() => {
    const controller = new AbortController();
    getSession(controller.signal).then(setSession).catch((reason) => {
      if ((reason as WorkbenchError).status === 401) setSession(null);
      else if ((reason as Error).name !== "AbortError") { setSession(null); setDomainsError((reason as Error).message); }
    });
    return () => controller.abort();
  }, []);

  useEffect(() => { if (session) onAuthenticated(); }, [session, onAuthenticated]);

  useEffect(() => {
    if (!session) return;
    const controller = new AbortController();
    getResearchDomains(controller.signal).then((value) => { setDomains(value.domains); setDomainsError(""); })
      .catch((reason) => { if ((reason as Error).name !== "AbortError") setDomainsError((reason as Error).message); })
      .finally(() => { if (!controller.signal.aborted) setDomainsLoading(false); });
    return () => controller.abort();
  }, [session]);

  useEffect(() => {
    if (domains.length && !location.domain) {
      const current = readLocation();
      if (current.domain) { setLocation(current); return; }
      navigate(domains.find((domain) => domain.domain_id === "ai_hardware")?.domain_id
        ?? domains.find((domain) => domain.domain_id === "semiconductor")?.domain_id
        ?? domains[0].domain_id, current.node, current.map, current.depth, true,
        current.overlay, current.qualified);
    }
  }, [domains, location, navigate]);

  useEffect(() => {
    setTree(null); setTreeError("");
    if (!session || !location.domain || !domains.length) return;
    if (!domains.some((domain) => domain.domain_id === location.domain)) {
      setTreeError("Unknown navigation domain."); return;
    }
    const controller = new AbortController(); setTreeLoading(true);
    getResearchDomainTree(location.domain, controller.signal).then(setTree)
      .catch((reason) => { if ((reason as Error).name !== "AbortError") setTreeError((reason as Error).message); })
      .finally(() => { if (!controller.signal.aborted) setTreeLoading(false); });
    return () => controller.abort();
  }, [session, location.domain, domains]);

  useEffect(() => {
    setMapData(null); setQualifiedMap(null); setMapError(""); setMapLoading(false);
    if (!session || !location.domain || !domains.length) return;
    if (!domains.some((domain) => domain.domain_id === location.domain)) return;
    if (!modeValid || (mode !== "hierarchy" && !location.node && !location.qualified) ||
        (mode === "focus" && (!Number.isInteger(focusDepth) || focusDepth < 1 || focusDepth > 3))) {
      setMapError("Invalid map mode, depth, or missing selected Node."); return;
    }
    const controller = new AbortController(); setMapLoading(true);
    const request = location.overlay === "qualified"
      ? getQualifiedStructureMap(location.domain, mode, location.node, location.qualified, focusDepth, controller.signal)
      : getResearchStructureMap(location.domain, mode, location.node, focusDepth, controller.signal);
    request.then((value) => {
      if (!controller.signal.aborted) {
        if (location.overlay === "qualified") setQualifiedMap(value as QualifiedMapResult);
        else setMapData(value as StructureMapResult);
      }
    }).catch((reason) => { if ((reason as Error).name !== "AbortError") setMapError((reason as Error).message); })
      .finally(() => { if (!controller.signal.aborted) setMapLoading(false); });
    return () => controller.abort();
  }, [session, location.domain, location.node, location.qualified, location.overlay, mode, focusDepth, domains, modeValid]);

  useEffect(() => {
    setNodeData(null); setContext(null); setNodeError("");
    if (!session || !location.node) return;
    const controller = new AbortController(); setNodeLoading(true);
    Promise.all([getResearchNode(location.node, controller.signal), getNodeDomainContext(location.node, controller.signal)])
      .then(([node, nodeContext]) => { if (!controller.signal.aborted) { setNodeData(node); setContext(nodeContext); } })
      .catch((reason) => { if ((reason as Error).name !== "AbortError") setNodeError((reason as Error).message); })
      .finally(() => { if (!controller.signal.aborted) setNodeLoading(false); });
    return () => controller.abort();
  }, [session, location.node]);

  useEffect(() => {
    setQualifiedData(null);
    if (!session || location.overlay !== "qualified" || !location.qualified) return;
    const controller = new AbortController(); setNodeLoading(true); setNodeError("");
    getQualifiedNode(location.qualified, controller.signal)
      .then((value) => { if (!controller.signal.aborted) setQualifiedData(value); })
      .catch((reason) => { if ((reason as Error).name !== "AbortError") setNodeError((reason as Error).message); })
      .finally(() => { if (!controller.signal.aborted) setNodeLoading(false); });
    return () => controller.abort();
  }, [session, location.overlay, location.qualified]);

  useEffect(() => {
    setCanonicalProvenance(null);
    if (!session || location.overlay !== "qualified" || !location.node) return;
    const controller = new AbortController();
    getQualifiedCanonicalProvenance(location.node, controller.signal).then((value) => {
      if (!controller.signal.aborted) setCanonicalProvenance(value);
    }).catch(() => undefined);
    return () => controller.abort();
  }, [session, location.overlay, location.node]);

  useEffect(() => {
    setOverlaySummary(null); setGovernance(null);
    if (!session || location.overlay !== "qualified") return;
    const controller = new AbortController();
    getQualifiedOverlaySummary(controller.signal).then((value) => {
      if (!controller.signal.aborted) setOverlaySummary(value);
    }).catch((reason) => { if ((reason as Error).name !== "AbortError") setMapError((reason as Error).message); });
    getQualifiedGovernance(controller.signal).then((value) => {
      if (!controller.signal.aborted) setGovernance(value);
    }).catch(() => undefined);
    return () => controller.abort();
  }, [session, location.overlay]);

  useEffect(() => {
    if (!session || query.trim().length < 2) { setResults([]); setQualifiedResults([]); return; }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      searchResearch(query, "NODE", controller.signal)
        .then((value) => { if (!controller.signal.aborted) setResults(value.results); })
        .catch(() => { if (!controller.signal.aborted) setResults([]); });
      if (location.overlay === "qualified") searchQualified(query, controller.signal)
        .then((value) => { if (!controller.signal.aborted) setQualifiedResults(value.results); })
        .catch(() => { if (!controller.signal.aborted) setQualifiedResults([]); });
      else setQualifiedResults([]);
    }, 160);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [query, session, location.overlay]);

  function inspectorNavigate(route: { kind: ResearchRouteKind; id?: string }, values?: Record<string, string>) {
    if (route.kind === "node" && route.id) { navigate(location.domain, route.id, location.map, location.depth); return; }
    const path = route.kind === "home" ? "/research" : route.kind === "coverage" ? "/coverage"
      : route.kind === "claims" || route.kind === "sources" ? `/research/${route.kind}`
        : `/${route.kind}/${encodeURIComponent(route.id ?? "")}`;
    const params = new URLSearchParams(values);
    window.history.pushState(null, "", path + (params.size ? `?${params}` : ""));
    window.dispatchEvent(new PopStateEvent("popstate"));
  }

  if (session === undefined) return <main className="research-loading" role="status">Opening Industry Explorer…</main>;
  if (session === null) return <ResearchLogin onLogin={setSession} title="Industry Explorer" />;

  const inTree = !!tree && !!ancestorPath(tree.roots, location.node).length;
  const currentNodeData = nodeData?.node.node_id === location.node ? nodeData : null;
  const currentContext = context?.node_id === location.node ? context : null;
  const otherContexts = currentContext?.navigation_contexts.filter((item) => item.domain_id !== location.domain) ?? [];
  return <main className="industry-workspace">
    <header className="industry-header"><div><span className="eyebrow">Research navigation</span><h1>Industry Explorer</h1>
      <p>Explore Production hierarchy and, when enabled, frozen HUMAN_USER qualified research.</p>
      <div className="industry-layer" role="group" aria-label="Knowledge Layer">
        <span>Knowledge Layer</span>
        <button type="button" aria-pressed={location.overlay === "canonical"}
          onClick={() => navigate(location.domain, location.node, location.qualified ? "hierarchy" : location.map,
            location.depth, false, "canonical")}>Canonical</button>
        <button type="button" aria-pressed={location.overlay === "qualified"}
          onClick={() => navigate(location.domain, location.node, location.map, location.depth,
            false, "qualified", location.qualified)}>Canonical + Qualified</button>
      </div></div>
      <div className="industry-search"><label htmlFor="industry-search">
        {location.overlay === "qualified" ? "Find a canonical or Qualified identity" : "Find a canonical Node"}</label>
        <input id="industry-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search Nodes…" />
        {!!(results.length || qualifiedResults.length) && <div className="industry-search-results">{results.map((item) => <button key={item.object_id}
          onClick={() => { selectMapNode(item.object_id); setQuery(""); setResults([]); }}>
          {item.label}<small>{item.subtitle} · Canonical</small></button>)}
          {qualifiedResults.map((item) => <button key={item.candidate_id}
            onClick={() => { selectQualified(item.candidate_id); setQuery(""); setResults([]); setQualifiedResults([]); }}>
            {item.display_name}<small>Qualified · {item.qualification_stage} · Not in Production</small></button>)}</div>}</div></header>
    {domainsError && <p role="alert" className="research-error">Unable to load domains: {domainsError}</p>}
    {location.overlay === "qualified" && <div className="industry-governance">
      <span>{overlaySummary ? `${overlaySummary.visible_qualified_nodes} Qualified identities · ${overlaySummary.visible_qualified_relations} Qualified relations`
        : "Loading Qualified overlay…"}</span>
      <button type="button" aria-expanded={governanceOpen} onClick={() => setGovernanceOpen((value) => !value)}>
        Qualification Governance · Deferred review</button>
      {governanceOpen && governance && <div className="industry-governance-detail" role="region"
        aria-label="Qualification Governance">
        <h2>Qualification Governance</h2>
        <p>Deferred: {governance.deferred_identities.length} identities · {governance.deferred_relations.length} relations.
          {" "}Rejected: {governance.rejected_identities.length} identity.
          {" "}Endpoint References: {governance.endpoint_references.length} without independent identity qualification.</p>
        <details><summary>Deferred identities</summary><ul>{governance.deferred_identities.map((item: any) =>
          <li key={item.candidate_id}>{item.candidate_id} · {item.display_name} · Not research-eligible · Not shown in semantic graph</li>)}</ul></details>
        <details><summary>Deferred relations</summary><ul>{governance.deferred_relations.map((item: any) =>
          <li key={item.candidate_id}>{item.candidate_id} · {item.from_label} → {item.to_label}
            {" · "}Not research-eligible · Not shown in semantic graph</li>)}</ul></details>
        <details><summary>Rejected — excluded from research overlay</summary><ul>{governance.rejected_identities.map((item: any) =>
          <li key={item.candidate_id}>{item.candidate_id} · {item.display_name} · Not research-eligible · Not shown in semantic graph</li>)}</ul></details>
        <details><summary>Endpoint References</summary><ul>{governance.endpoint_references.map((item: any) =>
          <li key={item.candidate_ref}>{item.candidate_ref} · {item.display_name}
            {" · "}Identity not independently HUMAN_USER-qualified · Relation anchor only</li>)}</ul></details>
      </div>}</div>}
    <div className="industry-layout">
      <DomainHierarchyPanel domains={domains} domainId={location.domain} tree={tree} loading={treeLoading || domainsLoading}
        error={treeError || domainsError} selectedNodeId={location.node} onDomain={(id) => navigate(id, "")}
        onNode={selectMapNode} />
      {location.overlay === "canonical" ? <SemanticStructureMap map={mapData} loading={mapLoading} error={mapError} mode={mode} depth={focusDepth}
        selectedNodeId={location.node} onMode={(next) => navigate(location.domain, location.node, next, location.depth)}
        onDepth={(next) => navigate(location.domain, location.node, "focus", String(next))}
        onNode={selectMapNode} onRelation={openRelation} /> :
        <QualifiedStructureMap map={qualifiedMap} loading={mapLoading} error={mapError} mode={mode} depth={focusDepth}
          hasSelection={!!(location.node || location.qualified)}
          onMode={(next) => navigate(location.domain, location.node, next, location.depth,
            false, "qualified", location.qualified)}
          onDepth={(next) => navigate(location.domain, location.node, "focus", String(next),
            false, "qualified", location.qualified)}
          onCanonical={selectMapNode} onQualified={selectQualified} onCanonicalRelation={openRelation} />}
      <section className="industry-inspector" aria-label="Research Inspector">
        {!location.node && !location.qualified && <p className="industry-prompt">Select a node to inspect research.</p>}
        {(nodeLoading || (location.node && !currentNodeData && !nodeError)) && <p role="status">Loading Research Inspector…</p>}
        {nodeError && <p role="alert" className="research-error">Unable to load Node research: {nodeError}</p>}
        {location.qualified && qualifiedData?.candidate_id === location.qualified &&
          <QualifiedResearchInspector data={qualifiedData} onVisual={selectVisual} />}
        {currentNodeData && currentContext && <>
          {!inTree && <p className="industry-outside-tree">Node is outside the selected navigation tree.</p>}
          {!!otherContexts.length && <div className="industry-other-contexts">{otherContexts.map((item) => <button key={`${item.domain_id}:${item.root_node_id}`}
            onClick={() => navigate(item.domain_id, location.node, location.map, location.depth)}>Open in {item.display_name}</button>)}</div>}
          <ResearchNodeInspector data={currentNodeData} domainContext={currentContext} csrf={session.csrf_token ?? ""} navigate={inspectorNavigate} />
          {location.overlay === "qualified" && canonicalProvenance?.node_id === location.node &&
            !!(canonicalProvenance.qualified_reuse_candidates.length || canonicalProvenance.qualified_relations.length) &&
            <section className="industry-qualification-card"><h2>Qualification Provenance</h2>
              <p>Canonical Node · Stage 3 HUMAN_USER qualified reuse is not a new canonical object.</p>
              <p>{canonicalProvenance.qualified_reuse_candidates.length} qualified reuse candidates ·
                {" "}{canonicalProvenance.qualified_relations.length} qualified relations.</p>
              <ul>{canonicalProvenance.qualified_reuse_candidates.map((item: any) =>
                <li key={item.candidate_id}>{item.candidate_id} · {item.display_name}
                  {" · "}Qualified reuse, not canonical creation</li>)}</ul>
              <p>Qualified overlay relations are excluded from canonical Direct Impact.</p>
            </section>}
        </>}
      </section>
    </div>
  </main>;
}
