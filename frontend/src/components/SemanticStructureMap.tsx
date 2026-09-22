import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import { useEffect, useMemo, useRef, useState } from "react";

import type { StructureMapEdge, StructureMapMode, StructureMapResult } from "../api/research";

const GROUP_LABELS: Record<string, string> = {
  structure: "Structure", supply_flow: "Supply / Flow", dependency: "Dependency / Influence",
  competition: "Competition / Substitution", general_association: "General Association",
};

export function visibleMap(map: StructureMapResult, group: string) {
  const edges = group === "all" ? map.edges : map.edges.filter((edge) => edge.semantic_group === group);
  const ids = new Set(edges.flatMap((edge) => [edge.from_node_id, edge.to_node_id]));
  if (map.selected_node_id) ids.add(map.selected_node_id);
  return { nodes: map.nodes.filter((node) => group === "all" || ids.has(node.node_id)), edges };
}

export function toStructureElements(map: StructureMapResult, group = "all"): ElementDefinition[] {
  const shown = visibleMap(map, group);
  const levels = new Map<number, typeof shown.nodes>();
  shown.nodes.forEach((node) => levels.set(node.distance, [...(levels.get(node.distance) ?? []), node]));
  const elements: ElementDefinition[] = [];
  [...levels.entries()].sort(([a], [b]) => a - b).forEach(([distance, nodes]) => {
    nodes.forEach((node, index) => {
      const angle = (index / Math.max(nodes.length, 1)) * 2 * Math.PI - Math.PI / 2;
      const position = map.mode === "hierarchy"
        ? { x: (index - (nodes.length - 1) / 2) * 165, y: distance * 135 }
        : map.mode === "focus" ? { x: distance * 175, y: (index - (nodes.length - 1) / 2) * 115 }
          : distance === 0 ? { x: 0, y: 0 }
            : { x: Math.round(Math.cos(angle) * 160), y: Math.round(Math.sin(angle) * 160) };
      elements.push({ data: { id: node.node_id, label: `${node.canonical_name}\n${node.primary_type}`,
        type: node.primary_type, canonical_name: node.canonical_name, distance: node.distance }, position,
      classes: [node.selected ? "map-selected" : "", node.on_selected_path ? "map-selected-path" : "",
        node.in_navigation_context ? "" : "map-outside",
        `map-distance-${node.distance}`].filter(Boolean).join(" ") });
    });
  });
  shown.edges.forEach((edge) => elements.push({ data: { id: edge.relation_id,
    source: edge.from_node_id, target: edge.to_node_id, label: edge.relation_type,
    relation_type: edge.relation_type }, classes: `map-edge-${edge.semantic_group}${edge.on_selected_path ? " map-edge-selected-path" : ""}` }));
  return elements;
}

type Props = {
  map: StructureMapResult | null; loading: boolean; error: string;
  mode: StructureMapMode; depth: number; selectedNodeId: string;
  onMode: (mode: StructureMapMode) => void; onDepth: (depth: number) => void;
  onNode: (nodeId: string) => void; onRelation: (relationId: string) => void;
};

