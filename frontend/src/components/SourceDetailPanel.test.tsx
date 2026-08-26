import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { SourceDetail } from "../api/types";
import { SourceDetailPanel } from "./SourceDetailPanel";

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

describe("SourceDetailPanel", () => {
  it("renders metadata, linked Nodes and Claims, and supports navigation/back", () => {
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
  });
});
