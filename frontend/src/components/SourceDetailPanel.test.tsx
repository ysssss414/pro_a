import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getSourceImpactCandidates } from "../api/client";
import type { SourceDetail, SourceImpactCandidatesResult } from "../api/types";
import { SourceDetailPanel } from "./SourceDetailPanel";

vi.mock("../api/client", () => ({ getSourceImpactCandidates: vi.fn() }));

const source: SourceDetail = {
  source_id: "SRC_1",
  title: "Optical Components Report",
  original_name: "optical-report.pdf",
  source_type: "research_report",
  source_rank: "A",
  origin_type: "local_file",
  author: "Analyst One",
  organization: "Research Org",
  publication_time: "2026-01-15",
  ingested_at: "2026-01-16",
  ingestion_mode: "standard",
  analysis_mode: "standard",
  status: "analyzed",
  underlying_source_id: "",
  linked_nodes: [{
    node_id: "NODE_EML",
    canonical_name: "EML",
    primary_type: "Product",
    role: "primary",
    confidence: 0.95,
    link_origin: "existing_node_match",
    derived_from_node_id: "",
    evidence_excerpt: "EML",
  }],
  claims: [{
    claim_id: "CLAIM_1",
    statement: "EML demand is growing.",
    nature: "fact",
    fact_time: "2026-01-10",
    publication_time: "2026-01-15",
    status: "current",
    confidence: 0.9,
    novelty_level: "N1",
    attributed_to: "Research Org",
    scope: "optical",
    evidence_pointer: "p.3",
    evidence_excerpt: "Demand is growing.",
    linked_nodes: [{ node_id: "NODE_EML", canonical_name: "EML", primary_type: "Product", role: "subject" }],
  }],
};

const impactResult: SourceImpactCandidatesResult = {
  source_id: "SRC_1",
  claim_count: 4,
  candidates: [
    {
      node: { node_id: "NODE_ALPHA", canonical_name: "Alpha Product", primary_type: "Product" },
      current_view: { view_id: "VIEW_ALPHA", version: "v_20260201", change_level: "minor", revision_date: "20260201" },
      roles: ["subject", "context"],
      claims: [
        { claim_id: "IMPACT_RAW_ID_1", statement: "Alpha one", status: "current", confidence: 0.9, role: "subject", fact_time: "2026-01-01", publication_time: "2026-01-02" },
        { claim_id: "IMPACT_RAW_ID_2", statement: "Alpha two", status: "current", confidence: 0.8, role: "context", fact_time: "2026-01-03", publication_time: "2026-01-04" },
      ],
    },
    {
      node: { node_id: "NODE_BETA", canonical_name: "Beta Company", primary_type: "Company" },
      current_view: { view_id: "VIEW_BETA", version: "v_20260115", change_level: "initial", revision_date: "20260115" },
      roles: ["related"],
      claims: [
        { claim_id: "IMPACT_RAW_ID_3", statement: "Beta", status: "current", confidence: null, role: "related", fact_time: "", publication_time: "2026-01-15" },
      ],
    },
  ],
  linked_nodes_without_current_view: [{
    node: { node_id: "NODE_GAMMA", canonical_name: "Gamma Product", primary_type: "Product" },
    roles: ["related"],
    claims: [
      { claim_id: "IMPACT_RAW_ID_4", statement: "Gamma", status: "current", confidence: 0.7, role: "related", fact_time: "", publication_time: "2026-01-15" },
    ],
  }],
};

function renderPanel(
  sourceId = "SRC_1",
  onOpenView = vi.fn(),
) {
  const result = render(
    <SourceDetailPanel
      sourceId={sourceId}
      source={source}
      loading={false}
      error={null}
      onBack={vi.fn()}
      onSelectNode={vi.fn()}
      onOpenView={onOpenView}
    />,
  );
  return { ...result, onOpenView };
}

