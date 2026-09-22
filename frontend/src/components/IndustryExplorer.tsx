import { useCallback, useEffect, useState } from "react";

import {
  getNodeDomainContext, getResearchDomains, getResearchDomainTree, getResearchNode, getResearchStructureMap,
  searchResearch, type NavigationDomain, type NavigationNode, type NavigationTree,
  type NodeDomainContext, type ResearchRouteKind, type SearchResult, type StructureMapMode, type StructureMapResult,
} from "../api/research";
import { getSession, WorkbenchError } from "../api/workbench";
import { ResearchLogin, ResearchNodeInspector, type Session } from "./ResearchExplorer";
import type { InspectorData } from "./inspectorSelection";
import { SemanticStructureMap } from "./SemanticStructureMap";

function readLocation() {
  const params = new URLSearchParams(window.location.search);
  return { domain: params.get("domain") ?? "", node: params.get("node") ?? "",
    map: params.get("map") ?? "", depth: params.get("depth") ?? "" };
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
  const [mapLoading, setMapLoading] = useState(false);
  const [mapError, setMapError] = useState("");
  const [nodeData, setNodeData] = useState<InspectorData | null>(null);
  const [context, setContext] = useState<NodeDomainContext | null>(null);
  const [nodeLoading, setNodeLoading] = useState(false);
  const [nodeError, setNodeError] = useState("");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);

  const navigate = useCallback((domain: string, node: string, map = "", depth = "", replace = false) => {
    const url = new URL("/industry", window.location.origin);
    if (domain) url.searchParams.set("domain", domain);
    if (node) url.searchParams.set("node", node);
    if (map) url.searchParams.set("map", map);
    if (map === "focus" && depth) url.searchParams.set("depth", depth);
    window.history[replace ? "replaceState" : "pushState"](null, "", url);
    setLocation({ domain, node, map, depth: map === "focus" ? depth : "" });
  }, []);
  const selectMapNode = useCallback((id: string) => navigate(location.domain, id, location.map, location.depth),
    [location.domain, location.map, location.depth, navigate]);
  const openRelation = useCallback((id: string) => {
    window.history.pushState(null, "", `/relation/${encodeURIComponent(id)}`);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, []);

  const mode = (location.map || (location.node ? "relationship" : "hierarchy")) as StructureMapMode;
  const focusDepth = location.depth ? Number(location.depth) : 2;
  const modeValid = ["hierarchy", "relationship", "focus"].includes(mode);

  useEffect(() => {
    const pop = () => setLocation(readLocation());
    window.addEventListener("popstate", pop);
    return () => window.removeEventListener("popstate", pop);
  }, []);

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
      navigate(domains.find((domain) => domain.domain_id === "ai_hardware")?.domain_id
        ?? domains.find((domain) => domain.domain_id === "semiconductor")?.domain_id
        ?? domains[0].domain_id, location.node, location.map, location.depth, true);
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
    setMapData(null); setMapError(""); setMapLoading(false);
    if (!session || !location.domain || !domains.length) return;
    if (!domains.some((domain) => domain.domain_id === location.domain)) return;
    if (!modeValid || (mode !== "hierarchy" && !location.node) ||
        (mode === "focus" && (!Number.isInteger(focusDepth) || focusDepth < 1 || focusDepth > 3))) {
      setMapError("Invalid map mode, depth, or missing selected Node."); return;
    }
    const controller = new AbortController(); setMapLoading(true);
    getResearchStructureMap(location.domain, mode, location.node, focusDepth, controller.signal).then((value) => {
      if (!controller.signal.aborted) setMapData(value);
    }).catch((reason) => { if ((reason as Error).name !== "AbortError") setMapError((reason as Error).message); })
      .finally(() => { if (!controller.signal.aborted) setMapLoading(false); });
    return () => controller.abort();
  }, [session, location.domain, location.node, mode, focusDepth, domains, modeValid]);

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
    if (!session || query.trim().length < 2) { setResults([]); return; }
    const controller = new AbortController();
    const timer = window.setTimeout(() => searchResearch(query, "NODE", controller.signal)
      .then((value) => { if (!controller.signal.aborted) setResults(value.results); })
      .catch(() => { if (!controller.signal.aborted) setResults([]); }), 160);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [query, session]);

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
    <header className="industry-header"><div><span className="eyebrow">Canonical research navigation</span><h1>Industry Explorer</h1>
      <p>Explore existing Production hierarchy. Navigation context and operational assignments are separate.</p></div>
      <div className="industry-search"><label htmlFor="industry-search">Find a canonical Node</label>
        <input id="industry-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search Nodes…" />
        {!!results.length && <div className="industry-search-results">{results.map((item) => <button key={item.object_id}
          onClick={() => { selectMapNode(item.object_id); setQuery(""); setResults([]); }}>
          {item.label}<small>{item.subtitle}</small></button>)}</div>}</div></header>
    {domainsError && <p role="alert" className="research-error">Unable to load domains: {domainsError}</p>}
    <div className="industry-layout">
      <DomainHierarchyPanel domains={domains} domainId={location.domain} tree={tree} loading={treeLoading || domainsLoading}
        error={treeError || domainsError} selectedNodeId={location.node} onDomain={(id) => navigate(id, "")}
        onNode={selectMapNode} />
      <SemanticStructureMap map={mapData} loading={mapLoading} error={mapError} mode={mode} depth={focusDepth}
        selectedNodeId={location.node} onMode={(next) => navigate(location.domain, location.node, next, location.depth)}
        onDepth={(next) => navigate(location.domain, location.node, "focus", String(next))}
        onNode={selectMapNode} onRelation={openRelation} />
      <section className="industry-inspector" aria-label="Research Inspector">
        {!location.node && <p className="industry-prompt">Select a node to inspect research.</p>}
        {(nodeLoading || (location.node && !currentNodeData && !nodeError)) && <p role="status">Loading Research Inspector…</p>}
        {nodeError && <p role="alert" className="research-error">Unable to load Node research: {nodeError}</p>}
        {currentNodeData && currentContext && <>
          {!inTree && <p className="industry-outside-tree">Node is outside the selected navigation tree.</p>}
          {!!otherContexts.length && <div className="industry-other-contexts">{otherContexts.map((item) => <button key={`${item.domain_id}:${item.root_node_id}`}
            onClick={() => navigate(item.domain_id, location.node, location.map, location.depth)}>Open in {item.display_name}</button>)}</div>}
          <ResearchNodeInspector data={currentNodeData} domainContext={currentContext} csrf={session.csrf_token ?? ""} navigate={inspectorNavigate} />
        </>}
      </section>
    </div>
  </main>;
}
