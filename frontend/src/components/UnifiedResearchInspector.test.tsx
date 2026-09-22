import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { UnifiedResearchInspector } from "./UnifiedResearchInspector";
import type { InspectorData } from "./inspectorSelection";

vi.mock("./CurrentViewWorkbench", () => ({ CurrentViewWorkbench: ({ nodeId }: { nodeId: string }) =>
  <p>Workbench for {nodeId}</p> }));

function data(): InspectorData {
  const claims = Array.from({ length: 4 }, (_, index) => ({ claim_id: `C${index}`, statement: `Recorded claim ${index}`,
    business_date: `2026-09-0${index + 1}`, status: "current", source_id: "S1", source_title: "Recorded source",
    evidence_excerpt: `Exact excerpt ${index}`, linked_nodes: [{ node_id: "N", role: "subject" }] }));
  return { node: { node_id: "N", canonical_name: "HBM", primary_type: "Product", status: "active", aliases: ["High Bandwidth Memory"] },
    current_view: { version: "v2", change_level: "minor", revision_date: "2026-09-01", trigger_claim_ids: ["C0"],
      content_json: { one_line_conclusion: "Recorded conclusion", core_logic: ["Recorded logic"], recent_change: "Recorded update" } },
    claims: { items: claims, total: 5, limit: 20 },
    sources: [{ source_id: "S1", title: "Recorded source", source_type: "filing", source_rank: "A",
      publication_time: "2026-09-01", organization: "Recorded Org" }],
    relations: [{ relation_id: "R1", from_name: "HBM", to_name: "Memory", relation_type: "part_of", status: "current", evidence_count: 1 }],
    research_question: { question: "Recorded question?", current_answer: "Recorded answer", status: "open", confidence: 0.7,
      key_variables: ["Capacity"] },
    knowledge_gaps: [{ gap_id: "G1", title: "Open item", status: "open", freshness_due: "2026-10-01" },
      { gap_id: "G2", title: "Resolved item", status: "resolved" }],
    impact: { items: [{ impact_id: "I1", reason_code: "RECORDED_PATH", official_or_staged: "OFFICIAL",
      relationship_types: ["part_of"], path_steps: [{ object_type: "NODE", object_id: "N2", label: "Memory", status: "active" }] }] },
    notes: [], coverage: { knowledge_level: "LEVEL_4_RESEARCH_ACTIVE", claims: 5, sources: 1, official_views: 1, questions: 1, gaps: 2 } };
}

const context = { node_id: "N", navigation_contexts: [{ domain_id: "ai_hardware", display_name: "AI Hardware",
  root_node_id: "ROOT", path_from_root: ["ROOT", "N"], depth: 1 }],
  operational_domain_assignments: [{ primary_domain: "operations_only", revision: 1 }] };

