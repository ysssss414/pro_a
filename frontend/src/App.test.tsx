import { StrictMode } from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  getClaims,
  getCurrentView,
  getCurrentViewHistory,
  getHealth,
  getKnowledgeGaps,
  getNeighbors,
  getNode,
  getResearchQuestion,
  getSourceDetail,
  getSourceImpactCandidates,
  getSources,
  getStats,
  getViewProposals,
} from "./api/client";
import type {
  CurrentViewHistoryResult,
  CurrentViewResult,
  NodeDetail,
  SourceDetail,
} from "./api/types";
import App from "./App";

vi.mock("./api/client", () => ({
  getClaims: vi.fn(),
  getCurrentView: vi.fn(),
  getCurrentViewCompare: vi.fn(),
  getCurrentViewHistory: vi.fn(),
  getHealth: vi.fn(),
  getKnowledgeGaps: vi.fn(),
  getNeighbors: vi.fn(),
  getNode: vi.fn(),
  getResearchQuestion: vi.fn(),
  getSourceDetail: vi.fn(),
  getSourceImpactCandidates: vi.fn(),
  getSources: vi.fn(),
  getStats: vi.fn(),
  getViewProposals: vi.fn(),
  getViewProposal: vi.fn(),
  searchNodes: vi.fn(),
}));

