import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  createNote, getNodeDomainContext, getResearchClaim, getResearchClaims, getResearchCoverage, getResearchHome,
  getResearchNode, getResearchRelation, getResearchSource, getResearchSources, searchResearch,
  updateNote,
} from "../api/research";
import { getSession, loginWorkbench } from "../api/workbench";
import { ResearchExplorer } from "./ResearchExplorer";

vi.mock("../api/research", () => ({
  createNote: vi.fn(), getNodeDomainContext: vi.fn(), getResearchClaim: vi.fn(), getResearchClaims: vi.fn(),
  getResearchCoverage: vi.fn(), getResearchHome: vi.fn(), getResearchNode: vi.fn(),
  getResearchRelation: vi.fn(), getResearchSource: vi.fn(), getResearchSources: vi.fn(),
  searchResearch: vi.fn(), updateNote: vi.fn(),
}));
vi.mock("../api/workbench", async (original) => {
  const actual = await original<typeof import("../api/workbench")>();
  return { ...actual, getSession: vi.fn(), loginWorkbench: vi.fn() };
});
vi.mock("./CurrentViewWorkbench", () => ({
  CurrentViewWorkbench: ({ nodeId, onOpenClaim }: { nodeId: string; onOpenClaim: (id: string) => void }) =>
    <div><span>Current View for {nodeId}</span><button onClick={() => onOpenClaim("CLAIM_VIEW")}>Open View Claim</button></div>,
}));

const emptyImpact = { items: [], snapshot: { snapshot_id: "impact" } };
const home = { stats: { nodes: 2, claims: 2 }, recent_official_views: [], open_gaps: [],
  open_notes: [], impact: emptyImpact };

function nodeData(id: string, name: string) {
  return { node: { node_id: id, canonical_name: name, primary_type: "Company", status: "active", aliases: [] },
    current_view: { view_id: "VIEW_" + id, version: "v1" }, impact: emptyImpact,
    coverage: { sources: 0 }, claims: { items: [], total: 0, limit: 20 }, sources: [], relations: [],
    research_question: null, knowledge_gaps: [], notes: [] };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}

