import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { StructureMapResult } from "../api/research";
import { SemanticStructureMap, toStructureElements, visibleMap } from "./SemanticStructureMap";

const cy = vi.hoisted(() => ({ fit: vi.fn(), destroy: vi.fn(), on: vi.fn() }));
vi.mock("cytoscape", () => ({ default: vi.fn(() => cy) }));

const map: StructureMapResult = {
  domain_id: "ai_hardware", display_name: "AI Hardware", mode: "relationship",
  selected_node_id: "A", depth: 1,
  nodes: [
    { node_id: "A", canonical_name: "Alpha", primary_type: "Product", status: "active",
      distance: 0, selected: true, in_navigation_context: true, navigation_depth: 1, on_selected_path: true },
    { node_id: "B", canonical_name: "Beta", primary_type: "Material", status: "active",
      distance: 1, selected: false, in_navigation_context: true, navigation_depth: 2 },
    { node_id: "OUT", canonical_name: "Outside", primary_type: "Technology", status: "active",
      distance: 1, selected: false, in_navigation_context: false, navigation_depth: null },
  ],
  edges: [
    { relation_id: "R1", from_node_id: "A", to_node_id: "B", relation_type: "uses",
      semantic_group: "supply_flow", scope: "", status: "current", confidence: .8, on_selected_path: true },
    { relation_id: "R2", from_node_id: "OUT", to_node_id: "A", relation_type: "depends_on",
      semantic_group: "dependency", scope: "local", status: "current", confidence: null },
  ],
  stats: { node_count: 3, edge_count: 2 }, available_relation_types: ["uses", "depends_on"],
  truncated: false, truncation_reasons: [], snapshot_id: "fixed",
};

function props(value: StructureMapResult | null = map) {
  return { map: value, loading: false, error: "", mode: "relationship" as const, depth: 2,
    selectedNodeId: "A", onMode: vi.fn(), onDepth: vi.fn(), onNode: vi.fn(), onRelation: vi.fn() };
}

describe("Semantic Structure Map", () => {
  it("preserves canonical identity, direction, group and deterministic positions", () => {
    const elements = toStructureElements(map);
    expect(elements).toEqual(toStructureElements(map));
    expect(elements.find((item) => item.data.id === "A")?.classes).toContain("map-selected");
    expect(elements.find((item) => item.data.id === "A")?.classes).toContain("map-selected-path");
    expect(elements.find((item) => item.data.id === "OUT")?.classes).toContain("map-outside");
    expect(elements.find((item) => item.data.id === "R2")?.data).toMatchObject({
      source: "OUT", target: "A", label: "depends_on" });
    expect(elements.find((item) => item.data.id === "R1")?.classes).toBe("map-edge-supply_flow map-edge-selected-path");
    expect(visibleMap(map, "supply_flow").edges.map((edge) => edge.relation_id)).toEqual(["R1"]);
    expect(visibleMap(map, "supply_flow").nodes.map((node) => node.node_id)).toEqual(["A", "B"]);
  });

  it("switches modes and depth, filters, opens canonical nodes and relations, fits and resets", () => {
    const input = props();
    const { container } = render(<SemanticStructureMap {...input} />);
    expect(screen.getByRole("heading", { name: "Semantic Structure Map" })).toBeInTheDocument();
    expect(container.querySelector(".industry-map-index")).toBeInTheDocument();
    expect(container.querySelector(".industry-map-footer")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "关系视图" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: "聚焦视图" }));
    expect(input.onMode).toHaveBeenCalledWith("focus");
    fireEvent.click(screen.getByRole("button", { name: "Supply / Flow" }));
    expect(screen.getByText("2 Nodes · 1 Relations · Depth 1")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "All" }));
    fireEvent.click(screen.getByText("Map Nodes (3)"));
    fireEvent.click(screen.getByRole("button", { name: /Outside · Technology/ }));
    expect(input.onNode).toHaveBeenCalledWith("OUT");
    fireEvent.click(screen.getByText("Recorded Relations (2)"));
    fireEvent.click(screen.getByRole("button", { name: /Outside → Alpha · depends_on/ }));
    expect(screen.getByRole("region", { name: "Selected relation" })).toHaveTextContent("Outside → Alpha");
    expect(screen.getByRole("region", { name: "Selected relation" })).toHaveTextContent("Confidence: Unspecified");
    fireEvent.click(screen.getByRole("button", { name: "Open relation" }));
    expect(input.onRelation).toHaveBeenCalledWith("R2");
    fireEvent.click(screen.getByRole("button", { name: "Fit map view" }));
    expect(cy.fit).toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Reset map view" }));
    expect(cy.destroy).toHaveBeenCalled();
    expect(screen.getByLabelText("Relation legend")).toHaveTextContent("General Association");
  });

  it("announces loading, errors, empty maps, truncation and focus depth", () => {
    const input = props(null);
    const { rerender } = render(<SemanticStructureMap {...input} loading />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading semantic map");
    rerender(<SemanticStructureMap {...input} error="Unavailable" />);
    expect(screen.getByRole("alert")).toHaveTextContent("Unavailable");
    const focus = props({ ...map, nodes: [], edges: [], truncated: true, truncation_reasons: ["max_nodes"] });
    rerender(<SemanticStructureMap {...focus} mode="focus" />);
    expect(screen.getByText("No active canonical Nodes in this map.")).toBeInTheDocument();
    expect(screen.getByText("No current canonical Relations in this map.")).toBeInTheDocument();
    expect(screen.getByText(/Map truncated: max_nodes/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Focus depth"), { target: { value: "3" } });
    expect(focus.onDepth).toHaveBeenCalledWith(3);
  });
});