describe("App error boundary", () => {
  beforeEach(() => {
    window.history.replaceState(null, "", "/");
    const unavailable = new TypeError("Failed to fetch");
    vi.mocked(getHealth).mockRejectedValue(unavailable);
    vi.mocked(getStats).mockRejectedValue(unavailable);
    vi.mocked(getNode).mockRejectedValue(unavailable);
    vi.mocked(getNeighbors).mockRejectedValue(unavailable);
    vi.mocked(getClaims).mockRejectedValue(unavailable);
    vi.mocked(getCurrentViewHistory).mockRejectedValue(unavailable);
    vi.mocked(getCurrentView).mockRejectedValue(unavailable);
    vi.mocked(getKnowledgeGaps).mockRejectedValue(unavailable);
    vi.mocked(getResearchQuestion).mockRejectedValue(unavailable);
    vi.mocked(getSourceDetail).mockRejectedValue(unavailable);
    vi.mocked(getSourceImpactCandidates).mockRejectedValue(unavailable);
    vi.mocked(getSources).mockRejectedValue(unavailable);
  });

  it("renders a useful unavailable state instead of a white screen", async () => {
    render(<App />);
    expect(await screen.findByText("Knowledge API unavailable.")).toBeInTheDocument();
    expect(screen.getByText("Start the local pro_a API and retry.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(screen.getByText("Search for a node to start exploring.")).toBeInTheDocument();
  });

  it("opens the read-only Human View Proposal surface", async () => {
    vi.mocked(getViewProposals).mockResolvedValue([]);
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Human View Proposals" }));
    expect(await screen.findByText("No pending Human View Proposals")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Explorer" }));
    expect(screen.getByText("Search for a node to start exploring.")).toBeInTheDocument();
  });

  it("restores a selected node from the URL in StrictMode", async () => {
    window.history.replaceState(null, "", "/?node=NODE_EML");
    vi.mocked(getHealth).mockResolvedValue({ status: "ok" });
    vi.mocked(getStats).mockResolvedValue({
      active_node_count: 1,
      alias_count: 1,
      current_relation_count: 0,
      current_part_of_count: 0,
      source_count: 0,
      claim_count: 0,
      current_view_count: 0,
      open_knowledge_gap_count: 0,
      open_research_question_count: 0,
    });
    vi.mocked(getNode).mockResolvedValue({
      node_id: "NODE_EML",
      canonical_name: "EML",
      primary_type: "Product",
      description: "高速光芯片技术",
      status: "active",
      aliases: ["Electro-Absorption Modulated Laser"],
      parents: [],
      children: [],
      incoming_relations: [],
      outgoing_relations: [],
    });
    vi.mocked(getNeighbors).mockResolvedValue({
      center: { node_id: "NODE_EML", canonical_name: "EML", primary_type: "Product" },
      nodes: [{ node_id: "NODE_EML", canonical_name: "EML", primary_type: "Product" }],
      edges: [],
    });
    vi.mocked(getClaims).mockResolvedValue([]);
    vi.mocked(getSources).mockResolvedValue([]);
    vi.mocked(getCurrentViewHistory).mockResolvedValue({ node_id: "NODE_EML", views: [] });
    vi.mocked(getResearchQuestion).mockResolvedValue(null);
    vi.mocked(getKnowledgeGaps).mockResolvedValue([]);

    render(
      <StrictMode>
        <App />
      </StrictMode>,
    );

    expect(await screen.findByRole("heading", { name: "EML" })).toBeInTheDocument();
    expect(getNode).toHaveBeenCalledTimes(2);
  });

  it("keeps the selected Node usable when the Research endpoint fails", async () => {
    window.history.replaceState(null, "", "/?node=NODE_EML");
    vi.mocked(getHealth).mockResolvedValue({ status: "ok" });
    vi.mocked(getStats).mockResolvedValue({
      active_node_count: 1,
      alias_count: 0,
      current_relation_count: 0,
      current_part_of_count: 0,
      source_count: 0,
      claim_count: 0,
      current_view_count: 0,
      open_knowledge_gap_count: 0,
      open_research_question_count: 0,
    });
    vi.mocked(getNode).mockResolvedValue({
      node_id: "NODE_EML",
      canonical_name: "EML",
      primary_type: "Product",
      description: "Still visible.",
      status: "active",
      aliases: [],
      parents: [],
      children: [],
      incoming_relations: [],
      outgoing_relations: [],
    });
    vi.mocked(getNeighbors).mockResolvedValue({
      center: { node_id: "NODE_EML", canonical_name: "EML", primary_type: "Product" },
      nodes: [],
      edges: [],
    });
    vi.mocked(getClaims).mockResolvedValue([]);
    vi.mocked(getSources).mockResolvedValue([]);
    vi.mocked(getCurrentViewHistory).mockResolvedValue({ node_id: "NODE_EML", views: [] });
    vi.mocked(getResearchQuestion).mockRejectedValue(new Error("research unavailable"));
    vi.mocked(getKnowledgeGaps).mockResolvedValue([]);

    render(<App />);

    expect(await screen.findByRole("heading", { name: "EML" })).toBeInTheDocument();
    expect(screen.getByText("Still visible.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "Research" }));
    expect(await screen.findByText("Unable to load Research Question.")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Overview" })).toBeInTheDocument();
  });

  it("ignores a stale Current View history response after switching Nodes", async () => {
    window.history.replaceState(null, "", "/?node=NODE_A");
    vi.mocked(getHealth).mockResolvedValue({ status: "ok" });
    vi.mocked(getStats).mockResolvedValue({
      active_node_count: 2,
      alias_count: 0,
      current_relation_count: 0,
      current_part_of_count: 0,
      source_count: 0,
      claim_count: 0,
      current_view_count: 2,
      open_knowledge_gap_count: 0,
      open_research_question_count: 0,
    });
    const nodeA: NodeDetail = {
      node_id: "NODE_A",
      canonical_name: "Node A",
      primary_type: "Product",
      description: "First Node",
      status: "active",
      aliases: [],
      parents: [{ node_id: "NODE_B", canonical_name: "Node B", primary_type: "Product" }],
      children: [],
      incoming_relations: [],
      outgoing_relations: [],
    };
    const nodeB: NodeDetail = {
      ...nodeA,
      node_id: "NODE_B",
      canonical_name: "Node B",
      description: "Second Node",
      parents: [],
    };
    vi.mocked(getNode).mockImplementation(async (nodeId) => nodeId === "NODE_A" ? nodeA : nodeB);
    vi.mocked(getNeighbors).mockImplementation(async (nodeId) => ({
      center: nodeId === "NODE_A"
        ? { node_id: "NODE_A", canonical_name: "Node A", primary_type: "Product" }
        : { node_id: "NODE_B", canonical_name: "Node B", primary_type: "Product" },
      nodes: [],
      edges: [],
    }));
    vi.mocked(getClaims).mockResolvedValue([]);
    vi.mocked(getSources).mockResolvedValue([]);
    vi.mocked(getResearchQuestion).mockResolvedValue(null);
    vi.mocked(getKnowledgeGaps).mockResolvedValue([]);

    const viewB: CurrentViewResult = {
      view_id: "VIEW_B",
      node_id: "NODE_B",
      version: "v_20260401",
      status: "official",
      change_level: "initial",
      previous_view_id: null,
      content_md: "Node B view",
      content_json: { one_line_conclusion: "Node B Current View." },
      trigger_source_id: null,
      trigger_claim_ids: [],
      revision_date: "20260401",
      revision_seq: 0,
      accepted_proposal_id: "PROP_B",
      created_at: "2026-04-01",
      confirmed_at: "2026-04-01",
    };
    let resolveStaleHistory!: (value: CurrentViewHistoryResult) => void;
    const staleHistory = new Promise<CurrentViewHistoryResult>((resolve) => {
      resolveStaleHistory = resolve;
    });
    vi.mocked(getCurrentViewHistory).mockImplementation((nodeId) => (
      nodeId === "NODE_A"
        ? staleHistory
        : Promise.resolve({ node_id: "NODE_B", views: [viewB] })
    ));

    render(<App />);
    expect(await screen.findByRole("heading", { name: "Node A" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Node B/ }));
    expect(await screen.findByRole("heading", { name: "Node B" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "View" }));
    expect(await screen.findByText("Node B Current View.")).toBeInTheDocument();

    await act(async () => {
      resolveStaleHistory({
        node_id: "NODE_A",
        views: [{ ...viewB, view_id: "VIEW_A", node_id: "NODE_A", content_json: { one_line_conclusion: "Stale Node A View." } }],
      });
      await staleHistory;
    });
    expect(screen.getByText("Node B Current View.")).toBeInTheDocument();
    expect(screen.queryByText("Stale Node A View.")).not.toBeInTheDocument();
  });

  it("opens a discovered candidate directly in its existing View tab", async () => {
    window.history.replaceState(null, "", "/?node=NODE_SOURCE");
    vi.mocked(getHealth).mockResolvedValue({ status: "ok" });
    vi.mocked(getStats).mockResolvedValue({
      active_node_count: 2,
      alias_count: 0,
      current_relation_count: 0,
      current_part_of_count: 0,
      source_count: 1,
      claim_count: 1,
      current_view_count: 1,
      open_knowledge_gap_count: 0,
      open_research_question_count: 0,
    });
    const sourceNode: NodeDetail = {
      node_id: "NODE_SOURCE",
      canonical_name: "Source Node",
      primary_type: "Product",
      description: "Starting Node",
      status: "active",
      aliases: [],
      parents: [],
      children: [],
      incoming_relations: [],
      outgoing_relations: [],
    };
    const candidateNode: NodeDetail = {
      ...sourceNode,
      node_id: "NODE_CANDIDATE",
      canonical_name: "Candidate Node",
      description: "Direct candidate",
    };
    vi.mocked(getNode).mockImplementation(async (nodeId) => (
      nodeId === "NODE_SOURCE" ? sourceNode : candidateNode
    ));
    vi.mocked(getNeighbors).mockImplementation(async (nodeId) => ({
      center: nodeId === "NODE_SOURCE"
        ? { node_id: "NODE_SOURCE", canonical_name: "Source Node", primary_type: "Product" }
        : { node_id: "NODE_CANDIDATE", canonical_name: "Candidate Node", primary_type: "Product" },
      nodes: [],
      edges: [],
    }));
    vi.mocked(getClaims).mockResolvedValue([]);
    vi.mocked(getResearchQuestion).mockResolvedValue(null);
    vi.mocked(getKnowledgeGaps).mockResolvedValue([]);
    vi.mocked(getSources).mockImplementation(async (nodeId) => nodeId === "NODE_SOURCE" ? [{
      source_id: "SRC_IMPACT",
      title: "Impact Source",
      original_name: "impact.md",
      author: "Analyst",
      organization: "Research Org",
      publication_time: "2026-02-01",
      source_type: "research_report",
      source_rank: "A",
      provenance: [{
        origin_path: "claim",
        role: "subject",
        link_origin: "claim",
        evidence_excerpt: "Direct evidence",
        claim_id: "CLAIM_IMPACT",
      }],
    }] : []);
    const candidateView: CurrentViewResult = {
      view_id: "VIEW_CANDIDATE",
      node_id: "NODE_CANDIDATE",
      version: "v_20260201",
      status: "official",
      change_level: "initial",
      previous_view_id: null,
      content_md: "Candidate View",
      content_json: { one_line_conclusion: "Candidate Current View conclusion." },
      trigger_source_id: null,
      trigger_claim_ids: [],
      revision_date: "20260201",
      revision_seq: 0,
      accepted_proposal_id: "PROP_CANDIDATE",
      created_at: "2026-02-01",
      confirmed_at: "2026-02-01",
    };
    vi.mocked(getCurrentViewHistory).mockImplementation(async (nodeId) => ({
      node_id: nodeId,
      views: nodeId === "NODE_CANDIDATE" ? [candidateView] : [],
    }));
    const sourceDetail: SourceDetail = {
      source_id: "SRC_IMPACT",
      title: "Impact Source",
      original_name: "impact.md",
      source_type: "research_report",
      source_rank: "A",
      origin_type: "local_file",
      author: "Analyst",
      organization: "Research Org",
      publication_time: "2026-02-01",
      ingested_at: "2026-02-02",
      ingestion_mode: "standard",
      analysis_mode: "standard",
      status: "analyzed",
      underlying_source_id: "",
      linked_nodes: [],
      claims: [],
    };
    vi.mocked(getSourceDetail).mockResolvedValue(sourceDetail);
    vi.mocked(getSourceImpactCandidates).mockResolvedValue({
      source_id: "SRC_IMPACT",
      claim_count: 1,
      candidates: [{
        node: { node_id: "NODE_CANDIDATE", canonical_name: "Candidate Node", primary_type: "Product" },
        current_view: { view_id: "VIEW_CANDIDATE", version: "v_20260201", change_level: "initial", revision_date: "20260201" },
        roles: ["subject"],
        claims: [{
          claim_id: "CLAIM_IMPACT",
          statement: "Direct evidence",
          status: "current",
          confidence: 0.9,
          role: "subject",
          fact_time: "2026-01-31",
          publication_time: "2026-02-01",
        }],
      }],
      linked_nodes_without_current_view: [],
    });

    render(<App />);
    expect(await screen.findByRole("heading", { name: "Source Node" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: /^Sources/ }));
    fireEvent.click(await screen.findByRole("button", { name: "Open Source" }));
    fireEvent.click(await screen.findByRole("button", { name: "Open View" }));

    expect(await screen.findByText("Candidate Current View conclusion.")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "View" })).toHaveAttribute("aria-selected", "true");
    expect(new URLSearchParams(window.location.search).get("node")).toBe("NODE_CANDIDATE");
  });
});
