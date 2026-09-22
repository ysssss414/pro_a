import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import { useEffect, useMemo, useRef, useState } from "react";

import { getQualifiedRelation, type QualifiedMapEdge, type QualifiedMapNode,
  type QualifiedMapResult, type StructureMapMode } from "../api/research";

type Props = {
  map: QualifiedMapResult | null; loading: boolean; error: string; mode: StructureMapMode; depth: number;
  hasSelection: boolean; onMode: (mode: StructureMapMode) => void; onDepth: (depth: number) => void;
  onCanonical: (id: string) => void; onQualified: (id: string) => void;
  onCanonicalRelation: (id: string) => void;
};

export function QualifiedStructureMap({ map, loading, error, mode, depth, hasSelection,
  onMode, onDepth, onCanonical, onQualified, onCanonicalRelation }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const instance = useRef<Core | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<QualifiedMapEdge | null>(null);
  const [relationDetail, setRelationDetail] = useState<any>(null);
  const [selectedReference, setSelectedReference] = useState<QualifiedMapNode | null>(null);
  const [reset, setReset] = useState(0);
  const elements = useMemo(() => {
    if (!map) return [];
    const levels = new Map<number, QualifiedMapNode[]>();
    map.nodes.forEach((node) => levels.set(node.distance, [...(levels.get(node.distance) ?? []), node]));
    const result: ElementDefinition[] = [];
    [...levels.entries()].sort(([a], [b]) => a - b).forEach(([distance, nodes]) => {
      nodes.forEach((node, index) => {
        const angle = (index / Math.max(nodes.length, 1)) * 2 * Math.PI - Math.PI / 2;
        const position = map.mode === "hierarchy"
          ? { x: (index - (nodes.length - 1) / 2) * 170, y: distance * 135 }
          : map.mode === "focus" ? { x: distance * 185, y: (index - (nodes.length - 1) / 2) * 115 }
            : distance === 0 ? { x: 0, y: 0 }
              : { x: Math.round(Math.cos(angle) * 170), y: Math.round(Math.sin(angle) * 170) };
        const badge = node.knowledge_state === "canonical" ? "Canonical"
          : node.knowledge_state === "qualified_identity" ? `Qualified · ${node.qualification_stage}`
            : "Endpoint Reference";
        result.push({ data: { id: node.visual_id, label: `${node.display_name}\n${badge}` }, position,
          classes: [node.knowledge_state, node.selected ? "selected" : ""].filter(Boolean).join(" ") });
      });
    });
    map.edges.forEach((edge) => result.push({ data: { id: edge.visual_id,
      source: edge.from_visual_id, target: edge.to_visual_id, label: edge.relation_type },
    classes: edge.knowledge_state }));
    return result;
  }, [map]);

  useEffect(() => {
    if (!container.current || !map || !elements.length) return;
    const cy = cytoscape({ container: container.current, elements,
      layout: { name: "preset", fit: true, padding: 38 }, minZoom: 0.1, maxZoom: 3,
      autoungrabify: true,
      style: [
        { selector: "node", style: { width: 140, height: 62, shape: "round-rectangle",
          "background-color": "#f8fbfd", "border-color": "#718ca4", "border-width": 2,
          label: "data(label)", color: "#28425c", "font-size": 10, "font-family": "system-ui, sans-serif",
          "text-wrap": "wrap", "text-max-width": "126px", "text-valign": "center",
          "text-halign": "center" } },
        { selector: "node.qualified_identity", style: { "border-style": "dashed",
          "border-width": 3, "border-color": "#9a6e31", "background-color": "#fffaf0" } },
        { selector: "node.relation_endpoint_reference", style: { "border-style": "dotted",
          "border-width": 3, "border-color": "#776f7e", "background-color": "#f7f5f8" } },
        { selector: "node.selected", style: { "border-width": 4, "background-color": "#e0effa" } },
        { selector: "edge", style: { width: 2, "line-color": "#7896ad",
          "target-arrow-color": "#527b9d", "target-arrow-shape": "triangle", "curve-style": "bezier",
          label: "data(label)", color: "#3c5d77", "font-size": 10, "font-family": "system-ui, sans-serif",
          "text-background-color": "#fff", "text-background-opacity": 0.94 } },
        { selector: "edge.qualified_relation", style: { "line-style": "dashed",
          "line-color": "#9a6e31", "target-arrow-color": "#9a6e31", width: 3 } },
      ],
    });
    instance.current = cy;
    cy.on("tap", "node", (event) => {
      const node = map.nodes.find((item) => item.visual_id === event.target.id());
      if (node?.canonical_node_id) onCanonical(node.canonical_node_id);
      else if (node?.qualified_candidate_id) onQualified(node.qualified_candidate_id);
      else if (node?.endpoint_reference_id) setSelectedReference(node);
    });
    cy.on("tap", "edge", (event) => setSelectedEdge(map.edges.find(
      (item) => item.visual_id === event.target.id()) ?? null));
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(() => {
      cy.resize(); cy.fit(undefined, 38);
    });
    observer?.observe(container.current);
    return () => { observer?.disconnect(); cy.destroy(); if (instance.current === cy) instance.current = null; };
  }, [map, elements, onCanonical, onQualified, reset]);

  useEffect(() => { setSelectedEdge(null); setSelectedReference(null); }, [map]);
  useEffect(() => {
    setRelationDetail(null);
    if (!selectedEdge?.qualified_relation_id) return;
    const controller = new AbortController();
    getQualifiedRelation(selectedEdge.qualified_relation_id, controller.signal).then(setRelationDetail)
      .catch(() => undefined);
    return () => controller.abort();
  }, [selectedEdge]);

  const label = (id: string) => map?.nodes.find((item) => item.visual_id === id)?.display_name ?? id;
  return <section className="industry-map" aria-label="Qualified Semantic Structure Map">
    <header className="industry-map-header"><div><span className="eyebrow">Canonical + HUMAN_USER qualified</span>
      <h2>Semantic Structure Map</h2><p>Qualified relations are not applied to Production.</p></div>
      <div className="industry-map-view-actions"><button type="button" onClick={() => instance.current?.fit(undefined, 38)}
        disabled={!map}>Fit view</button><button type="button" onClick={() => setReset((value) => value + 1)}
          disabled={!map}>Reset view</button></div></header>
    <div className="industry-map-modes" role="group" aria-label="Map mode">
      {([["hierarchy", "层级视图"], ["relationship", "关系视图"], ["focus", "聚焦视图"]] as const).map(([value, title]) =>
        <button key={value} type="button" aria-pressed={mode === value}
          disabled={value !== "hierarchy" && !hasSelection} onClick={() => onMode(value)}>{title}</button>)}
      {mode === "focus" && <label>Depth <select aria-label="Focus depth" value={depth}
        onChange={(event) => onDepth(Number(event.target.value))}>
        {[1, 2, 3].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>}
    </div>
    <div className="industry-map-canvas" ref={container} aria-label="Canonical and qualified semantic structure diagram" />
    <div className="industry-map-messages" aria-live="polite">
      {loading && <p role="status">Loading qualified map…</p>}
      {error && <p role="alert">{error}</p>}
      {map?.truncated && <p role="status">Map truncated: {map.truncation_reasons.join(", ")}</p>}
      {!!map?.omitted_reference_hierarchy_relations && mode === "hierarchy" &&
        <p>{map.omitted_reference_hierarchy_relations} qualified part_of relations omitted from hierarchy because endpoint identity is not independently qualified.</p>}
    </div>
    {selectedReference && <div className="industry-map-edge-detail" role="region" aria-label="Endpoint Reference detail">
      <strong>Endpoint Reference · {selectedReference.display_name}</strong>
      <span>{selectedReference.endpoint_reference_id}</span>
      <span>Identity qualified: No. Relation qualified: Yes. Production canonical: No.</span>
      <span>This endpoint appears only as part of a HUMAN_USER-qualified relation. Its standalone identity has not been independently HUMAN_USER-qualified.</span>
      <span>Appears in {map?.edges.filter((edge) => selectedReference.visual_id === edge.from_visual_id ||
        selectedReference.visual_id === edge.to_visual_id).length ?? 0} visible qualified relations.</span>
    </div>}
    {selectedEdge && <div className="industry-map-edge-detail" role="region" aria-label="Selected relation">
      <strong>{selectedEdge.knowledge_state === "qualified_relation" ? "Qualified Relation · Not canonical" : "Canonical Relation"}
        {" · "}{selectedEdge.relation_type}</strong>
      <span>{label(selectedEdge.from_visual_id)} → {label(selectedEdge.to_visual_id)}</span>
      <span>Scope: {selectedEdge.scope || "Unspecified"}</span>
      {selectedEdge.qualified_relation_id ? <>
        <span>Candidate: {selectedEdge.qualified_relation_id} · Production Applied: No</span>
        <span>From endpoint authority: {selectedEdge.from_endpoint_authority}</span>
        <span>To endpoint authority: {selectedEdge.to_endpoint_authority}</span>
        <span>HUMAN_USER qualified the relation. Endpoint Reference has no independent identity qualification.</span>
        <details className="qualified-provenance"><summary>Frozen qualification provenance</summary>
          <span>Phase 4.3 Stage 3 · HUMAN_USER · Production Applied: No</span>
          <span>Source population SHA256: {selectedEdge.qualification_population_sha256}</span>
          <span>Candidate content SHA256: {selectedEdge.candidate_content_sha256}</span>
          <span>Decision artifact SHA256: {selectedEdge.qualification_decision_sha256}</span>
        </details>
        {relationDetail?.evidence?.map((item: any) => <span key={item.evidence_id}>
          {item.evidence_id} · {item.source_title} · {item.section} · page {item.pdf_page}
        </span>)}
      </> : selectedEdge.canonical_relation_id &&
        <button type="button" onClick={() => onCanonicalRelation(selectedEdge.canonical_relation_id!)}>
          Open canonical relation</button>}
    </div>}
    <footer className="industry-map-footer">
      <span>{map?.stats.canonical_nodes ?? 0} Canonical Nodes · {map?.stats.qualified_nodes ?? 0} Qualified Identities ·
        {" "}{map?.stats.endpoint_references ?? 0} Endpoint References</span>
      <span>{map?.stats.canonical_relations ?? 0} Canonical Relations · {map?.stats.qualified_relations ?? 0} Qualified Relations</span>
      <div className="industry-map-legend" aria-label="Knowledge state legend">
        <span>Canonical — solid Node and Relation</span>
        <span>Qualified Identity — dashed Node, HUMAN_USER qualified, not applied</span>
        <span>Qualified Relation — dashed line, HUMAN_USER qualified, not applied</span>
        <span>Endpoint Reference — dotted Node, identity not independently qualified</span>
        <span>Deferred and Rejected — governance only</span>
      </div>
    </footer>
  </section>;
}
