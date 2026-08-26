import cytoscape, { type ElementDefinition } from "cytoscape";
import { useEffect, useRef } from "react";

import type { NeighborGraph } from "../api/types";

interface GraphPanelProps {
  graph: NeighborGraph | null;
  loading: boolean;
  error: string | null;
  onSelect: (nodeId: string) => void;
}

export function toCytoscapeElements(graph: NeighborGraph): ElementDefinition[] {
  const nodes: ElementDefinition[] = [
    {
      data: {
        id: graph.center.node_id,
        label: graph.center.canonical_name,
        type: graph.center.primary_type,
      },
      classes: "center-node",
    },
    ...graph.nodes.map((node) => ({
      data: { id: node.node_id, label: node.canonical_name, type: node.primary_type },
      classes: "neighbor-node",
    })),
  ];
  const edges: ElementDefinition[] = graph.edges.map((edge) => ({
    data: {
      id: edge.relation_id,
      source: edge.from_node_id,
      target: edge.to_node_id,
      label: edge.relation_type,
    },
  }));
  return [...nodes, ...edges];
}

export function GraphPanel({ graph, loading, error, onSelect }: GraphPanelProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!containerRef.current || !graph || graph.edges.length === 0) return;

    const instance = cytoscape({
      container: containerRef.current,
      elements: toCytoscapeElements(graph),
      minZoom: 0.35,
      maxZoom: 2.5,
      autoungrabify: true,
      style: [
        {
          selector: "node",
          style: {
            width: 132,
            height: 54,
            shape: "round-rectangle",
            "background-color": "#f8fafc",
            "border-color": "#94a3b8",
            "border-width": 1,
            label: "data(label)",
            color: "#1e293b",
            "font-size": 10,
            "font-family": "system-ui, sans-serif",
            "text-wrap": "ellipsis",
            "text-max-width": "112px",
            "text-valign": "center",
            "text-halign": "center",
            "overlay-opacity": 0,
          },
        },
        {
          selector: ".center-node",
          style: {
            "background-color": "#e0ecff",
            "border-color": "#245ea8",
            "border-width": 2.5,
            color: "#123a68",
            "font-weight": 600,
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.4,
            "line-color": "#94a3b8",
            "target-arrow-color": "#64748b",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(label)",
            color: "#475569",
            "font-size": 9,
            "font-family": "system-ui, sans-serif",
            "text-background-color": "#f8fafc",
            "text-background-opacity": 0.92,
            "text-background-padding": "3px",
            "text-rotation": "autorotate",
            "overlay-opacity": 0,
          },
        },
        {
          selector: "node:active",
          style: {
            "overlay-color": "#245ea8",
            "overlay-opacity": 0.08,
          },
        },
      ],
      layout: {
        name: "breadthfirst",
        directed: true,
        padding: 42,
        spacingFactor: 1.2,
      },
    });

    instance.on("tap", "node", (event) => {
      const nodeId = event.target.id();
      if (nodeId !== graph.center.node_id) onSelect(nodeId);
    });

    return () => instance.destroy();
  }, [graph, onSelect]);

  let emptyState: string | null = null;
  if (loading) emptyState = "Loading neighborhood…";
  else if (error) emptyState = error;
  else if (!graph) emptyState = "Search for a node to start exploring.";
  else if (graph.edges.length === 0) emptyState = "No current neighboring relations.";

  return (
    <section className="graph-panel" aria-labelledby="graph-heading">
      <div className="graph-toolbar">
        <div>
          <p className="eyebrow">Current 1-hop</p>
          <h2 id="graph-heading">Neighborhood</h2>
        </div>
        {graph && graph.edges.length > 0 && (
          <span className="graph-counts">
            {graph.nodes.length + 1} nodes · {graph.edges.length} edges
          </span>
        )}
      </div>
      <div className="graph-canvas" ref={containerRef} aria-label="Knowledge neighborhood graph" />
      {emptyState && (
        <div className={`graph-empty ${error ? "is-error" : ""}`} role={error ? "alert" : undefined}>
          <span className="empty-glyph" aria-hidden="true">◎</span>
          <p>{emptyState}</p>
          {!graph && !loading && !error && <span>Results stay local and read-only.</span>}
        </div>
      )}
      <div className="graph-hint">Scroll to zoom · Drag background to pan · Click a neighbor to focus</div>
    </section>
  );
}
