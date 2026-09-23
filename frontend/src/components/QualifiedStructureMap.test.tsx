import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { getQualifiedRelation, type QualifiedMapResult } from "../api/research";
import { QualifiedStructureMap } from "./QualifiedStructureMap";

const cy = vi.hoisted(() => ({ fit: vi.fn(), resize: vi.fn(), destroy: vi.fn(),
  on: vi.fn(), callbacks: {} as Record<string, (event: any) => void> }));
vi.mock("cytoscape", () => ({ default: vi.fn((options) => {
  cy.callbacks = {};
  cy.on.mockImplementation((event, selector, callback) => { cy.callbacks[`${event}:${selector}`] = callback; });
  cy.fit.mockClear();
  return { ...cy, options };
}) }));
vi.mock("../api/research", () => ({ getQualifiedRelation: vi.fn() }));

const map: QualifiedMapResult = {
  domain_id: "semiconductor", display_name: "Semiconductor", mode: "relationship",
  selected_visual_id: "qualified-stage2:SC-CN-0034", selected_node_id: null,
  selected_qualified_id: "SC-CN-0034", depth: 1, truncated: false, truncation_reasons: [],
  omitted_reference_hierarchy_relations: 0,
  stats: { canonical_nodes: 1, qualified_nodes: 1, endpoint_references: 1,
    canonical_relations: 0, qualified_relations: 1 },
  nodes: [
    { visual_id: "qualified-stage2:SC-CN-0034", knowledge_state: "qualified_identity",
      canonical_node_id: null, qualified_candidate_id: "SC-CN-0034", endpoint_reference_id: null,
      display_name: "Czochralski Crystal Growth", primary_type: "Technology",
      distance: 0, selected: true, in_navigation_context: false, qualification_stage: "Stage 2" },
    { visual_id: "endpoint-ref:SC-CN-0024", knowledge_state: "relation_endpoint_reference",
      canonical_node_id: null, qualified_candidate_id: null, endpoint_reference_id: "SC-CN-0024",
      display_name: "Silicon Ingot", primary_type: "Unqualified reference",
      distance: 1, selected: false, in_navigation_context: false },
    { visual_id: "canonical:N", knowledge_state: "canonical",
      canonical_node_id: "N", qualified_candidate_id: null, endpoint_reference_id: null,
      display_name: "Existing", primary_type: "Product",
      distance: 1, selected: false, in_navigation_context: true },
  ],
  edges: [{ visual_id: "qualified:SC-RL-0027", knowledge_state: "qualified_relation",
    canonical_relation_id: null, qualified_relation_id: "SC-RL-0027",
    from_visual_id: "qualified-stage2:SC-CN-0034", to_visual_id: "endpoint-ref:SC-CN-0024",
    relation_type: "uses", semantic_group: "supply_flow", scope: "Frozen scope",
    from_endpoint_authority: "stage2_human_identity", to_endpoint_authority: "relation_scoped_reference" }],
};

describe("Qualified Structure Map", () => {
  it("separates canonical, qualified and reference styles and forbids reference selection", async () => {
    vi.mocked(getQualifiedRelation).mockResolvedValue({ evidence: [{ evidence_id: "EV1",
      source_title: "Source", section: "Section", pdf_page: 1 }] });
    const onCanonical = vi.fn();
    const onQualified = vi.fn();
    const { container } = render(<QualifiedStructureMap map={map} loading={false} error="" mode="relationship" depth={2}
      hasSelection onMode={vi.fn()} onDepth={vi.fn()} onCanonical={onCanonical}
      onQualified={onQualified} onCanonicalRelation={vi.fn()} />);
    expect(container.querySelector(".industry-map-footer")).toBeInTheDocument();
    expect(screen.getByLabelText("Knowledge state legend")).toHaveTextContent("Endpoint Reference");
    expect(screen.getByLabelText("Knowledge state legend")).toHaveTextContent("Qualified Identity");
    await act(async () => cy.callbacks["tap:node"]({ target: { id: () => "endpoint-ref:SC-CN-0024" } }));
    expect(screen.getByRole("region", { name: "Endpoint Reference detail" })).toHaveTextContent("Identity qualified: No");
    expect(onQualified).not.toHaveBeenCalled();
    await act(async () => cy.callbacks["tap:node"]({ target: { id: () => "qualified-stage2:SC-CN-0034" } }));
    expect(onQualified).toHaveBeenCalledWith("SC-CN-0034");
    await act(async () => cy.callbacks["tap:node"]({ target: { id: () => "canonical:N" } }));
    expect(onCanonical).toHaveBeenCalledWith("N");
    await act(async () => cy.callbacks["tap:edge"]({ target: { id: () => "qualified:SC-RL-0027" } }));
    expect(screen.getByRole("region", { name: "Selected relation" })).toHaveTextContent("relation_scoped_reference");
    expect(screen.queryByRole("button", { name: "Open canonical relation" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Fit view" }));
    expect(cy.fit).toHaveBeenCalled();
  });
});
