import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ClaimResult, NodeDetail, NodeSource } from "../api/types";
import { NodeDetailPanel, type DetailTab } from "./NodeDetailPanel";

const detail: NodeDetail = {
  node_id: "NODE_EML",
  canonical_name: "EML",
  primary_type: "Product",
  description: "Electro-absorption modulated laser.",
  status: "active",
  aliases: ["电吸收调制激光器"],
  parents: [{ node_id: "NODE_PARENT", canonical_name: "Optical Components", primary_type: "Segment" }],
  children: [{ node_id: "NODE_CHILD", canonical_name: "EML Chip", primary_type: "Product" }],
  incoming_relations: [],
  outgoing_relations: [{
    relation_id: "REL_PART",
    from_node_id: "NODE_EML",
    relation_type: "part_of",
    to_node_id: "NODE_PARENT",
    scope: "",
    status: "current",
    confidence: 1,
    from_canonical_name: "EML",
    to_canonical_name: "Optical Components",
  }],
};

const claims: ClaimResult[] = [{
  claim_id: "CLAIM_1",
  link_role: "subject",
  statement: "EML is used in high-speed optical transmitters.",
  nature: "fact",
  fact_time: "2026-01-10",
  publication_time: "2026-01-15",
  status: "current",
  confidence: 0.9,
  novelty_level: "N1",
  attributed_to: "Research Org",
  scope: "optical transmitters",
  evidence_pointer: "p.3",
  source_locator: { status: "resolved", locator: "PAGE:3" },
  evidence_excerpt: "EML is used in high-speed optical transmitters.",
  source_id: "SRC_1",
  source: {
    source_id: "SRC_1",
    title: "Optical Components Report",
    original_name: "optical-report.pdf",
    author: "Analyst One",
    organization: "Research Org",
    publication_time: "2026-01-15",
    source_type: "research_report",
    source_rank: "A",
  },
}];

const sources: NodeSource[] = [{
  ...claims[0].source,
  provenance: [
    {
      origin_path: "direct",
      role: "primary",
      link_origin: "existing_node_match",
      evidence_excerpt: "EML",
      claim_id: null,
    },
    {
      origin_path: "claim",
      role: "subject",
      link_origin: "claim",
      evidence_excerpt: "EML is used in high-speed optical transmitters.",
      claim_id: "CLAIM_1",
    },
  ],
}];

function renderPanel(activeTab: DetailTab, onSelect = vi.fn(), onOpenSource = vi.fn()) {
  render(
    <NodeDetailPanel
      selectedNodeId="NODE_EML"
      detail={detail}
      claims={claims}
      sources={sources}
      currentViews={[]}
      researchQuestion={null}
      knowledgeGaps={[]}
      activeTab={activeTab}
      loading={false}
      knowledgeLoading={false}
      error={null}
      knowledgeErrors={{ claims: null, sources: null, view: null, research: null, gaps: null }}
      selectedSourceId={null}
      sourceDetail={null}
      sourceLoading={false}
      sourceError={null}
      onTabChange={vi.fn()}
      onSelect={onSelect}
      onOpenView={vi.fn()}
      onOpenSource={onOpenSource}
      onCloseSource={vi.fn()}
    />,
  );
  return { onSelect, onOpenSource };
}

describe("NodeDetailPanel", () => {
  it("renders aliases and navigable parent/child hierarchy", () => {
    const { onSelect } = renderPanel("overview");
    expect(screen.getByText("电吸收调制激光器")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Optical Components/ }));
    fireEvent.click(screen.getByRole("button", { name: /EML Chip/ }));
    expect(onSelect).toHaveBeenNthCalledWith(1, "NODE_PARENT");
    expect(onSelect).toHaveBeenNthCalledWith(2, "NODE_CHILD");
  });

  it("renders Claim, exact Evidence, and Source metadata", () => {
    renderPanel("claims");
    expect(screen.getByText("Subject")).toBeInTheDocument();
    expect(screen.getByText("Source locator: Page 3")).toBeInTheDocument();
    expect(screen.getByText("p.3")).toBeInTheDocument();
    expect(screen.getByText("EML is used in high-speed optical transmitters.", { selector: "h3" })).toBeInTheDocument();
    expect(screen.getByText("EML is used in high-speed optical transmitters.", { selector: "blockquote" })).toBeInTheDocument();
    expect(screen.getByText("Optical Components Report")).toBeInTheDocument();
    expect(screen.getByText(/Research Org · 2026-01-15 · Rank A/)).toBeInTheDocument();
  });

  it("renders one Source card with direct and Claim provenance", () => {
    const { onOpenSource } = renderPanel("sources");
    expect(screen.getAllByTestId("source-card")).toHaveLength(1);
    expect(screen.getByText("Direct node link")).toBeInTheDocument();
    expect(screen.getByText("Via Claim")).toBeInTheDocument();
    expect(screen.getByText("CLAIM_1")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open Source" }));
    expect(onOpenSource).toHaveBeenCalledWith("SRC_1");
  });
});