describe("SourceDetailPanel", () => {
  beforeEach(() => {
    vi.mocked(getSourceImpactCandidates).mockReset();
    vi.mocked(getSourceImpactCandidates).mockResolvedValue({
      source_id: "SRC_1",
      claim_count: 1,
      candidates: [],
      linked_nodes_without_current_view: [],
    });
  });

  it("renders metadata, linked Nodes and Claims, and supports navigation/back", async () => {
    const onBack = vi.fn();
    const onSelectNode = vi.fn();
    render(
      <SourceDetailPanel
        sourceId="SRC_1"
        source={source}
        loading={false}
        error={null}
        onBack={onBack}
        onSelectNode={onSelectNode}
        onOpenView={vi.fn()}
      />,
    );

    expect(screen.getByRole("heading", { name: "Optical Components Report" })).toBeInTheDocument();
    expect(screen.getByText("Research Org")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Claims from this Source" })).toBeInTheDocument();
    expect(screen.getByText("EML demand is growing.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "EML Product" }));
    expect(onSelectNode).toHaveBeenCalledWith("NODE_EML");
    fireEvent.click(screen.getByRole("button", { name: "← Back to Node" }));
    expect(onBack).toHaveBeenCalledTimes(1);
    expect(await screen.findByText("No directly linked Current Views")).toBeInTheDocument();
  });

  it("renders deduplicated candidates, aggregate counts, roles, and no-View Nodes", async () => {
    vi.mocked(getSourceImpactCandidates).mockResolvedValue(impactResult);
    const onOpenView = vi.fn();
    renderPanel("SRC_1", onOpenView);

    expect(await screen.findByText("2 Views to review")).toBeInTheDocument();
    expect(screen.getByText("Alpha Product")).toBeInTheDocument();
    expect(screen.getByText("Beta Company")).toBeInTheDocument();
    expect(screen.getByText("2 linked Claims")).toBeInTheDocument();
    expect(screen.getAllByText("Attribution role: subject")).toHaveLength(1);
    expect(screen.getByText("Attribution role: context")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Linked Nodes without Current View" })).toBeInTheDocument();
    expect(screen.getByText("Gamma Product")).toBeInTheDocument();
    expect(screen.queryByText("IMPACT_RAW_ID_1")).not.toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Open View" })[0]);
    expect(onOpenView).toHaveBeenCalledWith("NODE_ALPHA");
  });

  it("keeps Source Detail usable when impact discovery fails", async () => {
    vi.mocked(getSourceImpactCandidates).mockRejectedValue(new Error("unavailable"));
    renderPanel();

    expect(await screen.findByText("Unable to load direct Current View candidates.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Optical Components Report" })).toBeInTheDocument();
    expect(screen.getByText("EML demand is growing.")).toBeInTheDocument();
  });

  it("clears stale impact state when switching Sources", async () => {
    let resolveFirst!: (value: SourceImpactCandidatesResult) => void;
    const firstRequest = new Promise<SourceImpactCandidatesResult>((resolve) => {
      resolveFirst = resolve;
    });
    const secondResult: SourceImpactCandidatesResult = {
      source_id: "SRC_2",
      claim_count: 1,
      candidates: [{ ...impactResult.candidates[1] }],
      linked_nodes_without_current_view: [],
    };
    vi.mocked(getSourceImpactCandidates).mockImplementation((sourceId) => (
      sourceId === "SRC_1" ? firstRequest : Promise.resolve(secondResult)
    ));

    const { rerender } = renderPanel("SRC_1");
    rerender(
      <SourceDetailPanel
        sourceId="SRC_2"
        source={{ ...source, source_id: "SRC_2", title: "Second Source" }}
        loading={false}
        error={null}
        onBack={vi.fn()}
        onSelectNode={vi.fn()}
        onOpenView={vi.fn()}
      />,
    );
    expect(await screen.findByText("Beta Company")).toBeInTheDocument();

    await act(async () => {
      resolveFirst(impactResult);
      await firstRequest;
    });
    expect(screen.queryByText("Alpha Product")).not.toBeInTheDocument();
    expect(screen.getByText("Beta Company")).toBeInTheDocument();
  });
});