describe("Unified Research Inspector", () => {
  it("renders recorded summary sections and exact drill-down actions, with workbench collapsed", async () => {
    const navigate = vi.fn();
    render(<UnifiedResearchInspector data={data()} domainContext={context} navigate={navigate}
      notesSection={<section aria-label="Follow-up Notes">private · noncanonical</section>} />);
    expect(screen.getByRole("heading", { name: "HBM" })).toBeInTheDocument();
    expect(screen.getByText("Canonical Production Node")).toBeInTheDocument();
    expect(screen.getByText("AI Hardware")).toBeInTheDocument();
    expect(screen.getByText("operations_only")).toBeInTheDocument();
    expect(screen.getByText("Recorded conclusion")).toBeInTheDocument();
    expect(screen.getByText("Recorded update", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("Official View evidence")).toBeInTheDocument();
    expect(screen.getByText("Exact excerpt 3")).toBeInTheDocument();
    expect(screen.getByText("RECORDED_PATH")).toBeInTheDocument();
    expect(screen.getByText("Open item")).toBeInTheDocument();
    expect(screen.queryByText("Resolved item")).not.toBeInTheDocument();
    expect(screen.getByText("Recorded question?")).toBeInTheDocument();
    expect(screen.getByText("Recorded Org", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("LEVEL_4_RESEARCH_ACTIVE")).toBeInTheDocument();
    expect(screen.getByLabelText("Follow-up Notes")).toHaveTextContent("private · noncanonical");
    expect(screen.queryByText("Workbench for N")).not.toBeInTheDocument();

    const claims = screen.getByRole("region", { name: "Key Claims" });
    expect(within(claims).getAllByRole("button", { name: "Open Claim" })).toHaveLength(3);
    fireEvent.click(within(claims).getByRole("button", { name: "Show all 4 Claims" }));
    expect(within(claims).getAllByRole("button", { name: "Open Claim" })).toHaveLength(4);
    fireEvent.click(within(claims).getByRole("button", { name: "Show less Claims" }));
    fireEvent.click(within(claims).getAllByRole("button", { name: "Open Claim" })[0]);
    expect(navigate).toHaveBeenCalledWith({ kind: "claim", id: "C0" }, { from_node: "N" });
    fireEvent.click(within(screen.getByRole("region", { name: "Related Sources" })).getByRole("button", { name: "Open Source" }));
    expect(navigate).toHaveBeenCalledWith({ kind: "source", id: "S1" }, { from_node: "N" });
    fireEvent.click(within(screen.getByRole("region", { name: "Relations" })).getByRole("button", { name: "Open Relation" }));
    expect(navigate).toHaveBeenCalledWith({ kind: "relation", id: "R1" }, { from_node: "N" });
    fireEvent.click(screen.getByText("Open Current View details / Workbench"));
    expect(await screen.findByText("Workbench for N")).toBeInTheDocument();
  });

  it("renders sparse canonical research without synthetic claims or conclusions", () => {
    const sparse = data(); sparse.current_view = null; sparse.claims = { items: [], total: 0, limit: 20 };
    sparse.sources = []; sparse.relations = []; sparse.research_question = null; sparse.knowledge_gaps = [];
    sparse.impact.items = []; sparse.coverage = { knowledge_level: "LEVEL_0_STRUCTURE_ONLY", sources: 0 };
    render(<UnifiedResearchInspector data={sparse} domainContext={{ ...context, navigation_contexts: [], operational_domain_assignments: [] }}
      navigate={vi.fn()} notesSection={<section>private · noncanonical</section>} />);
    for (const message of ["No navigation context recorded.", "None recorded", "No official Current View.",
      "No explicit Claims linked.", "No recent Evidence available.", "No recorded Direct Impact paths.",
      "No open Knowledge Gaps.", "No Research Question.", "No linked Sources.", "No recorded Relations."]) {
      expect(screen.getByText(message)).toBeInTheDocument();
    }
  });

  it("marks a full bounded Source page without claiming it contains every Source", () => {
    const bounded = data();
    bounded.sources = Array.from({ length: 20 }, (_, index) => ({ ...bounded.sources[0], source_id: `S${index}` }));
    bounded.coverage.sources = 20;
    render(<UnifiedResearchInspector data={bounded} domainContext={context} navigate={vi.fn()} notesSection={<section>Notes</section>} />);
    expect(within(screen.getByRole("region", { name: "Related Sources" })).getByText("Showing 5 of at least 20 (bounded)")).toBeInTheDocument();
    expect(screen.getByText(/20\+ Sources/)).toBeInTheDocument();
  });

  it("announces standalone context loading and fetch errors", async () => {
    const mock = vi.spyOn(await import("../api/research"), "getNodeDomainContext");
    mock.mockRejectedValueOnce(new Error("context unavailable"));
    render(<UnifiedResearchInspector data={data()} navigate={vi.fn()} notesSection={<section>Notes</section>} />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading navigation context");
    expect(await screen.findByRole("alert")).toHaveTextContent("context unavailable");
    mock.mockRestore();
  });
});