export function SemanticStructureMap({ map, loading, error, mode, depth, selectedNodeId,
  onMode, onDepth, onNode, onRelation }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const instance = useRef<Core | null>(null);
  const [group, setGroup] = useState("all");
  const [selectedEdge, setSelectedEdge] = useState<StructureMapEdge | null>(null);
  const [reset, setReset] = useState(0);
  const shown = useMemo(() => map ? visibleMap(map, group) : null, [map, group]);
  const elements = useMemo(() => map ? toStructureElements(map, group) : [], [map, group]);

  useEffect(() => {
    if (!container.current || !map || !elements.length) return;
    const cy = cytoscape({ container: container.current, elements,
      layout: { name: "preset", fit: true, padding: 36 }, minZoom: 0.1, maxZoom: 3,
      autoungrabify: true,
      style: [
        { selector: "node", style: { width: 136, height: 56, shape: "round-rectangle",
          "background-color": "#f8fbfd", "border-color": "#9fb2c3", "border-width": 1.5,
          label: "data(label)", color: "#28425c", "font-size": 11, "font-family": "system-ui, sans-serif",
          "font-weight": 500, "text-wrap": "wrap", "text-max-width": "118px", "text-valign": "center",
          "text-halign": "center", "overlay-opacity": 0 } },
        { selector: ".map-selected-path", style: { "border-color": "#3c83ae", "border-width": 2.5 } },
        { selector: ".map-selected", style: { "background-color": "#e0effa", "border-color": "#2473a5",
          "border-width": 3, "font-weight": 700 } },
        { selector: ".map-outside", style: { "border-style": "dashed", "border-color": "#a47755" } },
        { selector: "edge", style: { width: 1.6, "line-color": "#7e9cb4",
          "target-arrow-color": "#527b9d", "target-arrow-shape": "triangle", "curve-style": "bezier",
          label: "data(label)", color: "#3c5d77", "font-size": 10,
          "font-family": "system-ui, sans-serif", "text-background-color": "#fff",
          "text-background-opacity": 0.93, "text-background-padding": "3px", "overlay-opacity": 0 } },
        { selector: ".map-edge-supply_flow", style: { "line-style": "dashed" } },
        { selector: ".map-edge-dependency", style: { "line-color": "#8372a4", "target-arrow-color": "#8372a4" } },
        { selector: ".map-edge-competition", style: { "line-style": "dotted", "line-color": "#ad786a" } },
        { selector: ".map-edge-general_association", style: { "line-style": "dashed", "line-color": "#829089" } },
        { selector: ".map-edge-selected-path", style: { width: 3, "line-color": "#2c79ab", "target-arrow-color": "#2c79ab" } },
      ],
    });
    instance.current = cy;
    cy.on("tap", "node", (event) => onNode(event.target.id()));
    cy.on("tap", "edge", (event) => {
      setSelectedEdge(map.edges.find((edge) => edge.relation_id === event.target.id()) ?? null);
    });
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(() => {
      cy.resize(); cy.fit(undefined, 36);
    });
    observer?.observe(container.current);
    return () => { observer?.disconnect(); cy.destroy(); if (instance.current === cy) instance.current = null; };
  }, [map, elements, onNode, reset]);

  useEffect(() => setSelectedEdge(null), [map, group]);

  return <section className="industry-map" aria-label="Semantic Structure Map">
    <header className="industry-map-header"><div><span className="eyebrow">Current canonical relations</span>
      <h2>Semantic Structure Map</h2><p>Explore recorded hierarchy and relationships.</p></div>
      <div className="industry-map-view-actions"><button type="button" onClick={() => instance.current?.fit(undefined, 36)}
        disabled={!map} aria-label="Fit map view">Fit view</button>
        <button type="button" onClick={() => setReset((value) => value + 1)} disabled={!map}
          aria-label="Reset map view">Reset view</button></div></header>
    <div className="industry-map-modes" role="group" aria-label="Map mode">
      {([["hierarchy", "层级视图"], ["relationship", "关系视图"], ["focus", "聚焦视图"]] as const).map(([value, label]) =>
        <button key={value} type="button" aria-pressed={mode === value} disabled={value !== "hierarchy" && !selectedNodeId}
          onClick={() => onMode(value)}>{label}</button>)}
      {mode === "focus" && <label>Depth <select aria-label="Focus depth" value={depth}
        onChange={(event) => onDepth(Number(event.target.value))}><option value={1}>1</option>
        <option value={2}>2</option><option value={3}>3</option></select></label>}
    </div>
    <div className="industry-map-filters" role="group" aria-label="Relation filters">
      {[["all", "All"], ...Object.entries(GROUP_LABELS)].map(([value, label]) =>
        <button key={value} type="button" aria-pressed={group === value} onClick={() => setGroup(value)}>{label}</button>)}
    </div>
    <div className="industry-map-canvas" ref={container} aria-label="Canonical semantic structure diagram" />
    <div className="industry-map-messages" aria-live="polite">
      {loading && <p role="status">Loading semantic map…</p>}
      {error && <p role="alert">Unable to load structure map: {error}</p>}
      {!loading && !error && !map && <p>Select a domain to view its canonical structure.</p>}
      {!loading && !error && map && !map.nodes.length && <p>No active canonical Nodes in this map.</p>}
      {!loading && !error && map && !map.edges.length && <p>No current canonical Relations in this map.</p>}
      {!loading && !error && map && group !== "all" && !shown?.edges.length && <p>No recorded Relations match this filter.</p>}
      {!selectedNodeId && mode !== "hierarchy" && <p>Select a Node to use this map mode.</p>}
      {map?.truncated && <p role="status" className="industry-truncation">Map truncated: {map.truncation_reasons.join(", ")}</p>}
    </div>
    {!!shown?.nodes.length && <div className="industry-map-index">
      <details><summary>Map Nodes ({shown.nodes.length})</summary><div>{shown.nodes.map((node) =>
        <button key={node.node_id} type="button" aria-current={node.selected ? "true" : undefined}
          onClick={() => onNode(node.node_id)}>{node.canonical_name} · {node.primary_type}
          {!node.in_navigation_context && " · Outside navigation tree"}</button>)}</div></details>
      <details><summary>Recorded Relations ({shown.edges.length})</summary><div>{shown.edges.map((edge) =>
        <button key={edge.relation_id} type="button" onClick={() => setSelectedEdge(edge)}>
          {map?.nodes.find((node) => node.node_id === edge.from_node_id)?.canonical_name ?? edge.from_node_id}
          {" → "}{map?.nodes.find((node) => node.node_id === edge.to_node_id)?.canonical_name ?? edge.to_node_id}
          {" · "}{edge.relation_type}</button>)}</div></details>
    </div>}
    {selectedEdge && <div className="industry-map-edge-detail" role="region" aria-label="Selected relation">
      <strong>{selectedEdge.relation_type}</strong>
      <span>{map?.nodes.find((item) => item.node_id === selectedEdge.from_node_id)?.canonical_name ?? selectedEdge.from_node_id}
        {" → "}{map?.nodes.find((item) => item.node_id === selectedEdge.to_node_id)?.canonical_name ?? selectedEdge.to_node_id}</span>
      <span>Scope: {selectedEdge.scope || "Unspecified"} · Confidence: {selectedEdge.confidence ?? "Unspecified"}</span>
      <button type="button" onClick={() => onRelation(selectedEdge.relation_id)}>Open relation</button>
    </div>}
    <footer className="industry-map-footer"><span>{shown?.nodes.length ?? 0} Nodes · {shown?.edges.length ?? 0} Relations · Depth {map?.depth ?? depth}</span>
      <span>{map?.display_name ?? "No domain"}</span>
      <div className="industry-map-legend" aria-label="Relation legend">{Object.entries(GROUP_LABELS).map(([key, label]) =>
        <span key={key} className={`map-legend-${key}`}>{label}</span>)}<span>Dashed Node: outside navigation tree</span></div>
    </footer>
  </section>;
}