describe("Research Explorer routing and race control", () => {
  beforeEach(() => {
    window.history.replaceState(null, "", "/research");
    vi.clearAllMocks();
    vi.mocked(getSession).mockResolvedValue({ actor: "operator", mode: "DEMO", csrf_token: "csrf" });
    vi.mocked(loginWorkbench).mockResolvedValue({});
    vi.mocked(getResearchHome).mockResolvedValue(home);
    vi.mocked(getResearchClaims).mockResolvedValue({ items: [], total: 0, limit: 25, offset: 0, next_cursor: null, previous_cursor: null });
    vi.mocked(getResearchSources).mockResolvedValue({ items: [], total: 0, limit: 25, offset: 0, next_cursor: null, previous_cursor: null });
    vi.mocked(getResearchCoverage).mockResolvedValue({ summary: { node_coverage: {} }, node_coverage: { items: [], total: 0, limit: 25 }, unlinked_claims: { items: [], total: 0, limit: 25 }, knowledge_gaps: [] });
    vi.mocked(searchResearch).mockResolvedValue({ query: "", results: [] });
    vi.mocked(getNodeDomainContext).mockImplementation(async (id) => ({ node_id: id,
      navigation_contexts: [], operational_domain_assignments: [] }));
  });

  it("loads an exact Claim from a fresh stable URL with evidence, Source, attribution, View and Impact", async () => {
    window.history.replaceState(null, "", "/claim/CLAIM_EXACT");
    vi.mocked(getResearchClaim).mockResolvedValue({
      claim: { claim_id: "CLAIM_EXACT", statement: "Exact recorded evidence", nature: "fact", status: "current",
        fact_time: "2026-05-01", publication_time: "2026-05-02", evidence_excerpt: "Quoted synthetic evidence",
        evidence_pointer: "p.7", source_locator: { locator: "PAGE_7" }, scope: "company" },
      source: { source_id: "SOURCE_EXACT", title: "Exact Source", source_rank: "A", source_type: "filing",
        organization: "Synthetic Org", publication_time: "2026-05-02" },
      linked_nodes: [{ node_id: "NODE_EXACT", canonical_name: "Exact Company", primary_type: "Company", role: "subject" }],
      official_view_citations: [{ view_id: "VIEW_EXACT", node_id: "NODE_EXACT", canonical_name: "Exact Company", version: "v1", view_rank: 1 }],
      claim_relations: [], relation_evidence: [], notes: [], impact: { items: [{ impact_id: "I1", reason_code: "CLAIM_CITED_BY_VIEW",
        official_or_staged: "OFFICIAL", is_current_impact: true, relationship_types: ["OFFICIAL_EVIDENCE"],
        path_steps: [{ object_type: "SOURCE", object_id: "SOURCE_EXACT", label: "Exact Source", status: "stored" },
          { object_type: "CLAIM", object_id: "CLAIM_EXACT", label: "Exact recorded evidence", status: "current" },
          { object_type: "VIEW", object_id: "VIEW_EXACT", label: "v1", status: "official" }] }] },
    });
    render(<ResearchExplorer />);
    expect(await screen.findByRole("heading", { name: "Exact recorded evidence" }, { timeout: 5000 })).toBeInTheDocument();
    expect(screen.getByText("Quoted synthetic evidence")).toBeInTheDocument();
    expect(screen.getAllByText("Exact Source").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Exact Company").length).toBeGreaterThan(0);
    expect(screen.getByText(/current official/)).toBeInTheDocument();
    expect(screen.getByText("CLAIM_CITED_BY_VIEW")).toBeInTheDocument();
    expect(getResearchClaim).toHaveBeenCalledWith("CLAIM_EXACT", expect.any(AbortSignal));
  });

  it("keeps Node B visible when the slower Node A response arrives late", async () => {
    window.history.replaceState(null, "", "/node/NODE_A");
    const slow = deferred<any>();
    vi.mocked(getResearchNode).mockImplementation((id) => id === "NODE_A" ? slow.promise : Promise.resolve(nodeData("NODE_B", "Node B")));
    render(<ResearchExplorer />);
    await waitFor(() => expect(getResearchNode).toHaveBeenCalledWith("NODE_A", expect.any(AbortSignal)));
    act(() => { window.history.pushState(null, "", "/node/NODE_B"); window.dispatchEvent(new PopStateEvent("popstate")); });
    expect(await screen.findByRole("heading", { name: "Node B" })).toBeInTheDocument();
    await act(async () => { slow.resolve(nodeData("NODE_A", "Stale Node A")); await slow.promise; });
    expect(screen.getByRole("heading", { name: "Node B" })).toBeInTheDocument();
    expect(screen.queryByText("Stale Node A")).not.toBeInTheDocument();
  });

  it("opens a Gap follow-up note through its recorded Node route", async () => {
    vi.mocked(getResearchHome).mockResolvedValue({ ...home, open_notes: [{
      note_id: "NOTE_GAP", object_type: "GAP", object_id: "GAP_1", text: "Check newer evidence",
      status: "OPEN", revision: 1, operator: "operator", created_at: "now", updated_at: "now",
      route_kind: "node", route_id: "NODE_GAP",
    }] });
    vi.mocked(getResearchNode).mockResolvedValue(nodeData("NODE_GAP", "Gap Company"));
    render(<ResearchExplorer />);
    fireEvent.click(await screen.findByRole("button", { name: /Check newer evidence/ }));
    expect(await screen.findByRole("heading", { name: "Gap Company" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/node/NODE_GAP");
  });

  it("ignores a stale search response after a rapid query change", async () => {
    const first = deferred<{ query: string; results: any[] }>();
    const second = deferred<{ query: string; results: any[] }>();
    vi.mocked(searchResearch).mockImplementation((q) => q === "first" ? first.promise : second.promise);
    render(<ResearchExplorer />);
    const input = await screen.findByLabelText("Search Nodes, Claims, Sources, Questions and Gaps");
    fireEvent.change(input, { target: { value: "first" } });
    await waitFor(() => expect(searchResearch).toHaveBeenCalledWith("first", "", expect.any(AbortSignal)));
    fireEvent.change(input, { target: { value: "second" } });
    await waitFor(() => expect(searchResearch).toHaveBeenCalledWith("second", "", expect.any(AbortSignal)));
    await act(async () => { second.resolve({ query: "second", results: [{ object_type: "NODE", object_id: "B", label: "Fresh B", subtitle: "Company", status: "active" }] }); await second.promise; });
    expect(await screen.findByText("Fresh B")).toBeInTheDocument();
    await act(async () => { first.resolve({ query: "first", results: [{ object_type: "NODE", object_id: "A", label: "Stale A", subtitle: "Company", status: "active" }] }); await first.promise; });
    expect(screen.getByText("Fresh B")).toBeInTheDocument();
    expect(screen.queryByText("Stale A")).not.toBeInTheDocument();
  });

  it("resets pagination when a Claim filter changes", async () => {
    window.history.replaceState(null, "", "/research/claims?cursor=25");
    render(<ResearchExplorer />);
    await screen.findByRole("heading", { name: "Claims" });
    fireEvent.change(screen.getByLabelText("Text"), { target: { value: "pricing" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply filters" }));
    await waitFor(() => expect(window.location.search).toContain("q=pricing"));
    expect(window.location.search).not.toContain("cursor=");
  });

  it("creates a private note and updates its bounded lifecycle", async () => {
    window.history.replaceState(null, "", "/node/NODE_NOTE");
    vi.mocked(getResearchNode).mockResolvedValue(nodeData("NODE_NOTE", "Notes Company"));
    const saved = { note_id: "NOTE_1", object_type: "NODE", object_id: "NODE_NOTE", text: "Check earnings", status: "OPEN" as const,
      revision: 1, operator: "operator", created_at: "now", updated_at: "now" };
    vi.mocked(createNote).mockResolvedValue({ note: saved });
    vi.mocked(updateNote).mockResolvedValue({ note: { ...saved, status: "DONE", revision: 2 } });
    render(<ResearchExplorer />);
    await screen.findByRole("heading", { name: "Notes Company" });
    fireEvent.change(screen.getByLabelText("Follow-up note"), { target: { value: "Check earnings" } });
    fireEvent.click(screen.getByRole("button", { name: "Add note" }));
    expect(await screen.findByText("Check earnings")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Status for Check earnings"), { target: { value: "DONE" } });
    await waitFor(() => expect(updateNote).toHaveBeenCalled());
    expect(screen.getByLabelText("Status for Check earnings")).toHaveValue("DONE");
  });
});
